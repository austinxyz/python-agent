import os
import pytest
from unittest.mock import patch, MagicMock


REQUIRED_VARS = [
    "LLM_PROVIDER", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
    "LLM_MODEL", "EMBEDDING_MODEL", "QDRANT_HOST", "QDRANT_PORT",
    "FLASK_SECRET_KEY",
]

STUB_ROUTES = [
    "/api/wiki", "/api/chat",
    "/api/private", "/api/files", "/api/prompts",
]


def _make_app(monkeypatch, tmp_path):
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
    with patch("app.services.qdrant_service.QdrantClient") as MockQdrant:
        MockQdrant.return_value.get_collection.return_value = MagicMock()
        from app import create_app
        flask_app = create_app({"TESTING": True})
    return flask_app


def test_missing_openai_api_key_raises(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        from app import create_app
        create_app()


def test_health_endpoint_returns_200(monkeypatch, tmp_path):
    app = _make_app(monkeypatch, tmp_path)
    client = app.test_client()
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"


@pytest.mark.parametrize("route", STUB_ROUTES)
def test_stub_routes_return_200(monkeypatch, tmp_path, route):
    app = _make_app(monkeypatch, tmp_path)
    client = app.test_client()
    resp = client.get(route)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["stub"] is True
