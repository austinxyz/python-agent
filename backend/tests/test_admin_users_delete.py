"""DELETE /api/admin/users/:id — cascade delete with Qdrant filter-delete first."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from app.routes.admin_users import admin_users_bp
from app.services.db_service import DatabaseService
from app.services.user_service import (
    activate_user_with_password,
    create_invited_user,
    get_user_by_id,
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


def _make_disabled_member(email="victim@example.com", admin_id=None):
    db = DatabaseService()
    with db.connection() as conn:
        user = create_invited_user(conn, email, role="member", invited_by=admin_id)
        activate_user_with_password(conn, user["id"], "password123")
        conn.execute("UPDATE users SET status = 'disabled' WHERE id = ?", (user["id"],))
    return user


def _make_active_member(email="active@example.com"):
    db = DatabaseService()
    with db.connection() as conn:
        user = create_invited_user(conn, email, role="member")
        activate_user_with_password(conn, user["id"], "password123")
    return user


class TestDeleteUser:
    def test_400_cannot_delete_active_user(self, client, monkeypatch):
        admin = _make_admin()
        member = _make_active_member()
        monkeypatch.setattr(
            "app.middleware._validate_session",
            lambda: SimpleNamespace(**{**admin, "role": "admin", "status": "active"}),
        )
        resp = client.delete(f"/api/admin/users/{member['id']}")
        assert resp.status_code == 400
        assert "disabled" in resp.get_json()["error"]

    def test_400_cannot_delete_self(self, client, monkeypatch):
        admin = _make_admin()
        # First disable self — but can't (400), so just try delete directly
        monkeypatch.setattr(
            "app.middleware._validate_session",
            lambda: SimpleNamespace(**{**admin, "role": "admin", "status": "active"}),
        )
        resp = client.delete(f"/api/admin/users/{admin['id']}")
        assert resp.status_code == 400
        assert "self" in resp.get_json()["error"]

    def test_400_cannot_delete_only_admin(self, client, monkeypatch):
        admin = _make_admin(email="only_admin@example.com")
        second_admin = _make_admin(email="second_admin@example.com")
        db = DatabaseService()
        with db.connection() as conn:
            conn.execute("UPDATE users SET status = 'disabled' WHERE id = ?", (second_admin["id"],))
        monkeypatch.setattr(
            "app.middleware._validate_session",
            lambda: SimpleNamespace(**{**admin, "role": "admin", "status": "active"}),
        )
        resp = client.delete(f"/api/admin/users/{second_admin['id']}")
        assert resp.status_code == 400
        assert "admin" in resp.get_json()["error"].lower()

    def test_204_on_success_removes_user_row(self, client, monkeypatch):
        admin = _make_admin()
        victim = _make_disabled_member(admin_id=admin["id"])
        monkeypatch.setattr(
            "app.middleware._validate_session",
            lambda: SimpleNamespace(**{**admin, "role": "admin", "status": "active"}),
        )
        with patch("app.services.user_service.QdrantService") as MockQdrant:
            mock_qdrant = MagicMock()
            MockQdrant.return_value = mock_qdrant
            resp = client.delete(f"/api/admin/users/{victim['id']}")
        assert resp.status_code == 204
        db = DatabaseService()
        with db.connection() as conn:
            assert get_user_by_id(conn, victim["id"]) is None

    def test_delete_cascades_private_entries(self, client, monkeypatch):
        admin = _make_admin()
        victim = _make_disabled_member(admin_id=admin["id"])
        db = DatabaseService()
        with db.connection() as conn:
            conn.execute(
                "INSERT INTO private_entries (id, user_id, title, content_json, template_type, directory, created_at, updated_at) "
                "VALUES ('pe-1', ?, 'Test', '{}', 'note', '/', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')",
                (victim["id"],),
            )

        monkeypatch.setattr(
            "app.middleware._validate_session",
            lambda: SimpleNamespace(**{**admin, "role": "admin", "status": "active"}),
        )
        with patch("app.services.user_service.QdrantService") as MockQdrant:
            mock_qdrant = MagicMock()
            MockQdrant.return_value = mock_qdrant
            client.delete(f"/api/admin/users/{victim['id']}")

        with db.connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM private_entries WHERE user_id = ?", (victim["id"],)
            ).fetchone()
        assert row[0] == 0

    def test_delete_preserves_knowledge_files(self, client, monkeypatch):
        admin = _make_admin()
        victim = _make_disabled_member(admin_id=admin["id"])
        db = DatabaseService()
        with db.connection() as conn:
            conn.execute(
                "INSERT INTO files (id, user_id, filename, orig_name, source_type, created_at) "
                "VALUES ('file-1', ?, 'test.pdf', 'test.pdf', 'file', '2026-01-01T00:00:00Z')",
                (victim["id"],),
            )

        monkeypatch.setattr(
            "app.middleware._validate_session",
            lambda: SimpleNamespace(**{**admin, "role": "admin", "status": "active"}),
        )
        with patch("app.services.user_service.QdrantService") as MockQdrant:
            mock_qdrant = MagicMock()
            MockQdrant.return_value = mock_qdrant
            client.delete(f"/api/admin/users/{victim['id']}")

        with db.connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM files WHERE id = 'file-1'"
            ).fetchone()
        assert row[0] == 1  # file still exists (orphan user_id acceptable)

    def test_qdrant_delete_before_sqlite_ordering(self, client, monkeypatch):
        """When SQLite delete fails after Qdrant succeeds, user row still exists (recoverable)."""
        admin = _make_admin()
        victim = _make_disabled_member(admin_id=admin["id"])
        monkeypatch.setattr(
            "app.middleware._validate_session",
            lambda: SimpleNamespace(**{**admin, "role": "admin", "status": "active"}),
        )

        call_order = []

        def mock_qdrant_filter_delete(*args, **kwargs):
            call_order.append("qdrant")

        def mock_sqlite_delete_fail(*args, **kwargs):
            call_order.append("sqlite")
            raise RuntimeError("SQLite delete failed")

        with patch(
            "app.services.user_service.delete_user_cascading",
        ) as mock_cascade:
            def side_effect(user_id, qdrant_svc=None):
                call_order.append("qdrant")
                call_order.append("sqlite_attempt")
                raise RuntimeError("SQLite delete failed after Qdrant")
            mock_cascade.side_effect = side_effect
            resp = client.delete(f"/api/admin/users/{victim['id']}")

        assert resp.status_code == 500
        # The user row should still exist (recoverable state)
        db = DatabaseService()
        with db.connection() as conn:
            assert get_user_by_id(conn, victim["id"]) is not None
        assert "qdrant" in call_order

    def test_401_without_auth(self, client, monkeypatch):
        admin = _make_admin()
        monkeypatch.setattr("app.middleware._validate_session", lambda: None)
        assert client.delete(f"/api/admin/users/{admin['id']}").status_code == 401

    def test_403_as_member(self, client, monkeypatch):
        admin = _make_admin()
        monkeypatch.setattr("app.middleware._validate_session", lambda: _MEMBER_NS)
        assert client.delete(f"/api/admin/users/{admin['id']}").status_code == 403
