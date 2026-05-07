## Why

The foundation scaffold ships `/api/ingest` as a stub — there is no way to put knowledge into Qdrant, so the system cannot answer questions or retrieve documents. This change wires up the full ingest flow: upload or paste content, process it through a LangGraph pipeline, and store embeddings in the appropriate Qdrant collection.

Addresses: ING-01, ING-02, ING-03, ING-04, ING-05, ING-06, ING-09, ING-10, UI-08–UI-14, DATA-03, DATA-07.

## What Changes

- Implement LangGraph `IngestPipeline` graph: Source Router → Fetch → Clean → Chunk → Embed → Store → Summary; Source Router supports all four source types — `file`, `url`, `text`, `mcp` (ING-01, ING-02); `mcp` Fetch branch returns a not-implemented error in V1 so V2 requires no graph restructuring (ING-03)
- `POST /api/ingest`: accept file upload / URL / text, launch pipeline in background thread, return `job_id` immediately (ING-09)
- `GET /api/ingest/status/{job_id}`: poll pipeline progress; returns `{job_id, status, chunk_count, file_id}` when complete (ING-06, ING-10)
- User selects destination at ingest time: `knowledge` (public Qdrant collection) or `private` (user-scoped, always with `user_id` filter) (ING-04)
- Original files saved to `/app/uploads/{user_id}/{file_id}/`; metadata registered in SQLite `files` table (ING-05, DATA-03, DATA-07)
- Replace `IngestView.vue` skeleton: two-tab layout (New Ingest / Uploaded Files), destination toggle, file-drag + URL + text inputs, real-time progress list, file-list tab with `TreeNav.vue` and file metadata (UI-08–UI-14)

**Non-Goals (this change):** MCP client implementation — Google Docs, Notion credentials and actual fetching (ING-07, P2); resync/incremental update for MCP files (ING-08, P2); file-list「+ 摄入到此分类」shortcut (UI-15, P2). The `mcp` source type route is wired but returns a not-implemented error until V2.

Design mockups are in `docs/superpowers/specs/2026-05-05-knowledge-agent-design.md` §3.1 and §5.1.

## Capabilities

### New Capabilities
- `ingest-pipeline`: LangGraph `IngestPipeline` graph — Source Router, Fetch, Clean, Chunk, Embed, Store, Summary nodes; in-memory job registry; routes output to `knowledge` or `private` Qdrant collection; `user_id` required for private destination
- `ingest-api`: Flask routes `POST /api/ingest` and `GET /api/ingest/status/{job_id}`; multipart file upload; input validation; background-thread execution; file persistence service
- `ingest-view`: Vue 3 `IngestView.vue` — two tabs (New Ingest / Uploaded Files), destination toggle (knowledge ↔ private), drag-and-drop file upload + URL input + text paste, real-time progress list, file-list tab with `TreeNav.vue` (domain → topic), file metadata rows with action buttons (view / download / delete)

### Modified Capabilities
<!-- No spec-level requirement changes to existing capabilities. The `/api/ingest` stub contract is fulfilled by the new ingest-api capability. -->

## Impact

- **Backend new files**: `backend/app/graphs/ingest_pipeline.py`, `backend/app/services/file_service.py`
- **Backend modified**: `backend/app/routes/ingest.py` (replaces stub), `backend/requirements.txt` (add `langgraph`, `pymupdf`, `python-multipart`, `httpx`, `chardet`)
- **Frontend modified**: `frontend/src/views/IngestView.vue` (replaces skeleton), `frontend/src/stores/ingest.js` (real state)
- **Infrastructure**: uploads Docker volume already defined — no new infrastructure needed
- **No breaking changes** to existing routes or data models
