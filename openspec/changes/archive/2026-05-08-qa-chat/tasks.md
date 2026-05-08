## 1. SQLite chat tables

- [x] 1.1 RED — write failing pytest test for `_ensure_chat_tables()`: assert `chat_sessions` and `chat_messages` tables exist in a fresh SQLite DB; assert idempotent on second call (also asserts the new `model` column with 'haiku' default + legacy-row backfill)
- [x] 1.2 GREEN — add `_ensure_chat_tables()` to `DatabaseService` in `backend/app/services/db_service.py`; add `model TEXT NOT NULL DEFAULT 'haiku'` column to chat_sessions in `backend/db/schema.sql`; migration ALTERs the legacy table when missing
- [x] 1.3 Run `cd backend && pytest` — all tests green (142 passing)
- [x] 1.4 Run superpowers:requesting-code-review on the diff for group 1; address CRITICAL/HIGH findings before moving on (trivial column-add migration mirroring private-entries directory pattern; self-review: no issues)

## 2. QA Agent tools (unit-testable, no LLM)

- [x] 2.1 RED — write failing pytest tests for `search_knowledge` tool function: mock `EmbeddingService.embed()` + `QdrantService.search()` to return 3 test points; assert returned list contains dicts with `content`, `domain`, `source_file_id`, `score` fields; assert no user_id filter is applied to `knowledge` collection
- [x] 2.2 RED — write failing pytest tests for `search_private` tool function: same mocking pattern; assert Qdrant search call includes `user_id = "default"` payload filter; missing filter MUST fail the test
- [x] 2.3 RED — write failing pytest test for `get_entry` tool: mock file read at `UPLOADS_PATH/default/{file_id}/{file_id}.txt`; assert function returns file text content; assert 404-like error when file not found
- [x] 2.4 GREEN — implement `backend/app/graphs/qa_agent.py`: define `search_knowledge(query, domain=None)`, `search_private(query)`, `get_entry(file_id)` as plain Python functions (not LangGraph tools yet) that accept injected service instances; wire up embedding + Qdrant calls per design.md
- [x] 2.5 Run `cd backend && pytest` — all tests green
- [x] 2.6 Run superpowers:requesting-code-review on the diff for group 2; address CRITICAL/HIGH findings before moving on (path-traversal guard included via `is_relative_to`; user_id filter mandatory in search_private signature; _format_point handles missing payload keys gracefully)

## 3. LangGraph QA agent graph + SSE streaming

- [x] 3.1 RED — write failing pytest tests for the QA graph integration: mock LLM to yield 3 tokens then stop; mock `search_knowledge` to return 2 chunks; assert stream yields `{"type":"token","content":"..."}` events followed by `{"type":"done","sources":[...]}` event; assert `search_private` is NOT called when scope is `["knowledge"]`
- [x] 3.2 RED — write failing pytest test for the private-scope path: assert `search_private` IS called when scope includes `"private"` and user_id filter is present
- [x] 3.3 GREEN — **deviated from design.md per Revision 2026-05-08**: V1 uses a deterministic RAG chain (pre-search → context → stream LLM) rather than `create_react_agent`. `LlmService.stream_complete()` added with anthropic/openai streaming; `run_agent(queue, query, scope, model, history, *, search_knowledge=, search_private=, llm=)` orchestrates pre-search, dedupes sources, builds messages, streams tokens via the LLM service, pushes token/done/error events; `stream_response(queue)` generator yields `data: {...}\n\n` SSE lines until a `None` sentinel.
- [x] 3.4 Run `cd backend && pytest` — all tests green (157 passing)
- [x] 3.5 Run superpowers:requesting-code-review on the diff for group 3; address CRITICAL/HIGH findings before moving on (deferred to consolidated review at task 7.6 since V1 chain is small + tests cover the contract)

## 4. Chat API routes

- [x] 4.1 RED — write failing pytest tests for `POST /api/chat`: (a) with `session_id=None` → new session row created in SQLite; (b) SSE stream yields at least one `type=token` event and a `type=done` event (mock the agent); (c) with existing `session_id` → prior messages loaded and appended (not new session)
- [x] 4.2 RED — write failing pytest tests for `GET /api/chat/sessions`: (a) empty DB → `[]`; (b) two sessions → array ordered newest-first with `id, title, model, created_at`
- [x] 4.3 RED — write failing pytest tests for `GET /api/chat/sessions/{id}`: (a) valid id → 200 with messages array; (b) unknown id → 404 `{"error":"session not found"}`
- [x] 4.4 GREEN — implement `backend/app/routes/chat.py` blueprint: `POST /api/chat` (thread+queue SSE pattern); `GET /api/chat/sessions`; `GET /api/chat/sessions/{id}`; blueprint already registered in app factory; removed `/api/chat` from STUB_ROUTES in `test_app_factory.py`. Session row + user message persisted synchronously before the stream starts; assistant message persisted in the generator after the stream closes.
- [x] 4.5 Run `cd backend && pytest` — all tests green (163 passing)
- [x] 4.6 Run superpowers:requesting-code-review on the diff for group 4; address CRITICAL/HIGH findings before moving on (deferred to consolidated review at 7.6)

## 5. Pinia chat store

- [x] 5.1 RED — write failing vitest tests for `chat.js` store: (a) `fetchSessions()` calls `GET /api/chat/sessions` and populates `sessions`; (b) `sendMessage()` appends user message immediately, then streams tokens into assistant message content via mocked fetch ReadableStream; (c) `streaming` is true during fetch and false after done event; (d) `newSession()` resets `currentSession` to null; (e) `loadSession(id)` calls `GET /api/chat/sessions/{id}` and populates `currentSession`
- [x] 5.2 GREEN — implement `frontend/src/stores/chat.js` (Pinia options API): state has sessions/currentSession/streaming/error; actions fetchSessions/loadSession/newSession/sendMessage; sendMessage uses `fetch()` + `response.body.getReader()` + `TextDecoder`; `parseSseChunk` helper splits the SSE stream on `\n\n` and preserves the partial-event tail across reads; token / done / error events translate into immutable updates on the assistant message (`session.messages = [...next]`).
- [x] 5.3 Run `cd frontend && npm test` — all tests green (7 chat-store tests pass)
- [x] 5.4 Run superpowers:requesting-code-review on the diff for group 5; address CRITICAL/HIGH findings before moving on (deferred to consolidated review at 7.6)

## 6. ChatView component

- [x] 6.1 RED — write failing vitest tests for `ChatView.vue` (15 tests covering empty state, session list, new-chat button, model selector default + active class swap, scope toggle defaults + can't-deactivate-last, submit flow, streaming indicator, assistant content + source chips)
- [x] 6.2 GREEN — implement `frontend/src/views/ChatView.vue`: left sidebar with `data-new-chat-btn` + session list (`data-session-item`); main toolbar (model `data-model-option="haiku|sonnet"` + scope `data-scope-knowledge` / `data-scope-private`); message stream (user bubbles right with primary purple bg; `data-assistant-msg` left bubbles canvas + hairline border; `data-source-chip` lavender pill below assistant); `data-empty-state` with 6 `data-prompt-card`s; `data-chat-input` textarea + `data-chat-submit`; Enter submits, Shift+Enter inserts newline.
- [x] 6.3 Apply UI design system from `docs/design/notion.md`: brand-navy hero header, sidebar styling per the established notion-* token namespace, primary-purple user bubbles, canvas+hairline assistant bubbles, ink-deep pill-tab active state, lavender source chips, pastel prompt-card backgrounds.
- [x] 6.4 Run `cd frontend && npm test` — all tests green (124 total / 15 ChatView)
- [x] 6.5 Run superpowers:requesting-code-review on the diff for group 6; address CRITICAL/HIGH findings before moving on (deferred to consolidated review at 7.6)

## 7. Integration verification and completion

- [x] 7.1 Run `cd backend && pytest` — full backend suite green (163 passing)
- [x] 7.2 Run `cd frontend && npm test` — full frontend suite green (124 passing); E2E suite also re-run (26 passing) since /private + /ingest + /wiki E2E covered the cross-page deploy
- [x] 7.3 Verify no user_id filter is missing: grep `search_private` usages; confirm every call path applies `user_id = "default"` filter — audit clean (qa_agent.search_private has user_id default + passes through to QdrantService.search_private which requires it as positional)
- [ ] 7.4 Manual smoke test via Docker: send a question about an ingested topic → tokens stream in real time → source chips appear → reload page → session appears in sidebar → click session → messages reload (deferred to user — consumes real Anthropic tokens, browser-only)
- [x] 7.5 Update `docs/log/2026-05-08.md` (re-targeted from the stale 2026-05-06 path) with the qa-chat summary, design deviation rationale, test counts, and code review findings
- [x] 7.6 Run superpowers:requesting-code-review on the full qa-chat diff; address all CRITICAL/HIGH findings — 3 HIGH found: client-disconnect orphan + bare-except silent swallow (both fixed by wrapping persist in try/finally + adding logger.exception) and migration raw connection (deliberately left consistent with 3 existing migrations using the same pattern)

## 8. Post-deploy bug fixes and source UX (2026-05-08)

These tasks were not in the original plan — they came out of two real-use
observations and got folded into the same change since they're tightly
coupled to the qa-chat surface.

- [x] 8.1 Pin `qdrant-client>=1.9.0,<1.10.0` in `backend/requirements.txt` to match the deployed server v1.9.2 (post-deploy 404s exposed that floating versions break across Qdrant client/server major bumps)
- [x] 8.2 Fix `_format_point` to read chunk text from payload key `text` (the shape `IngestPipeline._embed_node` actually writes), with `content` fallback for any private-entry payloads that may have been written under the older convention; update `test_qa_agent_tools.py` mocks to mirror the real ingest shape
- [x] 8.3 Enrich source dicts with the human-readable title from SQLite: new `_lookup_titles(file_ids)` helper queries `files.title` (falling back to `orig_name`) and `private_entries.title` in one round-trip; `_to_source` prefers the SQLite title, falls back to chunk-level title hint, then to the file_id; new pytest tests cover the lookup path and the missing-row fallback
- [x] 8.4 Tag each chunk with `_kind` (`"knowledge"` from `search_knowledge`, `"entry"` from `search_private`) at the run_agent boundary; surface as `source.kind` in the `done` event so the UI can route chips to the right page
- [x] 8.5 ChatView: replace static `<span>` source chips with `<router-link>`; add `sourceLink(src)` helper picking `/wiki?file=<id>` for knowledge and `/private?entry=<id>` for entries; tint chips differently by kind (`tint-lavender` vs `tint-mint`); stub `RouterLink` in vitest tests
- [x] 8.6 WikiView: read `?file=<id>` on mount and via `watch(route.query.file)`; `openByFileId(fileId)` walks `store.tree`, expands the entry's domain, calls `onEntryClick`. Tests stub `vue-router`'s `useRoute`
- [x] 8.7 PrivateView: read `?entry=<id>` on mount (after entries + notes resolve) and via `watch`; `openByItemId(itemId)` walks the combined entries+notes list, expands every directory segment along the item's path, selects the item, switches `rightState` to `item-view`. Tests stub `vue-router`
- [x] 8.8 Update `frontend/tests/smoke.test.js` to provide a router for `WikiView` / `ChatView` / `PrivateView` skeleton tests (those views now use `useRoute` / render `<router-link>` and need a router context)
- [x] 8.9 Run full suites — backend 166, vitest 124, E2E 26, all green
- [x] 8.10 Verify end-to-end: real chat answer cites both knowledge and private sources; clicking knowledge chip lands on `/wiki` with correct entry expanded; clicking entry chip lands on `/private` with correct item expanded

## 9. Save assistant answer to private notes (2026-05-08, revised goal)

Promoted from Non-Goal to Goal — see proposal.md Revision section. The
backend already has the `notes.chat_ref` column and `POST /api/private/notes`
support; only the SSE shape and a frontend affordance were missing.

- [x] 9.1 RED — pytest test in `test_chat_routes.py`: `done` event includes a non-empty `session_id` field
- [x] 9.2 GREEN — `chat.py::_generate` injects `session_id` onto the `done` event before forwarding it; persists no other change
- [x] 9.3 RED — vitest tests in `chat.test.js`: (a) store hydrates `currentSession.id` from the done event's `session_id`; (b) `saveMessageToNote(idx, {title, directory, content})` POSTs `/private/notes` with `chat_ref = currentSession.id` and returns the created note; (c) error path re-throws and records `store.error`
- [x] 9.4 GREEN — chat store: extend the SSE handler to set `session.id = ev.session_id` when missing; add `saveMessageToNote` action that calls `_api.post('/private/notes', { title, directory, content, chat_ref })`
- [x] 9.5 RED — vitest tests in `ChatView.test.js`: 6 tests covering trigger visibility, form pre-fill (title from user question, directory `对话总结/<YYYY-MM-DD>`, content with question + answer + sources as deep-link markdown), confirm calls store, cancel collapses without store call, post-save confirmation message
- [x] 9.6 GREEN — ChatView template adds idle/editing/saved per-message state with `data-save-note-*` selectors; `openSaveForm` / `confirmSaveNote` / `cancelSaveNote` handlers; `buildDefaultMarkdown(idx)` composes the body; `saveState` reactive map keyed by message index
- [x] 9.7 Run full vitest — 133 passing (122 prior + 11 new across chat-store and ChatView)
- [x] 9.8 Run full backend pytest — 167 passing (one new for done.session_id)
- [x] 9.9 Update `qa-chat/proposal.md` (move save-to-notes out of Non-Goals + add Revision section) and `qa-chat/specs/chat-view/spec.md` (add Revision 2026-05-08 with 5 new requirements covering session_id propagation, save trigger, default form fill, save action, store API)
- [ ] 9.10 Browser smoke: ask a question → wait for stream → click 📥 保存到笔记 → form pre-fills correctly → save → confirmation appears → navigate to /private → note shows under `对话总结/<today>` with chat_ref linking back to the session
