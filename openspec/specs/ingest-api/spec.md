## Requirements

### Requirement: POST /api/ingest — start ingest job
The system SHALL implement `POST /api/ingest` in `backend/app/routes/ingest.py`. The endpoint MUST accept `multipart/form-data` with the following fields:
- `source_type` (required): `"file"`, `"url"`, `"text"`, or `"mcp"` (mcp returns a not-implemented error in V1)
- `destination` (required): `"knowledge"` or `"private"`
- `domain` (optional, string): knowledge domain label (e.g., `"退休规划"`)
- `title` (optional, string): user-provided display title for the file; stored in `files.title`
- `file` (required when `source_type="file"`): uploaded file bytes
- `source_url` (required when `source_type="url"`): URL string
- `content` (required when `source_type="text"`): raw text string

All clients MUST send requests as `multipart/form-data` (using `FormData`) regardless of source type — JSON bodies are not accepted.

The endpoint SHALL validate inputs and return HTTP 400 with `{"error": "<message>"}` for missing or invalid fields. On success, it SHALL start an `IngestPipeline` run in a background thread, register the job with `JobRegistry`, and return HTTP 202 with `{"job_id": "<uuid>"}` immediately — before the pipeline completes.

#### Scenario: File upload with title returns job_id
- **WHEN** a valid `multipart/form-data` POST is sent with `source_type="file"`, `destination="knowledge"`, `title="Roth IRA详解"`, and a PDF attachment
- **THEN** the response is HTTP 202 with `{"job_id": "<uuid>"}` and `title` is passed to the pipeline for storage

#### Scenario: Missing source_type returns 400
- **WHEN** POST body omits `source_type`
- **THEN** response is HTTP 400 with `{"error": "source_type is required"}`

#### Scenario: Missing file when source_type is file returns 400
- **WHEN** POST body has `source_type="file"` but no `file` attachment
- **THEN** response is HTTP 400 with `{"error": "file is required for source_type 'file'"}`

#### Scenario: Invalid destination returns 400
- **WHEN** POST body has `destination="public"`
- **THEN** response is HTTP 400 with `{"error": "destination must be 'knowledge' or 'private'"}`

### Requirement: GET /api/ingest/status/{job_id} — poll job progress
The system SHALL implement `GET /api/ingest/status/{job_id}`. The endpoint MUST:
- Validate that `job_id` matches UUID format (`^[0-9a-f]{8}-…-[0-9a-f]{12}$`); return HTTP 400 for invalid format
- Look up the job in the `JobRegistry` and return its current state:
  - While running: HTTP 200 with `{"status": "running"}`
  - On completion: HTTP 200 with `{"status": "completed", "file_id": "<uuid>", "chunk_count": <int>}`
  - On error: HTTP 200 with `{"status": "error", "error": "<message>"}`
  - Unknown job_id: HTTP 404 with `{"error": "job not found"}`

The job registry entry MUST only store serialisable fields — `{status, file_id, chunk_count, error}`. Raw bytes, vectors, and other pipeline-internal state MUST NOT be stored in the registry.

#### Scenario: Invalid job_id format returns 400
- **WHEN** job_id is `"not-a-uuid"`
- **THEN** response is HTTP 400 with `{"error": "invalid job_id format"}`

#### Scenario: Running job returns status running
- **WHEN** the pipeline is still executing for the given job_id
- **THEN** response is HTTP 200 with `{"status": "running"}`

#### Scenario: Completed job returns full summary
- **WHEN** the pipeline has finished successfully
- **THEN** response is HTTP 200 with `status="completed"`, non-null `file_id`, and `chunk_count >= 1`

#### Scenario: Unknown job returns 404
- **WHEN** job_id does not exist in the registry
- **THEN** response is HTTP 404 with `{"error": "job not found"}`

### Requirement: In-memory JobRegistry
The system SHALL provide a `JobRegistry` class in `backend/app/services/job_registry.py`. It MUST be thread-safe (protected by `threading.Lock`). It SHALL support: `create(job_id) → None`, `update(job_id, state: dict) → None`, `get(job_id) → dict | None`. Initial state for a new job SHALL be `{"status": "running"}`.

#### Scenario: Concurrent updates do not corrupt state
- **WHEN** two threads call `update` simultaneously for different job_ids
- **THEN** both updates are applied correctly with no data corruption

### Requirement: SQLite title column migration
The system SHALL ensure the `title TEXT` column exists in the `files` table before serving any requests. `DatabaseService` SHALL implement `_ensure_title_column()` which executes `ALTER TABLE files ADD COLUMN title TEXT` only if the column does not already exist (detected via `PRAGMA table_info(files)`). This method SHALL be called during `DatabaseService` initialisation so it is idempotent across container restarts.

#### Scenario: Migration is idempotent
- **WHEN** `_ensure_title_column()` is called twice on a database that already has the `title` column
- **THEN** no exception is raised and the table structure is unchanged

### Requirement: FileService — file persistence
The system SHALL provide a `FileService` class in `backend/app/services/file_service.py`. It MUST implement:
- `save(user_id, file_id, filename, content: bytes) → Path`: write file bytes to `{UPLOADS_PATH}/{user_id}/{file_id}/{filename}`, creating parent directories as needed; protected by allowlist regex + `is_relative_to` path traversal guard
- `register(db, user_id, file_id, orig_name, source_type, source_url, domain, title, size_bytes, chunk_count, filename) → None`: insert a row into the SQLite `files` table; `title` and `filename` are optional (`str | None`)
- `resolve(user_id, file_id, filename) → Path | None`: return the absolute path for an existing upload without writing; return `None` if inputs fail validation or the path escapes the base directory

The uploads base path SHALL be read from the `UPLOADS_PATH` env var (default `/app/uploads`).

For `source_type="file"` and `source_type="text"` and `source_type="url"`, the ingest pipeline SHALL save the original or extracted text content to disk as `{file_id}.txt` (or the original filename for file uploads). This enables the content viewer to serve files locally rather than re-fetching the source.

#### Scenario: File is saved to correct path
- **WHEN** `FileService().save(user_id="default", file_id="abc123", filename="doc.pdf", content=<bytes>)` is called
- **THEN** the file exists at `{UPLOADS_PATH}/default/abc123/doc.pdf`

#### Scenario: File metadata with title is registered in SQLite
- **WHEN** `FileService().register(..., title="Roth IRA详解")` is called
- **THEN** a row exists in `files` with `title='Roth IRA详解'` and the correct `file_id`

#### Scenario: File registered without title stores NULL
- **WHEN** `FileService().register(..., title=None)` is called
- **THEN** a row exists in `files` with `title IS NULL`

### Requirement: File size limit
The `POST /api/ingest` endpoint SHALL reject uploads where the file size exceeds 50 MB. The limit SHALL apply to the raw bytes of the uploaded file, checked before the pipeline starts. Requests exceeding the limit SHALL receive HTTP 413 with `{"error": "file too large (max 50 MB)"}`.

#### Scenario: Oversized file rejected before processing
- **WHEN** a file larger than 50 MB is uploaded
- **THEN** response is HTTP 413 and no background thread is started

### Requirement: GET /api/files — list ingested files
The system SHALL implement `GET /api/files` in `backend/app/routes/files.py`. The endpoint MUST query the SQLite `files` table filtered by `user_id` and return rows as a JSON array ordered by `created_at DESC`. Each item SHALL include: `file_id`, `user_id`, `filename`, `orig_name`, `source_type`, `source_url`, `domain`, `title`, `size_bytes`, `chunk_count`, `created_at`. The `filename` field enables the frontend to determine whether local content is available.

#### Scenario: Returns all ingested files with title and filename fields
- **WHEN** two files have been ingested (one with title, one without)
- **THEN** `GET /api/files` returns a JSON array; the titled file has `"title": "<value>"`, the untitled file has `"title": null`; both include a `filename` field

### Requirement: PATCH /api/files/{file_id} — update file title
The system SHALL implement `PATCH /api/files/{file_id}` in `backend/app/routes/files.py`. The endpoint MUST accept JSON body `{"title": <string|null>}`. A null or blank title clears the stored title. Returns HTTP 400 if `title` key is absent or value is not string/null. Returns HTTP 404 if the file does not exist for the current user.

#### Scenario: Update title succeeds
- **WHEN** `PATCH /api/files/<id>` is called with `{"title": "新标题"}`
- **THEN** response is HTTP 200 with `{"file_id": "<id>", "title": "新标题"}` and the DB row is updated

#### Scenario: Clear title with null
- **WHEN** `PATCH /api/files/<id>` is called with `{"title": null}`
- **THEN** response is HTTP 200 and `files.title` is set to NULL

### Requirement: GET /api/files/{file_id}/download — download original file
The system SHALL implement `GET /api/files/{file_id}/download`. It MUST look up the file record in SQLite, resolve the path via `FileService.resolve()`, and serve the file as a download attachment (`Content-Disposition: attachment`). Returns HTTP 404 if the record or file does not exist.

### Requirement: GET /api/files/{file_id}/content — view file content inline
The system SHALL implement `GET /api/files/{file_id}/content`. Priority order:
1. If a local file exists (resolved via `FileService.resolve()`), serve it inline.
2. If `source_type="url"` and no local file: re-fetch the original URL using the SSRF-safe `httpx` client; apply `_html_to_text()` for HTML responses before returning as `text/plain`.
3. Otherwise: HTTP 404.

Returns HTTP 404 if the record does not exist.

#### Scenario: Local file served without re-fetching
- **WHEN** a text or URL ingestion has a saved local file
- **THEN** the content endpoint serves the local file directly

#### Scenario: Legacy URL file falls back to live fetch with HTML extraction
- **WHEN** a URL-type file has no local copy
- **THEN** the URL is re-fetched and HTML content is extracted to plain text before returning

### Requirement: SQLite persistence
The SQLite database path SHALL be configured via the `SQLITE_PATH` environment variable (default `knowledge_agent.db`). In the Docker Compose deployment, `SQLITE_PATH` MUST point to a path inside a named Docker volume (`sqlite_data` mounted at `/app/data`) so that data persists across container rebuilds (`docker compose up --build`).
