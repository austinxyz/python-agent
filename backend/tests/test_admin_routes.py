"""Tests for @require_admin decorator + GET /api/admin/cert-status.

Groups 2.1 (cert-status) + 2.3 (require_admin isolation).
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from flask import Flask, jsonify

from app.middleware import require_admin
from app.routes.admin import admin_bp
from app.services.db_service import DatabaseService

# ---------------------------------------------------------------------------
# Shared fake users
# ---------------------------------------------------------------------------

_ADMIN = SimpleNamespace(id="admin-uuid", email="admin@example.com", role="admin", status="active")
_MEMBER = SimpleNamespace(id="member-uuid", email="member@example.com", role="member", status="active")

# ---------------------------------------------------------------------------
# Fixtures — cert-status app
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    a = Flask(__name__)
    a.secret_key = "test-secret"
    a.register_blueprint(admin_bp, url_prefix="/api/admin")
    return a


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Fixtures — require_admin isolation app
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_app():
    a = Flask(__name__)
    a.secret_key = "test-secret"

    @a.get("/admin-only")
    @require_admin
    def admin_only():
        return jsonify({"ok": True})

    return a


@pytest.fixture
def admin_client(admin_app):
    return admin_app.test_client()


# ---------------------------------------------------------------------------
# 2.3: @require_admin isolation
# ---------------------------------------------------------------------------


class TestRequireAdmin:
    def test_admin_proceeds(self, admin_client, monkeypatch):
        monkeypatch.setattr("app.middleware._validate_session", lambda: _ADMIN)
        assert admin_client.get("/admin-only").status_code == 200

    def test_member_gets_403(self, admin_client, monkeypatch):
        monkeypatch.setattr("app.middleware._validate_session", lambda: _MEMBER)
        resp = admin_client.get("/admin-only")
        assert resp.status_code == 403
        assert resp.get_json() == {"error": "admin required"}

    def test_unauthenticated_gets_401(self, admin_client, monkeypatch):
        monkeypatch.setattr("app.middleware._validate_session", lambda: None)
        assert admin_client.get("/admin-only").status_code == 401


# ---------------------------------------------------------------------------
# 2.1: GET /api/admin/cert-status
# ---------------------------------------------------------------------------

_CERT_OK = {
    "hostname": "python-agent.tail-test.ts.net",
    "cert_expiry_iso": "2026-08-14T06:00:00+00:00",
    "days_remaining": 90,
    "tailscale_status": "online",
    "last_renew_iso": "2026-05-16T06:00:00+00:00",
}

_CERT_OFFLINE = {
    "hostname": "python-agent.tail-test.ts.net",
    "cert_expiry_iso": None,
    "days_remaining": None,
    "tailscale_status": "offline",
    "last_renew_iso": None,
}

_EXPECTED_FIELDS = {"hostname", "cert_expiry_iso", "days_remaining", "tailscale_status", "last_renew_iso"}


class TestCertStatus:
    def test_admin_200_valid_shape(self, client, monkeypatch):
        monkeypatch.setattr("app.middleware._validate_session", lambda: _ADMIN)
        with patch("app.routes.admin.tailscale_service.get_cert_status", return_value=_CERT_OK):
            resp = client.get("/api/admin/cert-status")
        assert resp.status_code == 200
        assert _EXPECTED_FIELDS == set(resp.get_json().keys())

    def test_member_gets_403(self, client, monkeypatch):
        monkeypatch.setattr("app.middleware._validate_session", lambda: _MEMBER)
        resp = client.get("/api/admin/cert-status")
        assert resp.status_code == 403
        assert resp.get_json() == {"error": "admin required"}

    def test_unauthenticated_gets_401(self, client, monkeypatch):
        monkeypatch.setattr("app.middleware._validate_session", lambda: None)
        assert client.get("/api/admin/cert-status").status_code == 401

    def test_tailscale_cli_fails_returns_200_offline(self, client, monkeypatch):
        monkeypatch.setattr("app.middleware._validate_session", lambda: _ADMIN)
        with patch("app.routes.admin.tailscale_service.get_cert_status", return_value=_CERT_OFFLINE):
            resp = client.get("/api/admin/cert-status")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["tailscale_status"] == "offline"
        assert body["cert_expiry_iso"] is None
        assert body["days_remaining"] is None
        assert body["last_renew_iso"] is None
