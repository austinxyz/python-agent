## Why

`POST /api/private/entries` embeds the derived text representation of each entry as a single vector via `EmbeddingService.embed(text)`. OpenAI's `text-embedding-3-small` rejects inputs longer than 8192 tokens with HTTP 400. During the bulk import of `wealth/output` (2026-05-08) six long personal-finance documents (`EBAY持仓分析`, `投资优化计划`, `资产全景`, `保留绿卡行动计划`, `入籍评估`, `绿卡放弃vs保留分析`) failed for this exact reason and had to be persisted as un-vectorized notes — losing AI retrieval over content the user explicitly wanted available to the chat agent.

The knowledge ingest pipeline already solves this: `IngestPipeline.chunk_node` splits long content into ~2000-character overlapping chunks and stores one Qdrant point per chunk (each linking back to the same `source_file_id`). Private entries should do the same.

## What Changes

- **Extract chunker into a reusable helper** (`backend/app/graphs/text_chunker.py`): the existing `chunk_node` body becomes a plain function `chunk_text(content, *, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP) -> list[dict]`. `IngestPipeline` calls the helper; `private.py` calls the same helper.
- **`POST /api/private/entries`**: derive text → chunk → embed each chunk → upsert one Qdrant point per chunk in the `private` collection. All points share `source_file_id = entry_id` and the same metadata (`user_id`, `template_type`, `title`, `directory`); each point gets its own `chunk_index`.
- **`PUT /api/private/entries/{id}`**: delete all existing Qdrant points for `source_file_id = entry_id` (filter-based, not by point id), re-chunk the new content, re-embed, upsert. SQLite update unchanged.
- **`DELETE /api/private/entries/{id}`**: switch from `QdrantService.delete_private(point_ids)` to a new `delete_private_by_source_file_id(user_id, file_id)` that uses Qdrant's filter-based delete. The old method stays as deprecated for the legacy 1-point-per-entry data (a no-op on chunked entries since the entry's UUID isn't a point id any more).
- **`QdrantService.delete_private_by_source_file_id(user_id, file_id)`**: new method using `Filter(must=[user_id=..., source_file_id=...])` on `points_selector`.
- **Backwards compatible**: existing single-point entries (created before this change, with `point.id == entry.id`) continue to work — the new filter-based delete also matches them since their `payload.source_file_id` equals their id. No SQLite migration. No re-embed required for already-stored short entries.

## Capabilities

### Modified Capabilities

- `private-entries`: long entries (>8192 tokens) now succeed; AI retrieval surfaces the most relevant chunk regardless of where it appears in the source document.

### New Capabilities

- `text-chunking`: a small shared utility for character-based chunking with overlap. Used by both `IngestPipeline` (knowledge collection) and the private-entries route.

## Impact

- **Backend**: `private.py::create_entry / update_entry / delete_entry` rewritten to chunk; new `text_chunker.py`; `QdrantService` gains `delete_private_by_source_file_id`; `ingest_pipeline.py::chunk_node` becomes a thin wrapper around the helper (preserving the LangGraph node signature).
- **Frontend**: no change — the REST contract (request body, response shape) is identical. Source chips already aggregate by `source_file_id` so chunked search results appear as a single source per entry.
- **Tests**: new `test_text_chunker.py`; extensions to `test_private_entries.py` for chunked create/update/delete; existing `test_ingest_pipeline.py` continues to pass against the refactored helper.
- **Data**: no migration. Existing short entries (single point, `point.id == entry.id`) keep working. Long files that fell back to notes during 2026-05-08's bulk import remain notes — promoting them to entries is a manual user action via the existing UI.

## Non-Goals

- Re-importing the 6 fallback notes as entries (user-driven manual step)
- Configurable chunk size per template (V1 uses one global size)
- Async / batched embedding (the OpenAI client handles a few sequential calls per entry just fine for personal-scale content)
- Token-aware chunking (V1 uses character count; OpenAI's 8192-token limit corresponds to ~30000 chars in CJK + English mix, well above the 2000-char boundary)
