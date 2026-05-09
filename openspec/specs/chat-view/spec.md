# chat-view Specification

## Purpose
TBD - created by archiving change qa-chat. Update Purpose after archive.
## Requirements
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

---

### Requirement: ChatView renders single-column mobile layout below md
Below the `md` breakpoint (768px), `ChatView.vue` SHALL render a single-column layout: header (h-12) + scrollable messages region (flex-1) + sticky input box. The desktop two-column layout (sessions sidebar + chat area) SHALL be retained at `md+`. The decision SHALL be expressed via Tailwind responsive utilities (no JS-driven viewport detection).

#### Scenario: Phone viewport hides desktop sessions sidebar
- **WHEN** ChatView is rendered at viewport width 393px
- **THEN** the inline sessions sidebar (`data-sessions-sidebar`) is `display: none` and the messages container takes full viewport width

#### Scenario: Desktop viewport keeps the existing two-column shape
- **WHEN** ChatView is rendered at viewport width 1280px
- **THEN** sessions sidebar and chat area both render as today

### Requirement: Mobile ChatView exposes sessions list via ☰ drawer and new-chat via 🆕 button
Below `md`, the ChatView header SHALL include a left-side `☰` button (data-sessions-toggle) that opens a full-width slide-in drawer containing the same session list rendered in the desktop sidebar, AND a right-side `🆕` button (data-new-chat) that creates a fresh session in one tap. Selecting a session in the drawer SHALL close the drawer and navigate to that session.

#### Scenario: ☰ opens the sessions drawer
- **WHEN** the user taps `data-sessions-toggle` at viewport 393px
- **THEN** an element with `data-sessions-drawer` becomes visible, sliding in from the left, containing one entry per session

#### Scenario: Tapping a session closes the drawer and navigates
- **WHEN** the drawer is open and the user taps a session entry
- **THEN** the drawer closes (slides out), the URL becomes `/chat/<session_id>`, and the messages of that session render

#### Scenario: 🆕 starts a new session
- **WHEN** the user taps `data-new-chat` at viewport 393px
- **THEN** a fresh empty session is created without opening the drawer; the input box is focused

### Requirement: Chat input is sticky and keyboard-aware via dvh + safe-area
Below `md`, the chat input box SHALL use `position: sticky; bottom: 0` and the messages container SHALL use a viewport unit (`100dvh` or equivalent) so iOS Safari keyboard pop-ups do not push the input off-screen. The input wrapper SHALL apply `padding-bottom: env(safe-area-inset-bottom)` so it clears the iPhone home indicator. Send button is icon-only (`➤`) on mobile to save horizontal space.

#### Scenario: Input remains visible above keyboard
- **WHEN** the user focuses the input field on iOS Safari and the soft keyboard appears
- **THEN** the input box is visible directly above the keyboard (not covered, not pushed below it)

#### Scenario: Input clears the home indicator
- **WHEN** the input box is rendered on a device that reports `safe-area-inset-bottom > 0`
- **THEN** the input wrapper has bottom padding equal to that inset value

### Requirement: Auto-scroll-to-bottom respects user reading position
When new tokens stream in via SSE, ChatView SHALL scroll the messages container to the bottom only if the user's current scroll position is within 100px of the bottom. If the user has scrolled up (more than 100px from bottom), the streaming tokens MUST NOT yank the scroll position.

#### Scenario: Auto-scroll fires when user is at bottom
- **WHEN** the messages container is scrolled to the bottom and a new token arrives
- **THEN** the container scrolls to keep the latest token visible

#### Scenario: Auto-scroll is suppressed when user has scrolled up
- **WHEN** the user has scrolled the messages container up by 500px and a new token arrives
- **THEN** the container does NOT scroll; the user's reading position is preserved

