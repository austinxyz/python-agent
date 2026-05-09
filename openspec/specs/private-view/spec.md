# private-view Specification

## Purpose
TBD - created by archiving change private-data. Update Purpose after archive.
## Requirements
### Requirement: PrivateView renders two-section layout
The system SHALL replace `frontend/src/views/PrivateView.vue` stub with a full page. The page SHALL have a header following `docs/design/notion.md` (brand-navy hero band). Below the header, the page is divided into two vertical sections: the upper section shows structured template entries, and the lower section shows private notes in a directory tree. The Pinia `private.js` store manages all state.

#### Scenario: PrivateView mounts and loads data
- **WHEN** the user navigates to `/private`
- **THEN** the store calls `fetchEntries()` and `fetchNotes()` on mount; the page renders both sections

### Requirement: Pinia private store manages entries and notes
The system SHALL implement `frontend/src/stores/private.js` (Pinia options API) with:
- `templates`: array from `GET /api/private/templates`
- `entries`: array from `GET /api/private/entries`
- `notes`: array and `notesTree` object from `GET /api/private/notes`
- `error`: string | null
- Actions: `fetchTemplates()`, `fetchEntries()`, `fetchNotes()`, `createEntry(payload)`, `updateEntry(id, payload)`, `deleteEntry(id)`, `createNote(payload)`, `updateNote(id, payload)`

#### Scenario: fetchEntries populates entries
- **WHEN** `fetchEntries()` is called
- **THEN** `GET /api/private/entries` is called and `entries` is populated immutably

#### Scenario: createEntry adds new entry to state immutably
- **WHEN** `createEntry({template_type, title, content_json})` is called
- **THEN** `POST /api/private/entries` is called; on success, the returned entry is prepended to `entries` (spread pattern, not push)

#### Scenario: deleteEntry removes entry from state immutably
- **WHEN** `deleteEntry(id)` is called
- **THEN** `DELETE /api/private/entries/{id}` is called; on success, `entries` is replaced with a new array filtering out the deleted id

### Requirement: Template entries section — select template and fill form
The upper section SHALL show the list of existing entries (each card showing template type badge, title, created date) and a "新建条目" button. Clicking "新建条目" opens a panel showing template type selector. After selecting a template, a dynamic form renders the template's fields. Submitting the form calls `store.createEntry()`. Each entry card SHALL have an "编辑" button to open the same form pre-filled with existing `content_json`, and a "删除" button.

#### Scenario: Template selector shows 6 options
- **WHEN** user clicks "新建条目"
- **THEN** all 6 template types are shown as selectable options with their Chinese labels

#### Scenario: Form fields render from template definition
- **WHEN** user selects the "retirement" template
- **THEN** the form renders the fields defined in that template (e.g., 401K balance, Roth IRA balance)

#### Scenario: Submitting form creates entry and updates list
- **WHEN** user fills the form and clicks save
- **THEN** `store.createEntry()` is called; on success, the new entry appears at the top of the entries list

#### Scenario: Deleting entry removes it from the list
- **WHEN** user clicks "删除" on an entry card and confirms
- **THEN** `store.deleteEntry(id)` is called; the entry disappears from the list

### Requirement: Notes section — directory tree with inline editor
The lower section SHALL show a collapsible directory tree of notes sourced from `store.notesTree`. Clicking a note title displays its content in a read panel to the right of the tree (or below on smaller layouts). The panel SHALL include an "编辑" button that switches the content area to an editable markdown textarea. Saving calls `store.updateNote(id, {content})`. A "新建笔记" button at the top of the notes section opens a note creation form (title, optional directory, markdown content).

#### Scenario: Notes tree renders directory hierarchy
- **WHEN** notes exist in directories "退休规划" and root
- **THEN** the tree shows a "退休规划" folder node and root-level notes

#### Scenario: Clicking note title shows content
- **WHEN** user clicks a note title in the tree
- **THEN** the note content is displayed in the reading panel

#### Scenario: Editing note saves updated content
- **WHEN** user clicks "编辑", modifies the textarea, and clicks "保存"
- **THEN** `store.updateNote(id, {content})` is called; the reading panel refreshes with the new content

#### Scenario: Note created from form appears in tree
- **WHEN** user fills the new-note form and submits
- **THEN** `store.createNote()` is called; the note appears under the correct directory in the tree

---

### Requirement: PrivateView renders TreeNav as drawer below md
Below the `md` breakpoint (768px), `PrivateView.vue` SHALL hide the inline left TreeNav and expose it via a `☰` button (`data-tree-toggle`) in the page header. Tapping `☰` opens a full-width slide-in drawer with the TreeNav. Selecting a directory or entry in the drawer SHALL close the drawer and update the right-panel state. The right panel SHALL render at full viewport width below `md`. The "create new entry" affordance SHALL remain reachable via a `＋` button in the page header on mobile (one tap, no drawer).

#### Scenario: Phone viewport hides inline tree
- **WHEN** PrivateView renders at viewport 393px
- **THEN** `data-tree-inline` is `display: none`, `data-tree-toggle` is visible in the header, and the right panel takes full width

#### Scenario: ＋ button creates a new entry without opening the drawer
- **WHEN** the user taps `data-new-entry` at viewport 393px
- **THEN** the right panel transitions to the new-entry form state directly; no drawer is opened

#### Scenario: Desktop layout unchanged
- **WHEN** PrivateView renders at viewport 1280px
- **THEN** the inline tree renders as today; no `☰` or mobile-only `＋` button is present

