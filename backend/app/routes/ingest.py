from flask import Blueprint, jsonify

ingest_bp = Blueprint("ingest", __name__)


@ingest_bp.get("", strict_slashes=False)
def index():
    return jsonify({"status": "ok", "stub": True})
