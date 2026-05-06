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


def test_schema_is_idempotent(tmp_path):
    db_path = str(tmp_path / "test.db")
    db1 = DatabaseService(db_path=db_path)
    conn = db1.get_connection()
    conn.execute("INSERT INTO files VALUES ('id1','default','f.txt','f.txt','file',NULL,NULL,NULL,100,1,'2026-01-01T00:00:00Z')")
    conn.commit()
    # Second init should not raise or destroy data
    db2 = DatabaseService(db_path=db_path)
    conn2 = db2.get_connection()
    row = conn2.execute("SELECT id FROM files WHERE id='id1'").fetchone()
    assert row is not None
