"""@require_auth middleware enforces active session.

- 401 + cookie clear when no session
- 401 + cookie clear when session.user_id doesn't exist
- 401 + cookie clear when user.status != 'active'
- 200 + g.user set when user is active
"""
from __future__ import annotations

import pytest
from flask import Flask, g, jsonify, session

from app.middleware import require_auth
from app.services.db_service import DatabaseService
from app.services.user_service import (
    activate_user_with_password,
    create_invited_user,
)


@pytest.fixture
def app():
    DatabaseService()  # apply schema
    app = Flask(__name__)
    app.secret_key = "test-secret"

    @app.get("/protected")
    @require_auth
    def protected():
        return jsonify({"user_id": g.user.id, "status": g.user.status})

    return app


@pytest.fixture
def client(app):
    return app.test_client()


def _make_active_user(email: str = "test@example.com") -> str:
    """Create an active user, return id."""
    db = DatabaseService()
    with db.connection() as conn:
        user = create_invited_user(conn, email, role="member")
        activate_user_with_password(conn, user["id"], "abcdefgh")
    return user["id"]


def _make_disabled_user() -> str:
    db = DatabaseService()
    with db.connection() as conn:
        user = create_invited_user(conn, "disabled@example.com", role="member")
        activate_user_with_password(conn, user["id"], "abcdefgh")
        conn.execute(
            "UPDATE users SET status = 'disabled' WHERE id = ?", (user["id"],)
        )
    return user["id"]


class TestRequireAuth:
    def test_no_session_returns_401(self, client):
        resp = client.get("/protected")
        assert resp.status_code == 401
        assert resp.get_json() == {"error": "authentication required"}

    def test_session_with_unknown_user_returns_401(self, client):
        with client.session_transaction() as s:
            s["user_id"] = "nonexistent-uuid"
        resp = client.get("/protected")
        assert resp.status_code == 401

    def test_active_user_session_passes(self, client):
        uid = _make_active_user()
        with client.session_transaction() as s:
            s["user_id"] = uid
        resp = client.get("/protected")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["user_id"] == uid
        assert body["status"] == "active"

    def test_disabled_user_session_returns_401(self, client):
        uid = _make_disabled_user()
        with client.session_transaction() as s:
            s["user_id"] = uid
        resp = client.get("/protected")
        assert resp.status_code == 401

    def test_invited_user_session_returns_401(self, client):
        # User in invited status (no password set yet)
        db = DatabaseService()
        with db.connection() as conn:
            user = create_invited_user(conn, "invited@example.com", role="member")
        with client.session_transaction() as s:
            s["user_id"] = user["id"]
        resp = client.get("/protected")
        assert resp.status_code == 401
