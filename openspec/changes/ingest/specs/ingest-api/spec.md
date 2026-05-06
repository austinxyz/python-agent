## ADDED Requirements

### Requirement: POST /api/ingest — start ingest job
The system SHALL implement `POST /api/ingest` in `backend/app/routes/ingest.py`. The endpoint MUST accept `multipart/form-data` with the following fields:
- `source_type` (required): `"file"`, `"url"`, `"text"`, or `"mcp"` (mcp returns a not-implemented error in V1)
- `destination` (required): `"knowledge"` or `"private"`
- `domain` (optional, string): knowledge domain label (e.g., `"finance"`)
- `topic` (optional, string): topic label (e.g., `"Roth IRA"`)
- `file` (required when `source_type="file"`): uploaded file bytes
- `url` (required when `source_type="url"`): URL string
- `text` (required when `source_type="text"`): raw text string

The endpoint SHALL validate inputs and return HTTP 400 with `{"error": "<message>"}` for missing or invalid fields. On success, it SHALL start an `IngestPipeline` run in a background thread, register the job with an in-memory `JobRegistry`, and return HTTP 202 with `{"job_id": "<uuid>"}` immediately — before the pipeline completes.

The endpoint SHALL NOT block waiting for the pipeline to finish.

#### Scenario: File upload starts job and returns job_id
- **WHEN** a valid `multipart/form-data` POST is sent with `source_type="file"`, `destination="knowledge"`, and a PDF file attachment
- **THEN** the response is HTTP 202 with body `{"job_id": "<uuid>"}` returned within 500 ms

#### Scenario: Missing source_type returns 400
- **WHEN** POST body omits `source_type`
- **THEN** response is HTTP 400 with `{"error": "source_type is required"}`

#### Scenario: Missing file when source_type is file returns 400
- **WHEN** POST body has `source_type="file"` but no `file` attachment
- **THEN** response is HTTP 400 with `{"error": "file is required for source_type 'file'"}`

#### Scenario: Invalid destination returns 400
- **WHEN** POST body has `destination="public"` (not a valid value)
- **THEN** response is HTTP 400 with `{"error": "destination must be 'knowledge' or 'private'"}`

### Requirement: GET /api/ingest/status/{job_id} — poll job progress
The system SHALL implement `GET /api/ingest/status/{job_id}`. The endpoint MUST look up the job in the `JobRegistry` and return its current state:
- While running: HTTP 200 with `{"job_id": "<id>", "status": "running"}`
- On completion: HTTP 200 with `{"job_id": "<id>", "status": "completed", "file_id": "<uuid>", "chunk_count": <int>}`
- On error: HTTP 200 with `{"job_id": "<id>", "status": "error", "error": "<message>"}`
- Unknown job_id: HTTP 404 with `{"error": "job not found"}`

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

### Requirement: FileService — file persistence
The system SHALL provide a `FileService` class in `backend/app/services/file_service.py`. It MUST:
- `save(user_id, file_id, filename, content: bytes) → Path`: write file bytes to `/app/uploads/{user_id}/{file_id}/{filename}`, creating parent directories as needed
- `register(db, user_id, file_id, orig_name, source_type, source_url, domain, topic, size_bytes, chunk_count) → None`: insert a row into the SQLite `files` table using the provided `DatabaseService` connection

The uploads base path SHALL be read from the `UPLOADS_PATH` env var (default `/app/uploads`).

#### Scenario: File is saved to correct path
- **WHEN** `FileService().save(user_id="default", file_id="abc123", filename="doc.pdf", content=<bytes>)` is called
- **THEN** the file exists at `{UPLOADS_PATH}/default/abc123/doc.pdf`

#### Scenario: File metadata is registered in SQLite
- **WHEN** `FileService().register(...)` is called with valid arguments
- **THEN** a row with the given `file_id` exists in the `files` table with correct `user_id`, `orig_name`, and `chunk_count`

### Requirement: File size limit
The `POST /api/ingest` endpoint SHALL reject uploads where the file size exceeds 50 MB. The limit SHALL apply to the raw bytes of the uploaded file, checked before the pipeline starts. Requests exceeding the limit SHALL receive HTTP 413 with `{"error": "file too large (max 50 MB)"}`.

#### Scenario: Oversized file rejected before processing
- **WHEN** a file larger than 50 MB is uploaded
- **THEN** response is HTTP 413 and no background thread is started
