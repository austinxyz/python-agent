"""@require_admin middleware — focused unit tests.

Covers:
- 401 + cookie cleared when unauthenticated
- 403 + cookie preserved when authenticated but role='member'
- 200 + g.user set when authenticated admin
- Cookie-clearing distinction: 401 path calls session.clear(), 403 path does not
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from flask import Flask, g, jsonify, session

from app.middleware import require_admin

_ADMIN = SimpleNamespace(id="admin-uuid", email="admin@example.com", role="admin", status="active")
_MEMBER = SimpleNamespace(id="member-uuid", email="member@example.com", role="member", status="active")


@pytest.fixture
def app():
    a = Flask(__name__)
    a.secret_key = "test-secret"

    @a.get("/admin-only")
    @require_admin
    def admin_only():
        return jsonify({"user_id": g.user.id, "role": g.user.role})

    return a


@pytest.fixture
def client(app):
    return app.test_client()


class TestRequireAdmin:
    def test_unauthenticated_returns_401(self, client, monkeypatch):
        monkeypatch.setattr("app.middleware._validate_session", lambda: None)
        resp = client.get("/admin-only")
        assert resp.status_code == 401
        assert resp.get_json() == {"error": "authentication required"}

    def test_member_returns_403(self, client, monkeypatch):
        monkeypatch.setattr("app.middleware._validate_session", lambda: _MEMBER)
        resp = client.get("/admin-only")
        assert resp.status_code == 403
        assert resp.get_json() == {"error": "admin access required"}

    def test_admin_returns_200_with_g_user(self, client, monkeypatch):
        monkeypatch.setattr("app.middleware._validate_session", lambda: _ADMIN)
        resp = client.get("/admin-only")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["user_id"] == "admin-uuid"
        assert body["role"] == "admin"

    def test_401_clears_session_cookie(self, client, monkeypatch):
        """Unauthenticated path calls session.clear() — Set-Cookie header deletes the session."""
        monkeypatch.setattr("app.middleware._validate_session", lambda: None)
        # Seed a session value so there is something to clear.
        with client.session_transaction() as s:
            s["some_key"] = "some_value"
        client.get("/admin-only")
        # After the 401, the session should be empty.
        with client.session_transaction() as s:
            assert "some_key" not in s

    def test_403_preserves_session_cookie(self, client, monkeypatch):
        """Member path does NOT call session.clear() — session data survives."""
        monkeypatch.setattr("app.middleware._validate_session", lambda: _MEMBER)
        with client.session_transaction() as s:
            s["user_id"] = "member-uuid"
        client.get("/admin-only")
        with client.session_transaction() as s:
            assert s.get("user_id") == "member-uuid"
