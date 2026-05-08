"""Unit tests for the QA agent tool functions.

The tools are plain Python functions that accept injected service instances.
We mock EmbeddingService + QdrantService at the call boundary to keep these
tests pure — no live Qdrant, no LLM, no real file I/O for the search tools.
"""
from unittest.mock import MagicMock, patch
from pathlib import Path

import pytest


def _mock_qdrant_point(score: float, content: str, domain: str, source_file_id: str, **extra):
    """Mirror the payload shape ingest_pipeline._embed_node actually writes —
    chunk text under `text`, not `content`."""
    p = MagicMock()
    p.score = score
    p.payload = {
        "text": content,
        "domain": domain,
        "source_file_id": source_file_id,
        **extra,
    }
    return p


# ---------------------------------------------------------------------------
# search_knowledge
# ---------------------------------------------------------------------------


class TestSearchKnowledge:
    def test_returns_formatted_chunks(self, monkeypatch):
        from app.graphs import qa_agent

        emb = MagicMock()
        emb.embed.return_value = [0.0] * 1536

        qdr = MagicMock()
        qdr.search_knowledge.return_value = [
            _mock_qdrant_point(0.91, "Roth IRA 概要", "退休规划", "f1"),
            _mock_qdrant_point(0.72, "401k 入门", "退休规划", "f2"),
            _mock_qdrant_point(0.65, "AMT 基础", "税务策略", "f3"),
        ]

        result = qa_agent.search_knowledge("退休账户怎么选", embedding=emb, qdrant=qdr)

        assert len(result) == 3
        first = result[0]
        assert first["content"] == "Roth IRA 概要"
        assert first["domain"] == "退休规划"
        assert first["source_file_id"] == "f1"
        assert first["score"] == 0.91

    def test_does_not_apply_user_id_filter(self):
        from app.graphs import qa_agent

        emb = MagicMock()
        emb.embed.return_value = [0.0] * 1536
        qdr = MagicMock()
        qdr.search_knowledge.return_value = []

        qa_agent.search_knowledge("anything", embedding=emb, qdrant=qdr)

        # No user_id keyword passed
        call_kwargs = qdr.search_knowledge.call_args.kwargs
        assert "user_id" not in call_kwargs

    def test_optional_domain_filter_passed_through(self):
        from app.graphs import qa_agent

        emb = MagicMock()
        emb.embed.return_value = [0.0] * 1536
        qdr = MagicMock()
        qdr.search_knowledge.return_value = []

        qa_agent.search_knowledge("retirement", domain="退休规划", embedding=emb, qdrant=qdr)

        call_kwargs = qdr.search_knowledge.call_args.kwargs
        assert call_kwargs.get("domain") == "退休规划"


# ---------------------------------------------------------------------------
# search_private
# ---------------------------------------------------------------------------


class TestSearchPrivate:
    def test_always_applies_user_id_filter(self):
        from app.graphs import qa_agent

        emb = MagicMock()
        emb.embed.return_value = [0.0] * 1536
        qdr = MagicMock()
        qdr.search_private.return_value = []

        qa_agent.search_private("我的房产情况", embedding=emb, qdrant=qdr)

        call = qdr.search_private.call_args
        # user_id MUST be passed; missing is a critical bug
        passed_user_id = call.kwargs.get("user_id") if call.kwargs else None
        if passed_user_id is None and len(call.args) >= 2:
            passed_user_id = call.args[1]
        assert passed_user_id == "default"

    def test_returns_formatted_chunks(self):
        from app.graphs import qa_agent

        emb = MagicMock()
        emb.embed.return_value = [0.0] * 1536
        qdr = MagicMock()
        qdr.search_private.return_value = [
            _mock_qdrant_point(0.88, "San Jose 自住房资产", "房产资产", "p1", template_type="real_estate"),
        ]

        result = qa_agent.search_private("房产", embedding=emb, qdrant=qdr)

        assert len(result) == 1
        item = result[0]
        assert item["content"] == "San Jose 自住房资产"
        assert item["domain"] == "房产资产"  # for private, "domain" carries template_type or directory; payload mapping documented in qa_agent.py
        assert item["source_file_id"] == "p1"
        assert item["score"] == 0.88


# ---------------------------------------------------------------------------
# get_entry
# ---------------------------------------------------------------------------


class TestGetEntry:
    def test_returns_text_when_file_exists(self, tmp_path, monkeypatch):
        from app.graphs import qa_agent
        # Lay out a file under UPLOADS_PATH/default/{file_id}/{file_id}.txt
        monkeypatch.setenv("UPLOADS_PATH", str(tmp_path))
        file_id = "abc123"
        file_dir = tmp_path / "default" / file_id
        file_dir.mkdir(parents=True)
        (file_dir / f"{file_id}.txt").write_text("Hello content\n第二段。", encoding="utf-8")

        result = qa_agent.get_entry(file_id)
        assert "Hello content" in result
        assert "第二段" in result

    def test_returns_error_marker_when_missing(self, tmp_path, monkeypatch):
        from app.graphs import qa_agent
        monkeypatch.setenv("UPLOADS_PATH", str(tmp_path))
        result = qa_agent.get_entry("nonexistent-id")
        # The agent must not raise — it should return a string indicating
        # the file was not found, so the LLM can respond gracefully.
        assert "not found" in result.lower() or "未找到" in result or "无法" in result
