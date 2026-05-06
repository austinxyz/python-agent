"""RED-phase unit tests for IngestPipeline nodes (Group 4).
All tests fail with ImportError until Group 5 creates ingest_pipeline.py.
"""
from unittest.mock import MagicMock, patch

from qdrant_client.http.models import PointStruct

from app.graphs.ingest_pipeline import (
    IngestState,
    chunk_node,
    clean_node,
    embed_node,
    fetch_node,
    source_router_node,
    store_node,
    summary_node,
)

# Overlap size is fixed at 200 per spec (Chunk Node requirement)
CHUNK_OVERLAP = 200


def _state(**overrides) -> dict:
    base: dict = {
        "source_type": "text",
        "destination": "knowledge",
        "user_id": "default",
        "content": None,
        "file_content": None,
        "source_url": None,
        "filename": None,
        "orig_name": "test.txt",
        "domain": "general",
        "topic": "test",
        "raw_content": None,
        "chunks": None,
        "vectors": None,
        "file_id": "file-test-001",
        "job_id": "job-test-001",
        "chunk_count": 0,
        "size_bytes": 0,
        "status": "running",
        "error": None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Source Router (task 4.1)
# ---------------------------------------------------------------------------

class TestSourceRouterNode:
    def test_file_source_passes_through(self):
        result = source_router_node(_state(source_type="file"))
        assert result.get("status") != "error"

    def test_url_source_passes_through(self):
        result = source_router_node(_state(source_type="url"))
        assert result.get("status") != "error"

    def test_text_source_passes_through(self):
        result = source_router_node(_state(source_type="text"))
        assert result.get("status") != "error"

    def test_mcp_source_passes_through_without_router_error(self):
        # The router accepts mcp; the Fetch Node is responsible for the not-implemented error
        result = source_router_node(_state(source_type="mcp"))
        assert result.get("status") != "error"

    def test_unrecognised_source_type_sets_error(self):
        result = source_router_node(_state(source_type="ftp"))
        assert result["status"] == "error"
        assert "unsupported source_type" in result["error"]


# ---------------------------------------------------------------------------
# Fetch Node (task 4.2)
# ---------------------------------------------------------------------------

class TestFetchNode:
    def test_pdf_file_extracts_page_text(self):
        fake_page = MagicMock()
        fake_page.get_text.return_value = "page one content"
        fake_doc = MagicMock()
        fake_doc.__iter__ = MagicMock(side_effect=lambda: iter([fake_page]))
        # Support `with fitz.open(...) as doc:` — __enter__ must return the doc itself
        fake_doc.__enter__ = MagicMock(return_value=fake_doc)
        fake_doc.__exit__ = MagicMock(return_value=False)

        with patch("app.graphs.ingest_pipeline.fitz") as mock_fitz:
            mock_fitz.open.return_value = fake_doc
            result = fetch_node(_state(
                source_type="file",
                file_content=b"%PDF fake",
                filename="doc.pdf",
            ))
            mock_fitz.open.assert_called_once()

        assert result.get("status") != "error"
        assert "page one content" in result["raw_content"]

    def test_url_fetch_extracts_visible_text_from_html(self):
        fake_resp = MagicMock()
        fake_resp.text = "<html><body><p>Hello from URL</p></body></html>"
        fake_resp.headers = {"content-type": "text/html; charset=utf-8"}
        fake_resp.raise_for_status = MagicMock()

        with patch("app.graphs.ingest_pipeline.httpx") as mock_httpx:
            mock_httpx.get.return_value = fake_resp
            result = fetch_node(_state(
                source_type="url",
                source_url="https://example.com",
            ))

        assert result.get("status") != "error"
        assert "Hello from URL" in result["raw_content"]

    def test_text_source_passes_content_unchanged(self):
        result = fetch_node(_state(source_type="text", content="direct text"))
        assert result["raw_content"] == "direct text"

    def test_mcp_fetch_branch_sets_not_implemented_error(self):
        # mcp is routed here by the Source Router; Fetch Node returns the stub error
        result = fetch_node(_state(source_type="mcp"))
        assert result["status"] == "error"
        assert "mcp not yet implemented" in result["error"]


# ---------------------------------------------------------------------------
# Clean Node (task 4.3)
# ---------------------------------------------------------------------------

class TestCleanNode:
    def test_collapses_three_blank_lines_to_one(self):
        result = clean_node(_state(raw_content="line1\n\n\n\nline2"))
        assert "\n\n\n" not in result["raw_content"]
        assert "line1" in result["raw_content"]
        assert "line2" in result["raw_content"]

    def test_strips_leading_and_trailing_whitespace(self):
        result = clean_node(_state(raw_content="   hello   "))
        assert result["raw_content"] == "hello"

    def test_removes_null_byte(self):
        result = clean_node(_state(raw_content="hel\x00lo"))
        assert "\x00" not in result["raw_content"]
        assert "hello" in result["raw_content"]

    def test_preserves_non_ascii_unicode(self):
        result = clean_node(_state(raw_content="财务报告 résumé café"))
        assert "财务报告" in result["raw_content"]
        assert "résumé" in result["raw_content"]
        assert "café" in result["raw_content"]


# ---------------------------------------------------------------------------
# Chunk Node (task 4.4)
# ---------------------------------------------------------------------------

class TestChunkNode:
    def test_500_char_input_produces_single_chunk_with_index_zero(self):
        result = chunk_node(_state(raw_content="x" * 500))
        assert len(result["chunks"]) == 1
        assert result["chunks"][0]["chunk_index"] == 0

    def test_5000_char_input_produces_at_least_three_chunks(self):
        # Three paragraphs of ~1700 chars each (each < 2000 chunk_size, so each becomes one chunk)
        para = "word " * 340  # 340 * 5 = 1700 chars
        content = f"{para}\n\n{para}\n\n{para}"
        result = chunk_node(_state(raw_content=content))
        assert len(result["chunks"]) >= 3

    def test_second_chunk_starts_with_last_200_chars_of_first(self):
        # Per spec: 200-char overlap prepended to each subsequent chunk
        para = "word " * 340
        content = f"{para}\n\n{para}\n\n{para}"
        result = chunk_node(_state(raw_content=content))
        chunks = result["chunks"]
        assert len(chunks) >= 2
        overlap = chunks[0]["text"][-CHUNK_OVERLAP:]
        assert chunks[1]["text"].startswith(overlap)


# ---------------------------------------------------------------------------
# Embed Node (task 4.5)
# ---------------------------------------------------------------------------

class TestEmbedNode:
    def test_vector_count_matches_chunk_count(self):
        chunks = [
            {"text": "chunk one", "chunk_index": 0},
            {"text": "chunk two", "chunk_index": 1},
        ]
        with patch("app.graphs.ingest_pipeline.EmbeddingService") as MockEmbed:
            MockEmbed.return_value.embed.return_value = [0.0] * 1536
            result = embed_node(_state(chunks=chunks))

        assert len(result["vectors"]) == 2

    def test_each_vector_has_1536_dimensions(self):
        chunks = [{"text": "hello", "chunk_index": 0}]
        with patch("app.graphs.ingest_pipeline.EmbeddingService") as MockEmbed:
            MockEmbed.return_value.embed.return_value = [0.0] * 1536
            result = embed_node(_state(chunks=chunks))

        assert len(result["vectors"][0]) == 1536

    def test_embed_called_with_chunk_text(self):
        chunks = [
            {"text": "chunk one", "chunk_index": 0},
            {"text": "chunk two", "chunk_index": 1},
        ]
        with patch("app.graphs.ingest_pipeline.EmbeddingService") as MockEmbed:
            MockEmbed.return_value.embed.return_value = [0.0] * 1536
            embed_node(_state(chunks=chunks))
            calls = MockEmbed.return_value.embed.call_args_list

        assert calls[0].args[0] == "chunk one"
        assert calls[1].args[0] == "chunk two"


# ---------------------------------------------------------------------------
# Store Node (task 4.6)
# ---------------------------------------------------------------------------

def _store_state(destination: str) -> dict:
    return _state(
        destination=destination,
        chunks=[{"text": "some text", "chunk_index": 0}],
        vectors=[[0.0] * 1536],
        file_id="file-store-001",
        orig_name="test.pdf",
        domain="finance",
        topic="budget",
        size_bytes=1024,
        chunk_count=1,
    )


class TestStoreNode:
    def test_knowledge_upsert_payload_excludes_user_id(self):
        with patch("app.graphs.ingest_pipeline.QdrantService") as MockQdrant, \
             patch("app.graphs.ingest_pipeline.FileService"), \
             patch("app.graphs.ingest_pipeline.DatabaseService"):
            store_node(_store_state("knowledge"))

        calls = MockQdrant.return_value.upsert_knowledge.call_args_list
        assert len(calls) >= 1
        for call in calls:
            points = call.args[0] if call.args else call.kwargs["points"]
            for pt in points:
                assert isinstance(pt, PointStruct), "points must be PointStruct objects"
                assert isinstance(pt.payload, dict)
                assert "text" in pt.payload
                assert "user_id" not in pt.payload

    def test_private_upsert_payload_includes_user_id(self):
        state = _store_state("private")
        state["user_id"] = "default"

        with patch("app.graphs.ingest_pipeline.QdrantService") as MockQdrant, \
             patch("app.graphs.ingest_pipeline.FileService"), \
             patch("app.graphs.ingest_pipeline.DatabaseService"):
            store_node(state)

        calls = MockQdrant.return_value.upsert_private.call_args_list
        assert len(calls) >= 1
        for call in calls:
            points = call.args[0] if call.args else call.kwargs["points"]
            for pt in points:
                assert isinstance(pt, PointStruct), "points must be PointStruct objects"
                assert isinstance(pt.payload, dict)
                assert pt.payload.get("user_id") == "default"

    def test_file_service_register_called_exactly_once(self):
        with patch("app.graphs.ingest_pipeline.QdrantService"), \
             patch("app.graphs.ingest_pipeline.FileService") as MockFile, \
             patch("app.graphs.ingest_pipeline.DatabaseService"):
            store_node(_store_state("knowledge"))

        MockFile.return_value.register.assert_called_once()


# ---------------------------------------------------------------------------
# Summary Node (task 4.7)
# ---------------------------------------------------------------------------

class TestSummaryNode:
    def test_success_state_returns_completed_with_file_id_and_chunk_count(self):
        state = _state(status="running", file_id="file-sum-001", chunk_count=3)
        result = summary_node(state)
        assert result["status"] == "completed"
        assert result["file_id"] == "file-sum-001"
        assert result["chunk_count"] == 3

    def test_error_state_returns_error_and_nullifies_file_id(self):
        # summary_node must explicitly set file_id=None in the error path,
        # since LangGraph state carries forward fields not returned by a node
        state = _state(status="error", error="something went wrong")
        result = summary_node(state)
        assert result["status"] == "error"
        assert result["error"] == "something went wrong"
        assert result.get("file_id") is None
