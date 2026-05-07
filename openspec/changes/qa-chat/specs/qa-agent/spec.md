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
