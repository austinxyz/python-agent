"""Tests for GET /api/files — verifies title field is present in response."""
from unittest.mock import MagicMock, patch

import pytest

from app.services.db_service import DatabaseService
from app.services.file_service import FileService


def _make_app(monkeypatch, tmp_path):
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("UPLOADS_PATH", str(tmp_path / "uploads"))
    with patch("app.services.qdrant_service.QdrantClient") as MockQdrant:
        MockQdrant.return_value.get_collection.return_value = MagicMock()
        from app import create_app
        return create_app({"TESTING": True})


class TestListFilesTitle:
    def test_get_files_response_includes_title_field(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        db = DatabaseService()
        svc = FileService()
        with db.connection() as conn:
            svc.register(
                conn,
                user_id="default",
                file_id="f-titled",
                orig_name="roth.pdf",
                source_type="file",
                source_url=None,
                domain="退休规划",
                topic=None,
                size_bytes=100,
                chunk_count=1,
                title="Roth IRA详解",
            )
            svc.register(
                conn,
                user_id="default",
                file_id="f-untitled",
                orig_name="notes.txt",
                source_type="text",
                source_url=None,
                domain="其他",
                topic=None,
                size_bytes=50,
                chunk_count=1,
                title=None,
            )

        client = app.test_client()
        resp = client.get("/api/files")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) == 2

        by_id = {item["file_id"]: item for item in data}
        assert "title" in by_id["f-titled"], "title field missing from response"
        assert by_id["f-titled"]["title"] == "Roth IRA详解"
        assert "title" in by_id["f-untitled"], "title field missing from response"
        assert by_id["f-untitled"]["title"] is None
