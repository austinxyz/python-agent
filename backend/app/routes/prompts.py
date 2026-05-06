from flask import Blueprint, jsonify

prompts_bp = Blueprint("prompts", __name__)


@prompts_bp.get("", strict_slashes=False)
def index():
    return jsonify({"status": "ok", "stub": True})
