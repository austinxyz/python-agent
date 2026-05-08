"""Tests for /api/private/templates and /api/private/entries CRUD."""
import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.db_service import DatabaseService


def _make_app(monkeypatch, tmp_path):
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("UPLOADS_PATH", str(tmp_path / "uploads"))
    with patch("app.services.qdrant_service.QdrantClient") as MockQdrant:
        MockQdrant.return_value.get_collection.return_value = MagicMock()
        from app import create_app
        return create_app({"TESTING": True})


def _seed_entry(
    db_path: str,
    *,
    entry_id: str,
    user_id: str = "default",
    template_type: str = "tax",
    title: str = "test",
    content_json: str = "{}",
    directory: str = "",
    created_at: str | None = None,
) -> None:
    import sqlite3
    conn = sqlite3.connect(db_path)
    try:
        if created_at:
            conn.execute(
                "INSERT INTO private_entries (id, user_id, template_type, title, content_json, directory, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (entry_id, user_id, template_type, title, content_json, directory, created_at, created_at),
            )
        else:
            conn.execute(
                "INSERT INTO private_entries (id, user_id, template_type, title, content_json, directory)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (entry_id, user_id, template_type, title, content_json, directory),
            )
        conn.commit()
    finally:
        conn.close()


class TestPrivateTemplates:
    def test_returns_six_templates(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with app.test_client() as client:
            resp = client.get("/api/private/templates")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) == 6

    def test_each_template_has_required_keys(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with app.test_client() as client:
            resp = client.get("/api/private/templates")
        for tpl in resp.get_json():
            assert "type" in tpl
            assert "label" in tpl
            assert "fields" in tpl
            assert isinstance(tpl["fields"], list)
            for field in tpl["fields"]:
                assert "key" in field
                assert "label" in field
                assert "type" in field

    def test_template_types_match_spec(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with app.test_client() as client:
            resp = client.get("/api/private/templates")
        types = {t["type"] for t in resp.get_json()}
        assert types == {"tax", "retirement", "portfolio", "personal", "real_estate", "freeform"}

    def test_each_template_has_default_directory(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with app.test_client() as client:
            resp = client.get("/api/private/templates")
        defaults = {t["type"]: t["default_directory"] for t in resp.get_json()}
        assert defaults == {
            "tax": "税务",
            "retirement": "退休账户",
            "portfolio": "投资持仓",
            "personal": "个人基本情况",
            "real_estate": "房产资产",
            "freeform": "自由格式",
        }


class TestListEntries:
    def test_empty_db_returns_empty_list(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with app.test_client() as client:
            resp = client.get("/api/private/entries")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_returns_entries_ordered_by_created_at_desc(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        db_path = str(tmp_path / "test.db")
        _seed_entry(db_path, entry_id="e1", title="older", created_at="2026-01-01T10:00:00Z")
        _seed_entry(db_path, entry_id="e2", title="newer", created_at="2026-02-01T10:00:00Z")
        with app.test_client() as client:
            resp = client.get("/api/private/entries")
        data = resp.get_json()
        assert len(data) == 2
        assert data[0]["id"] == "e2"
        assert data[1]["id"] == "e1"

    def test_only_returns_default_user_entries(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        db_path = str(tmp_path / "test.db")
        _seed_entry(db_path, entry_id="e1", user_id="default", title="mine")
        _seed_entry(db_path, entry_id="e2", user_id="other", title="theirs")
        with app.test_client() as client:
            resp = client.get("/api/private/entries")
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["id"] == "e1"


class TestCreateEntry:
    def test_valid_payload_creates_entry_and_upserts_qdrant(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with patch("app.routes.private.EmbeddingService") as MockEmb, \
             patch("app.routes.private.QdrantService") as MockQ:
            MockEmb.return_value.embed.return_value = [0.0] * 1536
            mock_q = MockQ.return_value
            with app.test_client() as client:
                resp = client.post(
                    "/api/private/entries",
                    json={
                        "template_type": "tax",
                        "title": "我的税务",
                        "content_json": {"filing_status": "single", "agi": 100000},
                    },
                )
            assert resp.status_code == 201
            entry = resp.get_json()
            assert entry["template_type"] == "tax"
            assert entry["title"] == "我的税务"
            assert "id" in entry

            mock_q.upsert_private.assert_called_once()
            points = mock_q.upsert_private.call_args.args[0]
            assert len(points) == 1
            point = points[0]
            assert point.id == entry["id"]
            assert point.payload["user_id"] == "default"
            assert point.payload["template_type"] == "tax"
            assert point.payload["title"] == "我的税务"
            assert point.payload["source_file_id"] == entry["id"]

        # Verify SQLite row exists
        import sqlite3
        conn = sqlite3.connect(str(tmp_path / "test.db"))
        try:
            row = conn.execute(
                "SELECT id, template_type, title, content_json FROM private_entries WHERE id = ?",
                (entry["id"],),
            ).fetchone()
        finally:
            conn.close()
        assert row is not None
        assert row[1] == "tax"
        assert row[2] == "我的税务"
        assert json.loads(row[3]) == {"filing_status": "single", "agi": 100000}

    def test_missing_template_type_returns_400(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with app.test_client() as client:
            resp = client.post(
                "/api/private/entries",
                json={"title": "x", "content_json": {}},
            )
        assert resp.status_code == 400
        assert "template_type" in resp.get_json()["error"]

    def test_missing_title_returns_400(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with app.test_client() as client:
            resp = client.post(
                "/api/private/entries",
                json={"template_type": "tax", "content_json": {}},
            )
        assert resp.status_code == 400
        assert "title" in resp.get_json()["error"]


class TestUpdateEntry:
    def test_valid_update_re_embeds_and_updates_timestamp(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        db_path = str(tmp_path / "test.db")
        _seed_entry(
            db_path,
            entry_id="e1",
            template_type="tax",
            title="orig",
            content_json='{"k":"v"}',
            created_at="2026-01-01T00:00:00Z",
        )
        with patch("app.routes.private.EmbeddingService") as MockEmb, \
             patch("app.routes.private.QdrantService") as MockQ:
            MockEmb.return_value.embed.return_value = [0.0] * 1536
            mock_q = MockQ.return_value
            with app.test_client() as client:
                resp = client.put(
                    "/api/private/entries/e1",
                    json={"title": "updated", "content_json": {"k": "new"}},
                )
            assert resp.status_code == 200
            mock_q.upsert_private.assert_called_once()

        # updated_at must differ from created_at
        import sqlite3
        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute(
                "SELECT title, content_json, created_at, updated_at FROM private_entries WHERE id='e1'"
            ).fetchone()
        finally:
            conn.close()
        assert row[0] == "updated"
        assert json.loads(row[1]) == {"k": "new"}
        assert row[3] != row[2]

    def test_unknown_id_returns_404(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with patch("app.routes.private.EmbeddingService"), \
             patch("app.routes.private.QdrantService"):
            with app.test_client() as client:
                resp = client.put(
                    "/api/private/entries/nonexistent",
                    json={"title": "x"},
                )
        assert resp.status_code == 404
        assert resp.get_json() == {"error": "entry not found"}


class TestDeleteEntry:
    def test_valid_id_deletes_from_sqlite_and_qdrant(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        db_path = str(tmp_path / "test.db")
        _seed_entry(db_path, entry_id="e1")
        with patch("app.routes.private.QdrantService") as MockQ:
            mock_q = MockQ.return_value
            with app.test_client() as client:
                resp = client.delete("/api/private/entries/e1")
            assert resp.status_code == 200
            mock_q.delete_private.assert_called_once()
            call = mock_q.delete_private.call_args
            passed = call.args[0] if call.args else call.kwargs.get("point_ids")
            assert passed == ["e1"]

        # Verify SQLite row is gone
        import sqlite3
        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute(
                "SELECT id FROM private_entries WHERE id='e1'"
            ).fetchone()
        finally:
            conn.close()
        assert row is None

    def test_unknown_id_returns_404(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with patch("app.routes.private.QdrantService"):
            with app.test_client() as client:
                resp = client.delete("/api/private/entries/nonexistent")
        assert resp.status_code == 404
        assert resp.get_json() == {"error": "entry not found"}


class TestEntryDirectory:
    def test_list_includes_directory_field(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        db_path = str(tmp_path / "test.db")
        _seed_entry(db_path, entry_id="e1", directory="税务/2025")
        with app.test_client() as client:
            resp = client.get("/api/private/entries")
        data = resp.get_json()
        assert data[0]["directory"] == "税务/2025"

    def test_create_without_directory_uses_template_default(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with patch("app.routes.private.EmbeddingService") as MockEmb, \
             patch("app.routes.private.QdrantService") as MockQ:
            MockEmb.return_value.embed.return_value = [0.0] * 1536
            with app.test_client() as client:
                resp = client.post(
                    "/api/private/entries",
                    json={"template_type": "tax", "title": "我的税务"},
                )
            assert resp.status_code == 201
            entry = resp.get_json()
            assert entry["directory"] == "税务"

    def test_create_with_explicit_directory_persists_it(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with patch("app.routes.private.EmbeddingService") as MockEmb, \
             patch("app.routes.private.QdrantService"):
            MockEmb.return_value.embed.return_value = [0.0] * 1536
            with app.test_client() as client:
                resp = client.post(
                    "/api/private/entries",
                    json={"template_type": "tax", "title": "x", "directory": "税务/2025"},
                )
            assert resp.status_code == 201
            assert resp.get_json()["directory"] == "税务/2025"

    def test_create_includes_directory_in_qdrant_payload(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with patch("app.routes.private.EmbeddingService") as MockEmb, \
             patch("app.routes.private.QdrantService") as MockQ:
            MockEmb.return_value.embed.return_value = [0.0] * 1536
            mock_q = MockQ.return_value
            with app.test_client() as client:
                client.post(
                    "/api/private/entries",
                    json={"template_type": "retirement", "title": "401k"},
                )
            point = mock_q.upsert_private.call_args.args[0][0]
            assert point.payload["directory"] == "退休账户"

    def test_update_can_change_directory(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        db_path = str(tmp_path / "test.db")
        _seed_entry(db_path, entry_id="e1", directory="税务")
        with patch("app.routes.private.EmbeddingService") as MockEmb, \
             patch("app.routes.private.QdrantService") as MockQ:
            MockEmb.return_value.embed.return_value = [0.0] * 1536
            mock_q = MockQ.return_value
            with app.test_client() as client:
                resp = client.put(
                    "/api/private/entries/e1",
                    json={"directory": "税务/历史"},
                )
            assert resp.status_code == 200
            assert resp.get_json()["directory"] == "税务/历史"
            point = mock_q.upsert_private.call_args.args[0][0]
            assert point.payload["directory"] == "税务/历史"
