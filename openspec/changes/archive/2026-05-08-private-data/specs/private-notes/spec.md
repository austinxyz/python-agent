## ADDED Requirements

### Requirement: GET /api/private/notes returns notes list with directory structure
The system SHALL implement `GET /api/private/notes` returning all notes for `user_id = "default"` ordered by `created_at DESC`. Each note SHALL include: `id`, `title`, `directory` (path string, e.g. `"退休规划/Roth相关"` or `""` for root), `content`, `chat_ref` (nullable session ID), `created_at`, `updated_at`. The response SHALL also include a `tree` field: a nested object derived by splitting each note's `directory` on `/` and grouping notes under their directory nodes.

#### Scenario: Returns flat list and derived tree
- **WHEN** two notes exist — one in `"退休规划"` and one in root
- **THEN** the response includes `notes` (flat array of 2) and `tree` reflecting the hierarchy

#### Scenario: Empty result when no notes exist
- **WHEN** no notes exist
- **THEN** `{"notes": [], "tree": {}}`

### Requirement: POST /api/private/notes creates a new note
The system SHALL implement `POST /api/private/notes` accepting `{title, content, directory?, chat_ref?}`. `directory` defaults to `""` (root). The note SHALL be stored in SQLite `notes` with a generated UUID and `user_id = "default"`. Notes are NOT embedded into Qdrant. Returns HTTP 201 with the created note object.

#### Scenario: Note created successfully
- **WHEN** `POST /api/private/notes` is called with `title` and `content`
- **THEN** a new row exists in `notes` with `user_id = "default"` and directory defaults to `""`

#### Scenario: Note with chat_ref records the source session
- **WHEN** `POST /api/private/notes` is called with a `chat_ref` session ID
- **THEN** the note row stores the `chat_ref` value

#### Scenario: Missing title returns 400
- **WHEN** `POST /api/private/notes` is called without `title`
- **THEN** HTTP 400 with `{"error": "title is required"}`

### Requirement: PUT /api/private/notes/{id} updates note content and/or directory
The system SHALL implement `PUT /api/private/notes/{id}` accepting `{title?, content?, directory?}`. It SHALL update only the provided fields and set `updated_at`. Returns the updated note. Returns HTTP 404 if the note does not exist for `user_id = "default"`.

#### Scenario: Updating content preserves other fields
- **WHEN** `PUT /api/private/notes/{id}` is called with only `content`
- **THEN** `notes.content` is updated and `updated_at` is refreshed; `title` and `directory` are unchanged

#### Scenario: Moving note to different directory
- **WHEN** `PUT /api/private/notes/{id}` is called with a new `directory` value
- **THEN** `notes.directory` is updated to the new path

#### Scenario: Unknown id returns 404
- **WHEN** `PUT /api/private/notes/nonexistent-id` is called
- **THEN** HTTP 404 with `{"error": "note not found"}`
