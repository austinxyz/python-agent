import sqlite3

from flask import Blueprint, jsonify, request

from app.middleware import require_auth
from app.services.db_service import DatabaseService
from app.services.qdrant_service import QdrantService

wiki_bp = Blueprint("wiki", __name__)

_ENTRY_COLS = "id AS file_id, title, orig_name, filename, source_type, source_url, domain, chunk_count, created_at"


def _row_to_entry(row: sqlite3.Row) -> dict:
    return {
        "file_id": row["file_id"],
        "title": row["title"],
        "orig_name": row["orig_name"],
        "filename": row["filename"],
        "source_type": row["source_type"],
        "source_url": row["source_url"],
        "domain": row["domain"],
        "chunk_count": row["chunk_count"],
        "created_at": row["created_at"],
    }


@wiki_bp.get("/tree", strict_slashes=False)
@require_auth
def get_tree():
    try:
        domain_to_file_ids = QdrantService().get_tree()
    except Exception:
        return jsonify({"error": "knowledge store unavailable"}), 503

    if not domain_to_file_ids:
        return jsonify({})

    all_ids = [fid for ids in domain_to_file_ids.values() for fid in ids]
    placeholders = ",".join("?" * len(all_ids))
    db = DatabaseService()
    with db.connection() as conn:
        rows = conn.execute(
            f"SELECT {_ENTRY_COLS} FROM files WHERE id IN ({placeholders})",
            all_ids,
        ).fetchall()
    row_map = {r["file_id"]: _row_to_entry(r) for r in rows}

    result: dict[str, list[dict]] = {}
    for domain, file_ids in domain_to_file_ids.items():
        entries = [row_map[fid] for fid in file_ids if fid in row_map]
        if entries:
            result[domain] = entries
    return jsonify(result)


@wiki_bp.get("", strict_slashes=False)
@require_auth
def list_entries():
    domain = request.args.get("domain")
    db = DatabaseService()
    with db.connection() as conn:
        if domain:
            rows = conn.execute(
                f"SELECT {_ENTRY_COLS} FROM files WHERE domain = ? ORDER BY created_at DESC",
                (domain,),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT {_ENTRY_COLS} FROM files ORDER BY created_at DESC"
            ).fetchall()
    return jsonify([_row_to_entry(r) for r in rows])


@wiki_bp.get("/<file_id>", strict_slashes=False)
@require_auth
def get_entry(file_id: str):
    db = DatabaseService()
    with db.connection() as conn:
        row = conn.execute(
            f"SELECT {_ENTRY_COLS} FROM files WHERE id = ?",
            (file_id,),
        ).fetchone()
    if row is None:
        return jsonify({"error": "entry not found"}), 404
    return jsonify(_row_to_entry(row))
