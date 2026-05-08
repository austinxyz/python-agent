import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator


class DatabaseService:
    def __init__(self, db_path: str | None = None):
        self._db_path = db_path or os.environ.get("SQLITE_PATH", "knowledge_agent.db")
        self._apply_schema()
        self._ensure_title_column()
        self._ensure_private_tables()
        self._ensure_private_entries_directory_column()

    def _ensure_private_entries_directory_column(self) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            existing = {row[1] for row in conn.execute("PRAGMA table_info(private_entries)").fetchall()}
            if "directory" not in existing:
                try:
                    conn.execute("ALTER TABLE private_entries ADD COLUMN directory TEXT NOT NULL DEFAULT ''")
                    conn.commit()
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e):
                        raise
            # Backfill: legacy rows (created before the column existed) have
            # directory = ''. Set them to the template's default directory so
            # they show up under the correct sidebar node. Idempotent — only
            # touches rows where directory is empty.
            from app.routes.private_templates import TEMPLATE_DEFAULT_DIRECTORIES
            for template_type, default_dir in TEMPLATE_DEFAULT_DIRECTORIES.items():
                conn.execute(
                    "UPDATE private_entries SET directory = ?"
                    " WHERE template_type = ? AND (directory IS NULL OR directory = '')",
                    (default_dir, template_type),
                )
            conn.commit()
        finally:
            conn.close()

    def _ensure_private_tables(self) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS private_entries (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL DEFAULT 'default',
                    template_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                );

                CREATE TABLE IF NOT EXISTS notes (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    directory TEXT NOT NULL DEFAULT '',
                    chat_ref TEXT,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                );

                CREATE INDEX IF NOT EXISTS idx_private_entries_user_id ON private_entries(user_id);
                CREATE INDEX IF NOT EXISTS idx_private_entries_created_at ON private_entries(created_at);
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _ensure_title_column(self) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            existing = {row[1] for row in conn.execute("PRAGMA table_info(files)").fetchall()}
            if "title" not in existing:
                try:
                    conn.execute("ALTER TABLE files ADD COLUMN title TEXT")
                    conn.commit()
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e):
                        raise
        finally:
            conn.close()

    def _apply_schema(self) -> None:
        schema_path = Path(__file__).parent.parent.parent / "db" / "schema.sql"
        schema_sql = schema_path.read_text(encoding="utf-8")
        conn = sqlite3.connect(self._db_path)
        try:
            conn.executescript(schema_sql)
            conn.execute("PRAGMA journal_mode=WAL")
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_connection(self) -> sqlite3.Connection:
        return self._connect()
