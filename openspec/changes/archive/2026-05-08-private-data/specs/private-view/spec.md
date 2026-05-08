## ADDED Requirements

### Requirement: PrivateView renders two-section layout
The system SHALL replace `frontend/src/views/PrivateView.vue` stub with a full page. The page SHALL have a gradient header (following `docs/frontend-ui-guide.md`). Below the header, the page is divided into two vertical sections: the upper section shows structured template entries, and the lower section shows private notes in a directory tree. The Pinia `private.js` store manages all state.

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

## Revision 2026-05-07 — Two-column directory-driven layout

The original requirements above describe a stacked two-section layout (entries on top, notes on bottom). They are SUPERSEDED by the requirements in this section. Tests written for the original layout are obsolete and replaced by tests under tasks 7.4.x.

### Requirement: PrivateView SHALL use a two-column layout matching IngestView
The page SHALL have a gradient header (blue→purple) followed by a flex row: a fixed-width left sidebar containing the directory tree, and a flex-1 right panel showing one of: `welcome`, `item-view`, `item-edit`, `new-entry`, `new-note`.

#### Scenario: Default state is welcome
- **WHEN** the user navigates to `/private` and no item is selected
- **THEN** the right panel shows the welcome state with hints on creating an entry or a note

### Requirement: Sidebar SHALL render a unified directory tree
The sidebar SHALL display a recursive tree built from `store.combinedTree`. Tree nodes are directories (📁); leaves are items rendered with a kind-discriminating icon (📋 for entries, 📝 for notes). The 6 template default directories (`税务`, `退休账户`, `投资持仓`, `个人基本情况`, `房产资产`, `自由格式`) SHALL be present as top-level nodes at all times, even when empty.

#### Scenario: Empty template directories still appear
- **WHEN** the database has zero entries
- **THEN** the sidebar still shows all 6 template directories as collapsible nodes

#### Scenario: Mixed item types appear under one directory
- **WHEN** an entry and a note both reside in `退休账户`
- **THEN** the sidebar shows both items under that directory, with their respective icons

### Requirement: Pinia store SHALL expose a combinedTree getter
The store SHALL implement a `combinedTree` getter that returns a nested directory→items dict built from the union of `entries` and `notes`. Each item carries a `kind: 'entry' | 'note'` discriminator. The 6 template default directories are seeded as keys even when empty.

### Requirement: Clicking an item SHALL display its content in the right panel
Clicking an item in the sidebar SHALL set `selectedItem` and switch the right panel to `item-view`. Entries render their template fields; notes render their markdown content.

#### Scenario: Entry view shows template fields
- **WHEN** user clicks an entry of template `tax`
- **THEN** the panel shows the title and each tax field's label + value

#### Scenario: Note view shows markdown content
- **WHEN** user clicks a note
- **THEN** the panel shows the title and content with `whitespace-pre-line`

### Requirement: New-entry flow SHALL pre-fill directory from chosen template
Clicking "+ 新建条目" SHALL switch the right panel to the `new-entry` state. The form SHALL show: a template picker (6 options); a directory input (pre-filled with the selected template's `default_directory`, editable); a title input; and the template's fields.

#### Scenario: Directory pre-fills from template
- **WHEN** the user picks the `retirement` template
- **THEN** the directory input value is `退休账户`

#### Scenario: Submitting saves and switches to item-view
- **WHEN** the user fills the form and clicks save
- **THEN** `store.createEntry({template_type, title, directory, content_json})` is called; on success the new item is selected and the right panel switches to `item-view`

### Requirement: New-note flow SHALL accept any directory
Clicking "+ 新建笔记" SHALL switch the right panel to the `new-note` state. The form SHALL show: directory input (free text, e.g., `退休规划/Roth相关`); title input; markdown textarea.

### Requirement: Right panel SHALL provide edit-in-place
When viewing an item, an "编辑" button SHALL switch to `item-edit`. For entries this re-uses the entry form pre-filled with current values; for notes this becomes a textarea. Saving calls `store.updateEntry` or `store.updateNote` with the changed fields.

### Requirement: Items SHALL be deletable from the view panel
A "删除" button on the item-view header SHALL call the appropriate store action after a confirmation dialog. The right panel SHALL return to `welcome` after deletion.
