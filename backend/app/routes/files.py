from flask import Blueprint, jsonify

files_bp = Blueprint("files", __name__)


@files_bp.get("", strict_slashes=False)
def index():
    return jsonify({"status": "ok", "stub": True})
