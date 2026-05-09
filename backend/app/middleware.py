"""Authentication middleware: @require_auth decorator.

Per multi-user-auth-core spec §6.1.
"""
from __future__ import annotations

import logging
from functools import wraps
from typing import Any

from flask import g, jsonify, request, session

from .services import user_service

logger = logging.getLogger(__name__)


def _clear_session_and_401() -> tuple[Any, int]:
    session.clear()
    resp = jsonify({"error": "authentication required"})
    return resp, 401


def require_auth(view_func):
    """Decorator: require an authenticated session whose user is currently
    `status='active'`. Sets `g.user` (full user dict) on success.

    On any failure: clear cookie + 401.
    """

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            return _clear_session_and_401()

        # Per-request status check (V1 enforcement model — disable kills next request).
        from .services.db_service import DatabaseService

        db = DatabaseService()
        with db.connection() as conn:
            user = user_service.get_user_by_id(conn, user_id)

        if user is None or user["status"] != "active":
            return _clear_session_and_401()

        g.user = user
        return view_func(*args, **kwargs)

    return wrapper
