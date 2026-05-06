## Context

The foundation scaffold provides `QdrantService`, `EmbeddingService`, and `DatabaseService` — all the infrastructure for storing and retrieving knowledge. The `/api/ingest` blueprint is a stub returning `{"status":"ok","stub":true}`. This design wires those services together through a LangGraph pipeline triggered by HTTP, with a Vue frontend for user interaction.

Primary reference: `docs/superpowers/specs/2026-05-05-knowledge-agent-design.md` §3.1 and §5.1.

## Goals / Non-Goals

**Goals:**
- File upload, URL fetch, and plain-text ingest via `POST /api/ingest`
- LangGraph pipeline: Source Router → Fetch → Clean → Chunk → Embed → Store → Summary
- Destination toggle: knowledge (public) or private (user-scoped, always `user_id="default"` in V1)
- Original file persistence at `/app/uploads/{user_id}/{file_id}/`
- SQLite `files` table population on successful ingest
- Progress polling via `GET /api/ingest/status/{job_id}`
- `IngestView.vue` with two tabs, drag-and-drop, real-time progress list, file-list with TreeNav

**Non-Goals:**
- MCP data sources (Google Docs, Notion) — P2
- Resync / incremental update of existing files — P2
- Multi-user authentication — V1 hardcodes `user_id="default"`
- Streaming pipeline progress (SSE) — polling is sufficient for ingest

## Decisions

### 1. Job execution: background thread (not Celery, not asyncio)

**Decision:** Run the pipeline in a `threading.Thread` started by the Flask route. Store job state in an in-memory `dict[str, JobState]` protected by a `threading.Lock`.

**Alternatives considered:**
- *Celery + Redis*: Robust for production, but adds two new services to Docker Compose. Over-engineered for single-user V1 where no parallel ingest backlog is expected.
- *asyncio / Flask-ASGI*: Would require migrating Flask to ASGI (Quart or Starlette). Not worth the churn for a synchronous pipeline.
- *Background thread*: Simple, zero new dependencies, sufficient for V1. Limitation: job state is lost on container restart — acceptable since ingest jobs are short-lived (seconds to minutes).

**Risk → Mitigation:** Long PDFs (hundreds of pages) may block the thread pool. → Cap accepted file size at 50 MB; log a warning for files > 10 MB.

### 2. LangGraph graph type: StateGraph (linear pipeline, not ReAct)

**Decision:** Use `langgraph.graph.StateGraph` with a fixed sequence of nodes, no conditional edges except Source Router's branching on `source_type`.

**Alternatives considered:**
- *ReAct agent*: Appropriate for the Q&A graph (dynamic tool calls), but ingest is deterministic — every run follows the same node sequence. Using ReAct here adds unnecessary complexity and retry risk.

### 3. MCP source type: wired now, implemented in V2

**Decision:** Source Router accepts `mcp` as a valid `source_type` and routes it to the Fetch Node. The Fetch Node's `mcp` branch returns `status="error"` with `"mcp not yet implemented"` in V1. No MCP client code is written yet.

**Rationale:** ING-02 (P1) requires the Source Router to support all four source types (`file`, `url`, `mcp`, `text`). The actual MCP client integration (Google Docs, Notion credentials — ING-07) is P2. Wiring the route now means V2 only needs to fill in the Fetch Node — no graph restructuring, no API contract changes, no frontend changes. Treating `mcp` as an "unsupported" type would have forced a breaking graph change at V2.

### 3. Text chunking: character-based, ~2 000 chars ≈ 512 tokens

**Decision:** Split on `\n\n` paragraph boundaries first; if a paragraph exceeds 2 000 characters, split further at sentence boundaries. Overlap: last 200 characters of previous chunk prepended to next. No external tokenizer dependency.

**Alternatives considered:**
- *tiktoken*: Accurate token counting but ~5 MB dependency and requires model-specific encoding. Character heuristic (1 token ≈ 4 chars) is sufficient for embedding quality.
- *LangChain TextSplitter*: Pulls in all of LangChain. Overkill.

### 4. Frontend progress: polling (not SSE)

**Decision:** `POST /api/ingest` returns `{job_id}` immediately; frontend polls `GET /api/ingest/status/{job_id}` every 2 seconds until `status == "completed"` or `"error"`.

**Alternatives considered:**
- *SSE from the pipeline*: Would require the Flask route to hold the connection open and stream updates. LangGraph's node callbacks are not async-friendly with Flask's WSGI model. Polling is simpler and fully sufficient for jobs that complete in < 60 seconds.

### 5. File parsing: PyMuPDF for PDF, stdlib for text/markdown

**Decision:** Use `pymupdf` (fitz) for PDF text extraction. For `.txt`, `.md`: read with `chardet`-detected encoding, no external parser. URL fetch via `httpx` (already in requirements as a transitive dep); extract text from HTML with `html.parser` stdlib.

**Alternatives considered:**
- *pdfplumber / pdfminer*: Slower than PyMuPDF; PyMuPDF has better table and column handling.
- *BeautifulSoup for HTML*: Adds a dependency; `html.parser` is sufficient for basic extraction.

### 6. Private destination: user_id always injected server-side

**Decision:** The frontend sends `destination: "private"` in the request body. The backend always sets `user_id = "default"` server-side when storing to the private collection. The frontend never sends `user_id`.

**Rationale:** Keeps `user_id` enforcement entirely server-side. When multi-user auth is added, only the backend changes (read `user_id` from session). Matches the invariant: every private Qdrant write MUST include `user_id`.

## Risks / Trade-offs

- **In-memory job registry**: Lost on container restart. → Acceptable for V1 (jobs are short-lived; user can simply re-upload).
- **Single background thread per job**: Flask's dev server is single-threaded by default; production mode (`threaded=True`, default in Flask 3) handles this. → Documented in `wsgi.py` comments.
- **PDF extraction quality**: PyMuPDF handles most PDFs well; scanned image PDFs without OCR layer will yield empty text. → Store the file anyway; return a warning in the summary response.
- **No deduplication**: Re-uploading the same file creates a new `file_id` and new Qdrant chunks. → Out of scope for V1; `files` table records all uploads.

## Migration Plan

1. Add Python dependencies to `backend/requirements.txt` (langgraph, pymupdf, python-multipart, chardet)
2. Create `backend/app/graphs/ingest_pipeline.py` and `backend/app/services/file_service.py`
3. Replace stub in `backend/app/routes/ingest.py`
4. Replace `IngestView.vue` skeleton and wire `ingest` Pinia store
5. `docker compose build api` — no schema migrations needed (SQLite `files` table already exists)
6. Rollback: revert `ingest.py` to stub, redeploy — no data migration required

## Open Questions

- Should chunk `text` field be stored in Qdrant payload (for display in Q&A sources) or only the embedding? → **Store chunk text in payload** (`text` key) so Q&A can display source excerpts without re-fetching the file.
- Domain / topic classification: manual input by user at ingest time (simple), or LLM-inferred (better UX)? → **V1: manual input** (two text fields in the form). LLM inference deferred to a future change.
