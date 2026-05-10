import os
from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def env_vars(tmp_path, monkeypatch):
    """Provide required env vars and use tmp SQLite path for tests."""
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("LLM_MODEL", "claude-haiku-4-5-20251001")
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-3-small")
    monkeypatch.setenv("QDRANT_HOST", "localhost")
    monkeypatch.setenv("QDRANT_PORT", "6333")
    monkeypatch.setenv("FLASK_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("UPLOADS_PATH", str(tmp_path / "uploads"))


# Tests in these files explicitly exercise the auth machinery and must NOT
# get the bypass — they need real session validation behavior.
_AUTH_TEST_FILES = (
    "test_auth_routes.py",
    "test_middleware_require_auth.py",
    "test_auth_service_password.py",
    "test_auth_service_google.py",
    "test_users_schema.py",
    "test_email_canonicalization.py",
    "test_bootstrap_migration.py",
)


@pytest.fixture(autouse=True)
def bypass_auth_for_legacy_tests(request, monkeypatch):
    """Most existing tests assume `user_id="default"` (single-tenant V1).
    multi-user-auth-core requires a real session. To preserve the existing
    test suite without rewriting every assertion, monkeypatch the
    `_validate_session()` function in the middleware to return a fixed
    test user. Tests that need to exercise the real auth machinery are
    excluded via _AUTH_TEST_FILES.

    The fake user has id="default" so existing fixtures that pass
    `user_id="default"` to file_service / etc still resolve to the same
    rows the route handlers (now using `g.user.id`) will query.
    """
    test_file = os.path.basename(str(request.node.fspath))
    if test_file in _AUTH_TEST_FILES:
        return  # Real auth behavior

    fake_user = SimpleNamespace(
        id="default",
        email="test@example.com",
        google_sub=None,
        password_hash=None,
        name="Test User",
        picture_url=None,
        role="admin",
        status="active",
        invited_at="2026-05-09T00:00:00Z",
        invited_by=None,
        activated_at="2026-05-09T00:00:00Z",
        last_login_at="2026-05-09T00:00:00Z",
    )
    monkeypatch.setattr("app.middleware._validate_session", lambda: fake_user)
