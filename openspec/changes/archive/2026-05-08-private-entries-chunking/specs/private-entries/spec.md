## MODIFIED Requirements

### Requirement: POST /api/private/entries creates entry and embeds into Qdrant
The system SHALL implement `POST /api/private/entries` accepting `{template_type, title, content_json, directory?}`. It SHALL: generate a UUID as the entry ID; derive a plain-text representation from `content_json`; **chunk the derived text using the shared text chunker (`text_chunker.chunk_text`); embed each chunk via `EmbeddingService.embed`; upsert one Qdrant point per chunk** into the `private` collection. Every chunk's payload SHALL include `{user_id: "default", template_type, title, directory, source_file_id: id, chunk_index: int}`. SQLite SHALL store one row in `private_entries` regardless of chunk count. Returns HTTP 201 with the created entry object.

#### Scenario: Short entry creates a single Qdrant point
- **WHEN** `POST /api/private/entries` is called with content that fits in one chunk (≤ CHUNK_SIZE characters)
- **THEN** exactly one Qdrant point is upserted with `chunk_index=0` and `source_file_id` equal to the entry's UUID

#### Scenario: Long entry creates multiple Qdrant points
- **WHEN** `POST /api/private/entries` is called with content longer than CHUNK_SIZE characters
- **THEN** multiple Qdrant points are upserted, all sharing the same `source_file_id` (the entry UUID), each with sequential `chunk_index` values starting at 0

#### Scenario: Embedding the long-document failure mode is gone
- **WHEN** the derived text is longer than 8192 OpenAI tokens (the original failure mode)
- **THEN** the request returns 201 (no 500) because each chunk is embedded individually within the limit

### Requirement: PUT /api/private/entries/{id} updates entry and re-embeds
The system SHALL implement `PUT /api/private/entries/{id}` accepting `{title?, content_json?, directory?}`. On any change to title / content / directory it SHALL: **filter-delete all existing Qdrant points whose `source_file_id` equals the entry id**; re-derive the text representation from the updated content; chunk; embed; upsert the new chunks. SQLite `updated_at` SHALL be refreshed. Returns the updated entry. Returns HTTP 404 if the entry does not exist for `user_id = "default"`.

#### Scenario: Update replaces all chunk points atomically
- **WHEN** an entry that previously had 5 Qdrant points is updated with longer content that splits into 8 chunks
- **THEN** after the request the Qdrant collection has exactly 8 points for that `source_file_id` (the 5 old points are gone)

#### Scenario: Update payload propagates to all chunks
- **WHEN** an entry's title is updated
- **THEN** every Qdrant point for that `source_file_id` carries the new title in its payload

### Requirement: DELETE /api/private/entries/{id} removes entry from SQLite and Qdrant
The system SHALL implement `DELETE /api/private/entries/{id}` which **filter-deletes every Qdrant point whose `source_file_id` equals the entry id** and removes the SQLite row. Returns HTTP 200 `{"ok": true}`. Returns 404 if the entry does not exist for `user_id = "default"`. The filter SHALL also include `user_id = "default"` so a hypothetical multi-tenant deployment cannot cross-delete other users' data.

#### Scenario: Delete removes every chunk
- **WHEN** an entry with N chunks (N ≥ 1) is deleted
- **THEN** zero Qdrant points remain with that `source_file_id`

#### Scenario: Legacy single-point entries are also removed
- **WHEN** a legacy entry (created before chunking, where `point.id == entry.id` and `payload.source_file_id == entry.id`) is deleted
- **THEN** the single Qdrant point is removed via the same filter-delete path

## ADDED Requirements

### Requirement: QdrantService SHALL expose filter-based delete for the private collection
`QdrantService` SHALL provide `delete_private_by_source_file_id(user_id: str, source_file_id: str) -> None`. The implementation SHALL use `points_selector=Filter(must=[user_id=..., source_file_id=...])`. `user_id` SHALL be a required positional argument with no default — same isolation invariant the search method enforces.

#### Scenario: Filter delete scopes by user_id
- **WHEN** `delete_private_by_source_file_id("default", "abc")` is called
- **THEN** the Qdrant request filters on both `user_id="default"` AND `source_file_id="abc"`

#### Scenario: Filter delete is mandatory when user_id is omitted
- **WHEN** the method is called without `user_id`
- **THEN** Python raises `TypeError` (positional argument missing)

### Requirement: Text chunker SHALL be reusable across knowledge and private paths
A module `backend/app/graphs/text_chunker.py` SHALL expose `chunk_text(content: str, *, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]` returning `[{text, chunk_index}, ...]`. The function SHALL preserve the existing behavior of `IngestPipeline.chunk_node` (paragraph-aware splitting, sentence-level splitting for long paragraphs, character-overlap between adjacent chunks). `chunk_node` SHALL be refactored to call `chunk_text` so both ingest paths share one algorithm.

#### Scenario: Short content yields a single chunk
- **WHEN** `chunk_text("hello world")` is called with content shorter than CHUNK_SIZE
- **THEN** the result is `[{"text": "hello world", "chunk_index": 0}]`

#### Scenario: Long content yields multiple chunks with overlap
- **WHEN** `chunk_text("...very long text...")` is called with content longer than 2 × CHUNK_SIZE
- **THEN** the result has at least 2 chunks AND consecutive chunks share `CHUNK_OVERLAP` characters of overlap (the tail of chunk N appears at the head of chunk N+1)

#### Scenario: Knowledge ingest behavior unchanged
- **WHEN** `IngestPipeline` runs against any input previously tested
- **THEN** `chunk_node` returns identical output (number of chunks, chunk text, chunk_index values)
