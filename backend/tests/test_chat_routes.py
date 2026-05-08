"""Tests for /api/chat endpoints."""
import json
import sqlite3
import threading
from unittest.mock import MagicMock, patch

import pytest


def _make_app(monkeypatch, tmp_path):
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("UPLOADS_PATH", str(tmp_path / "uploads"))
    with patch("app.services.qdrant_service.QdrantClient") as MockQdrant:
        MockQdrant.return_value.get_collection.return_value = MagicMock()
        from app import create_app
        return create_app({"TESTING": True})


def _seed_session(db_path, *, session_id, user_id="default", title="t", model="haiku", created_at=None):
    conn = sqlite3.connect(db_path)
    try:
        if created_at:
            conn.execute(
                "INSERT INTO chat_sessions (id, user_id, title, model, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, user_id, title, model, created_at, created_at),
            )
        else:
            conn.execute(
                "INSERT INTO chat_sessions (id, user_id, title, model)"
                " VALUES (?, ?, ?, ?)",
                (session_id, user_id, title, model),
            )
        conn.commit()
    finally:
        conn.close()


def _seed_message(db_path, *, message_id, session_id, role, content, sources='[]', created_at=None):
    conn = sqlite3.connect(db_path)
    try:
        if created_at:
            conn.execute(
                "INSERT INTO chat_messages (id, session_id, role, content, sources, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (message_id, session_id, role, content, sources, created_at),
            )
        else:
            conn.execute(
                "INSERT INTO chat_messages (id, session_id, role, content, sources)"
                " VALUES (?, ?, ?, ?, ?)",
                (message_id, session_id, role, content, sources),
            )
        conn.commit()
    finally:
        conn.close()


def _fake_agent_streaming_run(queue, query, scope, **kwargs):
    """Stand-in for run_agent that produces a deterministic SSE stream."""
    queue.put({"type": "token", "content": "Hello"})
    queue.put({"type": "token", "content": " world"})
    queue.put({"type": "done", "sources": [
        {"title": "X", "domain": "退休规划", "file_id": "f1"}
    ]})
    queue.put(None)


def _parse_sse(body: bytes) -> list[dict]:
    """Parse a chunk of SSE bytes into the list of decoded JSON events."""
    text = body.decode("utf-8")
    out = []
    for line in text.split("\n\n"):
        line = line.strip()
        if line.startswith("data: "):
            out.append(json.loads(line[len("data: "):]))
    return out


# ---------------------------------------------------------------------------
# POST /api/chat — new session
# ---------------------------------------------------------------------------


class TestPostChatNewSession:
    def test_new_session_row_created_when_no_session_id(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        db_path = str(tmp_path / "test.db")
        with patch("app.routes.chat.run_agent", side_effect=_fake_agent_streaming_run):
            with app.test_client() as client:
                resp = client.post("/api/chat", json={
                    "query": "退休账户怎么选？",
                    "model": "haiku",
                    "scope": ["knowledge"],
                })
            assert resp.status_code == 200
            # Drain the streamed body
            body = resp.get_data()
        events = _parse_sse(body)
        # Should have at least one token and a done event
        types = [e["type"] for e in events]
        assert "token" in types
        assert "done" in types

        # New session row exists
        conn = sqlite3.connect(db_path)
        try:
            sessions = conn.execute("SELECT id, title, model FROM chat_sessions").fetchall()
            assert len(sessions) == 1
            assert "退休账户" in sessions[0][1]   # title comes from the query (truncated)
            assert sessions[0][2] == "haiku"
            # Both user message and assistant message persisted
            msgs = conn.execute(
                "SELECT role, content FROM chat_messages WHERE session_id = ? ORDER BY created_at",
                (sessions[0][0],),
            ).fetchall()
            roles = [m[0] for m in msgs]
            assert roles == ["user", "assistant"]
            assert msgs[1][1] == "Hello world"
        finally:
            conn.close()

    def test_existing_session_id_appends_messages(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        db_path = str(tmp_path / "test.db")
        _seed_session(db_path, session_id="s1", title="prior")
        _seed_message(db_path, message_id="m1", session_id="s1", role="user", content="prior question")
        _seed_message(db_path, message_id="m2", session_id="s1", role="assistant", content="prior answer")
        captured_history = {}

        def _fake(queue, query, scope, **kwargs):
            captured_history["history"] = kwargs.get("history") or []
            queue.put({"type": "token", "content": "ok"})
            queue.put({"type": "done", "sources": []})
            queue.put(None)

        with patch("app.routes.chat.run_agent", side_effect=_fake):
            with app.test_client() as client:
                resp = client.post("/api/chat", json={
                    "query": "继续",
                    "model": "haiku",
                    "scope": ["knowledge"],
                    "session_id": "s1",
                })
            assert resp.status_code == 200
            resp.get_data()  # drain

        # Prior messages were passed as history
        assert any("prior question" in m.get("content", "") for m in captured_history["history"])
        assert any("prior answer" in m.get("content", "") for m in captured_history["history"])

        # No NEW session row created — still exactly 1 session
        conn = sqlite3.connect(db_path)
        try:
            count = conn.execute("SELECT COUNT(*) FROM chat_sessions").fetchone()[0]
            assert count == 1
            # The two new messages got appended (4 total)
            msg_count = conn.execute(
                "SELECT COUNT(*) FROM chat_messages WHERE session_id = 's1'"
            ).fetchone()[0]
            assert msg_count == 4
        finally:
            conn.close()

    def test_missing_query_returns_400(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with app.test_client() as client:
            resp = client.post("/api/chat", json={"model": "haiku", "scope": ["knowledge"]})
        assert resp.status_code == 400
        assert "query" in resp.get_json()["error"]

    def test_done_event_includes_session_id(self, monkeypatch, tmp_path):
        """Frontend uses session_id from the done event to populate
        chat_ref when the user saves an answer to private notes. Without
        it, freshly-created sessions have no client-side id until the
        sessions list is re-fetched."""
        app = _make_app(monkeypatch, tmp_path)
        with patch("app.routes.chat.run_agent", side_effect=_fake_agent_streaming_run):
            with app.test_client() as client:
                resp = client.post("/api/chat", json={
                    "query": "退休账户怎么选？",
                    "model": "haiku",
                    "scope": ["knowledge"],
                })
            body = resp.get_data()
        events = _parse_sse(body)
        done = next(e for e in events if e["type"] == "done")
        assert "session_id" in done
        assert isinstance(done["session_id"], str) and len(done["session_id"]) > 0


# ---------------------------------------------------------------------------
# GET /api/chat/sessions
# ---------------------------------------------------------------------------


class TestGetSessions:
    def test_empty_db_returns_empty_list(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with app.test_client() as client:
            resp = client.get("/api/chat/sessions")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_returns_sessions_ordered_newest_first(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        db_path = str(tmp_path / "test.db")
        _seed_session(db_path, session_id="s-old", title="older",
                      created_at="2026-04-01T00:00:00Z")
        _seed_session(db_path, session_id="s-new", title="newer",
                      created_at="2026-05-01T00:00:00Z")
        with app.test_client() as client:
            resp = client.get("/api/chat/sessions")
        data = resp.get_json()
        assert [s["id"] for s in data] == ["s-new", "s-old"]
        for s in data:
            assert "title" in s
            assert "model" in s
            assert "created_at" in s


# ---------------------------------------------------------------------------
# GET /api/chat/sessions/{id}
# ---------------------------------------------------------------------------


class TestGetSessionDetail:
    def test_valid_id_returns_messages(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        db_path = str(tmp_path / "test.db")
        _seed_session(db_path, session_id="s1", title="conversation",
                      created_at="2026-05-01T00:00:00Z")
        _seed_message(db_path, message_id="m1", session_id="s1", role="user",
                      content="Q1", created_at="2026-05-01T00:00:01Z")
        _seed_message(db_path, message_id="m2", session_id="s1", role="assistant",
                      content="A1", sources='[{"title":"X","domain":"D","file_id":"f"}]',
                      created_at="2026-05-01T00:00:02Z")

        with app.test_client() as client:
            resp = client.get("/api/chat/sessions/s1")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["id"] == "s1"
        assert data["title"] == "conversation"
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][0]["content"] == "Q1"
        assert data["messages"][1]["role"] == "assistant"
        # sources field is parsed back to a list
        assert isinstance(data["messages"][1]["sources"], list)
        assert data["messages"][1]["sources"][0]["file_id"] == "f"

    def test_unknown_id_returns_404(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with app.test_client() as client:
            resp = client.get("/api/chat/sessions/does-not-exist")
        assert resp.status_code == 404
        assert resp.get_json() == {"error": "session not found"}
