## ADDED Requirements

### Requirement: GET /api/private/templates returns preset template definitions
The system SHALL implement `GET /api/private/templates` returning a JSON array of 6 template objects. Each template object SHALL contain: `type` (string key), `label` (display name in Chinese), and `fields` (array of `{key, label, type, placeholder}` field descriptors). The 6 types are: `tax`, `retirement`, `portfolio`, `personal`, `real_estate`, `freeform`. Template definitions are server-side constants — not stored in the database.

#### Scenario: Returns all 6 preset templates
- **WHEN** `GET /api/private/templates` is called
- **THEN** the response is a JSON array with exactly 6 objects, each containing `type`, `label`, and `fields`

### Requirement: GET /api/private/entries lists user entries
The system SHALL implement `GET /api/private/entries` returning all `private_entries` rows for `user_id = "default"`, ordered by `created_at DESC`. Each item SHALL include `id`, `template_type`, `title`, `content_json`, `created_at`, `updated_at`.

#### Scenario: Returns entries for current user only
- **WHEN** `GET /api/private/entries` is called
- **THEN** only entries where `user_id = "default"` are returned

#### Scenario: Empty result when no entries exist
- **WHEN** no private entries have been created
- **THEN** the response is an empty JSON array

### Requirement: POST /api/private/entries creates entry and embeds into Qdrant
The system SHALL implement `POST /api/private/entries` accepting `{template_type, title, content_json}`. It SHALL: generate a UUID as the entry ID; derive a plain-text representation from `content_json` for embedding; call `EmbeddingService.embed(text)` to get the vector; upsert a Qdrant point into the `private` collection with payload `{user_id: "default", template_type, title, source_file_id: id}`; insert a row into `private_entries`. Returns HTTP 201 with the created entry object.

#### Scenario: Entry created and Qdrant point upserted
- **WHEN** `POST /api/private/entries` is called with valid template_type, title, content_json
- **THEN** a new row exists in `private_entries` AND a Qdrant point with the same UUID and correct user_id payload exists in the `private` collection

#### Scenario: Missing required fields returns 400
- **WHEN** `POST /api/private/entries` is called without `template_type` or `title`
- **THEN** HTTP 400 with `{"error": "template_type and title are required"}`

### Requirement: PUT /api/private/entries/{id} updates entry and re-embeds
The system SHALL implement `PUT /api/private/entries/{id}` accepting `{title?, content_json?}`. It SHALL re-derive the text representation, re-embed, and upsert the updated Qdrant point (same UUID). It SHALL update `private_entries.updated_at`. Returns the updated entry. Returns HTTP 404 if the entry does not exist for `user_id = "default"`.

#### Scenario: Successful update re-embeds and updates Qdrant
- **WHEN** `PUT /api/private/entries/{id}` is called with updated content_json
- **THEN** the Qdrant point for that ID is replaced with the new vector AND `private_entries.updated_at` is updated

#### Scenario: Unknown id returns 404
- **WHEN** `PUT /api/private/entries/nonexistent-id` is called
- **THEN** HTTP 404 with `{"error": "entry not found"}`

### Requirement: DELETE /api/private/entries/{id} removes entry from SQLite and Qdrant
The system SHALL implement `DELETE /api/private/entries/{id}` which deletes the Qdrant point and the SQLite row. Returns HTTP 200 `{"ok": true}`. Returns 404 if the entry does not exist for `user_id = "default"`.

#### Scenario: Entry deleted from both stores
- **WHEN** `DELETE /api/private/entries/{id}` is called for a valid entry
- **THEN** the row is removed from `private_entries` AND the Qdrant point is deleted from the `private` collection

#### Scenario: Deleting nonexistent entry returns 404
- **WHEN** `DELETE /api/private/entries/nonexistent-id` is called
- **THEN** HTTP 404 with `{"error": "entry not found"}`

### Requirement: All Qdrant private operations MUST include user_id filter
Every read and write on the Qdrant `private` collection MUST include `user_id = "default"` in the payload filter or payload. Omitting this filter on reads is a critical security bug.

#### Scenario: Upserted Qdrant point carries user_id in payload
- **WHEN** a private entry is created or updated
- **THEN** the Qdrant point payload includes `user_id: "default"`

#### Scenario: Listing or searching never returns other users' data
- **WHEN** any read operation targets the `private` Qdrant collection
- **THEN** the query includes a `user_id = "default"` payload filter

---

## Revision 2026-05-07 — Directory column on entries

### Requirement: private_entries SHALL carry a `directory` column
The `private_entries` table SHALL have a `directory TEXT NOT NULL DEFAULT ''` column. The column SHALL be added by `_ensure_private_tables()` via idempotent ALTER TABLE; the same column SHALL appear in `db/schema.sql`.

#### Scenario: Existing rows backfill to empty string
- **WHEN** the migration runs on a DB whose `private_entries` table predates the column
- **THEN** the column is added and existing rows have `directory = ''`

### Requirement: GET /api/private/entries SHALL include directory
Each entry returned by `GET /api/private/entries` SHALL include the `directory` field as a string (possibly empty).

### Requirement: POST /api/private/entries SHALL accept and persist directory
The endpoint SHALL accept an optional `directory` string in the JSON payload and persist it. If the field is absent, the server SHALL store the template's `default_directory` from the preset definitions.

#### Scenario: Directory pre-filled from template default when omitted
- **WHEN** `POST /api/private/entries` is called with `template_type="tax"` and no `directory`
- **THEN** the row's `directory` column is `'税务'`

#### Scenario: Caller-supplied directory wins
- **WHEN** `POST /api/private/entries` is called with `template_type="tax"`, `directory="税务/2025"`
- **THEN** the row's `directory` column is `'税务/2025'`

### Requirement: PUT /api/private/entries/{id} SHALL accept directory updates
The endpoint SHALL accept a `directory` field; if present, the column SHALL be updated and `updated_at` refreshed. The Qdrant payload's `directory` field SHALL also be re-upserted on changes (so AI-side filters stay accurate).

### Requirement: Each preset template SHALL carry a default_directory
Each entry in `PRIVATE_TEMPLATES` SHALL have a `default_directory` string field. The fixed mapping is:
- `tax` → `税务`
- `retirement` → `退休账户`
- `portfolio` → `投资持仓`
- `personal` → `个人基本情况`
- `real_estate` → `房产资产`
- `freeform` → `自由格式`

#### Scenario: Templates endpoint exposes default_directory
- **WHEN** `GET /api/private/templates` is called
- **THEN** each template object includes `default_directory` matching the mapping above
