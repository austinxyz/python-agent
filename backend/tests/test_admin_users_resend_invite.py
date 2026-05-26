"""POST /api/admin/users/:id/resend-invite — invalidate old token, issue new one."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from flask import Flask

from app.routes.admin_users import admin_users_bp
from app.services.db_service import DatabaseService
from app.services.user_service import (
    activate_user_with_password,
    create_invite_token,
    create_invited_user,
    get_invite_token,
)

_MEMBER_NS = SimpleNamespace(id="member-uuid", email="member@example.com", role="member", status="active")


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


def _make_invited_user(email="invited@example.com"):
    db = DatabaseService()
    with db.connection() as conn:
        user = create_invited_user(conn, email, role="member")
        token = create_invite_token(conn, user["id"])
    return user, token


class TestResendInvite:
    def test_200_resend_for_invited_user(self, client, monkeypatch):
        admin = _make_admin()
        user, old_token = _make_invited_user()
        monkeypatch.setattr(
            "app.middleware._validate_session",
            lambda: SimpleNamespace(**{**admin, "role": "admin", "status": "active"}),
        )
        resp = client.post(f"/api/admin/users/{user['id']}/resend-invite")
        assert resp.status_code == 200
        body = resp.get_json()
        assert "invite_url" in body
        assert "/accept-invite?token=" in body["invite_url"]

    def test_old_token_marked_used(self, client, monkeypatch):
        admin = _make_admin()
        user, old_token = _make_invited_user()
        monkeypatch.setattr(
            "app.middleware._validate_session",
            lambda: SimpleNamespace(**{**admin, "role": "admin", "status": "active"}),
        )
        client.post(f"/api/admin/users/{user['id']}/resend-invite")
        db = DatabaseService()
        with db.connection() as conn:
            token_row = get_invite_token(conn, old_token)
        assert token_row["used_at"] is not None

    def test_new_token_created_with_fresh_expiry(self, client, monkeypatch):
        admin = _make_admin()
        user, old_token = _make_invited_user()
        monkeypatch.setattr(
            "app.middleware._validate_session",
            lambda: SimpleNamespace(**{**admin, "role": "admin", "status": "active"}),
        )
        resp = client.post(f"/api/admin/users/{user['id']}/resend-invite")
        new_url = resp.get_json()["invite_url"]
        new_token = new_url.split("token=")[1]
        assert new_token != old_token
        db = DatabaseService()
        with db.connection() as conn:
            new_token_row = get_invite_token(conn, new_token)
        assert new_token_row is not None
        assert new_token_row["used_at"] is None

    def test_400_resend_for_active_user(self, client, monkeypatch):
        admin = _make_admin()
        db = DatabaseService()
        with db.connection() as conn:
            member = create_invited_user(conn, "active@example.com", role="member")
            activate_user_with_password(conn, member["id"], "password123")
        monkeypatch.setattr(
            "app.middleware._validate_session",
            lambda: SimpleNamespace(**{**admin, "role": "admin", "status": "active"}),
        )
        resp = client.post(f"/api/admin/users/{member['id']}/resend-invite")
        assert resp.status_code == 400
        assert "invited state" in resp.get_json()["error"]

    def test_400_resend_for_disabled_user(self, client, monkeypatch):
        admin = _make_admin()
        db = DatabaseService()
        with db.connection() as conn:
            member = create_invited_user(conn, "disabled@example.com", role="member")
            activate_user_with_password(conn, member["id"], "password123")
            conn.execute(
                "UPDATE users SET status = 'disabled' WHERE id = ?", (member["id"],)
            )
        monkeypatch.setattr(
            "app.middleware._validate_session",
            lambda: SimpleNamespace(**{**admin, "role": "admin", "status": "active"}),
        )
        resp = client.post(f"/api/admin/users/{member['id']}/resend-invite")
        assert resp.status_code == 400
        assert "invited state" in resp.get_json()["error"]

    def test_401_without_auth(self, client, monkeypatch):
        user, _ = _make_invited_user("z@z.com")
        monkeypatch.setattr("app.middleware._validate_session", lambda: None)
        assert client.post(f"/api/admin/users/{user['id']}/resend-invite").status_code == 401

    def test_403_as_member(self, client, monkeypatch):
        user, _ = _make_invited_user("zz@zz.com")
        monkeypatch.setattr("app.middleware._validate_session", lambda: _MEMBER_NS)
        assert client.post(f"/api/admin/users/{user['id']}/resend-invite").status_code == 403
