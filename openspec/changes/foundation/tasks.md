## 1. Project Infrastructure

- [x] 1.1 Create `.env.example` with all required variables (`LLM_PROVIDER`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `LLM_MODEL`, `EMBEDDING_MODEL`, `QDRANT_HOST`, `QDRANT_PORT`, `FLASK_SECRET_KEY`) with placeholder values and inline comments
- [x] 1.2 Add `.env` to `.gitignore`; verify `git status` does not surface `.env`
- [x] 1.3 Write `Dockerfile.api` (Python 3.11-slim, copies `backend/`, installs `requirements.txt`, runs Flask)
- [x] 1.4 Write `Dockerfile.frontend` (multi-stage: Node 20-alpine build stage → nginx-alpine serve stage)
- [x] 1.5 Write `docker-compose.yml` with `frontend`, `api`, `qdrant` services; `qdrant` healthcheck via `curl -f http://localhost:6333/health`; `api` `depends_on: qdrant: condition: service_healthy`; two named volumes `qdrant_data` and `uploads`
- [x] 1.6 Verify `docker compose build` exits 0 with a stubbed backend and frontend (empty `app.py`, empty `index.html`)
- [x] 1.7 Run superpowers:requesting-code-review on the diff for group 1; address CRITICAL/HIGH findings before moving on

## 2. Backend — SQLite Schema and Database Service

- [x] 2.1 RED — write failing pytest test (`tests/test_smoke.py`) that asserts the four SQLite tables (`files`, `chat_sessions`, `chat_messages`, `notes`) exist after `create_app`
- [x] 2.2 Create `backend/db/schema.sql` with idempotent `CREATE TABLE IF NOT EXISTS` for all four tables, columns matching DATA-03 through DATA-07
- [x] 2.3 GREEN — create `backend/app/services/db_service.py` with `DatabaseService` that applies `schema.sql` on init and enables WAL mode via `PRAGMA journal_mode=WAL` on each connection; verify the RED test now passes
- [x] 2.4 Run superpowers:requesting-code-review on the diff for group 2; address CRITICAL/HIGH findings before moving on

## 3. Backend — Qdrant Service

- [x] 3.1 RED — write failing pytest test asserting that after `create_app`, both `knowledge` and `private` Qdrant collections exist with vector size 1536
- [x] 3.2 Add `qdrant-client` to `backend/requirements.txt`
- [x] 3.3 GREEN — create `backend/app/services/qdrant_service.py` with `QdrantService`; idempotent collection creation (`get_collection` → create on 404); `knowledge` and `private` configs as per spec; `search_private` requires `user_id` as positional arg and applies `FieldCondition` filter; verify RED test passes
- [x] 3.4 RED — write unit test asserting `search_private` raises `TypeError` when called without `user_id`
- [x] 3.5 GREEN — confirm test passes (no default value for `user_id` in signature)
- [x] 3.6 Run superpowers:requesting-code-review on the diff for group 3; address CRITICAL/HIGH findings before moving on

## 4. Backend — LLM and Embedding Service Wrappers

- [x] 4.1 Add `anthropic`, `openai` to `backend/requirements.txt`
- [x] 4.2 RED — write unit test for `LlmService` asserting it selects Anthropic client when `LLM_PROVIDER=anthropic`
- [x] 4.3 GREEN — create `backend/app/services/llm_service.py` with `LlmService`; reads `LLM_PROVIDER` and `LLM_MODEL` env vars; `complete(messages, stream=False)` delegates to appropriate SDK; verify test passes
- [x] 4.4 RED — write unit test for `EmbeddingService` asserting it always uses OpenAI and returns a list of length 1536
- [x] 4.5 GREEN — create `backend/app/services/embedding_service.py` with `EmbeddingService`; always calls OpenAI; reads `EMBEDDING_MODEL` env var (default `text-embedding-3-small`); verify test passes
- [x] 4.6 Run superpowers:requesting-code-review on the diff for group 4; address CRITICAL/HIGH findings before moving on

## 5. Backend — Flask App Factory and Blueprints

- [x] 5.1 RED — write failing pytest test that calls `create_app()` without `OPENAI_API_KEY` and asserts `RuntimeError` with `"OPENAI_API_KEY"` in the message
- [x] 5.2 RED — write failing pytest test asserting `GET /api/health` returns HTTP 200 on a running app
- [x] 5.3 RED — write failing pytest tests for all six stub routes returning HTTP 200 with `{"status": "ok", "stub": true}`
- [x] 5.4 Create `backend/app/__init__.py` with `create_app(config=None)`: validates env vars (raises `RuntimeError` on missing), initialises `DatabaseService` and `QdrantService`, registers six blueprints, adds `GET /api/health` route
- [x] 5.5 Create six blueprint stubs in `backend/app/routes/`: `ingest.py`, `wiki.py`, `chat.py`, `private.py`, `files.py`, `prompts.py`; each registers at least one `GET` stub route returning `{"status": "ok", "stub": true}`
- [x] 5.6 Create `backend/tests/conftest.py` with `app` fixture using `create_app({'TESTING': True})`
- [x] 5.7 GREEN — verify all RED tests from 5.1–5.3 now pass
- [x] 5.8 Run superpowers:requesting-code-review on the diff for group 5; address CRITICAL/HIGH findings before moving on

## 6. Frontend — Scaffold and Routing

- [x] 6.1 Initialise `frontend/` with `npm create vue@latest` (Vue 3 + Vite + Vue Router + Pinia); add `axios` and dev deps `vitest`, `@vue/test-utils`, `happy-dom`
- [x] 6.2 Configure `vite.config.js`: add `@vitejs/plugin-vue` and `server.proxy['/api'] = 'http://localhost:5000'`
- [x] 6.3 RED — write vitest smoke test asserting `GET /api/health` proxy works (mock axios, verify baseURL is `/api`)
- [x] 6.4 Create `frontend/src/api/index.js` exporting a single Axios instance with `baseURL: '/api'`; GREEN — verify test passes
- [x] 6.5 RED — write vitest test mounting `AppLayout.vue` and asserting all four nav items are present
- [x] 6.6 Create `frontend/src/App.vue` rendering `AppLayout.vue`; create `frontend/src/components/AppLayout.vue` with 100px left nav containing four `<router-link>` items and a `<router-view />`; GREEN — verify test passes
- [x] 6.7 RED — write vitest tests mounting each view skeleton and asserting their heading is rendered
- [x] 6.8 Create four view skeletons: `frontend/src/views/WikiView.vue`, `IngestView.vue`, `ChatView.vue`, `PrivateView.vue`; each renders an `<h1>` heading
- [x] 6.9 Configure `frontend/src/router/index.js`: history mode, four routes + redirect `/` → `/wiki`; GREEN — verify view tests pass
- [x] 6.10 Run superpowers:requesting-code-review on the diff for group 6; address CRITICAL/HIGH findings before moving on

## 7. Frontend — Shared Components and Stores

- [x] 7.1 RED — write vitest test that mounts `TreeNav.vue` with `items=[{label:'Finance'},{label:'Health'}]` and asserts both labels are rendered
- [x] 7.2 Create `frontend/src/components/tree-nav/TreeNav.vue` stub using `defineEmits(['select'])`; prop: `items` (array); GREEN — verify test passes
- [x] 7.3 RED — write vitest tests importing each of the four store composables and asserting they are callable without error
- [x] 7.4 Create four Pinia store stubs in `frontend/src/stores/`: `wiki.js` (`useWikiStore`), `ingest.js` (`useIngestStore`), `chat.js` (`useChatStore`), `private.js` (`usePrivateStore`); each exports composable with empty `state: () => ({})`; GREEN — verify tests pass
- [x] 7.5 Run superpowers:requesting-code-review on the diff for group 7; address CRITICAL/HIGH findings before moving on

## 8. Integration and Verification

- [x] 8.1 Run `cd backend && pytest` — assert all backend smoke and unit tests pass with exit code 0
- [x] 8.2 Run `cd frontend && npm test` — assert all frontend vitest tests pass with exit code 0
- [ ] 8.3 Run `docker compose up --build` — assert all three services start healthy; verify `http://localhost:3000` loads the Vue app and `http://localhost:5000/api/health` returns 200
- [x] 8.4 Inspect backend code: `grep -rn "search_private" backend/` — confirm every call site passes `user_id` explicitly; no omissions
- [x] 8.5 Inspect frontend code: `grep -rn "console.log" frontend/src/` — confirm zero debug statements
- [x] 8.6 Run superpowers:verification-before-completion: run full test suites, check private collection user_id filter coverage, confirm no hardcoded secrets, confirm `.env` is gitignored
- [x] 8.7 Run superpowers:requesting-code-review on the complete diff for the foundation change; address all CRITICAL/HIGH findings
- [ ] 8.8 Commit with `feat: add project foundation scaffold (Docker Compose, Flask app factory, Qdrant/SQLite init, Vue 3 frontend)`
