"""Tests for GET /api/wiki/tree, GET /api/wiki, GET /api/wiki/{file_id}."""
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


def _register(conn, svc, file_id, domain, title=None, orig_name="doc.pdf", source_type="file"):
    svc.register(
        conn,
        user_id="default",
        file_id=file_id,
        orig_name=orig_name,
        source_type=source_type,
        source_url=None,
        domain=domain,
        topic=None,
        size_bytes=100,
        chunk_count=3,
        title=title,
        filename=f"{file_id}.pdf",
    )


class TestWikiTree:
    def test_empty_collection_returns_empty_object(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with patch("app.routes.wiki.QdrantService") as MockQdrant:
            MockQdrant.return_value.get_tree.return_value = {}
            with app.test_client() as client:
                resp = client.get("/api/wiki/tree")
        assert resp.status_code == 200
        assert resp.get_json() == {}

    def test_groups_entries_by_domain(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        db = DatabaseService()
        svc = FileService()
        with db.connection() as conn:
            _register(conn, svc, "file-a", "退休规划", title="Roth IRA")
            _register(conn, svc, "file-b", "退休规划", title="401k")
            _register(conn, svc, "file-c", "税务策略", title="Tax策略")
        with patch("app.routes.wiki.QdrantService") as MockQdrant:
            MockQdrant.return_value.get_tree.return_value = {
                "退休规划": ["file-a", "file-b"],
                "税务策略": ["file-c"],
            }
            with app.test_client() as client:
                resp = client.get("/api/wiki/tree")
        data = resp.get_json()
        assert resp.status_code == 200
        assert set(data.keys()) == {"退休规划", "税务策略"}
        assert len(data["退休规划"]) == 2
        assert len(data["税务策略"]) == 1

    def test_entry_fields_are_correct(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        db = DatabaseService()
        svc = FileService()
        with db.connection() as conn:
            _register(conn, svc, "file-a", "退休规划", title="Roth IRA")
        with patch("app.routes.wiki.QdrantService") as MockQdrant:
            MockQdrant.return_value.get_tree.return_value = {"退休规划": ["file-a"]}
            with app.test_client() as client:
                resp = client.get("/api/wiki/tree")
        entry = resp.get_json()["退休规划"][0]
        assert entry["file_id"] == "file-a"
        assert entry["title"] == "Roth IRA"
        assert entry["orig_name"] == "doc.pdf"
        assert entry["domain"] == "退休规划"
        assert entry["chunk_count"] == 3
        assert "created_at" in entry

    def test_unknown_file_ids_from_qdrant_are_skipped(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with patch("app.routes.wiki.QdrantService") as MockQdrant:
            # Qdrant returns file-x but it's not in SQLite
            MockQdrant.return_value.get_tree.return_value = {"退休规划": ["file-x"]}
            with app.test_client() as client:
                resp = client.get("/api/wiki/tree")
        assert resp.get_json() == {}

    def test_qdrant_unavailable_returns_503(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with patch("app.routes.wiki.QdrantService") as MockQdrant:
            MockQdrant.return_value.get_tree.side_effect = Exception("connection refused")
            with app.test_client() as client:
                resp = client.get("/api/wiki/tree")
        assert resp.status_code == 503
        assert resp.get_json() == {"error": "knowledge store unavailable"}


class TestWikiList:
    def test_no_filter_returns_all_entries(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        db = DatabaseService()
        svc = FileService()
        with db.connection() as conn:
            _register(conn, svc, "file-a", "退休规划", title="Roth")
            _register(conn, svc, "file-b", "税务策略", title="Tax")
        with app.test_client() as client:
            resp = client.get("/api/wiki")
        assert resp.status_code == 200
        data = resp.get_json()
        ids = [e["file_id"] for e in data]
        assert "file-a" in ids
        assert "file-b" in ids

    def test_domain_filter_returns_only_matching(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        db = DatabaseService()
        svc = FileService()
        with db.connection() as conn:
            _register(conn, svc, "file-a", "退休规划", title="Roth")
            _register(conn, svc, "file-b", "税务策略", title="Tax")
        with app.test_client() as client:
            resp = client.get("/api/wiki?domain=退休规划")
        assert resp.status_code == 200
        data = resp.get_json()
        assert all(e["domain"] == "退休规划" for e in data)
        assert len(data) == 1

    def test_unknown_domain_returns_empty_list(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with app.test_client() as client:
            resp = client.get("/api/wiki?domain=不存在")
        assert resp.status_code == 200
        assert resp.get_json() == []


class TestWikiEntry:
    def test_valid_file_id_returns_metadata(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        db = DatabaseService()
        svc = FileService()
        with db.connection() as conn:
            _register(conn, svc, "file-a", "退休规划", title="Roth IRA", source_type="file")
        with app.test_client() as client:
            resp = client.get("/api/wiki/file-a")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["file_id"] == "file-a"
        assert data["title"] == "Roth IRA"
        assert data["domain"] == "退休规划"
        assert data["chunk_count"] == 3
        assert data["source_type"] == "file"

    def test_unknown_file_id_returns_404(self, monkeypatch, tmp_path):
        app = _make_app(monkeypatch, tmp_path)
        with app.test_client() as client:
            resp = client.get("/api/wiki/does-not-exist")
        assert resp.status_code == 404
        assert resp.get_json() == {"error": "entry not found"}
