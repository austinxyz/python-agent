## ADDED Requirements

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
