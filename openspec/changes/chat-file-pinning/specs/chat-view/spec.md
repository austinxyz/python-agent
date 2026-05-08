## ADDED Requirements

### Requirement: ChatView SHALL render a 📎 引用 button next to the textarea
The chat input area SHALL include a discoverable trigger (`data-pin-btn`, label `📎 引用` or equivalent) directly adjacent to `[data-chat-input]`. Clicking it SHALL open a picker (`data-pin-picker`) listing all entries + notes (and optionally knowledge files in V1.1) sourced from `store.entries`, `store.notes`, and the wiki tree.

#### Scenario: trigger is visible in empty state and in active session
- **WHEN** the user navigates to `/chat`
- **THEN** the `data-pin-btn` element is visible in the input area regardless of whether a session is active

### Requirement: Picker SHALL list private entries + notes searchable by title
The picker SHALL show a flat list of items, each rendered with a kind badge (📋 entry / 📝 note / 📚 knowledge), title, and parent directory/domain. A search box SHALL filter items by case-insensitive substring match on `title`.

#### Scenario: typing filters the list
- **WHEN** the picker is open and the user types "FBAR" into the search box
- **THEN** only items whose title contains "FBAR" (case-insensitive) remain visible

### Requirement: Selected items SHALL render as removable chips above the input
Selecting an item in the picker SHALL add it to a `pinnedItems` ref. The chips SHALL render above the textarea with `[data-pin-chip]` selectors. Each chip SHALL have a `✕` (`[data-pin-chip-remove]`) that removes the item from `pinnedItems`. The picker stays open until the user dismisses it.

#### Scenario: pinning two items creates two chips
- **WHEN** the user opens the picker and selects two items
- **THEN** two `[data-pin-chip]` elements appear above `[data-chat-input]`

#### Scenario: removing a chip restores its picker entry as unselected
- **WHEN** the user clicks the `✕` on a chip
- **THEN** the chip is removed from the DOM and `pinnedItems` no longer contains that id

### Requirement: Sending a message SHALL forward pinned ids and clear them
On `data-chat-submit`, the request body SHALL include `pinned_file_ids: pinnedItems.map(i => i.id)`. After the response stream completes, `pinnedItems` SHALL be cleared (per-turn pinning, not session-wide).

#### Scenario: POST body includes pinned ids
- **WHEN** the user has pinned two items and clicks send
- **THEN** the POST body's `pinned_file_ids` array contains the two ids in the order the user pinned them

#### Scenario: pins clear after the stream completes
- **WHEN** a message with pins finishes streaming (done event received)
- **THEN** `pinnedItems` is empty and no chips remain in the DOM

### Requirement: chat store sendMessage SHALL accept pinnedFileIds
`chat.js::sendMessage(query, { model, scope, pinnedFileIds = [] })` SHALL forward `pinnedFileIds` to the request body as `pinned_file_ids`. The default empty list preserves the legacy contract for callers that don't pin.

#### Scenario: legacy caller without pins is unchanged
- **WHEN** `sendMessage(query, { model, scope })` is called without `pinnedFileIds`
- **THEN** the request body does NOT include a `pinned_file_ids` field (or includes an empty array — implementation choice)

#### Scenario: caller with pins forwards them
- **WHEN** `sendMessage(query, { model, scope, pinnedFileIds: ["a", "b"] })` is called
- **THEN** the POST body includes `"pinned_file_ids": ["a", "b"]`
