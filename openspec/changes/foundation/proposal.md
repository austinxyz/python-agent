## Why

The project has design specs and requirements but no runnable code. The foundation change establishes the complete project skeleton — Docker Compose orchestration, Flask app factory, Qdrant/SQLite initialization, and Vue 3 frontend scaffold — so that all subsequent feature changes have a working runtime to build into.

## What Changes

- Add `docker-compose.yml` with three services (`frontend`, `api`, `qdrant`) and two persistent volumes (`qdrant_data`, `uploads`)
- Add `.env.example` with all required environment variables; add `.env` to `.gitignore`
- Add `backend/` directory: Flask app factory, blueprint stubs for all six route modules, Qdrant service (creates `knowledge` and `private` collections on startup), SQLite schema migration (`backend/db/schema.sql`), and LLM/embedding service wrappers
- Add `frontend/` directory: Vue 3 + Vite + Pinia scaffold with Vue Router, four view skeletons (`WikiView`, `IngestView`, `ChatView`, `PrivateView`), left-nav layout shell, and Axios configured with `/api` baseURL
- No business logic in this change — routes return `{"status": "ok"}` stubs; views render placeholder headings

## Capabilities

### New Capabilities

- `project-infrastructure`: Docker Compose three-service setup, persistent volumes, `.env` / `.env.example`, Dockerfile for `api` and `frontend` services. Addresses ARCH-01, ARCH-02, ARCH-03, ARCH-06.
- `backend-scaffold`: Flask app factory (`create_app`), six blueprint stubs (`ingest`, `wiki`, `chat`, `private`, `files`, `prompts`), Qdrant service that initializes `knowledge` and `private` collections on startup, SQLite schema (`files`, `chat_sessions`, `chat_messages`, `notes` tables), LLM and embedding provider wrappers (env-driven). Addresses ARCH-04, ARCH-05, ARCH-07, DATA-01 through DATA-08, ING-09 stub, KB-01 stub, CHAT-03 stub, PRI-01 stub.
- `frontend-scaffold`: Vue 3 + Vite + Pinia app, Vue Router with four routes (`/wiki`, `/ingest`, `/chat`, `/private`), `AppLayout.vue` with 100px left nav, four view skeletons, Axios instance with `/api` baseURL, `TreeNav.vue` stub. Addresses UI-01, UI-02 (stub).

### Modified Capabilities

_(none — this is the first change; no existing specs to modify)_

## Impact

- Creates `backend/` and `frontend/` top-level directories (currently absent)
- Creates `docker-compose.yml`, `Dockerfile.api`, `Dockerfile.frontend`, `.env.example`, `.gitignore` additions
- Qdrant must be running (via Docker Compose) for the API to start successfully
- `OPENAI_API_KEY` is required at startup even when `LLM_PROVIDER=anthropic` (embedding hard dependency — ARCH-05)
- Subsequent feature changes (`ingest-pipeline`, `knowledge-base`, `chat-agent`, `private-data`) all build on top of this skeleton

## Non-Goals

- No actual ingest, search, or chat logic in this change
- No authentication or multi-user support (V1 `user_id` is always `"default"`)
- No MCP data source integration (deferred to a later change)
- No Railway or NAS deployment config (ARCH-06 deferred)
- No test suite beyond smoke-test that the Flask app starts and all routes respond 200
