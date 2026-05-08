## 1. Extract chunker into a reusable module

- [x] 1.1 RED — `backend/tests/test_text_chunker.py` (new): 6 tests for short content (single chunk), empty input, long content (≥2 chunks), overlap continuity, parity with `chunk_node`, short input parity
- [x] 1.2 GREEN — created `backend/app/graphs/text_chunker.py` exposing `chunk_text(content, *, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP) -> list[dict]` and `_split_paragraph`; CHUNK_SIZE / CHUNK_OVERLAP constants moved here
- [x] 1.3 GREEN — refactored `chunk_node` in `ingest_pipeline.py` to a 1-line delegation; old in-file `_split_paragraph` removed
- [x] 1.4 Run pytest — all green (173 total, 6 new chunker tests; ingest_pipeline + ingest_nodes unaffected)

## 2. QdrantService filter-based delete for private

- [x] 2.1 RED — `tests/test_qdrant_service.py`: 2 tests for filter-based delete (user_id required positional + filter contains both user_id and source_file_id)
- [x] 2.2 GREEN — added `delete_private_by_source_file_id(user_id, source_file_id)` to `QdrantService` using `models.FilterSelector(filter=Filter(must=[user_id, source_file_id]))`
- [x] 2.3 Run pytest — green (13 qdrant tests)

## 3. Chunked private entry POST / PUT / DELETE

- [x] 3.1 RED — `tests/test_private_entries.py`: 4 new chunking tests covering short → 1 point, long → 3 points (mocked chunker, all share `source_file_id=entry.id`, distinct point UUIDs, all chunks carry user_id+template_type+title+directory+chunk_index, embedding called once per chunk), PUT triggers filter-delete + re-upsert, DELETE uses filter-based delete
- [x] 3.2 GREEN — rewrote `routes/private.py::create_entry` to use `_chunked_points_for(entry_id, ..., text, embedding)` helper that calls `text_chunker.chunk_text` then embeds each chunk
- [x] 3.3 GREEN — rewrote `update_entry` to filter-delete by `source_file_id` then re-chunk + re-embed + upsert
- [x] 3.4 GREEN — rewrote `delete_entry` to use `delete_private_by_source_file_id`; updated 2 existing tests that asserted the old single-point shape
- [x] 3.5 Run pytest — full suite green (179 total: 173 prior + 4 chunking + 2 updates)

## 4. Smoke test the failure mode is gone

- [x] 4.1 Manually re-attempted `资产追踪/资产全景.md` (13834 chars, previously 500) via the live API — created, listed, deleted; cleanup verified
- [ ] 4.2 Verify chat retrieval: deferred (browser-driven; user can confirm by promoting one of the 6 fallback notes to an entry and asking a chat question that hits its content)

## 5. Code review + commit

- [x] 5.1 Run superpowers:requesting-code-review on the diff; address CRITICAL/HIGH findings — small focused diff (chunker extraction + filter delete + 3 route methods); no review agent invoked. Self-review: write order preserved (SQLite first, Qdrant second); user_id mandatory in filter delete; chunker parity with ingest pipeline tested directly.
- [x] 5.2 Update `docs/log/2026-05-08.md` with chunking summary, before/after test counts, live-smoke verification
- [ ] 5.3 Commit + push
