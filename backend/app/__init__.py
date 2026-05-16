import os
from datetime import timedelta

from flask import Flask, jsonify

from .services.db_service import DatabaseService
from .services.qdrant_service import QdrantService
from .services.user_service import bootstrap_initial_admin
from .routes.ingest import ingest_bp
from .routes.wiki import wiki_bp
from .routes.chat import chat_bp
from .routes.private import private_bp
from .routes.files import files_bp
from .routes.prompts import prompts_bp
from .routes.admin import admin_bp
from .routes.auth import auth_bp

REQUIRED_ENV_VARS = [
    "OPENAI_API_KEY",
    "FLASK_SECRET_KEY",
    "QDRANT_HOST",
    "QDRANT_PORT",
    "UPLOADS_PATH",
]


def _session_cookie_secure() -> bool:
    """Default True; set false explicitly for NAS HTTP via env var."""
    val = os.environ.get("SESSION_COOKIE_SECURE", "true").strip().lower()
    return val not in ("false", "0", "no")


def create_app(config: dict | None = None) -> Flask:
    _validate_env()

    app = Flask(__name__)
    app.secret_key = os.environ["FLASK_SECRET_KEY"]

    # Session cookie attributes (multi-user-auth-core).
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = _session_cookie_secure()
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

    if config:
        app.config.update(config)

    db = DatabaseService()
    qdrant = QdrantService()

    # Bootstrap initial admin + migrate user_id='default' data on first startup.
    base_url = os.environ.get("APP_BASE_URL", "http://10.0.0.20:8910")
    try:
        with db.connection() as conn:
            bootstrap_initial_admin(conn, qdrant=qdrant, base_url=base_url)
    except Exception as e:
        # Non-fatal — app still starts even if bootstrap fails (e.g., Qdrant
        # unreachable). Admin can manually invite via CLI later.
        app.logger.warning("[BOOTSTRAP] non-fatal failure: %s", e)

    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(ingest_bp, url_prefix="/api/ingest")
    app.register_blueprint(wiki_bp, url_prefix="/api/wiki")
    app.register_blueprint(chat_bp, url_prefix="/api/chat")
    app.register_blueprint(private_bp, url_prefix="/api/private")
    app.register_blueprint(files_bp, url_prefix="/api/files")
    app.register_blueprint(prompts_bp, url_prefix="/api/prompts")

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    return app


def _validate_env() -> None:
    for var in REQUIRED_ENV_VARS:
        if not os.environ.get(var):
            raise RuntimeError(f"Missing required environment variable: {var}")
    provider = os.environ.get("LLM_PROVIDER", "anthropic")
    if provider == "anthropic" and not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("Missing required environment variable: ANTHROPIC_API_KEY")
    elif provider == "openai" and not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("Missing required environment variable: OPENAI_API_KEY")
