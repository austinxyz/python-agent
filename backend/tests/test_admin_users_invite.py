"""POST /api/admin/users — invite new user or 409 duplicate."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from flask import Flask

from app.routes.admin_users import admin_users_bp
from app.services.db_service import DatabaseService
from app.services.user_service import (
    activate_user_with_password,
    create_invited_user,
)

_MEMBER = SimpleNamespace(id="member-uuid", email="member@example.com", role="member", status="active")


@pytest.fixture
def app():
    DatabaseService()
    a = Flask(__name__)
    a.secret_key = "test-secret"
    a.register_blueprint(admin_users_bp, url_prefix="/api/admin")
    return a


@pytest.fixture
def client(app):
    return app.test_client()


def _make_admin(email="admin@example.com"):
    db = DatabaseService()
    with db.connection() as conn:
        user = create_invited_user(conn, email, role="admin")
        activate_user_with_password(conn, user["id"], "password123")
    return user


@pytest.fixture
def admin_session(monkeypatch):
    admin = _make_admin()

    def fake_session():
        return SimpleNamespace(**{**admin, "role": "admin", "status": "active"})

    monkeypatch.setattr("app.middleware._validate_session", fake_session)
    return admin


class TestInviteUser:
    def test_201_new_email_creates_user_and_token(self, client, admin_session):
        resp = client.post(
            "/api/admin/users",
            json={"email": "wife@gmail.com", "role": "member"},
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert "user" in body
        assert "invite_url" in body
        assert body["user"]["email"] == "wife@gmail.com"
        assert body["user"]["status"] == "invited"
        assert body["user"]["role"] == "member"
        assert "/accept-invite?token=" in body["invite_url"]

    def test_201_invite_url_uses_request_host(self, client, admin_session):
        resp = client.post(
            "/api/admin/users",
            json={"email": "kid@gmail.com", "role": "member"},
        )
        assert resp.status_code == 201
        url = resp.get_json()["invite_url"]
        assert url.startswith("http://")

    def test_409_duplicate_email_returns_existing(self, client, admin_session):
        db = DatabaseService()
        with db.connection() as conn:
            existing = create_invited_user(conn, "dup@gmail.com", role="member")
            activate_user_with_password(conn, existing["id"], "pw123456")

        resp = client.post(
            "/api/admin/users",
            json={"email": "dup@gmail.com", "role": "member"},
        )
        assert resp.status_code == 409
        body = resp.get_json()
        assert body["error"] == "user already exists"
        assert body["existing"]["email"] == "dup@gmail.com"
        assert body["existing"]["status"] == "active"
        assert {"id", "email", "status", "role"}.issubset(set(body["existing"].keys()))

    def test_409_email_canonicalized_before_duplicate_check(self, client, admin_session):
        db = DatabaseService()
        with db.connection() as conn:
            create_invited_user(conn, "lower@gmail.com", role="member")

        resp = client.post(
            "/api/admin/users",
            json={"email": "LOWER@GMAIL.COM", "role": "member"},
        )
        assert resp.status_code == 409

    def test_invited_by_set_to_admin_id(self, client, admin_session):
        resp = client.post(
            "/api/admin/users",
            json={"email": "invitee@gmail.com", "role": "member"},
        )
        assert resp.status_code == 201
        user = resp.get_json()["user"]
        assert user.get("invited_by") == admin_session["id"] or True
        # invited_by is not in the response — check DB
        db = DatabaseService()
        with db.connection() as conn:
            row = conn.execute(
                "SELECT invited_by FROM users WHERE email = ?", ("invitee@gmail.com",)
            ).fetchone()
        assert row[0] == admin_session["id"]

    def test_401_without_auth(self, client, monkeypatch):
        monkeypatch.setattr("app.middleware._validate_session", lambda: None)
        assert client.post(
            "/api/admin/users", json={"email": "x@x.com", "role": "member"}
        ).status_code == 401

    def test_403_as_member(self, client, monkeypatch):
        monkeypatch.setattr("app.middleware._validate_session", lambda: _MEMBER)
        assert client.post(
            "/api/admin/users", json={"email": "x@x.com", "role": "member"}
        ).status_code == 403
