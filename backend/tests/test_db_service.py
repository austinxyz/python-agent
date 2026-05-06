import sqlite3
import pytest
from app.services.db_service import DatabaseService


def test_all_tables_exist(tmp_path):
    db = DatabaseService(db_path=str(tmp_path / "test.db"))
    conn = db.get_connection()
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert "files" in tables
    assert "chat_sessions" in tables
    assert "chat_messages" in tables
    assert "notes" in tables


def test_wal_mode_enabled(tmp_path):
    db = DatabaseService(db_path=str(tmp_path / "test.db"))
    conn = db.get_connection()
    row = conn.execute("PRAGMA journal_mode").fetchone()
    assert row[0] == "wal"


def test_ensure_title_column_adds_column(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE files ("
        "id TEXT, user_id TEXT, filename TEXT, orig_name TEXT,"
        "source_type TEXT, source_url TEXT, domain TEXT, topic TEXT,"
        "size_bytes INTEGER, chunk_count INTEGER, created_at TEXT)"
    )
    conn.commit()
    conn.close()
    db = DatabaseService(db_path=db_path)
    cols = {row[1] for row in db.get_connection().execute("PRAGMA table_info(files)").fetchall()}
    assert "title" in cols


def test_ensure_title_column_is_idempotent(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE files ("
        "id TEXT, user_id TEXT, filename TEXT, orig_name TEXT,"
        "source_type TEXT, source_url TEXT, domain TEXT, topic TEXT,"
        "size_bytes INTEGER, chunk_count INTEGER, created_at TEXT)"
    )
    conn.commit()
    conn.close()
    DatabaseService(db_path=db_path)
    # Second init must not raise even though title column already exists
    DatabaseService(db_path=db_path)


def test_schema_is_idempotent(tmp_path):
    db_path = str(tmp_path / "test.db")
    db1 = DatabaseService(db_path=db_path)
    conn = db1.get_connection()
    conn.execute(
        "INSERT INTO files (id, user_id, filename, orig_name, source_type, source_url, domain, topic, size_bytes, chunk_count, created_at)"
        " VALUES ('id1','default','f.txt','f.txt','file',NULL,NULL,NULL,100,1,'2026-01-01T00:00:00Z')"
    )
    conn.commit()
    # Second init should not raise or destroy data
    db2 = DatabaseService(db_path=db_path)
    conn2 = db2.get_connection()
    row = conn2.execute("SELECT id FROM files WHERE id='id1'").fetchone()
    assert row is not None
