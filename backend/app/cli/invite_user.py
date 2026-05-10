"""CLI tool to invite users.

Usage:
    docker exec -it python-agent-api python -m app.cli.invite_user <email> [role]

Default role is 'member'. Prints invite URL to stdout for the admin to copy.

Replaces / supplements the future POST /api/admin/users endpoint that ships
in the multi-user-auth-admin-ui change. Kept thereafter as an emergency
fallback (admin locked out, JS broken, debugging).
"""
from __future__ import annotations

import os
import sys

from ..services import user_service
from ..services.auth_service import canonicalize_email
from ..services.db_service import DatabaseService


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or len(argv) > 2:
        print("Usage: python -m app.cli.invite_user <email> [role]", file=sys.stderr)
        return 2
    raw_email = argv[0]
    role = argv[1] if len(argv) == 2 else "member"
    if role not in ("admin", "member"):
        print(f"role must be 'admin' or 'member', got {role!r}", file=sys.stderr)
        return 2

    email = canonicalize_email(raw_email)
    if not email or "@" not in email:
        print(f"invalid email: {raw_email!r}", file=sys.stderr)
        return 2

    db = DatabaseService()
    base_url = os.environ.get("APP_BASE_URL", "http://10.0.0.20:8910")
    with db.connection() as conn:
        existing = user_service.get_user_by_email(conn, email)
        if existing is not None:
            print(
                f"user already exists: {email} (status={existing['status']}, "
                f"role={existing['role']}). Use admin UI / API to manage.",
                file=sys.stderr,
            )
            return 1

        user = user_service.create_invited_user(conn, email, role=role)
        token = user_service.create_invite_token(conn, user["id"])

    url = user_service.invite_url_for(token, base_url)
    print(f"Invite URL: {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
