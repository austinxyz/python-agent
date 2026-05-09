## Purpose

Defines the IngestView (`/ingest`): two-column desktop layout (domain tree + ingest form / file content) plus a mobile drawer variant for the tree at md-. Backed by the ingest-pipeline backend capability.
## Requirements
### Requirement: DOMAINS constant
The system SHALL define a hardcoded ordered list of domain names in `frontend/src/constants/domains.js` exported as `DOMAINS`. The list SHALL be: `['退休规划', '账户类型', '税务策略', '投资品种', '保险规划', '股权激励', '家庭财务', '中美对比', '遗产规划', '其他']`. `'其他'` SHALL always be last and serves as the default catch-all domain. Files whose `domain` value is not in this list are grouped under `'其他'`.

#### Scenario: DOMAINS exports the full list
- **WHEN** `import { DOMAINS } from '@/constants/domains.js'` is evaluated
- **THEN** `DOMAINS` is an array of exactly 10 strings with `'其他'` as the last element

### Requirement: Left sidebar domain tree
The system SHALL render a persistent left sidebar (≈200px wide) inside `IngestView.vue`. The sidebar SHALL display all 10 DOMAINS as collapsible groups. Each group SHALL show: a SVG chevron icon (rotated when expanded), the domain name as a clickable element with bold font, and a file count badge (hidden when zero). Under an expanded group, the sidebar SHALL list the `title` (or `orig_name` if `title` is null) of every file in that domain, each as a clickable element. The chevron and domain name MUST be separate click targets.

#### Scenario: All domains are visible on mount
- **WHEN** `IngestView` mounts
- **THEN** all 10 domain names are rendered in the left sidebar

#### Scenario: Expanding a domain shows file titles
- **WHEN** the user clicks the chevron next to a domain that has files
- **THEN** file titles appear below the domain name

#### Scenario: Collapsing a domain hides file titles
- **WHEN** the user clicks the chevron next to an expanded domain
- **THEN** file titles are hidden

#### Scenario: Empty domain still shows in sidebar
- **WHEN** a domain has no ingested files
- **THEN** the domain is still visible in the sidebar with no file count badge

### Requirement: Right panel state machine
The system SHALL implement a `rightPanelState` ref in `IngestView.vue` with five values: `'welcome'`, `'domain'`, `'form'`, `'result'`, `'content'`. Only the panel matching the current state SHALL be rendered. The right panel SHALL default to `'welcome'` on mount.

#### Scenario: Default state is welcome
- **WHEN** `IngestView` mounts with no prior selection
- **THEN** `rightPanelState` equals `'welcome'` and the welcome placeholder is visible

#### Scenario: State transitions on user actions
- **WHEN** user clicks domain name → `rightPanelState` becomes `'domain'`
- **WHEN** user clicks "+ 新建摄入" on domain page → `rightPanelState` becomes `'form'`
- **WHEN** user successfully submits form → `rightPanelState` becomes `'result'`
- **WHEN** user clicks a file title → `rightPanelState` becomes `'content'`

### Requirement: Domain info state (right panel)
When `rightPanelState === 'domain'`, the right panel SHALL display: the selected domain name as heading, file count ("N 篇"), a description placeholder, a list of file titles in that domain (with inline edit support), and a "+ 新建摄入" button. Clicking "+ 新建摄入" SHALL set `rightPanelState` to `'form'` and lock the selected domain into the ingest form.

#### Scenario: Domain info shows file count
- **WHEN** a domain with 3 files is selected
- **THEN** the right panel shows "3 篇" and lists all 3 file titles

#### Scenario: New ingest button transitions to form
- **WHEN** user clicks "+ 新建摄入" on the domain info page
- **THEN** `rightPanelState` becomes `'form'` with `selectedDomain` set to the current domain

### Requirement: Inline title editing
Each file entry in the domain info panel SHALL render a ✏️ edit button on hover. Clicking it enters edit mode: the title becomes an `<input>` with Save and Cancel buttons. Save SHALL call `PATCH /api/files/<file_id>` with `{ title }` and update the local `files` array immutably. Cancel restores the previous title without a network call.

#### Scenario: Save updates title via PATCH
- **WHEN** the user edits a title and clicks Save
- **THEN** `PATCH /api/files/<file_id>` is called and the sidebar reflects the new title

### Requirement: Ingest form state (right panel)
When `rightPanelState === 'form'`, the right panel SHALL display the ingest form. The form SHALL contain: a back arrow that returns to `'domain'` state, a read-only domain badge showing `selectedDomain`, a required `title` text input (placeholder: "为这篇内容取个标题…"), a source type toggle with three options (URL / 文本 / 文件, default: URL), the appropriate content input for the selected source type, and an "开始摄入" submit button. The text `<textarea>` SHALL have `min-height: 55vh` and `resize-y`. The `destination` field SHALL be hardcoded to `'knowledge'` and NOT shown in the UI. No topic field SHALL be present.

The form SHALL validate: `title` is non-empty. Invalid submissions SHALL show an inline error; the API SHALL NOT be called.

All submissions SHALL use `multipart/form-data` with fields: `source_type`, `destination='knowledge'`, `domain` (the locked domain), `title`, and one of `file`/`source_url`/`content`.

#### Scenario: Domain badge is read-only
- **WHEN** the form is open for domain "退休规划"
- **THEN** a "退休规划" badge is visible and there is no domain dropdown

#### Scenario: Empty title blocks submission
- **WHEN** user clicks "开始摄入" with no title entered
- **THEN** an error message is shown and no API call is made

#### Scenario: Valid submission sends title in FormData
- **WHEN** user enters title "Roth IRA详解", selects URL, enters a URL, and submits
- **THEN** `POST /api/ingest` is called with FormData where `formData.get('title') === 'Roth IRA详解'` and `formData.get('destination') === 'knowledge'`

### Requirement: Ingest result state (right panel)
When `rightPanelState === 'result'`, the right panel SHALL display the ingest result inline. It SHALL show the job label (the submitted title), an animated status indicator while `status === 'running'`, "✓ 摄入完成 · N chunks" on completion, or an error message on failure. Polling SHALL use `store.pollJob(job_id, onComplete)` at 3-second intervals. On completion, the sidebar file list SHALL be refreshed via `fetchFiles()` and `rightPanelState` SHALL transition to `'domain'`. On error, `rightPanelState` SHALL transition back to `'form'` with the error displayed.

#### Scenario: Result panel shows running state
- **WHEN** `rightPanelState` transitions to `'result'` immediately after form submission
- **THEN** the job title and an animated indicator are visible

#### Scenario: Sidebar refreshes on completion
- **WHEN** polling returns `status='completed'`
- **THEN** `fetchFiles()` is called and the new file title appears in the left sidebar

### Requirement: Content viewer state (right panel)
When `rightPanelState === 'content'`, the right panel SHALL display file content inline using the `useFileContent` composable (calls `GET /api/files/{file_id}/content`). Files with no stored `filename` (e.g., legacy text ingestions) SHALL show a "无原始文件可预览" placeholder without making a network request. Content rendering: Markdown files rendered as HTML, all other types wrapped in `<pre>` with HTML escaping.

#### Scenario: Clicking file title loads content
- **WHEN** user clicks a file title in the left sidebar
- **THEN** `rightPanelState` becomes `'content'` and the right panel fetches and renders the file content

#### Scenario: No-filename entry shows placeholder
- **WHEN** the selected file has no stored filename
- **THEN** a "无原始文件可预览" message is shown and no fetch is made

### Requirement: useFileContent composable
The system SHALL implement `frontend/src/composables/useFileContent.js`. It SHALL export a `useFileContent()` function returning reactive refs: `loading`, `error`, `renderedContent`. It SHALL expose a `load(fileId, filename)` method that fetches `GET /api/files/{fileId}/content` and populates `renderedContent` using `renderContent` / `markdownToHtml` / `escapeHtml` logic. `markdownToHtml` MUST call `escapeHtml` on the input before applying regex transforms to prevent XSS.

#### Scenario: Composable fetches and renders content
- **WHEN** `load(fileId, filename)` is called
- **THEN** `loading` is true during fetch, then `renderedContent` is populated on success

### Requirement: Ingest Pinia store — pollJob with onComplete callback
The `pollJob(job_id, onComplete, intervalMs, maxAttempts)` action SHALL accept an optional `onComplete` callback. The callback SHALL be called when the job reaches a terminal state (`completed`, `error`) OR when `maxAttempts` is exhausted (treated as error with message "摄入超时"). The callback is never silently dropped.

#### Scenario: onComplete fires on completion
- **WHEN** polling returns `status='completed'`
- **THEN** `onComplete({ status: 'completed', ... })` is called exactly once

#### Scenario: onComplete fires on timeout
- **WHEN** `maxAttempts` attempts are exhausted with `status='running'`
- **THEN** `onComplete({ status: 'error', error: '摄入超时' })` is called

### Requirement: IngestView renders TreeNav as drawer below md
Below the `md` breakpoint (768px), `IngestView.vue` SHALL hide the inline left TreeNav and instead expose it via a `☰` button (`data-tree-toggle`) in the page header. Tapping the button opens a full-width slide-in drawer containing the TreeNav. Selecting a domain or file in the drawer SHALL close it and update the right-panel state-machine ref. The right panel SHALL render at full viewport width below `md`.

#### Scenario: Phone viewport hides inline tree, shows ☰
- **WHEN** IngestView renders at viewport 393px
- **THEN** the inline tree (`data-tree-inline`) is `display: none`, a `data-tree-toggle` button is visible in the page header, and the right panel takes full width

#### Scenario: Drawer selection updates the right panel
- **WHEN** the user opens the drawer and taps a domain
- **THEN** the drawer closes and the right panel transitions to `domain` state for that domain (state-machine ref unchanged from desktop behavior)

#### Scenario: Desktop layout unchanged
- **WHEN** IngestView renders at viewport 1280px
- **THEN** the inline tree renders as today; no `☰` button is present

