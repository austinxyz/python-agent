"""Tests for the three fixes from the 2026-05-10 multi-user-auth-core review:
1. _safe_picture_url() rejects non-https URLs
2. is_token_valid uses datetime parsing, not lex compare
3. (open-redirect fix lives on the frontend; covered in vitest)
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.routes.auth import _safe_picture_url
from app.services.db_service import DatabaseService
from app.services.user_service import (
    _ISO_FMT,
    _expiry_iso,
    _now_iso,
    _parse_iso,
    create_invite_token,
    create_invited_user,
    get_invite_token,
    is_token_valid,
)


# ---------------------------------------------------------------------------
# 1. _safe_picture_url
# ---------------------------------------------------------------------------


class TestSafePictureUrl:
    def test_accepts_https(self):
        assert (
            _safe_picture_url("https://lh3.googleusercontent.com/a/photo.jpg")
            == "https://lh3.googleusercontent.com/a/photo.jpg"
        )

    def test_rejects_plain_http(self):
        assert _safe_picture_url("http://example.com/avatar.png") is None

    def test_rejects_javascript_uri(self):
        assert _safe_picture_url("javascript:alert(1)") is None

    def test_rejects_data_uri(self):
        assert _safe_picture_url("data:image/svg+xml,<svg/>") is None

    def test_rejects_protocol_relative(self):
        assert _safe_picture_url("//evil.example/avatar") is None

    def test_passes_through_none(self):
        assert _safe_picture_url(None) is None

    def test_rejects_non_string(self):
        assert _safe_picture_url(42) is None
        assert _safe_picture_url({"url": "https://..."}) is None

    def test_rejects_empty_string(self):
        assert _safe_picture_url("") is None


# ---------------------------------------------------------------------------
# 2. is_token_valid — datetime comparison, not lex
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    return str(tmp_path / "test_token_valid.db")


@pytest.fixture
def conn(db_path):
    DatabaseService(db_path)
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def _make_user_and_token(conn, *, expires_at: str) -> str:
    user = create_invited_user(conn, email=f"u-{expires_at}@example.com", role="member")
    # create_invite_token writes a fresh future expiry — for negative tests we
    # need to override expires_at directly. Insert the token row manually.
    import secrets

    token = secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO invite_tokens (token, user_id, expires_at, used_at) VALUES (?, ?, ?, NULL)",
        (token, user["id"], expires_at),
    )
    conn.commit()
    return token


class TestIsTokenValid:
    def test_fresh_token_is_valid(self, conn):
        future = (datetime.now(timezone.utc) + timedelta(days=5)).strftime(_ISO_FMT)
        token = _make_user_and_token(conn, expires_at=future)
        row = get_invite_token(conn, token)
        valid, expired = is_token_valid(row)
        assert valid is True
        assert expired is False

    def test_expired_token_marks_expired(self, conn):
        past = (datetime.now(timezone.utc) - timedelta(days=1)).strftime(_ISO_FMT)
        token = _make_user_and_token(conn, expires_at=past)
        row = get_invite_token(conn, token)
        valid, expired = is_token_valid(row)
        assert valid is False
        assert expired is True

    def test_used_token_is_neither_valid_nor_expired(self, conn):
        future = (datetime.now(timezone.utc) + timedelta(days=5)).strftime(_ISO_FMT)
        token = _make_user_and_token(conn, expires_at=future)
        # Mark used.
        conn.execute(
            "UPDATE invite_tokens SET used_at = ? WHERE token = ?",
            (_now_iso(), token),
        )
        conn.commit()
        row = get_invite_token(conn, token)
        valid, expired = is_token_valid(row)
        assert valid is False
        assert expired is False

    def test_missing_token_row_returns_false_false(self):
        assert is_token_valid(None) == (False, False)

    def test_malformed_expires_at_raises_not_silently_passes(self, conn):
        """The old lex-compare implementation would silently accept an
        out-of-format string and (mis-)compare it. The new parse-based
        impl raises ValueError, which is the right loud-failure mode."""
        token = _make_user_and_token(conn, expires_at="not-a-date")
        row = get_invite_token(conn, token)
        with pytest.raises(ValueError):
            is_token_valid(row)


class TestParseIso:
    def test_round_trip(self):
        s = _now_iso()
        dt = _parse_iso(s)
        assert dt.tzinfo is not None
        # Round-trip preserves seconds (sub-second is dropped by format).
        assert dt.strftime(_ISO_FMT) == s

    def test_expiry_iso_round_trip(self):
        s = _expiry_iso(7)
        dt = _parse_iso(s)
        assert dt > datetime.now(timezone.utc)
        assert dt < datetime.now(timezone.utc) + timedelta(days=7, seconds=2)
