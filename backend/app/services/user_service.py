"""User service: users + invite_tokens CRUD, bootstrap migration.

Per multi-user-auth-core spec.
"""
from __future__ import annotations

import logging
import os
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from .auth_service import canonicalize_email, hash_password

logger = logging.getLogger(__name__)


INVITE_TOKEN_TTL_DAYS = 7


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _expiry_iso(days: int = INVITE_TOKEN_TTL_DAYS) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _new_token() -> str:
    # 32 bytes URL-safe random
    return secrets.token_urlsafe(32)


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------


def get_user_by_id(conn: sqlite3.Connection, user_id: str) -> dict | None:
    row = conn.execute(
        "SELECT id, email, google_sub, password_hash, name, picture_url, role, "
        "status, invited_at, invited_by, activated_at, last_login_at "
        "FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    return _row_to_dict(row)


def get_user_by_email(conn: sqlite3.Connection, email: str) -> dict | None:
    canonical = canonicalize_email(email)
    if not canonical:
        return None
    row = conn.execute(
        "SELECT id, email, google_sub, password_hash, name, picture_url, role, "
        "status, invited_at, invited_by, activated_at, last_login_at "
        "FROM users WHERE email = ?",
        (canonical,),
    ).fetchone()
    return _row_to_dict(row)


def get_user_by_google_sub(conn: sqlite3.Connection, sub: str) -> dict | None:
    row = conn.execute(
        "SELECT id, email, google_sub, password_hash, name, picture_url, role, "
        "status, invited_at, invited_by, activated_at, last_login_at "
        "FROM users WHERE google_sub = ?",
        (sub,),
    ).fetchone()
    return _row_to_dict(row)


def _row_to_dict(row) -> dict | None:
    if row is None:
        return None
    cols = [
        "id", "email", "google_sub", "password_hash", "name", "picture_url",
        "role", "status", "invited_at", "invited_by", "activated_at", "last_login_at",
    ]
    return dict(zip(cols, row))


# ---------------------------------------------------------------------------
# Invite token helpers
# ---------------------------------------------------------------------------


def create_invite_token(conn: sqlite3.Connection, user_id: str) -> str:
    """Insert a new invite_tokens row with a fresh random token. Returns the
    token string. Caller is responsible for committing the connection.
    """
    token = _new_token()
    conn.execute(
        "INSERT INTO invite_tokens (token, user_id, expires_at, used_at) "
        "VALUES (?, ?, ?, NULL)",
        (token, user_id, _expiry_iso()),
    )
    return token


def get_invite_token(conn: sqlite3.Connection, token: str) -> dict | None:
    row = conn.execute(
        "SELECT token, user_id, expires_at, used_at FROM invite_tokens WHERE token = ?",
        (token,),
    ).fetchone()
    if row is None:
        return None
    return {"token": row[0], "user_id": row[1], "expires_at": row[2], "used_at": row[3]}


def mark_token_used(conn: sqlite3.Connection, token: str) -> None:
    conn.execute(
        "UPDATE invite_tokens SET used_at = ? WHERE token = ?",
        (_now_iso(), token),
    )


def is_token_valid(token_row: dict) -> tuple[bool, bool]:
    """Returns (valid, expired). valid=True iff token exists, unused, unexpired."""
    if token_row is None:
        return (False, False)
    if token_row["used_at"] is not None:
        return (False, False)
    if token_row["expires_at"] < _now_iso():
        return (False, True)
    return (True, False)


# ---------------------------------------------------------------------------
# Create / invite user
# ---------------------------------------------------------------------------


def create_invited_user(
    conn: sqlite3.Connection,
    email: str,
    role: str = "member",
    invited_by: str | None = None,
) -> dict:
    """Insert a new users row in 'invited' status. Caller commits."""
    canonical = canonicalize_email(email)
    if not canonical:
        raise ValueError("email is required")
    if role not in ("admin", "member"):
        raise ValueError(f"invalid role: {role}")
    user_id = _new_uuid()
    conn.execute(
        "INSERT INTO users (id, email, role, status, invited_at, invited_by) "
        "VALUES (?, ?, ?, 'invited', ?, ?)",
        (user_id, canonical, role, _now_iso(), invited_by),
    )
    return get_user_by_id(conn, user_id)


def invite_url_for(token: str, base_url: str) -> str:
    """Compose the invite acceptance URL. base_url is e.g. 'http://10.0.0.20:8910'.
    Trailing slash is normalized.
    """
    base = base_url.rstrip("/")
    return f"{base}/accept-invite?token={token}"


# ---------------------------------------------------------------------------
# Activate / link
# ---------------------------------------------------------------------------


def activate_user_with_password(
    conn: sqlite3.Connection, user_id: str, plaintext_password: str
) -> None:
    """Set password_hash, status='active', activated_at=now. Caller commits."""
    conn.execute(
        "UPDATE users SET password_hash = ?, status = 'active', "
        "activated_at = ?, last_login_at = ? WHERE id = ?",
        (hash_password(plaintext_password), _now_iso(), _now_iso(), user_id),
    )


def activate_user_with_google(
    conn: sqlite3.Connection,
    user_id: str,
    google_sub: str,
    name: str | None,
    picture_url: str | None,
) -> None:
    """Activate (or refresh) a user via Google login. Sets google_sub +
    refreshes name/picture from claims.
    """
    conn.execute(
        "UPDATE users SET google_sub = ?, name = COALESCE(?, name), "
        "picture_url = COALESCE(?, picture_url), status = 'active', "
        "activated_at = COALESCE(activated_at, ?), last_login_at = ? "
        "WHERE id = ?",
        (google_sub, name, picture_url, _now_iso(), _now_iso(), user_id),
    )


def update_last_login(conn: sqlite3.Connection, user_id: str) -> None:
    conn.execute(
        "UPDATE users SET last_login_at = ? WHERE id = ?",
        (_now_iso(), user_id),
    )


def update_password(conn: sqlite3.Connection, user_id: str, plaintext: str) -> None:
    conn.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (hash_password(plaintext), user_id),
    )


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------


def bootstrap_initial_admin(
    conn: sqlite3.Connection,
    qdrant=None,
    base_url: str = "http://10.0.0.20:8910",
) -> dict | None:
    """If users is empty AND INITIAL_ADMIN_EMAIL env var is set:
       1. Insert admin row (status='invited', invited_by=NULL)
       2. Generate invite token (7-day expiry)
       3. Log invite URL to stdout
       4. Run migrate_default_user_data(admin.id)

    Idempotent: if users is non-empty, skip the admin creation.
    Even if users is non-empty, retry migrate_default_user_data
    (handles interrupted prior bootstrap).

    Returns the admin user dict if created, else None.
    """
    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    admin_email = os.environ.get("INITIAL_ADMIN_EMAIL", "").strip()

    if user_count == 0 and not admin_email:
        logger.warning(
            "[BOOTSTRAP] users table is empty and INITIAL_ADMIN_EMAIL is unset; "
            "every authenticated request will return 401 until you set the env var "
            "and restart the container."
        )
        return None

    admin = None
    if user_count == 0:
        # First-startup bootstrap path.
        admin = create_invited_user(
            conn, email=admin_email, role="admin", invited_by=None
        )
        token = create_invite_token(conn, admin["id"])
        conn.commit()

        url = invite_url_for(token, base_url)
        # Log to stdout so admin can find it via `docker logs python-agent-api`.
        logger.warning("[BOOTSTRAP] Admin invite URL: %s", url)
        # Also print for direct stdout visibility (logger may be configured to stderr).
        print(f"[BOOTSTRAP] Admin invite URL: {url}", flush=True)

    # Always retry the migration — covers the case where bootstrap created the
    # admin row but the migration was interrupted.
    if admin is None:
        # Find existing admin (the one matching INITIAL_ADMIN_EMAIL if set,
        # otherwise the first admin row).
        if admin_email:
            admin = get_user_by_email(conn, admin_email)
        if admin is None:
            row = conn.execute(
                "SELECT id, email, role FROM users WHERE role = 'admin' "
                "ORDER BY invited_at LIMIT 1"
            ).fetchone()
            if row:
                admin = {"id": row[0], "email": row[1], "role": row[2]}

    if admin is None:
        return None

    rewritten = migrate_default_user_data(conn, admin["id"], qdrant=qdrant)
    if rewritten:
        logger.info("[BOOTSTRAP] migrated %s rows from user_id='default' to admin", rewritten)

    return admin


def migrate_default_user_data(
    conn: sqlite3.Connection, admin_id: str, qdrant=None
) -> int:
    """Rewrite all user_id='default' rows in files / chat_sessions / notes /
    private_entries to admin_id. Also rewrites Qdrant private collection
    payloads. Idempotent (second run finds 0 rows).

    Returns total SQLite rows rewritten (Qdrant count not included).
    """
    total = 0
    for table in ("files", "chat_sessions", "notes", "private_entries"):
        cur = conn.execute(
            f"UPDATE {table} SET user_id = ? WHERE user_id = 'default'",
            (admin_id,),
        )
        total += cur.rowcount
    conn.commit()

    # Qdrant migration (best-effort; admin can re-run later if it fails).
    if qdrant is not None:
        try:
            _migrate_qdrant_default_payload(qdrant, admin_id)
        except Exception as e:
            logger.error("[BOOTSTRAP] Qdrant payload migration failed: %s", e)

    return total


def _migrate_qdrant_default_payload(qdrant, admin_id: str) -> None:
    """Scroll the private collection; for each point with user_id='default',
    set_payload to admin_id.
    """
    from qdrant_client.http.models import Filter, FieldCondition, MatchValue

    flt = Filter(
        must=[FieldCondition(key="user_id", match=MatchValue(value="default"))]
    )
    offset = None
    moved = 0
    while True:
        points, next_offset = qdrant._client.scroll(
            collection_name="private",
            scroll_filter=flt,
            limit=128,
            with_payload=False,
            offset=offset,
        )
        if not points:
            break
        ids = [p.id for p in points]
        qdrant._client.set_payload(
            collection_name="private",
            payload={"user_id": admin_id},
            points=ids,
        )
        moved += len(ids)
        if next_offset is None:
            break
        offset = next_offset
    if moved:
        logger.info("[BOOTSTRAP] rewrote %s qdrant private points to admin", moved)
