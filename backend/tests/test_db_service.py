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
    assert "private_entries" in tables


def test_ensure_private_tables_creates_both_tables(tmp_path):
    db_path = str(tmp_path / "test.db")
    DatabaseService(db_path=db_path)
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        assert "private_entries" in tables
        assert "notes" in tables
    finally:
        conn.close()


def test_ensure_private_tables_is_idempotent(tmp_path):
    db_path = str(tmp_path / "test.db")
    db1 = DatabaseService(db_path=db_path)
    conn = db1.get_connection()
    conn.execute(
        "INSERT INTO private_entries (id, user_id, template_type, title, content_json)"
        " VALUES ('e1','default','tax','My Tax','{}')"
    )
    conn.commit()
    conn.close()
    # Second init must not raise or destroy data
    db2 = DatabaseService(db_path=db_path)
    row = db2.get_connection().execute(
        "SELECT id FROM private_entries WHERE id='e1'"
    ).fetchone()
    assert row is not None


def test_private_entries_columns_match_schema(tmp_path):
    db = DatabaseService(db_path=str(tmp_path / "test.db"))
    conn = db.get_connection()
    cols = {row[1] for row in conn.execute("PRAGMA table_info(private_entries)").fetchall()}
    assert cols == {
        "id",
        "user_id",
        "template_type",
        "title",
        "content_json",
        "directory",
        "created_at",
        "updated_at",
    }


def test_ensure_private_entries_directory_column_added_to_legacy_table(tmp_path):
    """If a pre-revision DB has private_entries WITHOUT a directory column,
    the migration adds it AND backfills the directory from each row's
    template_type → default_directory mapping (so legacy entries show up
    under the right node in the tree)."""
    db_path = str(tmp_path / "test.db")
    # Simulate a legacy DB: create the old shape WITHOUT `directory`
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE private_entries (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL DEFAULT 'default',
                template_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )
        conn.execute(
            "INSERT INTO private_entries (id, user_id, template_type, title, content_json)"
            " VALUES ('legacy-tax','default','tax','Old Tax','{}')"
        )
        conn.execute(
            "INSERT INTO private_entries (id, user_id, template_type, title, content_json)"
            " VALUES ('legacy-house','default','real_estate','Old House','{}')"
        )
        conn.commit()
    finally:
        conn.close()

    DatabaseService(db_path=db_path)

    # Migration should have added the column AND backfilled both rows
    conn = sqlite3.connect(db_path)
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(private_entries)").fetchall()}
        assert "directory" in cols
        rows = dict(conn.execute(
            "SELECT id, directory FROM private_entries"
        ).fetchall())
        assert rows == {"legacy-tax": "税务", "legacy-house": "房产资产"}
    finally:
        conn.close()


def test_directory_backfill_does_not_overwrite_existing_values(tmp_path):
    """Rows that already have a non-empty directory must be left alone."""
    db_path = str(tmp_path / "test.db")
    DatabaseService(db_path=db_path)
    # Insert a row with an explicit custom directory
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO private_entries (id, user_id, template_type, title, content_json, directory)"
            " VALUES ('e1','default','tax','Custom','{}','税务/2025')"
        )
        conn.commit()
    finally:
        conn.close()
    # Re-init triggers migration again
    DatabaseService(db_path=db_path)
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT directory FROM private_entries WHERE id='e1'").fetchone()
        assert row[0] == "税务/2025"
    finally:
        conn.close()


def test_ensure_private_entries_directory_column_idempotent(tmp_path):
    """Running the migration again is a no-op."""
    db_path = str(tmp_path / "test.db")
    DatabaseService(db_path=db_path)
    DatabaseService(db_path=db_path)  # second init, must not raise
    conn = sqlite3.connect(db_path)
    try:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(private_entries)").fetchall()]
        # 'directory' appears exactly once
        assert cols.count("directory") == 1
    finally:
        conn.close()


def test_notes_columns_match_schema(tmp_path):
    db = DatabaseService(db_path=str(tmp_path / "test.db"))
    conn = db.get_connection()
    cols = {row[1] for row in conn.execute("PRAGMA table_info(notes)").fetchall()}
    assert cols == {
        "id",
        "user_id",
        "title",
        "directory",
        "content",
        "chat_ref",
        "created_at",
        "updated_at",
    }


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
