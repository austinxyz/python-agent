import os
import re
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

_SAFE_COMPONENT = re.compile(r'^[a-zA-Z0-9_\-. ]+$')


class FileService:
    def __init__(self) -> None:
        self._base = Path(os.environ.get("UPLOADS_PATH", "/app/uploads")).resolve()

    def _check_component(self, value: str, label: str) -> None:
        if not value or not _SAFE_COMPONENT.match(value):
            raise ValueError(f"Path traversal detected: invalid characters in {label}")

    def resolve(self, user_id: str, file_id: str, filename: str) -> Path | None:
        try:
            self._check_component(user_id, "user_id")
            self._check_component(file_id, "file_id")
            self._check_component(filename, "filename")
            path = (self._base / user_id / file_id / filename).resolve()
            if not path.is_relative_to(self._base):
                return None
            return path
        except ValueError:
            return None

    def save(self, user_id: str, file_id: str, filename: str, content: bytes) -> Path:
        self._check_component(user_id, "user_id")
        self._check_component(file_id, "file_id")
        self._check_component(filename, "filename")
        file_dir = (self._base / user_id / file_id).resolve()
        if not file_dir.is_relative_to(self._base):
            raise ValueError("Path traversal detected in upload path")
        dest = (file_dir / filename).resolve()
        if not dest.is_relative_to(file_dir):
            raise ValueError("Path traversal detected in upload path")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        return dest

    def register(
        self,
        conn: sqlite3.Connection,
        user_id: str,
        file_id: str,
        orig_name: str,
        source_type: str,
        source_url: str | None,
        domain: str,
        topic: str,
        size_bytes: int,
        chunk_count: int,
        filename: str | None = None,
        title: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        stored_filename = filename if filename is not None else orig_name
        conn.execute(
            """
            INSERT INTO files
                (id, user_id, filename, orig_name, source_type, source_url,
                 domain, topic, size_bytes, chunk_count, created_at, title)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (file_id, user_id, stored_filename, orig_name, source_type, source_url,
             domain, topic, size_bytes, chunk_count, now, title),
        )
