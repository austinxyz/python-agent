"""GET /api/admin/users — list all users sorted by invited_at DESC."""
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
)

_ADMIN = SimpleNamespace(id="admin-uuid", email="admin@example.com", role="admin", status="active")
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


def _make_member(email="member@example.com", invited_by=None):
    db = DatabaseService()
    with db.connection() as conn:
        user = create_invited_user(conn, email, role="member", invited_by=invited_by)
        activate_user_with_password(conn, user["id"], "password123")
    return user


class TestGetUsers:
    def test_401_without_auth(self, client, monkeypatch):
        monkeypatch.setattr("app.middleware._validate_session", lambda: None)
        assert client.get("/api/admin/users").status_code == 401

    def test_403_as_member(self, client, monkeypatch):
        monkeypatch.setattr("app.middleware._validate_session", lambda: _MEMBER)
        assert client.get("/api/admin/users").status_code == 403

    def test_200_returns_all_users_sorted_newest_first(self, client, monkeypatch):
        admin = _make_admin()
        member = _make_member(invited_by=admin["id"])
        monkeypatch.setattr(
            "app.middleware._validate_session",
            lambda: SimpleNamespace(**{**admin, "role": "admin", "status": "active"}),
        )
        resp = client.get("/api/admin/users")
        assert resp.status_code == 200
        users = resp.get_json()
        assert isinstance(users, list)
        assert len(users) == 2
        # newest invited_at first — member was invited after admin
        assert users[0]["email"] == member["email"]
        assert users[1]["email"] == admin["email"]

    def test_response_shape_has_required_fields(self, client, monkeypatch):
        admin = _make_admin()
        monkeypatch.setattr(
            "app.middleware._validate_session",
            lambda: SimpleNamespace(**{**admin, "role": "admin", "status": "active"}),
        )
        resp = client.get("/api/admin/users")
        user = resp.get_json()[0]
        required = {
            "id", "email", "name", "picture_url", "role", "status",
            "has_google", "has_password", "invited_at", "invited_by_email",
            "activated_at", "last_login_at",
        }
        assert required.issubset(set(user.keys()))

    def test_has_password_true_for_password_user(self, client, monkeypatch):
        admin = _make_admin()
        monkeypatch.setattr(
            "app.middleware._validate_session",
            lambda: SimpleNamespace(**{**admin, "role": "admin", "status": "active"}),
        )
        users = client.get("/api/admin/users").get_json()
        admin_row = next(u for u in users if u["email"] == admin["email"])
        assert admin_row["has_password"] is True
        assert admin_row["has_google"] is False

    def test_invited_by_email_null_for_bootstrap_admin(self, client, monkeypatch):
        admin = _make_admin()
        monkeypatch.setattr(
            "app.middleware._validate_session",
            lambda: SimpleNamespace(**{**admin, "role": "admin", "status": "active"}),
        )
        users = client.get("/api/admin/users").get_json()
        admin_row = next(u for u in users if u["email"] == admin["email"])
        assert admin_row["invited_by_email"] is None

    def test_invited_by_email_populated_when_invited_by_admin(self, client, monkeypatch):
        admin = _make_admin()
        member = _make_member(invited_by=admin["id"])
        monkeypatch.setattr(
            "app.middleware._validate_session",
            lambda: SimpleNamespace(**{**admin, "role": "admin", "status": "active"}),
        )
        users = client.get("/api/admin/users").get_json()
        member_row = next(u for u in users if u["email"] == member["email"])
        assert member_row["invited_by_email"] == admin["email"]
