## 1. Project Setup

- [x] 1.1 Add to `backend/requirements.txt`: `langgraph>=0.2`, `pymupdf`, `python-multipart`, `httpx`, `chardet`; verify `pip install -r requirements.txt` exits 0
- [x] 1.2 Create `backend/app/graphs/__init__.py` (empty); confirm the package is importable
- [x] 1.3 Add `UPLOADS_PATH=/app/uploads` to `.env.example` (with comment); add `UPLOADS_PATH` to the `api` service env block in `docker-compose.yml`; add to local `.env`
- [x] 1.4 Run superpowers:requesting-code-review on the diff for group 1; address CRITICAL/HIGH findings before moving on

## 2. JobRegistry Service

- [x] 2.1 RED — write failing pytest tests in `backend/tests/test_job_registry.py`: `create` → initial state is `{status: "running"}`; `get` returns state; `update` merges patch; `get` unknown id returns `None`
- [x] 2.2 GREEN — create `backend/app/services/job_registry.py` with thread-safe `JobRegistry` (threading.Lock); verify all RED tests pass
- [x] 2.3 RED — write failing test asserting concurrent `update` calls from two threads do not corrupt state (use `threading.Thread` + `threading.Barrier`)
- [x] 2.4 GREEN — confirm test passes (Lock already protects state; no code change needed)
- [x] 2.5 Run superpowers:requesting-code-review on the diff for group 2; address CRITICAL/HIGH findings before moving on

## 3. FileService

- [x] 3.1 RED — write failing pytest test in `backend/tests/test_file_service.py`: `FileService().save(user_id, file_id, filename, content)` writes bytes to `{UPLOADS_PATH}/{user_id}/{file_id}/{filename}` (use `tmp_path` fixture to set UPLOADS_PATH)
- [x] 3.2 RED — write failing pytest test: `FileService().register(db, ...)` inserts a row into the `files` table with correct `file_id`, `user_id`, `orig_name`, `chunk_count`
- [x] 3.3 GREEN — create `backend/app/services/file_service.py` with `save()` and `register()`; reads `UPLOADS_PATH` env var (default `/app/uploads`); verify both RED tests pass
- [x] 3.4 Run superpowers:requesting-code-review on the diff for group 3; address CRITICAL/HIGH findings before moving on

## 4. IngestPipeline — Node Unit Tests (RED phase)

- [x] 4.1 RED — `tests/unit/test_ingest_nodes.py` — Source Router: `source_type="file"` / `"url"` / `"text"` / `"mcp"` each routes to Fetch without error; unrecognised `source_type="ftp"` sets `status="error"` with `"unsupported source_type"`; `source_type="mcp"` Fetch branch sets `status="error"` with `"mcp not yet implemented"`
- [x] 4.2 RED — Fetch Node: mocked `fitz.open` returns page text for `source_type="file"` PDF; `httpx.get` mock returns HTML for `source_type="url"` and text is extracted; `source_type="text"` passes `content` through unchanged
- [x] 4.3 RED — Clean Node: input with three consecutive blank lines → output has exactly one; leading/trailing whitespace stripped; null-byte removed
- [x] 4.4 RED — Chunk Node: 500-char `raw_content` → exactly 1 chunk with `chunk_index=0`; 5 000-char `raw_content` → at least 3 chunks; second chunk starts with last 200 chars of first chunk
- [x] 4.5 RED — Embed Node: mocked `EmbeddingService.embed` returning `[0.0]*1536`; assert `len(state["vectors"]) == len(state["chunks"])`; each vector has length 1536
- [x] 4.6 RED — Store Node: `destination="knowledge"` → `QdrantService.upsert` payload does NOT contain `user_id`; `destination="private"` → payload contains `user_id="default"`; `FileService.register` is called exactly once
- [x] 4.7 RED — Summary Node: success state → returns dict with `status="completed"`, non-null `file_id`, `chunk_count >= 1`; error state (prior node set `status="error"`) → returns `{status: "error", error: <message>}` without `file_id`
- [x] 4.8 Run superpowers:requesting-code-review on the RED test files only (no implementation yet); confirm tests fail for the right reasons

## 5. IngestPipeline — GREEN and Integration

- [x] 5.1 GREEN — create `backend/app/graphs/ingest_pipeline.py` with `IngestPipeline` using `langgraph.graph.StateGraph`; implement all seven nodes; wire graph edges; verify all unit tests from group 4 pass
- [x] 5.2 RED — write integration test: `IngestPipeline().run(source_type="text", content="hello world", destination="knowledge", user_id="default")` with mocked `EmbeddingService` and `QdrantService`; assert return dict has `status="completed"` and `chunk_count >= 1`
- [x] 5.3 GREEN — verify integration test passes with no further changes
- [x] 5.4 RED — write integration test for private destination: `destination="private"` → every `QdrantService.upsert` call includes `user_id="default"` in the payload
- [x] 5.5 GREEN — verify test passes
- [x] 5.6 Run superpowers:requesting-code-review on the diff for group 5; address CRITICAL/HIGH findings before moving on

## 6. Flask API Routes

- [x] 6.1 RED — write failing pytest tests in `backend/tests/test_ingest_routes.py`: `POST /api/ingest` without `source_type` → 400; without `file` when `source_type="file"` → 400; `destination="public"` → 400; valid file upload → 202 with `{"job_id": "<uuid>"}`
- [x] 6.2 RED — write failing pytest tests: `GET /api/ingest/status/<unknown>` → 404; `GET /api/ingest/status/<running>` → `{status: "running"}`; `GET /api/ingest/status/<completed>` → `{status: "completed", file_id, chunk_count}`
- [x] 6.3 RED — write failing pytest test: file > 50 MB → 413 `{"error": "file too large (max 50 MB)"}`
- [x] 6.4 GREEN — replace stub in `backend/app/routes/ingest.py` with real `POST /api/ingest` and `GET /api/ingest/status/<job_id>`; wire `JobRegistry`, `IngestPipeline` background thread, and `FileService`; verify all RED tests from 6.1–6.3 pass
- [x] 6.5 Inspect: `grep -rn "private\|user_id" backend/app/graphs/ingest_pipeline.py` — confirm every write to the private collection passes `user_id` in the payload; zero omissions
- [x] 6.6 Run superpowers:requesting-code-review on the diff for group 6; address CRITICAL/HIGH findings before moving on

## 7. Frontend — Ingest Pinia Store

- [x] 7.1 RED — write vitest test in `frontend/tests/stores/ingest.test.js`: `useIngestStore().destination` defaults to `"knowledge"`; `setDestination("private")` updates it
- [x] 7.2 RED — write vitest test: `addJob("abc", "budget.pdf")` appends `{job_id:"abc", label:"budget.pdf", status:"running", chunk_count:null, error:null}`; `updateJob("abc", {status:"completed", chunk_count:8})` patches the entry
- [x] 7.3 RED — write vitest test: `fetchJobStatus("abc")` calls `GET /api/ingest/status/abc` (mock axios) and calls `updateJob` with the response body
- [x] 7.4 GREEN — implement `frontend/src/stores/ingest.js` with full state and actions; verify all RED tests pass
- [x] 7.5 Run superpowers:requesting-code-review on the diff for group 7; address CRITICAL/HIGH findings before moving on

## 8. Frontend — IngestView

- [x] 8.1 RED — write vitest test in `frontend/tests/views/IngestView.test.js`: renders two tab buttons with correct labels; clicking the second tab shows the files panel and hides the new-ingest panel
- [x] 8.2 RED — write vitest test: destination toggle defaults to "公共知识库" selected; clicking "私有数据" updates `useIngestStore().destination` to `"private"`
- [x] 8.3 RED — write vitest test: clicking "开始摄入" with no file/URL/text shows error message "请提供摄入内容" and axios.post is NOT called
- [x] 8.4 RED — write vitest test: submitting a valid URL triggers `POST /api/ingest` (mocked), receives `{job_id}`, and calls `useIngestStore().addJob`; a progress row with status "running" appears
- [x] 8.5 GREEN — implement `IngestView.vue` (two tabs, destination toggle, file drop zone, URL input, text textarea, domain/topic fields, submit button, progress list); verify RED tests from 8.1–8.4 pass
- [x] 8.6 RED — write vitest test: Uploaded Files tab renders `TreeNav.vue` with domain→topic items built from a mocked file list; selecting a node filters the visible file rows
- [x] 8.7 GREEN — implement file list tab using `TreeNav.vue` component (no duplication of tree logic); verify 8.6 passes
- [x] 8.8 Inspect: `grep -rn "console.log" frontend/src/` — assert zero debug statements
- [x] 8.9 Run superpowers:requesting-code-review on the diff for group 8; address CRITICAL/HIGH findings before moving on

## 9. Integration and Verification

- [x] 9.1 Run `cd backend && pytest` — assert all backend tests pass with exit code 0
- [x] 9.2 Run `cd frontend && npm test` — assert all frontend vitest tests pass with exit code 0
- [x] 9.3 Run superpowers:verification-before-completion: full test suites; `grep -rn "user_id" backend/app/graphs/ingest_pipeline.py` confirm every private Qdrant write carries `user_id`; `grep -rn "console.log" frontend/src/` confirm zero; no hardcoded secrets
- [ ] 9.4 Manual smoke test: `docker compose up`; open `http://localhost:3000/ingest`; paste a short text snippet with destination "公共知识库"; click "开始摄入"; verify progress row reaches "completed"; confirm chunk appears in Qdrant at `http://localhost:6333/collections/knowledge`
- [x] 9.5 Run superpowers:requesting-code-review on the complete ingest diff; address all CRITICAL/HIGH findings
- [x] 9.6 Commit with `feat: implement ingest pipeline (LangGraph, Flask API, Vue IngestView)`
