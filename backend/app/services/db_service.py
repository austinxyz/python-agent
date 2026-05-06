import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator


class DatabaseService:
    def __init__(self, db_path: str | None = None):
        self._db_path = db_path or os.environ.get("SQLITE_PATH", "knowledge_agent.db")
        self._apply_schema()

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
        finally:
            conn.close()

    def get_connection(self) -> sqlite3.Connection:
        return self._connect()
