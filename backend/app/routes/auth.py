"""Authentication routes — multi-user-auth-core.

Endpoints (all under /api/auth/):
- POST /login              — email+password
- POST /login/google       — Google ID token
- POST /logout             — clear session
- GET  /me                 — current user
- GET  /config             — public; tells frontend whether to show GSI button
- GET  /invite/<token>     — public; render context for accept-invite page
- POST /accept-invite      — public; activates invited user with new password
- POST /change-password    — authenticated; rotate password
"""
from __future__ import annotations

import logging
import os
from typing import Any

from flask import Blueprint, current_app, g, jsonify, request, session

from ..middleware import require_auth
from ..services import auth_service, user_service
from ..services.db_service import DatabaseService

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)

MIN_PASSWORD_LEN = 8


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user_response(user) -> dict:
    """Strip private fields (password_hash) from user dict/namespace before
    returning. Accepts either a dict (from user_service) or SimpleNamespace
    (from g.user via @require_auth)."""
    if isinstance(user, dict):
        get = user.get
        getitem = lambda k: user[k]
    else:
        get = lambda k, d=None: getattr(user, k, d)
        getitem = lambda k: getattr(user, k)
    return {
        "id": getitem("id"),
        "email": getitem("email"),
        "name": get("name"),
        "picture_url": get("picture_url"),
        "role": getitem("role"),
    }


def _open_session(user_id: str, auth_method: str) -> None:
    session.clear()
    session["user_id"] = user_id
    session["auth_method"] = auth_method
    session.permanent = True


def _invalid_credentials():
    """Constant 401 response — never leaks whether email exists."""
    return jsonify({"error": "invalid credentials"}), 401


def _base_url() -> str:
    """Base URL used to compose invite URLs in admin/CLI flows.
    Derived from request.host_url when available."""
    if request:
        return request.host_url.rstrip("/")
    return "http://localhost:5000"


# ---------------------------------------------------------------------------
# POST /api/auth/login (email + password)
# ---------------------------------------------------------------------------


@auth_bp.post("/login")
def login_password():
    body = request.get_json(silent=True) or {}
    email_in = body.get("email", "")
    password = body.get("password", "")
    if not email_in or not password:
        return _invalid_credentials()

    db = DatabaseService()
    with db.connection() as conn:
        user = user_service.get_user_by_email(conn, email_in)
        if user is None or user["status"] != "active":
            return _invalid_credentials()
        if not user.get("password_hash"):
            return _invalid_credentials()
        if not auth_service.verify_password(user["password_hash"], password):
            return _invalid_credentials()
        user_service.update_last_login(conn, user["id"])

    _open_session(user["id"], "password")
    return jsonify({"user": _user_response(user)}), 200


# ---------------------------------------------------------------------------
# POST /api/auth/login/google (Google ID token)
# ---------------------------------------------------------------------------


@auth_bp.post("/login/google")
def login_google():
    body = request.get_json(silent=True) or {}
    id_token = body.get("id_token", "")
    if not id_token:
        return jsonify({"error": "id_token is required"}), 401

    try:
        claims = auth_service.verify_google_token(id_token)
    except ValueError:
        return jsonify({"error": "invalid token"}), 401

    sub = claims.get("sub")
    email = claims.get("email", "")
    name = claims.get("name")
    picture = claims.get("picture")

    if not sub or not email:
        return jsonify({"error": "invalid token claims"}), 401

    db = DatabaseService()
    with db.connection() as conn:
        user = user_service.get_user_by_email(conn, email)
        if user is None:
            return jsonify({"error": "not invited"}), 403
        if user["status"] == "disabled":
            return jsonify({"error": "account disabled"}), 403

        existing_sub = user.get("google_sub")
        if existing_sub and existing_sub != sub:
            return jsonify({"error": "google account mismatch"}), 403

        # Activate (if invited) or just refresh google_sub/name/picture
        user_service.activate_user_with_google(
            conn, user["id"], google_sub=sub, name=name, picture_url=picture
        )
        user = user_service.get_user_by_id(conn, user["id"])

    _open_session(user["id"], "google")
    return jsonify({"user": _user_response(user)}), 200


# ---------------------------------------------------------------------------
# POST /api/auth/logout
# ---------------------------------------------------------------------------


@auth_bp.post("/logout")
def logout():
    session.clear()
    return ("", 204)


# ---------------------------------------------------------------------------
# GET /api/auth/me (auth required)
# ---------------------------------------------------------------------------


@auth_bp.get("/me")
@require_auth
def me():
    return jsonify({"user": _user_response(g.user)}), 200


# ---------------------------------------------------------------------------
# GET /api/auth/config (public)
# ---------------------------------------------------------------------------


@auth_bp.get("/config")
def config():
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    return jsonify(
        {
            "has_google": bool(client_id),
            "google_client_id": client_id or None,
        }
    ), 200


# ---------------------------------------------------------------------------
# GET /api/auth/invite/<token> (public)
# ---------------------------------------------------------------------------


@auth_bp.get("/invite/<token>")
def invite_info(token: str):
    db = DatabaseService()
    with db.connection() as conn:
        token_row = user_service.get_invite_token(conn, token)
        if token_row is None:
            return jsonify({"valid": False, "expired": False, "user": None}), 200

        valid, expired = user_service.is_token_valid(token_row)
        user = user_service.get_user_by_id(conn, token_row["user_id"])

        # Inviter context (admin's name + email)
        inviter = None
        if user and user.get("invited_by"):
            inviter_row = user_service.get_user_by_id(conn, user["invited_by"])
            if inviter_row:
                inviter = {
                    "email": inviter_row["email"],
                    "name": inviter_row.get("name"),
                    "picture_url": inviter_row.get("picture_url"),
                }

        return jsonify(
            {
                "valid": valid,
                "expired": expired,
                "user": (
                    {
                        "email": user["email"],
                        "name": user.get("name"),
                        "picture_url": user.get("picture_url"),
                    }
                    if user
                    else None
                ),
                "inviter": inviter,
            }
        ), 200


# ---------------------------------------------------------------------------
# POST /api/auth/accept-invite (public)
# ---------------------------------------------------------------------------


@auth_bp.post("/accept-invite")
def accept_invite():
    body = request.get_json(silent=True) or {}
    token = body.get("token", "")
    password = body.get("password", "")

    if not token:
        return jsonify({"error": "token is required"}), 400
    if not password or len(password) < MIN_PASSWORD_LEN:
        return jsonify({"error": f"password must be at least {MIN_PASSWORD_LEN} characters"}), 400

    db = DatabaseService()
    with db.connection() as conn:
        token_row = user_service.get_invite_token(conn, token)
        if token_row is None:
            return jsonify({"error": "invalid token"}), 410
        valid, expired = user_service.is_token_valid(token_row)
        if not valid:
            if expired:
                return jsonify({"error": "invite expired"}), 410
            return jsonify({"error": "invite already used"}), 410

        user_service.activate_user_with_password(conn, token_row["user_id"], password)
        user_service.mark_token_used(conn, token)
        user = user_service.get_user_by_id(conn, token_row["user_id"])

    _open_session(user["id"], "password")
    return jsonify({"user": _user_response(user)}), 200


# ---------------------------------------------------------------------------
# POST /api/auth/change-password (auth required)
# ---------------------------------------------------------------------------


@auth_bp.post("/change-password")
@require_auth
def change_password():
    body = request.get_json(silent=True) or {}
    old_password = body.get("old_password", "")
    new_password = body.get("new_password", "")

    if not new_password or len(new_password) < MIN_PASSWORD_LEN:
        return jsonify({"error": f"new password must be at least {MIN_PASSWORD_LEN} characters"}), 400
    if new_password == old_password:
        return jsonify({"error": "new password must differ from old"}), 400

    db = DatabaseService()
    with db.connection() as conn:
        user = user_service.get_user_by_id(conn, g.user.id)
        if not user.get("password_hash"):
            # Google-only user setting a password for the first time —
            # accept any old_password but still apply the rules.
            user_service.update_password(conn, user["id"], new_password)
            return ("", 200)
        if not auth_service.verify_password(user["password_hash"], old_password):
            return jsonify({"error": "old password incorrect"}), 401
        user_service.update_password(conn, user["id"], new_password)

    return ("", 200)
