import os
from flask import Flask, jsonify

from .services.db_service import DatabaseService
from .services.qdrant_service import QdrantService
from .routes.ingest import ingest_bp
from .routes.wiki import wiki_bp
from .routes.chat import chat_bp
from .routes.private import private_bp
from .routes.files import files_bp
from .routes.prompts import prompts_bp

REQUIRED_ENV_VARS = [
    "OPENAI_API_KEY",
    "FLASK_SECRET_KEY",
    "QDRANT_HOST",
    "QDRANT_PORT",
]


def create_app(config: dict | None = None) -> Flask:
    _validate_env()

    app = Flask(__name__)
    app.secret_key = os.environ["FLASK_SECRET_KEY"]

    if config:
        app.config.update(config)

    DatabaseService()
    QdrantService()

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
