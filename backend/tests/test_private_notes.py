"""Tests for /api/private/notes CRUD plus tree builder."""
import sqlite3
from unittest.mock import MagicMock, patch

import pytest


def _make_app(monkeypatch, tmp_path):
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("UPLOADS_PATH", str(tmp_path / "uploads"))
    with patch("app.services.qdrant_service.QdrantClient") as MockQdrant:
        MockQdrant.return_value.get_collection.return_value = MagicMock()
        from app import create_app
        return create_app({"TESTING": True})


def _seed_note(
    db_path: str,
    *,
    note_id: str,
    title: str,
    directory: str = "",
    content: str = "body",
    chat_ref: str | None = None,
    user_id: str = "default",
    created_at: str | None = None,
) -> None:
    conn = sqlite3.connect(db_path)
    try:
        if created_at:
            conn.execute(
                "INSERT INTO notes (id, user_id, title, directory, content, chat_ref, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (note_id, user_id, title, directory, content, chat_ref, created_at, created_at),
            )
        else:
            conn.execute(
                "INSERT INTO notes (id, user_id, title, directory, content, chat_ref)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (note_id, user_id, title, directory, content, chat_ref),
            )
        conn.commit()
    finally:
        conn.close()


class TestListNotes:
    def test_empty_db_returns_empty_structure(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with app.test_client() as client:
            resp = client.get("/api/private/notes")
        assert resp.status_code == 200
        assert resp.get_json() == {"notes": [], "tree": {}}

    def test_returns_flat_list_and_tree(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        db_path = str(tmp_path / "test.db")
        _seed_note(db_path, note_id="n1", title="退休总览", directory="退休规划")
        _seed_note(db_path, note_id="n2", title="入门", directory="")
        with app.test_client() as client:
            resp = client.get("/api/private/notes")
        data = resp.get_json()
        assert len(data["notes"]) == 2
        assert "退休规划" in data["tree"]
        retire_branch = data["tree"]["退休规划"]
        # tree node values can be either {"_notes": [...], "<sub>": {...}} or list — accept either
        if isinstance(retire_branch, dict):
            note_titles = [n["title"] for n in retire_branch.get("_notes", [])]
        else:
            note_titles = [n["title"] for n in retire_branch]
        assert "退休总览" in note_titles

    def test_root_notes_appear_at_top_level(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        db_path = str(tmp_path / "test.db")
        _seed_note(db_path, note_id="n1", title="random", directory="")
        with app.test_client() as client:
            resp = client.get("/api/private/notes")
        data = resp.get_json()
        # Root notes live under empty key or _notes at root level
        if "_notes" in data["tree"]:
            titles = [n["title"] for n in data["tree"]["_notes"]]
        else:
            titles = [n["title"] for n in data["tree"].get("", [])]
        assert "random" in titles

    def test_only_returns_default_user_notes(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        db_path = str(tmp_path / "test.db")
        _seed_note(db_path, note_id="n1", title="mine", user_id="default")
        _seed_note(db_path, note_id="n2", title="theirs", user_id="other")
        with app.test_client() as client:
            resp = client.get("/api/private/notes")
        data = resp.get_json()
        assert len(data["notes"]) == 1
        assert data["notes"][0]["title"] == "mine"


class TestCreateNote:
    def test_with_title_and_content_creates_row(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with patch("app.routes.private.QdrantService") as MockQ:
            mock_q = MockQ.return_value
            with app.test_client() as client:
                resp = client.post(
                    "/api/private/notes",
                    json={"title": "新建笔记", "content": "正文"},
                )
            assert resp.status_code == 201
            note = resp.get_json()
            assert note["title"] == "新建笔记"
            assert note["content"] == "正文"
            assert note["directory"] == ""
            mock_q.upsert_private.assert_not_called()

        conn = sqlite3.connect(str(tmp_path / "test.db"))
        try:
            row = conn.execute(
                "SELECT user_id, title FROM notes WHERE id = ?",
                (note["id"],),
            ).fetchone()
        finally:
            conn.close()
        assert row[0] == "default"
        assert row[1] == "新建笔记"

    def test_with_chat_ref_stores_value(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with app.test_client() as client:
            resp = client.post(
                "/api/private/notes",
                json={"title": "对话总结", "content": "x", "chat_ref": "session-42"},
            )
        assert resp.status_code == 201
        assert resp.get_json()["chat_ref"] == "session-42"

    def test_missing_title_returns_400(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with app.test_client() as client:
            resp = client.post(
                "/api/private/notes",
                json={"content": "正文"},
            )
        assert resp.status_code == 400
        assert "title" in resp.get_json()["error"]

    def test_does_not_call_qdrant(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with patch("app.routes.private.QdrantService") as MockQ:
            mock_q = MockQ.return_value
            with app.test_client() as client:
                resp = client.post(
                    "/api/private/notes",
                    json={"title": "x", "content": "y"},
                )
            assert resp.status_code == 201
            mock_q.upsert_private.assert_not_called()
            mock_q.delete_private.assert_not_called()


class TestUpdateNote:
    def test_update_content_refreshes_updated_at(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        db_path = str(tmp_path / "test.db")
        _seed_note(
            db_path,
            note_id="n1",
            title="t",
            content="orig",
            created_at="2026-01-01T00:00:00Z",
        )
        with app.test_client() as client:
            resp = client.put("/api/private/notes/n1", json={"content": "new"})
        assert resp.status_code == 200
        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute(
                "SELECT content, created_at, updated_at FROM notes WHERE id='n1'"
            ).fetchone()
        finally:
            conn.close()
        assert row[0] == "new"
        assert row[2] != row[1]

    def test_update_directory_stores_new_path(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        db_path = str(tmp_path / "test.db")
        _seed_note(db_path, note_id="n1", title="t", directory="")
        with app.test_client() as client:
            resp = client.put("/api/private/notes/n1", json={"directory": "退休规划"})
        assert resp.status_code == 200
        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute("SELECT directory FROM notes WHERE id='n1'").fetchone()
        finally:
            conn.close()
        assert row[0] == "退休规划"

    def test_unknown_id_returns_404(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with app.test_client() as client:
            resp = client.put(
                "/api/private/notes/nonexistent",
                json={"content": "x"},
            )
        assert resp.status_code == 404
        assert resp.get_json() == {"error": "note not found"}


class TestDeleteNote:
    def test_valid_id_removes_row(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        db_path = str(tmp_path / "test.db")
        _seed_note(db_path, note_id="n1", title="t")
        with patch("app.routes.private.QdrantService") as MockQ:
            mock_q = MockQ.return_value
            with app.test_client() as client:
                resp = client.delete("/api/private/notes/n1")
            assert resp.status_code == 200
            assert resp.get_json() == {"ok": True}
            # Notes are SQLite-only — Qdrant must NOT be touched
            mock_q.upsert_private.assert_not_called()
            mock_q.delete_private.assert_not_called()

        # Row gone
        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute("SELECT id FROM notes WHERE id='n1'").fetchone()
        finally:
            conn.close()
        assert row is None

    def test_unknown_id_returns_404(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with app.test_client() as client:
            resp = client.delete("/api/private/notes/nonexistent")
        assert resp.status_code == 404
        assert resp.get_json() == {"error": "note not found"}

    def test_only_default_user_can_delete(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        db_path = str(tmp_path / "test.db")
        _seed_note(db_path, note_id="n1", title="theirs", user_id="other")
        with app.test_client() as client:
            resp = client.delete("/api/private/notes/n1")
        # Note belongs to a different user; default user must not see/delete it
        assert resp.status_code == 404
        # Row still exists
        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute("SELECT id FROM notes WHERE id='n1'").fetchone()
        finally:
            conn.close()
        assert row is not None
