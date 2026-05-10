"""Private data API: structured template entries (Qdrant + SQLite) and notes (SQLite)."""
import json
import sqlite3
import uuid
from typing import Any

from flask import Blueprint, g, jsonify, request
from qdrant_client.http import models as qmodels

from app.graphs.text_chunker import chunk_text
from app.middleware import require_auth
from app.routes.private_templates import (
    PRIVATE_TEMPLATES,
    VALID_TEMPLATE_TYPES,
    derive_text_for_embedding,
    template_default_directory,
)
from app.services.db_service import DatabaseService
from app.services.embedding_service import EmbeddingService
from app.services.qdrant_service import QdrantService

private_bp = Blueprint("private", __name__)

# All route handlers in this blueprint use @require_auth and g.user.id;
# the legacy hardcoded user_id="default" was removed in multi-user-auth-core.


def _row_to_entry(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "template_type": row["template_type"],
        "title": row["title"],
        "content_json": json.loads(row["content_json"]) if row["content_json"] else {},
        "directory": row["directory"] or "",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _normalize_directory(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("directory must be a string")
    return value.strip().strip("/")


def _chunked_points_for(
    entry_id: str,
    template_type: str,
    title: str,
    directory: str,
    text: str,
    embedding: EmbeddingService,
) -> list[qmodels.PointStruct]:
    """Chunk the entry text and produce one Qdrant point per chunk.

    All points share the same `source_file_id = entry_id` so search-side
    deduplication (qa_agent._to_source) treats them as a single source.
    Each point gets a fresh UUID `id` and its own `chunk_index`. This is
    what unblocks long entries — V1 used to call `embed(text)` once and
    1-shotted on inputs > 8192 OpenAI tokens.
    """
    chunks = chunk_text(text)
    points: list[qmodels.PointStruct] = []
    for chunk in chunks:
        vector = embedding.embed(chunk["text"])
        points.append(
            qmodels.PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "user_id": g.user.id,
                    "template_type": template_type,
                    "title": title,
                    "directory": directory,
                    "source_file_id": entry_id,
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                },
            )
        )
    return points


def _coerce_content_json(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
    raise ValueError("content_json must be a JSON object")


@private_bp.get("", strict_slashes=False)
@require_auth
def index():
    return jsonify({"status": "ok", "stub": True})


@private_bp.get("/templates", strict_slashes=False)
@require_auth
def list_templates():
    return jsonify(PRIVATE_TEMPLATES)


@private_bp.get("/entries", strict_slashes=False)
@require_auth
def list_entries():
    db = DatabaseService()
    with db.connection() as conn:
        rows = conn.execute(
            """
            SELECT id, template_type, title, content_json, directory, created_at, updated_at
            FROM private_entries
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (g.user.id,),
        ).fetchall()
    return jsonify([_row_to_entry(r) for r in rows])


@private_bp.post("/entries", strict_slashes=False)
@require_auth
def create_entry():
    payload = request.get_json(silent=True) or {}
    template_type = (payload.get("template_type") or "").strip()
    title = (payload.get("title") or "").strip()

    if not template_type or not title:
        return jsonify({"error": "template_type and title are required"}), 400
    if template_type not in VALID_TEMPLATE_TYPES:
        return jsonify({"error": f"unknown template_type: {template_type}"}), 400

    try:
        content_json = _coerce_content_json(payload.get("content_json"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        directory = _normalize_directory(payload.get("directory"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if not directory:
        directory = template_default_directory(template_type)

    entry_id = str(uuid.uuid4())
    text = derive_text_for_embedding(template_type, title, content_json)

    # SQLite is the source of truth — write metadata first. If Qdrant
    # upsert later fails, we end up with a row whose vectors can be
    # re-built by a re-index job, but we never end up with orphaned
    # vectors that can't be reconciled.
    db = DatabaseService()
    with db.connection() as conn:
        conn.execute(
            """
            INSERT INTO private_entries (id, user_id, template_type, title, content_json, directory)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (entry_id, g.user.id, template_type, title, json.dumps(content_json, ensure_ascii=False), directory),
        )
        row = conn.execute(
            "SELECT id, template_type, title, content_json, directory, created_at, updated_at"
            " FROM private_entries WHERE id = ? AND user_id = ?",
            (entry_id, g.user.id),
        ).fetchone()

    points = _chunked_points_for(
        entry_id=entry_id,
        template_type=template_type,
        title=title,
        directory=directory,
        text=text or title,
        embedding=EmbeddingService(),
    )
    QdrantService().upsert_private(points)

    return jsonify(_row_to_entry(row)), 201


@private_bp.put("/entries/<entry_id>", strict_slashes=False)
@require_auth
def update_entry(entry_id: str):
    payload = request.get_json(silent=True) or {}

    db = DatabaseService()
    with db.connection() as conn:
        existing = conn.execute(
            "SELECT id, template_type, title, content_json, directory FROM private_entries"
            " WHERE id = ? AND user_id = ?",
            (entry_id, g.user.id),
        ).fetchone()
        if existing is None:
            return jsonify({"error": "entry not found"}), 404

        new_title = payload.get("title", existing["title"])
        if not isinstance(new_title, str) or not new_title.strip():
            return jsonify({"error": "title must be a non-empty string"}), 400
        new_title = new_title.strip()

        if "content_json" in payload:
            try:
                new_content = _coerce_content_json(payload["content_json"])
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400
        else:
            new_content = json.loads(existing["content_json"]) if existing["content_json"] else {}

        if "directory" in payload:
            try:
                new_directory = _normalize_directory(payload["directory"])
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400
        else:
            new_directory = existing["directory"] or ""

        template_type = existing["template_type"]
        conn.execute(
            """
            UPDATE private_entries
            SET title = ?, content_json = ?, directory = ?,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id = ? AND user_id = ?
            """,
            (new_title, json.dumps(new_content, ensure_ascii=False), new_directory, entry_id, g.user.id),
        )
        row = conn.execute(
            "SELECT id, template_type, title, content_json, directory, created_at, updated_at"
            " FROM private_entries WHERE id = ? AND user_id = ?",
            (entry_id, g.user.id),
        ).fetchone()

    # Refresh embedding only after SQLite commit succeeds. Chunked update
    # = filter-delete the old chunks (whatever count) then upsert the new
    # ones. The single-point legacy entries also match the filter (their
    # payload.source_file_id == entry_id) so cleanup is uniform.
    text = derive_text_for_embedding(template_type, new_title, new_content)
    qdrant = QdrantService()
    qdrant.delete_private_by_source_file_id(g.user.id, entry_id)
    points = _chunked_points_for(
        entry_id=entry_id,
        template_type=template_type,
        title=new_title,
        directory=new_directory,
        text=text or new_title,
        embedding=EmbeddingService(),
    )
    qdrant.upsert_private(points)

    return jsonify(_row_to_entry(row)), 200


@private_bp.delete("/entries/<entry_id>", strict_slashes=False)
@require_auth
def delete_entry(entry_id: str):
    db = DatabaseService()
    with db.connection() as conn:
        existing = conn.execute(
            "SELECT id FROM private_entries WHERE id = ? AND user_id = ?",
            (entry_id, g.user.id),
        ).fetchone()
        if existing is None:
            return jsonify({"error": "entry not found"}), 404

        conn.execute(
            "DELETE FROM private_entries WHERE id = ? AND user_id = ?",
            (entry_id, g.user.id),
        )

    # Drop every chunk only after SQLite has committed. Filter-based
    # delete cleans up both new chunked entries (multiple points sharing
    # source_file_id) and legacy single-point entries (1 point whose
    # payload.source_file_id == entry_id).
    QdrantService().delete_private_by_source_file_id(g.user.id, entry_id)

    return jsonify({"ok": True}), 200


# ---------------------------------------------------------------------------
# Notes endpoints (SQLite-only — never embedded into Qdrant in V1)
# ---------------------------------------------------------------------------


def _row_to_note(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "directory": row["directory"] or "",
        "content": row["content"] or "",
        "chat_ref": row["chat_ref"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _build_tree(notes: list[dict[str, Any]]) -> dict[str, Any]:
    """Convert a flat note list into a nested tree.

    Each tree node is a dict whose keys are subdirectory names; the special
    `_notes` key holds the list of notes that live directly in that node.
    Root-level notes appear under `tree["_notes"]`.
    """
    tree: dict[str, Any] = {}
    for note in notes:
        directory = (note.get("directory") or "").strip("/").strip()
        node = tree
        if directory:
            for segment in directory.split("/"):
                segment = segment.strip()
                if not segment:
                    continue
                if segment not in node or not isinstance(node[segment], dict):
                    node[segment] = {}
                node = node[segment]
        node.setdefault("_notes", []).append(note)
    return tree


@private_bp.get("/notes", strict_slashes=False)
@require_auth
def list_notes():
    db = DatabaseService()
    with db.connection() as conn:
        rows = conn.execute(
            """
            SELECT id, title, directory, content, chat_ref, created_at, updated_at
            FROM notes
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (g.user.id,),
        ).fetchall()
    notes = [_row_to_note(r) for r in rows]
    return jsonify({"notes": notes, "tree": _build_tree(notes)})


@private_bp.post("/notes", strict_slashes=False)
@require_auth
def create_note():
    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    content = payload.get("content") or ""
    if not isinstance(content, str):
        return jsonify({"error": "content must be a string"}), 400

    directory = payload.get("directory") or ""
    if not isinstance(directory, str):
        return jsonify({"error": "directory must be a string"}), 400
    directory = directory.strip().strip("/")

    chat_ref = payload.get("chat_ref")
    if chat_ref is not None and not isinstance(chat_ref, str):
        return jsonify({"error": "chat_ref must be a string"}), 400

    note_id = str(uuid.uuid4())
    db = DatabaseService()
    with db.connection() as conn:
        conn.execute(
            """
            INSERT INTO notes (id, user_id, title, directory, content, chat_ref)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (note_id, g.user.id, title, directory, content, chat_ref),
        )
        row = conn.execute(
            "SELECT id, title, directory, content, chat_ref, created_at, updated_at"
            " FROM notes WHERE id = ?",
            (note_id,),
        ).fetchone()
    return jsonify(_row_to_note(row)), 201


@private_bp.put("/notes/<note_id>", strict_slashes=False)
@require_auth
def update_note(note_id: str):
    payload = request.get_json(silent=True) or {}
    db = DatabaseService()
    with db.connection() as conn:
        existing = conn.execute(
            "SELECT id, title, directory, content FROM notes WHERE id = ? AND user_id = ?",
            (note_id, g.user.id),
        ).fetchone()
        if existing is None:
            return jsonify({"error": "note not found"}), 404

        new_title = payload.get("title", existing["title"])
        if not isinstance(new_title, str) or not new_title.strip():
            return jsonify({"error": "title must be a non-empty string"}), 400
        new_title = new_title.strip()

        new_directory = payload.get("directory", existing["directory"])
        if not isinstance(new_directory, str):
            return jsonify({"error": "directory must be a string"}), 400
        new_directory = new_directory.strip().strip("/")

        new_content = payload.get("content", existing["content"])
        if not isinstance(new_content, str):
            return jsonify({"error": "content must be a string"}), 400

        conn.execute(
            """
            UPDATE notes
            SET title = ?, directory = ?, content = ?,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id = ? AND user_id = ?
            """,
            (new_title, new_directory, new_content, note_id, g.user.id),
        )
        row = conn.execute(
            "SELECT id, title, directory, content, chat_ref, created_at, updated_at"
            " FROM notes WHERE id = ?",
            (note_id,),
        ).fetchone()
    return jsonify(_row_to_note(row)), 200


@private_bp.delete("/notes/<note_id>", strict_slashes=False)
@require_auth
def delete_note(note_id: str):
    db = DatabaseService()
    with db.connection() as conn:
        existing = conn.execute(
            "SELECT id FROM notes WHERE id = ? AND user_id = ?",
            (note_id, g.user.id),
        ).fetchone()
        if existing is None:
            return jsonify({"error": "note not found"}), 404
        conn.execute(
            "DELETE FROM notes WHERE id = ? AND user_id = ?",
            (note_id, g.user.id),
        )
    # Notes are SQLite-only — Qdrant is intentionally NOT touched.
    return jsonify({"ok": True}), 200
