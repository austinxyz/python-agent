from flask import Blueprint, jsonify, send_file, abort

from app.services.db_service import DatabaseService
from app.services.file_service import FileService

files_bp = Blueprint("files", __name__)


@files_bp.get("", strict_slashes=False)
def list_files():
    user_id = "default"
    db = DatabaseService()
    with db.connection() as conn:
        rows = conn.execute(
            """
            SELECT id AS file_id, user_id, orig_name, source_type, source_url,
                   domain, topic, title, size_bytes, chunk_count, created_at
            FROM files
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@files_bp.get("/<file_id>/download", strict_slashes=False)
def download_file(file_id: str):
    db = DatabaseService()
    with db.connection() as conn:
        row = conn.execute(
            "SELECT user_id, filename, orig_name FROM files WHERE id = ?",
            (file_id,),
        ).fetchone()
    if row is None:
        abort(404)

    svc = FileService()
    path = svc.resolve(row["user_id"], file_id, row["filename"])
    if path is None or not path.exists():
        abort(404)

    return send_file(path, as_attachment=True, download_name=row["orig_name"])


@files_bp.get("/<file_id>/content", strict_slashes=False)
def view_file(file_id: str):
    db = DatabaseService()
    with db.connection() as conn:
        row = conn.execute(
            "SELECT user_id, filename, orig_name, source_type, source_url FROM files WHERE id = ?",
            (file_id,),
        ).fetchone()
    if row is None:
        abort(404)

    if row["source_type"] == "url":
        import httpx
        from flask import Response
        from app.graphs.ingest_pipeline import _validate_url
        url = row["source_url"]
        _validate_url(url)
        resp = httpx.get(url, timeout=15.0, follow_redirects=True)
        resp.raise_for_status()
        return Response(resp.text, mimetype="text/plain; charset=utf-8")

    svc = FileService()
    path = svc.resolve(row["user_id"], file_id, row["filename"])
    if path is None or not path.exists():
        abort(404)
    return send_file(path, as_attachment=False)
