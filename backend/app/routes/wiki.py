from flask import Blueprint, jsonify

wiki_bp = Blueprint("wiki", __name__)


@wiki_bp.get("", strict_slashes=False)
def index():
    return jsonify({"status": "ok", "stub": True})
