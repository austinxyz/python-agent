## ADDED Requirements

### Requirement: QA agent answers questions via RAG
The system SHALL implement a LangGraph ReAct agent in `backend/app/graphs/qa_agent.py` that retrieves relevant chunks from Qdrant and generates a grounded answer using the configured LLM. The agent SHALL support `knowledge` scope (searches `knowledge` collection) and `private` scope (searches `private` collection with mandatory `user_id` filter). Both scopes MAY be active simultaneously.

#### Scenario: Knowledge-scope question answered
- **WHEN** a user submits a question with scope `["knowledge"]`
- **THEN** the agent calls `search_knowledge` tool, retrieves relevant chunks, and generates an answer grounded in those chunks

#### Scenario: Private-scope question answered
- **WHEN** a user submits a question with scope `["private"]`
- **THEN** the agent calls `search_private` tool with user_id filter applied, retrieves private chunks, and generates an answer

#### Scenario: Both scopes active
- **WHEN** a user submits a question with scope `["knowledge", "private"]`
- **THEN** the agent MAY call both `search_knowledge` and `search_private` and synthesizes an answer from both result sets

#### Scenario: No relevant results found
- **WHEN** Qdrant returns no results for the query
- **THEN** the agent responds that it does not have relevant information rather than hallucinating

### Requirement: Private collection search MUST include user_id filter
Every call to `search_private` tool MUST include a Qdrant payload filter `user_id = "default"` (V1). Omitting this filter is a critical bug that exposes other users' private data.

#### Scenario: search_private always filters by user_id
- **WHEN** `search_private` tool is invoked with any query
- **THEN** the Qdrant search payload filter includes `user_id = "default"`

### Requirement: Agent streams tokens via SSE
The system SHALL stream LLM tokens to the caller as they are generated. The `POST /api/chat` endpoint SHALL return `Content-Type: text/event-stream`. Each token SHALL be sent as a separate SSE event. The final event SHALL include the list of source documents used.

#### Scenario: Token events received during generation
- **WHEN** the LLM generates tokens
- **THEN** each token is sent as `data: {"type":"token","content":"<text>"}\n\n`

#### Scenario: Done event includes sources
- **WHEN** the agent finishes generating its answer
- **THEN** a final `data: {"type":"done","sources":[...]}\n\n` event is sent where sources contains title, domain, and file_id for each retrieved chunk

#### Scenario: Error during generation
- **WHEN** an exception occurs during agent execution
- **THEN** `data: {"type":"error","message":"<msg>"}\n\n` is sent and the stream closes

### Requirement: Chat API persists sessions and messages
The system SHALL provide three endpoints:
- `POST /api/chat` — start/continue a chat session; returns SSE stream; accepts `{query, model, scope, session_id?}`; creates a new session if `session_id` is absent; saves user message and assistant response to SQLite after stream completes
- `GET /api/chat/sessions` — returns list of sessions ordered by `created_at DESC`
- `GET /api/chat/sessions/{id}` — returns session metadata + all messages for that session

#### Scenario: New session created on first message
- **WHEN** `POST /api/chat` is called without `session_id`
- **THEN** a new `chat_sessions` row is created with auto-generated UUID and title from the first 60 chars of the query

#### Scenario: Existing session continued
- **WHEN** `POST /api/chat` is called with an existing `session_id`
- **THEN** prior messages from that session are loaded from SQLite and passed as context to the agent; new messages are appended

#### Scenario: Sessions list returns all sessions
- **WHEN** `GET /api/chat/sessions` is called
- **THEN** the response is a JSON array of `{id, title, model, created_at}` objects ordered newest-first

#### Scenario: Session detail returns messages
- **WHEN** `GET /api/chat/sessions/{id}` is called with a valid session id
- **THEN** the response includes `{id, title, model, created_at, messages: [{role, content, sources, created_at}]}`

#### Scenario: Unknown session returns 404
- **WHEN** `GET /api/chat/sessions/{id}` is called with an unknown id
- **THEN** the response is 404 `{"error": "session not found"}`

### Requirement: Agent tools are unit-testable with mocked Qdrant
The QA agent tools (`search_knowledge`, `search_private`, `get_entry`) SHALL be independently callable Python functions that accept a mocked Qdrant client, enabling unit tests without a live Qdrant or LLM.

#### Scenario: search_knowledge called with mock
- **WHEN** `search_knowledge` is called with a mocked QdrantService
- **THEN** it returns a list of chunk dicts with `content`, `domain`, `source_file_id`, `score` fields

#### Scenario: search_private called with mock
- **WHEN** `search_private` is called with a mocked QdrantService
- **THEN** it calls QdrantService with user_id filter and returns formatted chunks

---

## Revision 2026-05-08 — V1 chain, payload shape, source enrichment

The implementation deviates from the original LangGraph ReAct design (see
`design.md` §2 "Why the deviation") and ships a deterministic RAG chain
instead. The functional contract on the SSE stream is unchanged; the
following requirements capture what the implementation actually delivers
so the spec matches reality.

### Requirement: V1 agent SHALL ship as a deterministic RAG chain (no autonomous tool dispatch)
The QA agent SHALL pre-search Qdrant based on the user-selected `scope`,
build a context block from the retrieved chunks, and stream the LLM's
answer. Multi-step reasoning, autonomous `get_entry` follow-ups, and
ReAct-style decision loops SHALL be deferred until a use case for them
appears. The 3 tool functions remain in place as the public API the
future ReAct upgrade will plug in to.

#### Scenario: Single-turn Q&A produces a grounded answer
- **WHEN** a user sends a single query with `scope=["knowledge"]`
- **THEN** the agent calls `search_knowledge` once, builds a context block, and streams the LLM answer

#### Scenario: No autonomous tool calls in V1
- **WHEN** the LLM emits text suggesting a follow-up tool call
- **THEN** V1 ignores the suggestion (no ReAct loop); the answer simply ends

### Requirement: Tool result formatting SHALL read chunk text from the `text` payload key
The `IngestPipeline` writes chunk content into Qdrant payload key `text`
(see `ingest_pipeline._embed_node`). The QA agent's `_format_point` helper
SHALL read `payload.get("text")` first and fall back to `payload.get("content")`
to remain compatible with any private-entry payloads written under the
older convention. Reading only `content` is a CRITICAL bug — the LLM
receives empty context and refuses to answer.

#### Scenario: Knowledge chunk produces non-empty content
- **WHEN** a Qdrant point's payload contains `{"text": "FBAR 是…"}`
- **THEN** `search_knowledge` returns a chunk dict whose `content` field is `"FBAR 是…"`

### Requirement: Sources SHALL carry `kind`, `title`, `domain`, `file_id`
The `done` SSE event's `sources` array SHALL contain objects with all four
fields. `kind` is `"knowledge"` for chunks from the knowledge collection
and `"entry"` for chunks from the private collection. `title` is the
human-readable title looked up from SQLite (`files.title` falling back to
`files.orig_name` for knowledge; `private_entries.title` for private
entries; the file_id itself when neither row exists). `domain` is the
domain string for knowledge and the directory string for private entries.
The chat UI uses `kind` to route the source chip to the correct page.

#### Scenario: Knowledge source carries kind=knowledge
- **WHEN** the agent retrieves a chunk from the `knowledge` collection
- **THEN** the corresponding source in the `done` event has `kind: "knowledge"`

#### Scenario: Private source carries kind=entry
- **WHEN** the agent retrieves a chunk from the `private` collection
- **THEN** the corresponding source has `kind: "entry"`

#### Scenario: Title is looked up from SQLite
- **WHEN** a knowledge chunk references file_id `"abc"` and `files.title` for `"abc"` is `"FBAR"`
- **THEN** the source's `title` is `"FBAR"`, not `"abc"`

#### Scenario: Title falls back to file_id when SQLite has no row
- **WHEN** a chunk references a file_id that is not present in `files` or `private_entries`
- **THEN** the source's `title` is the file_id itself (so the user can still report which document the agent cited)

### Requirement: qdrant-client SHALL be pinned to match the deployed Qdrant server
The `qdrant-client` Python dependency SHALL be pinned to a version
compatible with the Qdrant server image declared in `docker-compose.yml`.
qdrant-client v1.13+ removed the `.search()` method; the deployed server
v1.9.2 does not yet support `.query_points()`. Allowing the client to
float caused production to receive `404 Not Found` from Qdrant.

#### Scenario: backend/requirements.txt pins qdrant-client to a server-compatible range
- **WHEN** a developer runs `pip install -r backend/requirements.txt` against the docker-compose Qdrant version
- **THEN** the installed qdrant-client supports the `.search()` API used by `QdrantService`
