## Why

The knowledge base is fully ingested and browsable, but the core value proposition — answering user questions by combining public knowledge with private data — is not yet implemented. This change delivers the Q&A chat feature that makes the knowledge agent actually useful.

## What Changes

- **New LangGraph QA Agent** (`backend/app/graphs/qa_agent.py`): ReAct agent with `search_knowledge`, `search_private`, and `get_entry` tools; streams tokens via SSE; includes user_id scoping for private collection searches
- **New chat API routes** (`backend/app/routes/chat.py`): `POST /api/chat` (SSE stream), `GET /api/chat/sessions`, `GET /api/chat/sessions/{id}` backed by SQLite `chat_sessions` + `chat_messages` tables
- **New SQLite tables**: `chat_sessions` (id, title, created_at) and `chat_messages` (id, session_id, role, content, sources, created_at) — schema added to `backend/db/schema.sql`
- **Functional ChatView.vue**: replaces the stub placeholder; two-column layout (session list + chat area); SSE token streaming; model selector (Haiku/Sonnet); scope toggles (knowledge / private); citation chips; empty-state prompt cards
- **Pinia chat store** (`frontend/src/stores/chat.js`): sessions list, current messages, streaming state, error handling

## Capabilities

### New Capabilities

- `qa-agent`: LangGraph ReAct agent that answers questions via RAG over knowledge and private Qdrant collections; exposes tools search_knowledge, search_private, get_entry; streams token-by-token via SSE; records session + messages in SQLite
- `chat-view`: Vue 3 two-column chat interface; session history sidebar; SSE stream rendering; model/scope selectors; source citation chips; recommended prompt cards empty state

### Modified Capabilities

- `backend-scaffold`: Two new SQLite tables (chat_sessions, chat_messages) added to db/schema.sql; `_ensure_chat_tables()` migration called at app startup

## Impact

- **Backend**: new `chat.py` blueprint registered in `app.py`; `qa_agent.py` LangGraph graph; `_ensure_chat_tables()` in `db_service.py`
- **Frontend**: `ChatView.vue` (currently stub) replaced; `chat.js` Pinia store added; `api/index.js` used for session CRUD, raw `EventSource` for SSE stream
- **Dependencies**: no new packages (LangGraph, anthropic, qdrant-client, marked, DOMPurify already installed)
- **Requirements addressed**: CHAT-01 (RAG Q&A), CHAT-02 (SSE streaming), CHAT-03 (session history), CHAT-04 (scope toggle knowledge/private), CHAT-05 (source citations)

## Non-Goals

- Prompt library management (separate feature)
- Multi-user auth (V1 user_id is always "default")
- Regenerate / thumbs-up actions (post-MVP)
- MCP data sources for chat context

## Revision 2026-05-08 — Save-answer-to-private-notes promoted to a goal

The original plan listed "Save-answer-to-private-notes" as a non-goal,
to be deferred to a separate PrivateView change. Once the chat path was
working end-to-end the user identified the save flow as the immediately
useful next step — answers grounded in your own knowledge base are most
valuable when they get pinned alongside the rest of your private data.
Folding it into qa-chat keeps the UX surface coherent (the `chat_ref`
column on `notes` was already present from `private-data`; the only
thing missing was the UI affordance and a backend tweak so the SSE
`done` event carries the new session's `id`).
