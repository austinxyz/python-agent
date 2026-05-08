## Purpose

The Flask scaffold for the knowledge-agent backend. Provides the app factory, the six top-level blueprints, the Qdrant + SQLite service wrappers, and a smoke-test suite that the rest of the backend builds on.
## Requirements
### Requirement: Flask app factory
The system SHALL expose a `create_app(config=None)` factory function in `backend/app/__init__.py`. The factory MUST: validate all required environment variables and raise `RuntimeError` with the missing variable name if any are absent; initialise the SQLite database (applying schema from `backend/db/schema.sql`); initialise the Qdrant service (creating collections if absent); register all six blueprints under the `/api` URL prefix. The factory MUST return a configured `Flask` app instance.

#### Scenario: Factory creates a working app
- **WHEN** `create_app()` is called with all required environment variables set
- **THEN** the returned app responds to `GET /api/health` with HTTP 200 and body `{"status": "ok"}`

#### Scenario: Factory fails on missing env var
- **WHEN** `create_app()` is called without `OPENAI_API_KEY` in the environment
- **THEN** a `RuntimeError` is raised with a message containing `"OPENAI_API_KEY"`

### Requirement: Six blueprint stubs
The system SHALL register six Flask blueprints, each in its own module under `backend/app/routes/`. Blueprint names and URL prefixes:
- `ingest_bp` → `/api/ingest`
- `wiki_bp` → `/api/wiki`
- `chat_bp` → `/api/chat`
- `private_bp` → `/api/private`
- `files_bp` → `/api/files`
- `prompts_bp` → `/api/prompts`

Each blueprint MUST define at least one stub route that returns `{"status": "ok", "stub": true}` with HTTP 200. Stub routes are placeholders; feature changes replace them with real implementations.

#### Scenario: All stub routes return 200
- **WHEN** `GET /api/ingest`, `GET /api/wiki`, `GET /api/chat`, `GET /api/private`, `GET /api/files`, `GET /api/prompts` are called on the running Flask app
- **THEN** each returns HTTP 200 with `{"status": "ok", "stub": true}`

### Requirement: Qdrant service with idempotent collection initialisation
The system SHALL provide a `QdrantService` class in `backend/app/services/qdrant_service.py`. On initialisation, it MUST connect to Qdrant using `QDRANT_HOST` and `QDRANT_PORT` env vars and create the following collections if they do not already exist:
- `knowledge`: vectors of size 1536, distance Cosine; payload schema: `domain` (keyword), `topic` (keyword), `source_file_id` (keyword), `chunk_index` (integer), `updated_at` (datetime), `status` (keyword)
- `private`: vectors of size 1536, distance Cosine; payload schema: `user_id` (keyword, required), `topic` (keyword), `template_type` (keyword), `source_file_id` (keyword), `updated_at` (datetime)

The `private` collection's search methods MUST accept `user_id` as a required positional parameter and apply it as a `FieldCondition` filter on every query. There SHALL be no default value for `user_id`.

#### Scenario: Collections created on first startup
- **WHEN** `QdrantService()` is instantiated against an empty Qdrant instance
- **THEN** both `knowledge` and `private` collections exist in Qdrant with the correct vector configuration

#### Scenario: Idempotent re-initialisation
- **WHEN** `QdrantService()` is instantiated a second time (e.g., container restart) against a Qdrant instance that already has the collections
- **THEN** no error is raised and the existing collections are unchanged

#### Scenario: Private search always applies user_id filter
- **WHEN** `qdrant_service.search_private(query_vector, user_id="default", ...)` is called
- **THEN** the Qdrant query includes a `FieldCondition(key="user_id", match=MatchValue(value="default"))` filter

### Requirement: SQLite schema initialisation
The system SHALL provide a `backend/db/schema.sql` file containing idempotent `CREATE TABLE IF NOT EXISTS` statements for: `files`, `chat_sessions`, `chat_messages`, `notes`. A `DatabaseService` in `backend/app/services/db_service.py` MUST call `connection.executescript(schema_sql)` on startup and enable WAL mode via `PRAGMA journal_mode=WAL` on every new connection.

Table columns MUST match DATA-03 through DATA-07 in the requirements catalogue.

#### Scenario: Schema applied on first startup
- **WHEN** `DatabaseService()` is initialised against a new SQLite file
- **THEN** all four tables exist and can be queried without error

#### Scenario: WAL mode is active
- **WHEN** a connection is opened via `DatabaseService`
- **THEN** `PRAGMA journal_mode` returns `wal`

#### Scenario: Schema is idempotent
- **WHEN** `DatabaseService()` is initialised a second time against an existing SQLite file with data
- **THEN** no error is raised and existing data is preserved

### Requirement: LLM and embedding service wrappers
The system SHALL provide two service modules:
- `backend/app/services/llm_service.py`: reads `LLM_PROVIDER` (`anthropic` or `openai`) and `LLM_MODEL` env vars; exposes a `complete(messages, stream=False)` method that delegates to the appropriate SDK
- `backend/app/services/embedding_service.py`: always uses OpenAI `text-embedding-3-small` (ignores `LLM_PROVIDER`); reads `EMBEDDING_MODEL` env var (default `text-embedding-3-small`); exposes an `embed(text)` method returning a list of 1536 floats

Neither service SHALL hardcode API keys, model names, or provider URLs.

#### Scenario: LLM service selects Anthropic when configured
- **WHEN** `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY` are set
- **THEN** `LlmService().complete([{"role":"user","content":"hi"}])` calls the Anthropic API (not OpenAI) and returns a string response

#### Scenario: Embedding service always uses OpenAI
- **WHEN** `LLM_PROVIDER=anthropic` and `OPENAI_API_KEY` are set
- **THEN** `EmbeddingService().embed("hello")` calls the OpenAI embeddings API and returns a list of 1536 floats

### Requirement: pytest smoke-test suite
The system SHALL include a `tests/` directory under `backend/` with at minimum:
- `tests/conftest.py` providing an `app` fixture via `create_app({'TESTING': True})`
- `tests/test_smoke.py` testing that: all six blueprint stub routes return HTTP 200; the Qdrant `knowledge` and `private` collections exist after `create_app`; the SQLite tables exist

#### Scenario: All smoke tests pass
- **WHEN** `cd backend && pytest tests/test_smoke.py` is run with a valid `.env`
- **THEN** all tests pass with exit code 0

### Requirement: SQLite private_entries and notes tables created at startup
The system SHALL create `private_entries` and `notes` tables idempotently at application startup via `_ensure_private_tables()` in `DatabaseService`. The tables SHALL be added to `backend/db/schema.sql`.

Schema:
```sql
CREATE TABLE IF NOT EXISTS private_entries (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    template_type TEXT NOT NULL,
    title TEXT NOT NULL,
    content_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    title TEXT NOT NULL,
    directory TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    chat_ref TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

#### Scenario: Tables created when absent
- **WHEN** the Flask app starts with a fresh SQLite database
- **THEN** `private_entries` and `notes` tables exist after startup

#### Scenario: Startup is idempotent on existing tables
- **WHEN** the Flask app starts and the tables already exist
- **THEN** no error is raised and the existing data is preserved

