## ADDED Requirements

### Requirement: ChatView renders two-column layout
The system SHALL implement `frontend/src/views/ChatView.vue` with a left sidebar (session list) and a main chat area. The component SHALL replace the existing stub. The Pinia chat store (`frontend/src/stores/chat.js`) SHALL manage all state.

#### Scenario: ChatView mounts in new-chat state
- **WHEN** the user navigates to `/chat`
- **THEN** the left sidebar shows a "新建对话" button; the main area shows the empty-state prompt cards; no messages are visible

#### Scenario: Session list visible in sidebar
- **WHEN** the chat store has loaded sessions
- **THEN** each session is listed in the left sidebar with its title and a relative timestamp

#### Scenario: Clicking a session loads its messages
- **WHEN** the user clicks a session in the sidebar
- **THEN** the chat area renders all messages for that session (user messages right-aligned, assistant messages left-aligned)

### Requirement: Chat store manages sessions and streaming state
The system SHALL implement `frontend/src/stores/chat.js` (Pinia options API) with:
- `sessions`: array of session objects
- `currentSession`: active session (id, title, model, messages)
- `streaming`: boolean true while SSE stream is active
- `error`: string | null
- Actions: `fetchSessions()`, `loadSession(id)`, `sendMessage(query, model, scope)`, `newSession()`

#### Scenario: fetchSessions populates sessions list
- **WHEN** `fetchSessions()` is called
- **THEN** `GET /api/chat/sessions` is called and `sessions` is populated

#### Scenario: sendMessage streams tokens into currentSession messages
- **WHEN** `sendMessage(query, model, scope)` is called
- **THEN** a user message is immediately appended to `currentSession.messages`; `streaming` is set to true; SSE tokens append to the assistant message content; on done event sources are attached; `streaming` is set to false

#### Scenario: streaming flag is true during fetch and false after
- **WHEN** `sendMessage` is called
- **THEN** `streaming` is true until the done event is received

### Requirement: Model selector controls LLM model
The system SHALL render a model selector in the chat toolbar. Selecting "Haiku" sends `model="haiku"` in the POST body; selecting "Sonnet" sends `model="sonnet"`.

#### Scenario: Haiku selected by default
- **WHEN** the user opens a new chat
- **THEN** the Haiku option is selected by default in the model selector

#### Scenario: Model selection persists for session
- **WHEN** the user selects Sonnet and sends a message
- **THEN** the POST body includes `"model":"sonnet"`

### Requirement: Scope toggles control knowledge/private search
The system SHALL render two independent toggle buttons: "知识库" and "私有". At least one MUST be active. The active scopes are sent as an array in `POST /api/chat` body under `scope`.

#### Scenario: Default scope is knowledge only
- **WHEN** the user opens a new chat
- **THEN** "知识库" toggle is active and "私有" is inactive; POST body includes `"scope":["knowledge"]`

#### Scenario: Both scopes can be active simultaneously
- **WHEN** the user activates both toggles
- **THEN** POST body includes `"scope":["knowledge","private"]`

#### Scenario: Cannot deactivate all scopes
- **WHEN** only one scope is active and the user clicks it
- **THEN** the toggle does not deactivate (at least one scope remains active)

### Requirement: Source citations appear below assistant messages
The system SHALL display source citation chips below each assistant message. Each chip shows the document title and domain. Chips use the done-event sources array.

#### Scenario: Sources rendered after stream completes
- **WHEN** the done SSE event is received with sources
- **THEN** citation chips appear below the assistant message, each showing title and domain badge

#### Scenario: No sources shown if done event has empty sources
- **WHEN** the done SSE event sources array is empty
- **THEN** no citation section is rendered below the message

### Requirement: Empty state shows recommended prompt cards
The system SHALL show 6 recommended prompt cards when no conversation is active. Clicking a card fills the input box with the prompt text.

#### Scenario: Prompt cards visible in empty state
- **WHEN** no session is selected and `currentSession` is null
- **THEN** 6 prompt cards are visible in the main area

#### Scenario: Clicking prompt card populates input
- **WHEN** the user clicks a prompt card
- **THEN** the text input is populated with the card's prompt text and focused
