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

---

## Revision 2026-05-08 — Clickable source chips + kind-based routing

### Requirement: Source chips SHALL be navigable links, not static spans
Each source rendered below an assistant message SHALL be a `router-link`
(or equivalent navigable element) whose target depends on `src.kind`:
- `kind === "knowledge"` → `{ path: '/wiki', query: { file: src.file_id } }`
- `kind === "entry"` → `{ path: '/private', query: { entry: src.file_id } }`

#### Scenario: Knowledge source chip routes to /wiki
- **WHEN** a source with `kind="knowledge"` and `file_id="abc"` is rendered
- **THEN** clicking it navigates to `/wiki?file=abc`

#### Scenario: Private entry source chip routes to /private
- **WHEN** a source with `kind="entry"` and `file_id="def"` is rendered
- **THEN** clicking it navigates to `/private?entry=def`

### Requirement: Source chips SHALL be visually distinct by kind
Knowledge chips and entry chips SHALL use different background tints so
the user can tell which page a click will land on without hovering. The
implementation uses Notion's `tint-lavender` for knowledge and `tint-mint`
for entries, but any pair of distinct tints from `docs/design/notion.md`
satisfies this requirement.

#### Scenario: Mixed-scope answer surfaces both chip styles
- **WHEN** an answer cites both knowledge and private sources
- **THEN** the chip backgrounds visually distinguish the two kinds

### Requirement: WikiView SHALL accept `?file=<id>` and auto-open the entry
On mount, `WikiView` SHALL read `route.query.file`. If present, it SHALL
locate the entry in the loaded tree, expand its domain group, set the
viewing file id, and load the content panel. A subsequent route change
(e.g., user clicks a different chip while still on `/wiki`) SHALL update
the panel without a full remount.

#### Scenario: Deep-link opens the entry directly
- **WHEN** the user navigates to `/wiki?file=abc` from a chat source chip
- **THEN** the right panel shows `abc`'s content and its domain is expanded in the sidebar

### Requirement: PrivateView SHALL accept `?entry=<id>` and auto-open the item
On mount (after `fetchEntries` and `fetchNotes` resolve), `PrivateView`
SHALL read `route.query.entry`. If present, it SHALL find the matching
item in the combined tree, expand every directory segment along its
path, select the item, and switch the right panel to `item-view`. A
subsequent route change SHALL update the panel without remount.

#### Scenario: Deep-link opens a private entry directly
- **WHEN** the user navigates to `/private?entry=xyz` from a chat source chip
- **THEN** the directory containing `xyz` is expanded and the right panel shows the entry's template fields

---

## Revision 2026-05-08 — Save assistant answer to private notes

### Requirement: SSE `done` event SHALL carry the resolved `session_id`
Without an explicit signal, the frontend has no way to know the id of a
session created by the current request. The `done` event SHALL include
the field `session_id: string`. The chat store SHALL hydrate
`currentSession.id` from this field on its first arrival so the
save-to-notes flow can attach `chat_ref` accurately.

#### Scenario: First message in a new session
- **WHEN** the user sends a query without `session_id` and the stream completes
- **THEN** the `done` event includes `session_id` and the store sets `currentSession.id` to that value

### Requirement: Each assistant message SHALL offer a save-to-notes affordance
Every assistant message that has finished streaming SHALL render a
discoverable "保存到笔记" trigger. Clicking the trigger SHALL expand an
inline form pre-filled with sensible defaults; saving SHALL persist the
message as a private note via `POST /api/private/notes`, threading
`chat_ref = currentSession.id` through.

#### Scenario: Idle trigger is visible after streaming completes
- **WHEN** an assistant message has finished streaming
- **THEN** a `data-save-note-btn` element is rendered below it

#### Scenario: Trigger is hidden while the same message is still streaming
- **WHEN** an assistant message is still being streamed (the last one in the list)
- **THEN** no save trigger is rendered for that message

### Requirement: The save form SHALL pre-fill title, directory, and Markdown content
Defaults:
- `title`: first ~40 characters of the preceding user question
- `directory`: `对话总结/<YYYY-MM-DD>` (today's local date)
- `content`: a Markdown structure containing:
  - The user question as a blockquote
  - The assistant answer body
  - A "## 参考来源" section listing each source as a Markdown link to
    `/wiki?file=<id>` (knowledge) or `/private?entry=<id>` (entry)

All three fields SHALL be editable before save.

#### Scenario: Sources render as deep-link Markdown
- **WHEN** an assistant message cites a knowledge source `f1` titled `401k` in domain `退休规划`
- **THEN** the default content includes the line ``- [401k](/wiki?file=f1) · 退休规划``

#### Scenario: Private entry source uses /private?entry= path
- **WHEN** an assistant message cites a private source `p1` with `kind="entry"`
- **THEN** the default content includes a link to `/private?entry=p1`

### Requirement: Saving SHALL call store.saveMessageToNote and confirm inline
Clicking "保存" in the form SHALL call `store.saveMessageToNote(idx, payload)`.
On success, the form SHALL collapse and a confirmation message SHALL
replace it, naming the directory the note was saved to. Clicking "取消"
SHALL collapse the form without calling the store.

#### Scenario: Successful save shows confirmation
- **WHEN** the user clicks 保存 and the API call resolves
- **THEN** the form is removed from the DOM and a `data-save-note-confirmation` element appears with text containing "已保存" and the directory name

#### Scenario: Cancel does nothing observable except hiding the form
- **WHEN** the user clicks 取消
- **THEN** `store.saveMessageToNote` is not called and the form is removed from the DOM

### Requirement: chat store SHALL implement saveMessageToNote
`saveMessageToNote(messageIndex, { title, directory, content })` SHALL
POST `/api/private/notes` with the supplied fields and `chat_ref =
currentSession.id`. It SHALL return the created note on success and
re-throw on failure (after recording `store.error`).

#### Scenario: chat_ref is sent with the request
- **WHEN** `saveMessageToNote(1, payload)` is called while `currentSession.id === "s1"`
- **THEN** the POST body includes `chat_ref: "s1"`
