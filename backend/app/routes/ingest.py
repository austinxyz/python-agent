import re
import threading
import uuid

from flask import Blueprint, g, jsonify, request

from app.graphs.ingest_pipeline import IngestPipeline
from app.middleware import require_auth
from app.services.job_registry import JobRegistry

ingest_bp = Blueprint("ingest", __name__)

job_registry = JobRegistry()

_MAX_FILE_BYTES = 50 * 1024 * 1024  # 50 MB
_VALID_DESTINATIONS = {"knowledge", "private"}
_UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')


@ingest_bp.post("", strict_slashes=False)
@require_auth
def ingest_post():
    source_type = request.form.get("source_type", "").strip()
    if not source_type:
        return jsonify({"error": "source_type is required"}), 400

    destination = request.form.get("destination", "knowledge").strip()
    if destination not in _VALID_DESTINATIONS:
        return jsonify({"error": f"destination must be one of {sorted(_VALID_DESTINATIONS)}"}), 400

    file_content: bytes | None = None
    filename: str | None = None
    orig_name: str = ""

    if source_type == "file":
        f = request.files.get("file")
        if f is None:
            return jsonify({"error": "file is required when source_type is 'file'"}), 400
        if request.content_length and request.content_length > _MAX_FILE_BYTES:
            return jsonify({"error": "file too large (max 50 MB)"}), 413
        file_content = f.read()
        if len(file_content) > _MAX_FILE_BYTES:
            return jsonify({"error": "file too large (max 50 MB)"}), 413
        filename = f.filename or ""
        orig_name = filename

    content = request.form.get("content") if source_type == "text" else None
    source_url = request.form.get("source_url") if source_type == "url" else None
    domain = request.form.get("domain", "general").strip()
    topic = request.form.get("topic", "general").strip()
    title = request.form.get("title") or None
    user_id = g.user.id

    job_id = str(uuid.uuid4())
    file_id = str(uuid.uuid4())
    job_registry.create(job_id)

    def _run() -> None:
        try:
            pipeline = IngestPipeline()
            result = pipeline.run(
                source_type=source_type,
                destination=destination,
                user_id=user_id,
                orig_name=orig_name or filename or source_url or "",
                domain=domain,
                topic=topic,
                title=title,
                content=content,
                file_content=file_content,
                filename=filename,
                source_url=source_url,
                job_id=job_id,
                file_id=file_id,
            )
            job_registry.update(job_id, {
                "status": result.get("status"),
                "file_id": result.get("file_id"),
                "chunk_count": result.get("chunk_count"),
                "error": result.get("error"),
            })
        except Exception as exc:
            job_registry.update(job_id, {"status": "error", "error": str(exc)})

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return jsonify({"job_id": job_id}), 202


@ingest_bp.get("/status/<job_id>", strict_slashes=False)
@require_auth
def ingest_status(job_id: str):
    if not _UUID_RE.match(job_id):
        return jsonify({"error": "invalid job_id format"}), 400
    job = job_registry.get(job_id)
    if job is None:
        return jsonify({"error": "job not found"}), 404
    return jsonify(job), 200
