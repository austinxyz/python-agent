"""Bootstrap migration: empty users + INITIAL_ADMIN_EMAIL → admin row +
invite token + rewrites all user_id='default' across 4 tables.

Idempotent.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.services.db_service import DatabaseService
from app.services.user_service import (
    bootstrap_initial_admin,
    migrate_default_user_data,
)


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    return str(tmp_path / "bootstrap.db")


@pytest.fixture
def admin_email_env(monkeypatch):
    monkeypatch.setenv("INITIAL_ADMIN_EMAIL", "austin.xyz@gmail.com")


def _seed_default_data(conn: sqlite3.Connection) -> dict[str, int]:
    """Seed each user-data table with rows under user_id='default'."""
    counts = {}
    # files
    for i in range(3):
        conn.execute(
            "INSERT INTO files (id, user_id, filename, orig_name, source_type, "
            "domain, title) VALUES (?, ?, ?, ?, 'file', 'test', ?)",
            (f"f{i}", "default", f"f{i}.pdf", f"f{i}.pdf", f"File {i}"),
        )
    counts["files"] = 3
    # chat_sessions
    for i in range(2):
        conn.execute(
            "INSERT INTO chat_sessions (id, user_id, title) VALUES (?, ?, ?)",
            (f"s{i}", "default", f"Session {i}"),
        )
    counts["chat_sessions"] = 2
    # notes
    conn.execute(
        "INSERT INTO notes (id, user_id, title, content) VALUES (?, ?, ?, ?)",
        ("n1", "default", "Note", "content"),
    )
    counts["notes"] = 1
    # private_entries
    conn.execute(
        "INSERT INTO private_entries (id, user_id, template_type, title, "
        "content_json) VALUES (?, ?, ?, ?, ?)",
        ("pe1", "default", "tax", "Tax Entry", "{}"),
    )
    counts["private_entries"] = 1
    conn.commit()
    return counts


class TestBootstrapAdmin:
    def test_creates_admin_row_and_invite_token(self, db_path, admin_email_env, capsys):
        DatabaseService(db_path)
        with sqlite3.connect(db_path) as conn:
            admin = bootstrap_initial_admin(conn, qdrant=None)
            assert admin is not None
            assert admin["email"] == "austin.xyz@gmail.com"
            assert admin["role"] == "admin"
            assert admin["status"] == "invited"
            # Token created
            tokens = conn.execute(
                "SELECT token, user_id FROM invite_tokens WHERE user_id = ?",
                (admin["id"],),
            ).fetchall()
            assert len(tokens) == 1
        # Invite URL printed to stdout
        captured = capsys.readouterr()
        assert "[BOOTSTRAP] Admin invite URL:" in captured.out
        assert "/accept-invite?token=" in captured.out

    def test_idempotent_second_run_no_op(self, db_path, admin_email_env):
        DatabaseService(db_path)
        with sqlite3.connect(db_path) as conn:
            bootstrap_initial_admin(conn, qdrant=None)
            count_before = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            tokens_before = conn.execute(
                "SELECT COUNT(*) FROM invite_tokens"
            ).fetchone()[0]
            # Run again
            bootstrap_initial_admin(conn, qdrant=None)
            count_after = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            tokens_after = conn.execute(
                "SELECT COUNT(*) FROM invite_tokens"
            ).fetchone()[0]
            assert count_after == count_before == 1
            assert tokens_after == tokens_before == 1

    def test_no_email_env_no_op(self, db_path, monkeypatch):
        monkeypatch.delenv("INITIAL_ADMIN_EMAIL", raising=False)
        DatabaseService(db_path)
        with sqlite3.connect(db_path) as conn:
            result = bootstrap_initial_admin(conn, qdrant=None)
            assert result is None
            count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            assert count == 0

    def test_canonicalizes_email(self, db_path, monkeypatch):
        monkeypatch.setenv("INITIAL_ADMIN_EMAIL", "  AUSTIN@GMAIL.COM  ")
        DatabaseService(db_path)
        with sqlite3.connect(db_path) as conn:
            admin = bootstrap_initial_admin(conn, qdrant=None)
            assert admin["email"] == "austin@gmail.com"


class TestMigrateDefaultData:
    def test_rewrites_all_4_tables(self, db_path, admin_email_env):
        DatabaseService(db_path)
        with sqlite3.connect(db_path) as conn:
            counts = _seed_default_data(conn)
            admin = bootstrap_initial_admin(conn, qdrant=None)
            for table, expected in counts.items():
                left_default = conn.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE user_id = 'default'"
                ).fetchone()[0]
                rewritten = conn.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE user_id = ?",
                    (admin["id"],),
                ).fetchone()[0]
                assert left_default == 0, f"{table} still has user_id='default' rows"
                assert rewritten == expected, (
                    f"{table} should have {expected} rewritten rows, got {rewritten}"
                )

    def test_idempotent_migration(self, db_path, admin_email_env):
        DatabaseService(db_path)
        with sqlite3.connect(db_path) as conn:
            _seed_default_data(conn)
            admin = bootstrap_initial_admin(conn, qdrant=None)
            # Second invocation should find no default rows to migrate
            rewritten = migrate_default_user_data(conn, admin["id"], qdrant=None)
            assert rewritten == 0

    def test_qdrant_migration_called(self, db_path, admin_email_env):
        DatabaseService(db_path)
        # Mock qdrant client interface
        mock_qdrant = MagicMock()
        mock_qdrant._client = MagicMock()
        mock_qdrant._client.scroll.return_value = ([], None)  # empty result → done
        with sqlite3.connect(db_path) as conn:
            bootstrap_initial_admin(conn, qdrant=mock_qdrant)
        # scroll was called at least once on the private collection
        scroll_calls = mock_qdrant._client.scroll.call_args_list
        assert len(scroll_calls) >= 1
        assert scroll_calls[0].kwargs.get("collection_name") == "private"
