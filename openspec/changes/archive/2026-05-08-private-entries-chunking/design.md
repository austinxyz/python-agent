## Context

Bulk-importing 40 personal-finance documents into private entries on 2026-05-08 surfaced an 8192-token cap in OpenAI's `text-embedding-3-small`. Six long documents 500'd at the embedding step. The knowledge ingest pipeline already has chunking (`chunk_node` in `ingest_pipeline.py`); the private-entries route was written before chunking was needed and embeds the full derived text in one shot.

This change brings the private path up to parity with knowledge ingest by reusing the same chunker.

## Goals / Non-Goals

**Goals:**
- Long entries succeed silently (no user-visible 500)
- AI retrieval works on long entries — the chat agent finds the relevant chunk regardless of where it sits in the source
- One source-chip per entry in chat answers (no chip duplication just because retrieval returned multiple chunks of the same doc)

**Non-Goals:**
- Token-aware chunking (V1 character-based is sufficient)
- Configurable chunk size per template
- Async / batched embedding
- Auto-promoting the 6 fallback notes — that's a manual user step

## Decisions

### 1. Reuse the existing chunker, don't write a new one

**Choice:** Extract `chunk_node`'s body into a free function `chunk_text(content) -> list[dict]` in a new module `backend/app/graphs/text_chunker.py`. `chunk_node` becomes a 3-line wrapper. `private.py` imports the helper directly.

**Rationale:** Same algorithm, same constants (CHUNK_SIZE=2000, CHUNK_OVERLAP=200), already tested via `test_ingest_pipeline.py`. Avoids drift between knowledge and private chunking.

### 2. Filter-based delete for the entry's chunks

**Choice:** New `QdrantService.delete_private_by_source_file_id(user_id, file_id)` that uses `points_selector=Filter(must=[user_id=..., source_file_id=...])`. The legacy `delete_private(point_ids)` method stays for the QA-agent code path (which targets specific points by id) but the entry route switches to filter-based.

**Rationale:** With chunked entries we no longer have a single Qdrant point id per entry — we have N point ids, all with the same `source_file_id`. Filter-based delete handles both the new chunked entries and the legacy single-point entries (their `payload.source_file_id == entry.id` so the filter matches them too).

**Alternatives considered:**
- Store the list of chunk point ids in SQLite as JSON: makes SQLite the source of truth for Qdrant ids, but adds a column and a sync risk. Filter-based delete is simpler.
- Use `points_selector=PointIdsList(...)` after fetching chunk ids via scroll: extra round trip, no benefit.

### 3. user_id stays mandatory in the new delete method

**Choice:** `delete_private_by_source_file_id` requires `user_id` as a positional argument, mirroring `search_private`. There is no default.

**Rationale:** Same isolation invariant the rest of the private path enforces. Forgetting `user_id` on a multi-tenant version would let user A delete user B's data — make it impossible to forget.

### 4. Chunked points share metadata except `chunk_index`

**Choice:** Each Qdrant point has the same `{user_id, template_type, title, directory, source_file_id}` payload as the single-point version, plus a new `chunk_index: int`. The point's own `id` is a fresh UUID per chunk.

**Rationale:**
- `source_file_id` is what the search code already aggregates by (de-dup happens in `qa_agent._to_source` keyed on `source_file_id`).
- `chunk_index` is informational — not currently used by the chat path but matches the knowledge ingest format and could drive "show me the most relevant section" UX later.
- A fresh per-chunk UUID lets `qdrant.upsert_private(points)` handle multiple new points in one call.

### 5. SQLite is unchanged

**Choice:** `private_entries` keeps one row per entry. The single-row content_json is the source of truth; Qdrant is a derived index that can be rebuilt from SQLite at any time.

**Rationale:** Already the design (see `private-data` design.md). Adding chunk metadata to SQLite would couple the row schema to the indexing strategy. If we ever switch to a different chunker, only Qdrant needs a re-index.

## Risks / Trade-offs

- **Embedding cost scales with chunk count.** Long entries cost more to embed than a single-vector version would (if it fit). Acceptable: the user's longest doc was ~30k chars → ~15 chunks → 15× embedding calls. At $0.02 per 1M tokens for `text-embedding-3-small`, this is < $0.001 per entry. Negligible.
- **Update path now does N+1 work** (delete all old points + re-embed every chunk). For a 15-chunk entry that's 1 filter delete + 15 embed calls + 1 upsert. Still < 5 seconds end-to-end.
- **Qdrant filter delete is asynchronous in some configurations.** With the local docker container we use, the operation is synchronous and immediate, but if the user later moves to Qdrant Cloud they'll need to verify. Out of scope for V1.
- **Source-chip aggregation in chat depends on `_to_source` deduplicating by `source_file_id`.** Already implemented (`qa_agent.py::run_agent` builds a `seen_ids` set). Verified by existing test `test_done_event_dedupes_sources_across_scopes`.
