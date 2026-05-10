from flask import Blueprint, g, jsonify, send_file, abort, request

from app.middleware import require_auth
from app.services.db_service import DatabaseService
from app.services.file_service import FileService

files_bp = Blueprint("files", __name__)


@files_bp.get("", strict_slashes=False)
@require_auth
def list_files():
    user_id = g.user.id
    db = DatabaseService()
    with db.connection() as conn:
        rows = conn.execute(
            """
            SELECT id AS file_id, user_id, filename, orig_name, source_type, source_url,
                   domain, topic, title, size_bytes, chunk_count, created_at
            FROM files
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@files_bp.patch("/<file_id>", strict_slashes=False)
@require_auth
def update_file_title(file_id: str):
    user_id = g.user.id
    data = request.get_json(silent=True) or {}
    if "title" not in data:
        abort(400)
    title = data["title"]
    if title is not None and not isinstance(title, str):
        abort(400)
    title = title.strip() if title else None
    db = DatabaseService()
    with db.connection() as conn:
        result = conn.execute(
            "UPDATE files SET title = ? WHERE id = ? AND user_id = ?",
            (title, file_id, user_id),
        )
        if result.rowcount == 0:
            abort(404)
    return jsonify({"file_id": file_id, "title": title})


@files_bp.get("/<file_id>/download", strict_slashes=False)
@require_auth
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
@require_auth
def view_file(file_id: str):
    db = DatabaseService()
    with db.connection() as conn:
        row = conn.execute(
            "SELECT user_id, filename, orig_name, source_type, source_url FROM files WHERE id = ?",
            (file_id,),
        ).fetchone()
    if row is None:
        abort(404)

    # Serve local file if available (covers file, text, and newly-ingested url types)
    svc = FileService()
    path = svc.resolve(row["user_id"], file_id, row["filename"]) if row["filename"] else None
    if path is not None and path.exists():
        return send_file(path, as_attachment=False)

    # Fallback for url-type files without a local copy: re-fetch and extract text
    if row["source_type"] == "url":
        import httpx
        from flask import Response
        from app.graphs.ingest_pipeline import _validate_url, _html_to_text
        url = row["source_url"]
        _validate_url(url)
        resp = httpx.get(url, timeout=15.0, follow_redirects=True)
        _validate_url(str(resp.url))
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        text = _html_to_text(resp.text) if "html" in content_type else resp.text
        return Response(text, mimetype="text/plain; charset=utf-8")

    abort(404)
