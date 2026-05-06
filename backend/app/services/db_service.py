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
