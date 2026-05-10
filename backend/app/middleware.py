"""Authentication middleware: @require_auth decorator.

Per multi-user-auth-core spec §6.1.

The actual session validation lives in `_validate_session()` so test
suites can monkeypatch one function rather than the whole decorator
(decorators bind at import time; the inner function is called at
request time, so monkeypatching it WORKS even after routes import).
"""
from __future__ import annotations

import logging
from functools import wraps
from types import SimpleNamespace
from typing import Any

from flask import g, jsonify, session

from .services import user_service

logger = logging.getLogger(__name__)


def _clear_session_and_401() -> tuple[Any, int]:
    session.clear()
    resp = jsonify({"error": "authentication required"})
    return resp, 401


def _validate_session() -> SimpleNamespace | None:
    """Return a SimpleNamespace user if the current session is valid + the
    user is `status='active'`. Return None on any failure.

    Tests monkeypatch this function to inject a fixed test user.
    """
    user_id = session.get("user_id")
    if not user_id:
        return None

    from .services.db_service import DatabaseService

    db = DatabaseService()
    with db.connection() as conn:
        user = user_service.get_user_by_id(conn, user_id)

    if user is None or user["status"] != "active":
        return None
    return SimpleNamespace(**user)


def require_auth(view_func):
    """Decorator: require an authenticated session whose user is currently
    `status='active'`. Sets `g.user` (SimpleNamespace) on success.

    On any failure: clear cookie + 401.
    """

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        user = _validate_session()
        if user is None:
            return _clear_session_and_401()
        g.user = user
        return view_func(*args, **kwargs)

    return wrapper
