"""Integration tests for IngestPipeline (Group 5, tasks 5.2 and 5.4)."""
from unittest.mock import MagicMock, patch

import pytest

from app.graphs.ingest_pipeline import IngestPipeline


@pytest.fixture()
def mock_embedding():
    with patch("app.graphs.ingest_pipeline.EmbeddingService") as MockEmbed:
        MockEmbed.return_value.embed.return_value = [0.0] * 1536
        yield MockEmbed


@pytest.fixture()
def mock_qdrant():
    with patch("app.graphs.ingest_pipeline.QdrantService") as MockQdrant:
        MockQdrant.return_value.upsert_knowledge = MagicMock()
        MockQdrant.return_value.upsert_private = MagicMock()
        yield MockQdrant


@pytest.fixture()
def mock_db(tmp_path, monkeypatch):
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("UPLOADS_PATH", str(tmp_path / "uploads"))


class TestIngestPipelineKnowledge:
    def test_text_ingest_returns_completed_status(self, mock_embedding, mock_qdrant, mock_db):
        pipeline = IngestPipeline()
        result = pipeline.run(
            source_type="text",
            content="hello world, this is a test document",
            destination="knowledge",
            user_id="default",
            orig_name="test.txt",
            domain="general",
            topic="test",
        )
        assert result["status"] == "completed"
        assert result["chunk_count"] >= 1

    def test_text_ingest_returns_non_null_file_id(self, mock_embedding, mock_qdrant, mock_db):
        pipeline = IngestPipeline()
        result = pipeline.run(
            source_type="text",
            content="hello world",
            destination="knowledge",
            user_id="default",
        )
        assert result["file_id"] is not None
        assert len(result["file_id"]) > 0


class TestIngestPipelinePrivateDestination:
    def test_private_destination_upsert_includes_user_id_in_every_payload(
        self, mock_embedding, mock_qdrant, mock_db
    ):
        pipeline = IngestPipeline()
        pipeline.run(
            source_type="text",
            content="private document content",
            destination="private",
            user_id="default",
            domain="finance",
            topic="budget",
        )

        upsert_calls = mock_qdrant.return_value.upsert_private.call_args_list
        assert len(upsert_calls) >= 1
        for call in upsert_calls:
            points = call.args[0] if call.args else call.kwargs["points"]
            for pt in points:
                assert pt.payload.get("user_id") == "default", (
                    f"private chunk missing user_id: {pt.payload}"
                )

    def test_knowledge_destination_upsert_excludes_user_id(
        self, mock_embedding, mock_qdrant, mock_db
    ):
        pipeline = IngestPipeline()
        pipeline.run(
            source_type="text",
            content="public knowledge content",
            destination="knowledge",
            user_id="default",
        )

        upsert_calls = mock_qdrant.return_value.upsert_knowledge.call_args_list
        assert len(upsert_calls) >= 1
        for call in upsert_calls:
            points = call.args[0] if call.args else call.kwargs["points"]
            for pt in points:
                assert "user_id" not in pt.payload, (
                    f"knowledge chunk must not contain user_id: {pt.payload}"
                )

    def test_empty_user_id_for_private_returns_error(self, mock_embedding, mock_qdrant, mock_db):
        pipeline = IngestPipeline()
        result = pipeline.run(
            source_type="text",
            content="private content",
            destination="private",
            user_id="",
        )
        assert result["status"] == "error"
        assert "user_id" in result["error"]
        # Qdrant must NOT have been called — no data written
        mock_qdrant.return_value.upsert_private.assert_not_called()

    def test_unknown_destination_returns_error(self, mock_embedding, mock_qdrant, mock_db):
        pipeline = IngestPipeline()
        result = pipeline.run(
            source_type="text",
            content="some content",
            destination="public",
            user_id="default",
        )
        assert result["status"] == "error"
        assert "destination" in result["error"]
        mock_qdrant.return_value.upsert_knowledge.assert_not_called()
        mock_qdrant.return_value.upsert_private.assert_not_called()


class TestIngestPipelineErrorHandling:
    def test_embed_failure_returns_error_status(self, mock_qdrant, mock_db):
        with patch("app.graphs.ingest_pipeline.EmbeddingService") as MockEmbed:
            MockEmbed.return_value.embed.side_effect = RuntimeError("API quota exceeded")
            pipeline = IngestPipeline()
            result = pipeline.run(
                source_type="text",
                content="some document",
                destination="knowledge",
                user_id="default",
            )
        assert result["status"] == "error"
        assert "API quota exceeded" in result["error"]

    def test_qdrant_failure_returns_error_status(self, mock_embedding, mock_db):
        with patch("app.graphs.ingest_pipeline.QdrantService") as MockQdrant:
            MockQdrant.return_value.upsert_knowledge.side_effect = RuntimeError("Qdrant down")
            pipeline = IngestPipeline()
            result = pipeline.run(
                source_type="text",
                content="some document",
                destination="knowledge",
                user_id="default",
            )
        assert result["status"] == "error"
        assert "Qdrant down" in result["error"]
