import pytest
from unittest.mock import MagicMock, patch


def test_llm_service_uses_anthropic_client_when_configured(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("LLM_MODEL", "claude-haiku-4-5-20251001")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    with patch("app.services.llm_service.anthropic.Anthropic") as MockAnthropic:
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text="hi")]
        )
        from app.services.llm_service import LlmService
        svc = LlmService()
        result = svc.complete([{"role": "user", "content": "hello"}])
        MockAnthropic.assert_called_once()
        mock_client.messages.create.assert_called_once()
        assert result == "hi"


def test_llm_service_uses_openai_client_when_configured(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    with patch("app.services.llm_service.openai.OpenAI") as MockOpenAI:
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="hi"))]
        )
        from app.services.llm_service import LlmService
        svc = LlmService()
        result = svc.complete([{"role": "user", "content": "hello"}])
        MockOpenAI.assert_called_once()
        assert result == "hi"


def test_embedding_service_always_uses_openai(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-3-small")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    with patch("app.services.embedding_service.openai.OpenAI") as MockOpenAI:
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        mock_client.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=[0.0] * 1536)]
        )
        from app.services.embedding_service import EmbeddingService
        svc = EmbeddingService()
        result = svc.embed("hello")
        MockOpenAI.assert_called_once()
        assert len(result) == 1536
