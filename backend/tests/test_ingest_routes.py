"""RED-phase tests for POST /api/ingest and GET /api/ingest/status/<job_id> (Group 6)."""
import io
from unittest.mock import MagicMock, patch

import pytest


def _make_app(monkeypatch, tmp_path):
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("UPLOADS_PATH", str(tmp_path / "uploads"))
    with patch("app.services.qdrant_service.QdrantClient") as MockQdrant:
        MockQdrant.return_value.get_collection.return_value = MagicMock()
        from app import create_app
        return create_app({"TESTING": True})


@pytest.fixture()
def client(monkeypatch, tmp_path):
    app = _make_app(monkeypatch, tmp_path)
    return app.test_client()


# ---------------------------------------------------------------------------
# POST /api/ingest — validation (task 6.1)
# ---------------------------------------------------------------------------

class TestIngestPostValidation:
    def test_missing_source_type_returns_400(self, client):
        resp = client.post("/api/ingest", data={"destination": "knowledge"})
        assert resp.status_code == 400
        assert "source_type" in resp.get_json().get("error", "")

    def test_file_source_without_file_returns_400(self, client):
        resp = client.post("/api/ingest", data={
            "source_type": "file",
            "destination": "knowledge",
        })
        assert resp.status_code == 400

    def test_destination_public_returns_400(self, client):
        resp = client.post("/api/ingest", data={
            "source_type": "text",
            "content": "hello",
            "destination": "public",
        })
        assert resp.status_code == 400

    def test_valid_file_upload_returns_202_with_job_id(self, client):
        with patch("app.routes.ingest.IngestPipeline"), \
             patch("app.routes.ingest.job_registry"):
            resp = client.post("/api/ingest", data={
                "source_type": "file",
                "destination": "knowledge",
                "file": (io.BytesIO(b"fake pdf content"), "test.pdf"),
            }, content_type="multipart/form-data")

        assert resp.status_code == 202
        data = resp.get_json()
        assert "job_id" in data
        assert len(data["job_id"]) > 0

    def test_file_exceeding_50mb_returns_413(self, client):
        large_content = b"x" * (50 * 1024 * 1024 + 1)
        resp = client.post("/api/ingest", data={
            "source_type": "file",
            "destination": "knowledge",
            "file": (io.BytesIO(large_content), "big.pdf"),
        }, content_type="multipart/form-data")

        assert resp.status_code == 413
        data = resp.get_json()
        assert "error" in data
        assert "50 MB" in data["error"]


# ---------------------------------------------------------------------------
# GET /api/ingest/status/<job_id> (task 6.2)
# ---------------------------------------------------------------------------

_VALID_UUID = "00000000-0000-0000-0000-000000000001"
_RUNNING_UUID = "00000000-0000-0000-0000-000000000002"
_DONE_UUID = "00000000-0000-0000-0000-000000000003"


class TestIngestStatusEndpoint:
    def test_unknown_job_id_returns_404(self, client):
        with patch("app.routes.ingest.job_registry") as mock_reg:
            mock_reg.get.return_value = None
            resp = client.get(f"/api/ingest/status/{_VALID_UUID}")
        assert resp.status_code == 404

    def test_invalid_job_id_format_returns_400(self, client):
        resp = client.get("/api/ingest/status/not-a-uuid")
        assert resp.status_code == 400

    def test_running_job_returns_running_status(self, client):
        with patch("app.routes.ingest.job_registry") as mock_reg:
            mock_reg.get.return_value = {"status": "running"}
            resp = client.get(f"/api/ingest/status/{_RUNNING_UUID}")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "running"

    def test_completed_job_returns_completed_with_file_id_and_chunk_count(self, client):
        with patch("app.routes.ingest.job_registry") as mock_reg:
            mock_reg.get.return_value = {
                "status": "completed",
                "file_id": "file-xyz",
                "chunk_count": 5,
            }
            resp = client.get(f"/api/ingest/status/{_DONE_UUID}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "completed"
        assert data["file_id"] == "file-xyz"
        assert data["chunk_count"] == 5
