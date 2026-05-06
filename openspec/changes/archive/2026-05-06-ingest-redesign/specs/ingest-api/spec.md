## MODIFIED Requirements

### Requirement: POST /api/ingest — start ingest job
The system SHALL implement `POST /api/ingest` in `backend/app/routes/ingest.py`. The endpoint MUST accept `multipart/form-data` with the following fields:
- `source_type` (required): `"file"`, `"url"`, `"text"`, or `"mcp"` (mcp returns a not-implemented error in V1)
- `destination` (required): `"knowledge"` or `"private"`
- `domain` (optional, string): knowledge domain label (e.g., `"退休规划"`)
- `title` (optional, string): user-provided display title for the file; stored in `files.title`
- `file` (required when `source_type="file"`): uploaded file bytes
- `source_url` (required when `source_type="url"`): URL string
- `content` (required when `source_type="text"`): raw text string

All clients MUST send requests as `multipart/form-data` (using `FormData`) regardless of source type.

The endpoint SHALL validate inputs and return HTTP 400 with `{"error": "<message>"}` for missing or invalid fields. On success, it SHALL start an `IngestPipeline` run in a background thread, register the job with `JobRegistry`, and return HTTP 202 with `{"job_id": "<uuid>"}` immediately.

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

### Requirement: FileService — file persistence
The system SHALL provide a `FileService` class in `backend/app/services/file_service.py`. It MUST implement:
- `save(user_id, file_id, filename, content: bytes) → Path`: write file bytes to `{UPLOADS_PATH}/{user_id}/{file_id}/{filename}`, with path traversal guard
- `register(db, user_id, file_id, orig_name, source_type, source_url, domain, title, size_bytes, chunk_count) → None`: insert a row into the SQLite `files` table including the `title` column (NULL if not provided)
- `resolve(user_id, file_id, filename) → Path | None`: return the absolute path for an existing upload; return `None` if inputs fail validation or path escapes base directory

The `title` parameter in `register()` is optional (`str | None`). Existing callers that omit `title` receive `None` stored in the column.

#### Scenario: File is saved to correct path
- **WHEN** `FileService().save(user_id="default", file_id="abc123", filename="doc.pdf", content=<bytes>)` is called
- **THEN** the file exists at `{UPLOADS_PATH}/default/abc123/doc.pdf`

#### Scenario: File metadata with title is registered in SQLite
- **WHEN** `FileService().register(..., title="Roth IRA详解")` is called
- **THEN** a row exists in `files` with `title='Roth IRA详解'` and the correct `file_id`

#### Scenario: File registered without title stores NULL
- **WHEN** `FileService().register(..., title=None)` is called
- **THEN** a row exists in `files` with `title IS NULL`

### Requirement: GET /api/files — list ingested files
The system SHALL implement `GET /api/files` in `backend/app/routes/files.py`. The endpoint MUST query the SQLite `files` table and return all rows as a JSON array ordered by `created_at DESC`. Each item SHALL include: `file_id`, `user_id`, `orig_name`, `source_type`, `source_url`, `domain`, `title`, `size_bytes`, `chunk_count`, `created_at`.

#### Scenario: Returns all ingested files with title field
- **WHEN** two files have been ingested (one with title, one without)
- **THEN** `GET /api/files` returns a JSON array with two objects; the titled file has `"title": "<value>"` and the untitled file has `"title": null`

---

## ADDED Requirements

### Requirement: SQLite title column migration
The system SHALL ensure the `title TEXT` column exists in the `files` table before serving any requests. `DatabaseService` SHALL implement `_ensure_title_column()` which executes `ALTER TABLE files ADD COLUMN title TEXT` only if the column does not already exist (detected via `PRAGMA table_info(files)`). This method SHALL be called during `DatabaseService` initialisation so it is idempotent across container restarts.

#### Scenario: Migration is idempotent
- **WHEN** `_ensure_title_column()` is called twice on a database that already has the `title` column
- **THEN** no exception is raised and the table structure is unchanged

#### Scenario: Existing rows have NULL title after migration
- **WHEN** the `title` column is added to a database with pre-existing rows
- **THEN** all pre-existing rows have `title IS NULL`
