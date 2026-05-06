import os
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
