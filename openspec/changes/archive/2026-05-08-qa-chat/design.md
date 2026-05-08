## Context

Knowledge ingestion and browsing are complete. The next step is making the knowledge base answerable: a user types a question, the agent retrieves relevant chunks from Qdrant (knowledge + optionally private), feeds them to an LLM, and streams the answer token-by-token. Session history is persisted in SQLite so users can return to prior conversations.

The design spec at `docs/superpowers/specs/2026-05-05-knowledge-agent-design.md` sections 5.4 and 6.4 defines the target API surface and UI layout. This document records the key technical decisions made to implement that spec.

## Goals / Non-Goals

**Goals:**
- LangGraph ReAct QA agent with tool calls for knowledge and private search
- SSE streaming so tokens appear in real-time (no full-round-trip wait)
- Session persistence (SQLite) with list and detail endpoints
- Functional ChatView.vue with streaming rendering, model selector, scope toggles, and source chips

**Non-Goals:**
- Prompt library (separate change)
- Save-answer-to-private-notes (PrivateView change)
- Thumbs-up / regenerate actions
- Multi-user auth (user_id = "default" throughout)

## Decisions

### 1. SSE over WebSocket for streaming

**Choice:** Flask SSE via `stream_with_context` + `Response(generator, mimetype='text/event-stream')`

**Rationale:** The existing stack uses Flask (not async). WebSocket requires a different server (gevent/asyncio) or a second process. SSE is unidirectional (server → client), which is all that's needed for token streaming. Flask SSE works with standard Gunicorn threaded workers. No new dependencies.

**Alternatives considered:**
- WebSocket (flask-sock): requires thread-per-connection or async; adds complexity without benefit for this use case
- Polling: wastes requests; poor UX for streaming text

**Event format:**
- Token event: `data: {"type":"token","content":"<text>"}\n\n`
- Sources event (final): `data: {"type":"done","sources":[{"title":"...","domain":"...","file_id":"..."}]}\n\n`
- Error event: `data: {"type":"error","message":"<msg>"}\n\n`

### 2. LangGraph ReAct agent (not a simple chain)

**Choice (revised 2026-05-08):** Deferred. V1 ships with a deterministic RAG chain: pre-search Qdrant based on the user-selected `scope` (knowledge / private / both), build a context block from the top chunks, then stream the LLM's answer.

**Why the deviation:** The original choice was `create_react_agent` from LangGraph. After implementation review, the ReAct loop adds significant test complexity (mocking `BaseChatModel`, parsing `astream_events` v2 output, handling tool-call events) while V1 single-turn Q&A doesn't actually exercise the multi-step decision-making that ReAct enables. The tools are well-defined and the user explicitly chooses the scope via the toggle UI — no autonomous decision is needed. Promoting to ReAct is straightforward when a multi-step use case (e.g., follow-up clarifying questions, drill-down via `get_entry`) lands.

**What's preserved:** The 3 tool functions (`search_knowledge` / `search_private` / `get_entry`) are kept as testable Python functions and are what the V1 chain calls directly. They remain the API the future ReAct agent will plug in to.

**Tools (unchanged):**
- `search_knowledge(query: str, domain: str | None) → list[Chunk]`: vector search on `knowledge` collection; no user_id filter (shared collection)
- `search_private(query: str) → list[Chunk]`: vector search on `private` collection; ALWAYS adds `user_id = "default"` filter
- `get_entry(file_id: str) → str`: fetches full text of a knowledge file from disk (for detailed lookups)

**Alternatives considered:**
- Original: ReAct via `create_react_agent` — deferred (see "Why the deviation" above)
- LangChain agent: project already uses LangGraph (IngestPipeline); staying consistent if/when we re-add agentic behavior

### 3. Streaming tokens from LangGraph

**Choice:** Run the graph in a background thread, pipe tokens via a `queue.Queue`, yield from the Flask generator.

**Rationale:** LangGraph's `astream_events` requires an async event loop. Flask is sync. The thread+queue pattern keeps Flask sync while allowing streaming. The generator yields each token from the queue until it sees a sentinel value (`None`), then yields the sources event.

**Event flow:**
```
POST /api/chat
  └─ start thread: run_agent(queue, ...)
  └─ return Response(generate(queue), mimetype=text/event-stream)
      ├─ queue.get() → yield token SSE
      ├─ ...
      └─ queue.get() → None sentinel → yield done SSE with sources
```

### 4. Session storage in SQLite

**Choice:** Two new tables `chat_sessions` + `chat_messages` in the existing SQLite DB.

**Rationale:** Already have SQLite for file metadata. Adding two tables is trivial. No need for a separate store.

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS chat_sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT 'haiku',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES chat_sessions(id),
    role TEXT NOT NULL CHECK(role IN ('user','assistant')),
    content TEXT NOT NULL,
    sources TEXT,           -- JSON array of source objects, NULL for user messages
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 5. Frontend SSE via EventSource

**Choice:** Native `EventSource` API (not axios) for the SSE stream. Axios for session CRUD.

**Rationale:** `EventSource` is the browser-native SSE client. It handles reconnection automatically. Axios cannot consume a streaming SSE response in the browser without hacks.

**Pattern:** When user submits a message, the store opens an `EventSource` to `POST /api/chat` by constructing a URL with query params (since `EventSource` only supports GET). To support POST with body, use `fetch` with `ReadableStream` instead of `EventSource`.

**Revised choice:** Use `fetch` with streaming `response.body.getReader()` — this allows POST with JSON body (model, scope, query, session_id) while still reading the SSE stream incrementally. `EventSource` only supports GET.

### 6. Qdrant user_id scoping

- `search_knowledge`: no user_id filter — knowledge collection is shared across all users (same as wiki routes)
- `search_private`: ALWAYS includes `Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))])` — private collection is per-user; V1 user_id = "default"

## Risks / Trade-offs

- **Thread + queue latency**: background thread adds ~1ms overhead per token. Acceptable for chat UX.
- **No cancellation**: if the user navigates away mid-stream, the server-side thread continues until the agent completes. Mitigation: agent responses are short (RAG-grounded); risk is low. Future: add cancel token.
- **Session title**: auto-generated from first user message (first 60 chars). Not editable in V1.
- **SQLite write concurrency**: agent thread writes messages while Flask serves reads. SQLite WAL mode (already enabled) handles this safely.
- **LangGraph graph state and history**: the QA agent does not maintain cross-turn memory in V1. Each POST /api/chat call loads prior messages from SQLite and passes them as `messages` input to create context — simple but sufficient for V1.
