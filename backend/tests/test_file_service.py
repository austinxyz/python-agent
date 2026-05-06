import pytest
from app.services.file_service import FileService
from app.services.db_service import DatabaseService


class TestFileServiceSave:
    def test_save_writes_bytes_to_correct_path(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UPLOADS_PATH", str(tmp_path))
        svc = FileService()
        content = b"hello world"
        svc.save(user_id="default", file_id="abc123", filename="doc.pdf", content=content)
        dest = tmp_path / "default" / "abc123" / "doc.pdf"
        assert dest.exists()
        assert dest.read_bytes() == content

    def test_save_creates_parent_directories(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UPLOADS_PATH", str(tmp_path))
        svc = FileService()
        svc.save(user_id="alice", file_id="xyz", filename="notes.txt", content=b"data")
        assert (tmp_path / "alice" / "xyz" / "notes.txt").exists()

    def test_save_returns_path_to_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UPLOADS_PATH", str(tmp_path))
        svc = FileService()
        result = svc.save(user_id="default", file_id="id1", filename="f.txt", content=b"x")
        assert result.name == "f.txt"
        assert result.exists()


class TestFileServiceSecurity:
    def test_save_rejects_path_traversal_in_user_id(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UPLOADS_PATH", str(tmp_path))
        svc = FileService()
        with pytest.raises(ValueError, match="traversal"):
            svc.save(user_id="../../etc", file_id="x", filename="f.txt", content=b"x")

    def test_save_rejects_path_traversal_in_filename(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UPLOADS_PATH", str(tmp_path))
        svc = FileService()
        with pytest.raises(ValueError, match="traversal"):
            svc.save(user_id="default", file_id="x", filename="../secret.key", content=b"x")

    def test_save_rejects_path_traversal_in_file_id(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UPLOADS_PATH", str(tmp_path))
        svc = FileService()
        with pytest.raises(ValueError, match="traversal"):
            svc.save(user_id="default", file_id="../../etc", filename="f.txt", content=b"x")

    def test_save_rejects_null_byte_in_user_id(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UPLOADS_PATH", str(tmp_path))
        svc = FileService()
        with pytest.raises(ValueError, match="traversal"):
            svc.save(user_id="default\x00", file_id="x", filename="f.txt", content=b"x")

    def test_save_rejects_backslash_in_filename(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UPLOADS_PATH", str(tmp_path))
        svc = FileService()
        with pytest.raises(ValueError, match="traversal"):
            svc.save(user_id="default", file_id="x", filename="..\\secret.key", content=b"x")


class TestFileServiceRegister:
    def test_register_inserts_row_into_files_table(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UPLOADS_PATH", str(tmp_path))
        monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
        db = DatabaseService()
        svc = FileService()
        with db.connection() as conn:
            svc.register(
                conn,
                user_id="default",
                file_id="file-001",
                filename="budget.pdf",
                orig_name="budget.pdf",
                source_type="file",
                source_url=None,
                domain="finance",
                topic="budgeting",
                size_bytes=1024,
                chunk_count=4,
            )
            row = conn.execute(
                "SELECT * FROM files WHERE id = ?", ("file-001",)
            ).fetchone()

        assert row is not None
        assert row["id"] == "file-001"
        assert row["user_id"] == "default"
        assert row["orig_name"] == "budget.pdf"
        assert row["filename"] == "budget.pdf"
        assert row["chunk_count"] == 4

    def test_register_stores_source_url_for_url_type(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UPLOADS_PATH", str(tmp_path))
        monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
        db = DatabaseService()
        svc = FileService()
        with db.connection() as conn:
            svc.register(
                conn,
                user_id="default",
                file_id="file-002",
                orig_name="example.com",
                source_type="url",
                source_url="https://example.com/article",
                domain="tech",
                topic="ai",
                size_bytes=512,
                chunk_count=2,
            )
            conn.commit()
            row = conn.execute(
                "SELECT source_url FROM files WHERE id = ?", ("file-002",)
            ).fetchone()

        assert row["source_url"] == "https://example.com/article"

    def test_register_stores_distinct_filename_and_orig_name(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UPLOADS_PATH", str(tmp_path))
        monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
        db = DatabaseService()
        svc = FileService()
        with db.connection() as conn:
            svc.register(
                conn,
                user_id="default",
                file_id="file-003",
                filename="abc123.pdf",
                orig_name="My Budget (Final).pdf",
                source_type="file",
                source_url=None,
                domain="finance",
                topic="budgeting",
                size_bytes=2048,
                chunk_count=6,
            )
            conn.commit()
            row = conn.execute(
                "SELECT filename, orig_name FROM files WHERE id = ?", ("file-003",)
            ).fetchone()

        assert row["filename"] == "abc123.pdf"
        assert row["orig_name"] == "My Budget (Final).pdf"

    def test_register_stores_title_when_provided(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UPLOADS_PATH", str(tmp_path))
        monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
        db = DatabaseService()
        svc = FileService()
        with db.connection() as conn:
            svc.register(
                conn,
                user_id="default",
                file_id="file-004",
                orig_name="roth.pdf",
                source_type="file",
                source_url=None,
                domain="退休规划",
                topic=None,
                size_bytes=500,
                chunk_count=2,
                title="Roth IRA详解",
            )
            row = conn.execute(
                "SELECT title FROM files WHERE id = ?", ("file-004",)
            ).fetchone()
        assert row["title"] == "Roth IRA详解"

    def test_register_stores_null_title_when_not_provided(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UPLOADS_PATH", str(tmp_path))
        monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
        db = DatabaseService()
        svc = FileService()
        with db.connection() as conn:
            svc.register(
                conn,
                user_id="default",
                file_id="file-005",
                orig_name="notes.txt",
                source_type="file",
                source_url=None,
                domain="其他",
                topic=None,
                size_bytes=100,
                chunk_count=1,
                title=None,
            )
            row = conn.execute(
                "SELECT title FROM files WHERE id = ?", ("file-005",)
            ).fetchone()
        assert row["title"] is None
