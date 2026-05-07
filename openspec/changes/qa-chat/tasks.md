## 1. SQLite chat tables

- [ ] 1.1 RED — write failing pytest test for `_ensure_chat_tables()`: assert `chat_sessions` and `chat_messages` tables exist in a fresh SQLite DB; assert idempotent on second call
- [ ] 1.2 GREEN — add `_ensure_chat_tables()` to `DatabaseService` in `backend/app/services/db_service.py`; add tables to `backend/db/schema.sql`; call from Flask app factory
- [ ] 1.3 Run `cd backend && pytest` — all tests green
- [ ] 1.4 Run superpowers:requesting-code-review on the diff for group 1; address CRITICAL/HIGH findings before moving on

## 2. QA Agent tools (unit-testable, no LLM)

- [ ] 2.1 RED — write failing pytest tests for `search_knowledge` tool function: mock `EmbeddingService.embed()` + `QdrantService.search()` to return 3 test points; assert returned list contains dicts with `content`, `domain`, `source_file_id`, `score` fields; assert no user_id filter is applied to `knowledge` collection
- [ ] 2.2 RED — write failing pytest tests for `search_private` tool function: same mocking pattern; assert Qdrant search call includes `user_id = "default"` payload filter; missing filter MUST fail the test
- [ ] 2.3 RED — write failing pytest test for `get_entry` tool: mock file read at `UPLOADS_PATH/default/{file_id}/{file_id}.txt`; assert function returns file text content; assert 404-like error when file not found
- [ ] 2.4 GREEN — implement `backend/app/graphs/qa_agent.py`: define `search_knowledge(query, domain=None)`, `search_private(query)`, `get_entry(file_id)` as plain Python functions (not LangGraph tools yet) that accept injected service instances; wire up embedding + Qdrant calls per design.md
- [ ] 2.5 Run `cd backend && pytest` — all tests green
- [ ] 2.6 Run superpowers:requesting-code-review on the diff for group 2; address CRITICAL/HIGH findings before moving on

## 3. LangGraph QA agent graph + SSE streaming

- [ ] 3.1 RED — write failing pytest tests for the QA graph integration: mock LLM to yield 3 tokens then stop; mock `search_knowledge` to return 2 chunks; assert stream yields `{"type":"token","content":"..."}` events followed by `{"type":"done","sources":[...]}` event; assert `search_private` is NOT called when scope is `["knowledge"]`
- [ ] 3.2 RED — write failing pytest test for the private-scope path: assert `search_private` IS called when scope includes `"private"` and user_id filter is present
- [ ] 3.3 GREEN — wrap tool functions as LangGraph `ToolNode` tools; build `create_react_agent` graph with `ChatAnthropic`/`ChatOpenAI` per `LLM_PROVIDER`; implement `run_agent(queue, query, scope, model, history)` function that runs the graph and pushes token/done/error events to a `queue.Queue`; implement `stream_response(queue)` generator for Flask SSE
- [ ] 3.4 Run `cd backend && pytest` — all tests green
- [ ] 3.5 Run superpowers:requesting-code-review on the diff for group 3; address CRITICAL/HIGH findings before moving on

## 4. Chat API routes

- [ ] 4.1 RED — write failing pytest tests for `POST /api/chat`: (a) with `session_id=None` → new session row created in SQLite; (b) SSE stream yields at least one `type=token` event and a `type=done` event (mock the agent); (c) with existing `session_id` → prior messages loaded and appended (not new session)
- [ ] 4.2 RED — write failing pytest tests for `GET /api/chat/sessions`: (a) empty DB → `[]`; (b) two sessions → array ordered newest-first with `id, title, model, created_at`
- [ ] 4.3 RED — write failing pytest tests for `GET /api/chat/sessions/{id}`: (a) valid id → 200 with messages array; (b) unknown id → 404 `{"error":"session not found"}`
- [ ] 4.4 GREEN — implement `backend/app/routes/chat.py` blueprint: `POST /api/chat` (thread+queue SSE pattern from design.md); `GET /api/chat/sessions`; `GET /api/chat/sessions/{id}`; register blueprint in app factory; update `test_app_factory.py` to remove `/api/chat` from STUB_ROUTES
- [ ] 4.5 Run `cd backend && pytest` — all tests green
- [ ] 4.6 Run superpowers:requesting-code-review on the diff for group 4; address CRITICAL/HIGH findings before moving on

## 5. Pinia chat store

- [ ] 5.1 RED — write failing vitest tests for `chat.js` store: (a) `fetchSessions()` calls `GET /api/chat/sessions` and populates `sessions`; (b) `sendMessage()` appends user message immediately, then streams tokens into assistant message content via mocked fetch ReadableStream; (c) `streaming` is true during fetch and false after done event; (d) `newSession()` resets `currentSession` to null; (e) `loadSession(id)` calls `GET /api/chat/sessions/{id}` and populates `currentSession`
- [ ] 5.2 GREEN — implement `frontend/src/stores/chat.js` (Pinia options API): `state`: sessions, currentSession, streaming, error; actions: fetchSessions, loadSession, sendMessage (fetch ReadableStream SSE pattern), newSession; token streaming uses `response.body.getReader()` + TextDecoder
- [ ] 5.3 Run `cd frontend && npm test` — all tests green
- [ ] 5.4 Run superpowers:requesting-code-review on the diff for group 5; address CRITICAL/HIGH findings before moving on

## 6. ChatView component

- [ ] 6.1 RED — write failing vitest tests for `ChatView.vue`: (a) mounts in empty state — prompt cards visible, no messages; (b) session list renders after store.fetchSessions; (c) clicking session calls store.loadSession; (d) clicking "新建对话" calls store.newSession; (e) model selector defaults to Haiku, selecting Sonnet updates model ref; (f) scope toggles — default "knowledge" active; clicking "私有" activates both; cannot deactivate last active scope; (g) submitting message calls store.sendMessage with query, model, scope; (h) streaming=true shows loading indicator; (i) assistant message renders markdown content; (j) source chips appear after done event
- [ ] 6.2 GREEN — implement `frontend/src/views/ChatView.vue`: left sidebar (新建对话 button + session list with `data-session-item`); main area toolbar (model selector `data-model-select` + scope toggles `data-scope-knowledge` / `data-scope-private`); message list (user messages right, assistant left with `data-assistant-msg`); source chips `data-source-chip`; empty state `data-empty-state` with 6 prompt cards; input area with submit button
- [ ] 6.3 Apply UI design system from `docs/frontend-ui-guide.md`: gradient header, sidebar styling, bubble styles for user/assistant messages, scope toggle active state
- [ ] 6.4 Run `cd frontend && npm test` — all tests green
- [ ] 6.5 Run superpowers:requesting-code-review on the diff for group 6; address CRITICAL/HIGH findings before moving on

## 7. Integration verification and completion

- [ ] 7.1 Run `cd backend && pytest` — full backend suite green
- [ ] 7.2 Run `cd frontend && npm test` — full frontend suite green
- [ ] 7.3 Verify no user_id filter is missing: grep `search_private` usages; confirm every call path applies `user_id = "default"` filter
- [ ] 7.4 Manual smoke test via Docker: send a question about an ingested topic → tokens stream in real time → source chips appear → reload page → session appears in sidebar → click session → messages reload
- [ ] 7.5 Update `docs/log/2026-05-06.md` with commit hash, features, test counts, and code review findings
- [ ] 7.6 Run superpowers:requesting-code-review on the full qa-chat diff; address all CRITICAL/HIGH findings
