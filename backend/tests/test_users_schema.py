"""Schema migration tests for users + invite_tokens tables.

Per spec: idempotent CREATE TABLE IF NOT EXISTS with the column shape from
multi-user-auth-core/specs/multi-user-auth/spec.md.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.services.db_service import DatabaseService


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    return str(tmp_path / "test_users_schema.db")


def _columns(conn: sqlite3.Connection, table: str) -> dict[str, dict]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    # row layout: (cid, name, type, notnull, dflt_value, pk)
    return {r[1]: {"type": r[2], "notnull": r[3], "default": r[4], "pk": r[5]} for r in rows}


def _indexes(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA index_list({table})").fetchall()
    return {r[1] for r in rows}


class TestUsersTable:
    def test_users_table_exists_with_required_columns(self, db_path):
        DatabaseService(db_path)
        with sqlite3.connect(db_path) as conn:
            cols = _columns(conn, "users")
        for required in [
            "id",
            "email",
            "google_sub",
            "password_hash",
            "name",
            "picture_url",
            "role",
            "status",
            "invited_at",
            "invited_by",
            "activated_at",
            "last_login_at",
        ]:
            assert required in cols, f"users.{required} missing"
        assert cols["id"]["pk"] == 1
        assert cols["email"]["notnull"] == 1
        assert cols["role"]["notnull"] == 1
        assert cols["status"]["notnull"] == 1

    def test_users_email_unique_constraint(self, db_path):
        DatabaseService(db_path)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO users (id, email, role, status, invited_at) VALUES (?, ?, ?, ?, ?)",
                ("u1", "a@b.com", "member", "invited", "2026-05-09T00:00:00Z"),
            )
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO users (id, email, role, status, invited_at) VALUES (?, ?, ?, ?, ?)",
                    ("u2", "a@b.com", "admin", "active", "2026-05-09T00:00:00Z"),
                )

    def test_users_role_check_constraint(self, db_path):
        DatabaseService(db_path)
        with sqlite3.connect(db_path) as conn:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO users (id, email, role, status, invited_at) VALUES (?, ?, ?, ?, ?)",
                    ("u1", "a@b.com", "superuser", "invited", "2026-05-09T00:00:00Z"),
                )

    def test_users_status_check_constraint(self, db_path):
        DatabaseService(db_path)
        with sqlite3.connect(db_path) as conn:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO users (id, email, role, status, invited_at) VALUES (?, ?, ?, ?, ?)",
                    ("u1", "a@b.com", "member", "pending", "2026-05-09T00:00:00Z"),
                )

    def test_users_indexes_exist(self, db_path):
        DatabaseService(db_path)
        with sqlite3.connect(db_path) as conn:
            idx = _indexes(conn, "users")
        # auto-indexes from UNIQUE constraints + explicit ones we added
        assert any("email" in name.lower() for name in idx)
        assert any("status" in name.lower() for name in idx)


class TestInviteTokensTable:
    def test_invite_tokens_table_exists(self, db_path):
        DatabaseService(db_path)
        with sqlite3.connect(db_path) as conn:
            cols = _columns(conn, "invite_tokens")
        for required in ["token", "user_id", "expires_at", "used_at"]:
            assert required in cols, f"invite_tokens.{required} missing"
        assert cols["token"]["pk"] == 1
        assert cols["user_id"]["notnull"] == 1
        assert cols["expires_at"]["notnull"] == 1

    def test_invite_tokens_user_id_fk_cascades(self, db_path):
        DatabaseService(db_path)
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                "INSERT INTO users (id, email, role, status, invited_at) VALUES (?, ?, ?, ?, ?)",
                ("u1", "a@b.com", "member", "invited", "2026-05-09T00:00:00Z"),
            )
            conn.execute(
                "INSERT INTO invite_tokens (token, user_id, expires_at) VALUES (?, ?, ?)",
                ("tok-1", "u1", "2026-05-16T00:00:00Z"),
            )
            conn.execute("DELETE FROM users WHERE id = 'u1'")
            remaining = conn.execute(
                "SELECT COUNT(*) FROM invite_tokens WHERE user_id = 'u1'"
            ).fetchone()[0]
            assert remaining == 0, "invite_tokens row should cascade-delete with user"


class TestSchemaIdempotency:
    def test_schema_runs_twice_without_error(self, db_path):
        DatabaseService(db_path)
        # Insert a row
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO users (id, email, role, status, invited_at) VALUES (?, ?, ?, ?, ?)",
                ("u1", "a@b.com", "member", "invited", "2026-05-09T00:00:00Z"),
            )
            conn.commit()
        # Re-init should be idempotent
        DatabaseService(db_path)
        with sqlite3.connect(db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        assert count == 1, "second migration should not wipe data"
