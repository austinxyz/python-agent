## Context

The project currently has only documentation (design spec, requirements catalogue, CLAUDE.md). No `backend/` or `frontend/` directories exist. Before any feature can be implemented, we need a runnable skeleton that all future changes can build into.

Key constraints from CLAUDE.md and requirements:
- SQLite accessed via plain `sqlite3` module with schema in `backend/db/schema.sql` — no ORM migrations
- Private Qdrant queries MUST always include `user_id` payload filter
- Axios baseURL is `/api` — never double-prefixed
- LLM provider is env-driven; embedding is OpenAI-only (hard dependency)
- `TreeNav.vue` is shared between wiki and ingest — implement once

## Goals / Non-Goals

**Goals:**
- Runnable `docker compose up` that brings up all three services
- Flask app factory with all six blueprint stubs returning `{"status": "ok"}`
- Qdrant service that creates `knowledge` and `private` collections on startup (idempotent)
- SQLite schema initialised from `backend/db/schema.sql` on startup
- LLM and embedding service wrappers that read config from env
- Vue 3 + Vite frontend with four view skeletons and the left-nav layout shell
- `TreeNav.vue` stub component usable by both wiki and ingest tabs
- Smoke-test suite: Flask starts, all blueprint routes return 200, Qdrant collections exist

**Non-Goals:**
- Any business logic (ingest, search, chat, private data flows)
- Authentication or multi-user support
- MCP data source integration
- Railway or NAS deployment config
- Full test coverage (80% gate deferred to feature changes)

## Decisions

### 1. Flask App Factory (`create_app`)

**Choice:** Implement `backend/app/__init__.py` as `create_app(config=None)` returning a configured `Flask` app.

**Why:** `pytest-flask` requires the factory pattern for the `app` fixture. Module-level `app = Flask(__name__)` works for simple scripts but cannot be re-instantiated per test, causing state leakage between tests.

**Alternative considered:** Module-level singleton — simpler, but breaks test isolation and blocks future multi-environment config (dev/test/prod).

### 2. SQLite via `sqlite3`, schema-first

**Choice:** Use Python's built-in `sqlite3` module. Schema lives in `backend/db/schema.sql`. On startup, `backend/app/services/db.py` calls `executescript` to apply the schema (idempotent `CREATE TABLE IF NOT EXISTS`).

**Why:** The CLAUDE.md convention explicitly states "SQLite accessed via sqlite3 module or SQLAlchemy, no ORM migrations — plain SQL schema in backend/db/schema.sql". SQLAlchemy ORM + Alembic adds migration infrastructure that's unnecessary for a single-user V1 with a stable schema.

**Alternative considered:** SQLAlchemy Core (no ORM) — adds query-builder ergonomics but still requires careful migration management. Defer until schema volatility justifies it.

**SQLite WAL mode:** Enable WAL on every connection open (`PRAGMA journal_mode=WAL`) to prevent reader-blocking-writer issues during concurrent Flask requests.

### 3. Qdrant Collection Initialization Strategy

**Choice:** On startup, the Qdrant service calls `get_collection` for each collection name. If it raises `UnexpectedResponse` (404), it calls `create_collection` with the correct vector config. This is idempotent — safe to run on every restart.

**Vector config:** `text-embedding-3-small` outputs 1536 dimensions. Collections: `size=1536, distance=Distance.COSINE`.

**Why:** A separate init script adds deployment complexity. Inline idempotent init is the simplest path and is standard practice for self-hosted Qdrant.

**Alternative considered:** Docker entrypoint init script — adds another file, another failure mode, and doesn't survive config changes without manual intervention.

**user_id filter enforcement:** The `private` collection service methods MUST accept `user_id` as a required parameter. No default value. This makes missing `user_id` a call-site error, not a runtime data leak.

### 4. Vite Dev Proxy for API Calls

**Choice:** Configure `vite.config.js` with `server.proxy: { '/api': 'http://api:5000' }` (container name in Docker, `localhost:5000` for bare `npm run dev`). Axios is configured with `baseURL: '/api'`.

**Why:** Eliminates CORS issues in development. The `/api` prefix is consistent between dev (proxied) and production (nginx or reverse proxy at the same path). Frontend code never needs to know the backend host.

**Alternative considered:** Flask-CORS with `*` origin — works but is a security footgun that can accidentally be left on in production.

### 5. Vue Router Mode

**Choice:** History mode (`createWebHistory()`).

**Why:** Clean URLs (`/wiki`, `/chat`) required for the design. Vite dev server handles history-mode fallback. Production Docker setup will use nginx with `try_files $uri /index.html`.

**Alternative considered:** Hash mode — easier server config, but `/#/wiki` is inconsistent with the brainstormed UI design.

### 6. Pinia Store Structure

**Choice:** Create one Pinia store stub per feature domain (`useWikiStore`, `useIngestStore`, `useChatStore`, `usePrivateStore`). Stores are empty in this change; feature changes fill them in.

**Why:** Establishes the store-per-domain pattern that all feature branches will follow. Avoids the anti-pattern of a single god-store.

## Risks / Trade-offs

**Qdrant startup race** → Flask starts before Qdrant is ready in Docker Compose.  
Mitigation: Add `healthcheck` to the `qdrant` service and `depends_on: qdrant: condition: service_healthy` on the `api` service.

**`OPENAI_API_KEY` hard dependency at startup** → App fails to start if key is missing, even when only doing non-embedding operations.  
Mitigation: Validate presence of all required env vars in `create_app` and raise a clear `RuntimeError` with the variable name. Document in `.env.example`.

**SQLite single-writer bottleneck** → Concurrent writes block under load.  
Mitigation: WAL mode (see Decision 2). Acceptable for V1 single-user. If this becomes an issue, migrate to PostgreSQL (schema is portable).

**Blueprint stubs returning 200 prematurely** → Frontend could be accidentally wired to stub endpoints.  
Mitigation: All stubs return `{"status": "ok", "stub": true}`. Feature changes replace `"stub": true` with real responses.

## Migration Plan

This is a greenfield change — no existing data or services to migrate.

To start fresh after a failed setup:
```
docker compose down -v
docker compose up --build
```

The `-v` flag removes named volumes (`qdrant_data`, `uploads`), giving a clean slate.

## Open Questions

- _(none blocking)_ — all technical decisions are resolved above.
- Future: Railway deployment config (ARCH-06) will need a separate `docker-compose.railway.yml` or environment variable overrides. Out of scope for this change.
