"""All /api/auth/* routes — login (password + google), logout, me, config,
invite, accept-invite, change-password.
"""
from __future__ import annotations

import pytest
from flask import Flask

from app.routes.auth import auth_bp
from app.services.db_service import DatabaseService
from app.services.user_service import (
    activate_user_with_password,
    create_invited_user,
    create_invite_token,
)


@pytest.fixture
def app():
    """Minimal Flask app with just /api/auth/* mounted (avoids the heavy app
    factory + qdrant / etc. Real app factory tested separately)."""
    DatabaseService()  # apply schema
    app = Flask(__name__)
    app.secret_key = "test-secret-key"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = False  # tests run over http
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def _make_active_user(email="austin.xyz@gmail.com", role="admin", password="hello12345"):
    db = DatabaseService()
    with db.connection() as conn:
        user = create_invited_user(conn, email, role=role)
        activate_user_with_password(conn, user["id"], password)
    return user


def _make_invited_user(email="invited@example.com", role="member"):
    db = DatabaseService()
    with db.connection() as conn:
        user = create_invited_user(conn, email, role=role)
        token = create_invite_token(conn, user["id"])
    return user, token


# ---------------------------------------------------------------------------
# POST /api/auth/login (password)
# ---------------------------------------------------------------------------


class TestLoginPassword:
    def test_correct_credentials_returns_user_and_session(self, client):
        u = _make_active_user(password="correct123")
        resp = client.post(
            "/api/auth/login",
            json={"email": u["email"], "password": "correct123"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["user"]["id"] == u["id"]
        assert body["user"]["email"] == u["email"]
        assert "password_hash" not in body["user"]
        # Session cookie should be set
        assert "Set-Cookie" in resp.headers

    def test_wrong_password_returns_401(self, client):
        u = _make_active_user(password="correct123")
        resp = client.post(
            "/api/auth/login",
            json={"email": u["email"], "password": "wrong"},
        )
        assert resp.status_code == 401
        assert resp.get_json() == {"error": "invalid credentials"}

    def test_unknown_email_returns_same_401(self, client):
        resp = client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "anything"},
        )
        assert resp.status_code == 401
        assert resp.get_json() == {"error": "invalid credentials"}

    def test_disabled_user_returns_401(self, client):
        u = _make_active_user(password="hello12345")
        db = DatabaseService()
        with db.connection() as conn:
            conn.execute("UPDATE users SET status='disabled' WHERE id=?", (u["id"],))
        resp = client.post(
            "/api/auth/login",
            json={"email": u["email"], "password": "hello12345"},
        )
        assert resp.status_code == 401

    def test_invited_user_no_password_returns_401(self, client):
        u, _ = _make_invited_user()
        resp = client.post(
            "/api/auth/login",
            json={"email": u["email"], "password": "anything"},
        )
        assert resp.status_code == 401

    def test_email_canonicalized_on_login(self, client):
        _make_active_user(email="austin@gmail.com", password="correct123")
        resp = client.post(
            "/api/auth/login",
            json={"email": "  AUSTIN@GMAIL.COM  ", "password": "correct123"},
        )
        assert resp.status_code == 200

    def test_missing_fields_returns_401(self, client):
        resp = client.post("/api/auth/login", json={})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/auth/login/google
# ---------------------------------------------------------------------------


class TestLoginGoogle:
    def _stub_verify(self, monkeypatch, sub, email, name="Test", picture=None):
        def fake_verify(token, audience=None):
            return {"sub": sub, "email": email, "name": name, "picture": picture}

        monkeypatch.setattr(
            "app.routes.auth.auth_service.verify_google_token", fake_verify
        )

    def test_invited_user_activated_by_google(self, client, monkeypatch):
        u, _ = _make_invited_user(email="newcomer@gmail.com")
        self._stub_verify(monkeypatch, sub="g-sub-123", email="newcomer@gmail.com")
        resp = client.post(
            "/api/auth/login/google", json={"id_token": "fake.jwt.token"}
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["user"]["email"] == "newcomer@gmail.com"
        # User now active
        db = DatabaseService()
        with db.connection() as conn:
            row = conn.execute(
                "SELECT status, google_sub FROM users WHERE id=?", (u["id"],)
            ).fetchone()
        assert row[0] == "active"
        assert row[1] == "g-sub-123"

    def test_active_user_with_matching_sub_logs_in(self, client, monkeypatch):
        u = _make_active_user(email="austin@gmail.com")
        # First time: link the sub
        self._stub_verify(monkeypatch, sub="g-sub-abc", email="austin@gmail.com")
        client.post("/api/auth/login/google", json={"id_token": "t1"})
        # Second time: same sub → success
        resp = client.post("/api/auth/login/google", json={"id_token": "t2"})
        assert resp.status_code == 200

    def test_active_user_with_mismatched_sub_403(self, client, monkeypatch):
        u = _make_active_user(email="austin@gmail.com")
        # Link with one sub
        self._stub_verify(monkeypatch, sub="real-sub", email="austin@gmail.com")
        client.post("/api/auth/login/google", json={"id_token": "t1"})
        # Try with different sub → 403
        self._stub_verify(monkeypatch, sub="impostor-sub", email="austin@gmail.com")
        resp = client.post("/api/auth/login/google", json={"id_token": "t2"})
        assert resp.status_code == 403
        assert "mismatch" in resp.get_json()["error"]

    def test_email_not_invited_returns_403(self, client, monkeypatch):
        self._stub_verify(monkeypatch, sub="g-x", email="stranger@gmail.com")
        resp = client.post("/api/auth/login/google", json={"id_token": "t"})
        assert resp.status_code == 403
        assert resp.get_json() == {"error": "not invited"}

    def test_disabled_user_returns_403(self, client, monkeypatch):
        u = _make_active_user(email="ex@gmail.com")
        db = DatabaseService()
        with db.connection() as conn:
            conn.execute("UPDATE users SET status='disabled' WHERE id=?", (u["id"],))
        self._stub_verify(monkeypatch, sub="g-x", email="ex@gmail.com")
        resp = client.post("/api/auth/login/google", json={"id_token": "t"})
        assert resp.status_code == 403
        assert "disabled" in resp.get_json()["error"]

    def test_invalid_token_returns_401(self, client, monkeypatch):
        def raise_(token, audience=None):
            raise ValueError("invalid sig")

        monkeypatch.setattr(
            "app.routes.auth.auth_service.verify_google_token", raise_
        )
        resp = client.post("/api/auth/login/google", json={"id_token": "bad"})
        assert resp.status_code == 401

    def test_missing_token_returns_401(self, client):
        resp = client.post("/api/auth/login/google", json={})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/auth/logout
# ---------------------------------------------------------------------------


class TestLogout:
    def test_logout_clears_session(self, client):
        u = _make_active_user()
        with client.session_transaction() as s:
            s["user_id"] = u["id"]
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 204

    def test_logout_works_without_session(self, client):
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 204


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------


class TestMe:
    def test_unauthenticated_returns_401(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_authenticated_returns_user(self, client):
        u = _make_active_user()
        with client.session_transaction() as s:
            s["user_id"] = u["id"]
        resp = client.get("/api/auth/me")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["user"]["id"] == u["id"]
        assert "password_hash" not in body["user"]


# ---------------------------------------------------------------------------
# GET /api/auth/config
# ---------------------------------------------------------------------------


class TestConfig:
    def test_unset_client_id_returns_has_google_false(self, client, monkeypatch):
        monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
        resp = client.get("/api/auth/config")
        body = resp.get_json()
        assert body == {"has_google": False, "google_client_id": None}

    def test_set_client_id_returns_has_google_true(self, client, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "abc-client-id")
        resp = client.get("/api/auth/config")
        body = resp.get_json()
        assert body == {"has_google": True, "google_client_id": "abc-client-id"}

    def test_config_does_not_require_auth(self, client):
        resp = client.get("/api/auth/config")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/auth/invite/<token>
# ---------------------------------------------------------------------------


class TestInviteInfo:
    def test_valid_token_returns_user_and_inviter(self, client):
        u, token = _make_invited_user(email="invitee@example.com")
        resp = client.get(f"/api/auth/invite/{token}")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["valid"] is True
        assert body["expired"] is False
        assert body["user"]["email"] == "invitee@example.com"

    def test_invalid_token_returns_valid_false(self, client):
        resp = client.get("/api/auth/invite/nonexistent-token")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["valid"] is False
        assert body["expired"] is False
        assert body["user"] is None

    def test_used_token_returns_valid_false(self, client):
        u, token = _make_invited_user()
        db = DatabaseService()
        with db.connection() as conn:
            from app.services.user_service import mark_token_used
            mark_token_used(conn, token)
        resp = client.get(f"/api/auth/invite/{token}")
        body = resp.get_json()
        assert body["valid"] is False


# ---------------------------------------------------------------------------
# POST /api/auth/accept-invite
# ---------------------------------------------------------------------------


class TestAcceptInvite:
    def test_valid_token_and_password_activates(self, client):
        u, token = _make_invited_user(email="newcomer@example.com")
        resp = client.post(
            "/api/auth/accept-invite",
            json={"token": token, "password": "newpass1234"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["user"]["email"] == "newcomer@example.com"
        # User is now active with password set
        db = DatabaseService()
        with db.connection() as conn:
            row = conn.execute(
                "SELECT status, password_hash FROM users WHERE id=?", (u["id"],)
            ).fetchone()
        assert row[0] == "active"
        assert row[1] is not None
        # Token marked used
        with db.connection() as conn:
            row = conn.execute(
                "SELECT used_at FROM invite_tokens WHERE token=?", (token,)
            ).fetchone()
        assert row[0] is not None

    def test_password_too_short_returns_400(self, client):
        u, token = _make_invited_user()
        resp = client.post(
            "/api/auth/accept-invite", json={"token": token, "password": "short"}
        )
        assert resp.status_code == 400
        assert "8 characters" in resp.get_json()["error"]

    def test_used_token_returns_410(self, client):
        u, token = _make_invited_user()
        # First accept
        client.post(
            "/api/auth/accept-invite",
            json={"token": token, "password": "valid12345"},
        )
        # Second attempt
        resp = client.post(
            "/api/auth/accept-invite",
            json={"token": token, "password": "valid12345"},
        )
        assert resp.status_code == 410

    def test_invalid_token_returns_410(self, client):
        resp = client.post(
            "/api/auth/accept-invite",
            json={"token": "nonexistent", "password": "valid12345"},
        )
        assert resp.status_code == 410


# ---------------------------------------------------------------------------
# POST /api/auth/change-password
# ---------------------------------------------------------------------------


class TestChangePassword:
    def test_unauthenticated_returns_401(self, client):
        resp = client.post(
            "/api/auth/change-password",
            json={"old_password": "x", "new_password": "newpass1234"},
        )
        assert resp.status_code == 401

    def test_correct_old_password_succeeds(self, client):
        u = _make_active_user(password="oldpass1234")
        with client.session_transaction() as s:
            s["user_id"] = u["id"]
        resp = client.post(
            "/api/auth/change-password",
            json={"old_password": "oldpass1234", "new_password": "newpass5678"},
        )
        assert resp.status_code == 200
        # New password works for login
        resp2 = client.post(
            "/api/auth/login",
            json={"email": u["email"], "password": "newpass5678"},
        )
        assert resp2.status_code == 200

    def test_wrong_old_password_returns_401(self, client):
        u = _make_active_user(password="oldpass1234")
        with client.session_transaction() as s:
            s["user_id"] = u["id"]
        resp = client.post(
            "/api/auth/change-password",
            json={"old_password": "wrong-old", "new_password": "newpass5678"},
        )
        assert resp.status_code == 401

    def test_short_new_password_returns_400(self, client):
        u = _make_active_user()
        with client.session_transaction() as s:
            s["user_id"] = u["id"]
        resp = client.post(
            "/api/auth/change-password",
            json={"old_password": "hello12345", "new_password": "short"},
        )
        assert resp.status_code == 400

    def test_same_as_old_returns_400(self, client):
        u = _make_active_user(password="hello12345")
        with client.session_transaction() as s:
            s["user_id"] = u["id"]
        resp = client.post(
            "/api/auth/change-password",
            json={"old_password": "hello12345", "new_password": "hello12345"},
        )
        assert resp.status_code == 400
