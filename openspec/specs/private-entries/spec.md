# private-entries Specification

## Purpose
TBD - created by archiving change private-data. Update Purpose after archive.
## Requirements
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

