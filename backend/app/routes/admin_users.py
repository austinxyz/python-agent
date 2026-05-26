"""Admin user management endpoints — all require admin role.

GET    /api/admin/users                  — list all users newest-first
POST   /api/admin/users                  — invite new user
PATCH  /api/admin/users/<id>             — update role or status
DELETE /api/admin/users/<id>             — delete disabled user (cascade)
POST   /api/admin/users/<id>/resend-invite — invalidate old token, issue new one
"""
from __future__ import annotations

import os

from flask import Blueprint, g, jsonify, request

from ..middleware import require_admin
from ..services import user_service as _user_svc
from ..services.auth_service import canonicalize_email
from ..services.db_service import DatabaseService
from ..services.user_service import (
    create_invite_token,
    create_invited_user,
    get_user_by_id,
    invite_url_for,
    mark_token_used,
)

admin_users_bp = Blueprint("admin_users", __name__)


def _user_to_dict(row) -> dict:
    return {
        "id": row[0],
        "email": row[1],
        "name": row[2],
        "picture_url": row[3],
        "role": row[4],
        "status": row[5],
        "has_google": bool(row[6]),
        "has_password": bool(row[7]),
        "invited_at": row[8],
        "activated_at": row[9],
        "last_login_at": row[10],
        "invited_by_email": row[11],
    }


def _safe_user(user: dict) -> dict:
    return {k: v for k, v in user.items() if k not in ("password_hash", "google_sub")}


@admin_users_bp.get("/users")
@require_admin
def get_users():
    db = DatabaseService()
    with db.connection() as conn:
        rows = conn.execute(
            "SELECT u.id, u.email, u.name, u.picture_url, u.role, u.status, "
            "u.google_sub IS NOT NULL, u.password_hash IS NOT NULL, "
            "u.invited_at, u.activated_at, u.last_login_at, "
            "inviter.email "
            "FROM users u "
            "LEFT JOIN users inviter ON u.invited_by = inviter.id "
            "ORDER BY u.invited_at DESC, u.rowid DESC"
        ).fetchall()
    return jsonify([_user_to_dict(r) for r in rows])


@admin_users_bp.post("/users")
@require_admin
def invite_user():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip()
    role = body.get("role", "member")

    if not email:
        return jsonify({"error": "email is required"}), 400
    if role not in ("admin", "member"):
        return jsonify({"error": "invalid role"}), 400

    canonical = canonicalize_email(email)
    if not canonical:
        return jsonify({"error": "invalid email"}), 400

    db = DatabaseService()
    with db.connection() as conn:
        existing = conn.execute(
            "SELECT id, email, role, status FROM users WHERE email = ?", (canonical,)
        ).fetchone()
        if existing:
            return jsonify({
                "error": "user already exists",
                "existing": {
                    "id": existing[0],
                    "email": existing[1],
                    "role": existing[2],
                    "status": existing[3],
                },
            }), 409

        user = create_invited_user(conn, canonical, role=role, invited_by=g.user.id)
        token = create_invite_token(conn, user["id"])

    base_url = os.environ.get("APP_BASE_URL", request.host_url.rstrip("/"))
    url = invite_url_for(token, base_url)
    return jsonify({"user": _safe_user(user), "invite_url": url}), 201


@admin_users_bp.patch("/users/<user_id>")
@require_admin
def patch_user(user_id):
    body = request.get_json(silent=True) or {}
    new_role = body.get("role")
    new_status = body.get("status")

    if new_role is None and new_status is None:
        return jsonify({"error": "no fields to update"}), 400

    db = DatabaseService()
    with db.connection() as conn:
        target = get_user_by_id(conn, user_id)
        if target is None:
            return jsonify({"error": "user not found"}), 404

        if new_role is not None and new_role not in ("admin", "member"):
            return jsonify({"error": "invalid role"}), 400
        if new_status is not None and new_status not in ("active", "disabled", "invited"):
            return jsonify({"error": "invalid status"}), 400

        # Only-admin protection (runs before own-role check to give clearer error)
        if new_role == "member" and target["role"] == "admin":
            count = conn.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'admin' AND status != 'disabled'"
            ).fetchone()[0]
            if count == 1:
                return jsonify({"error": "cannot demote the only admin"}), 400

        # Self-protection: own role change
        if new_role is not None and user_id == g.user.id:
            return jsonify({"error": "cannot change own role"}), 400

        # Self-protection: disable self
        if new_status == "disabled" and user_id == g.user.id:
            return jsonify({"error": "cannot disable self"}), 400

        if new_role is not None:
            conn.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
        if new_status is not None:
            conn.execute("UPDATE users SET status = ? WHERE id = ?", (new_status, user_id))

        updated = get_user_by_id(conn, user_id)

    return jsonify(_safe_user(updated))


@admin_users_bp.delete("/users/<user_id>")
@require_admin
def delete_user(user_id):
    db = DatabaseService()
    with db.connection() as conn:
        target = get_user_by_id(conn, user_id)
        if target is None:
            return jsonify({"error": "user not found"}), 404

        if user_id == g.user.id:
            return jsonify({"error": "cannot delete self"}), 400

        if target["status"] != "disabled":
            return jsonify({"error": "user must be disabled before deletion"}), 400

        if target["role"] == "admin":
            admin_count = conn.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'admin' AND status != 'disabled'"
            ).fetchone()[0]
            if admin_count <= 1:
                return jsonify({"error": "cannot delete the only admin"}), 400

    try:
        _user_svc.delete_user_cascading(user_id)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return "", 204


@admin_users_bp.post("/users/<user_id>/resend-invite")
@require_admin
def resend_invite(user_id):
    db = DatabaseService()
    with db.connection() as conn:
        target = get_user_by_id(conn, user_id)
        if target is None:
            return jsonify({"error": "user not found"}), 404

        if target["status"] != "invited":
            return jsonify({"error": "user is not in invited state"}), 400

        old_tokens = conn.execute(
            "SELECT token FROM invite_tokens WHERE user_id = ? AND used_at IS NULL",
            (user_id,),
        ).fetchall()
        for row in old_tokens:
            mark_token_used(conn, row[0])

        new_token = create_invite_token(conn, user_id)

    base_url = os.environ.get("APP_BASE_URL", request.host_url.rstrip("/"))
    url = invite_url_for(new_token, base_url)
    return jsonify({"invite_url": url})
