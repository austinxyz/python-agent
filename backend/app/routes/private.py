from flask import Blueprint, jsonify

private_bp = Blueprint("private", __name__)


@private_bp.get("", strict_slashes=False)
def index():
    return jsonify({"status": "ok", "stub": True})
