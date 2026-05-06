from flask import Blueprint, jsonify

chat_bp = Blueprint("chat", __name__)


@chat_bp.get("", strict_slashes=False)
def index():
    return jsonify({"status": "ok", "stub": True})
