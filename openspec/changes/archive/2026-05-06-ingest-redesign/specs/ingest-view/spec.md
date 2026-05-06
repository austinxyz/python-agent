## REMOVED Requirements

### Requirement: IngestView two-tab layout
**Reason**: Replaced by a unified left-right knowledge browser (see ADDED below). Two tabs forced users to switch context between browsing and ingesting.
**Migration**: All ingest and file-browsing functionality is now in a single page with a persistent left sidebar.

### Requirement: Destination toggle
**Reason**: V1 ingest always targets the `knowledge` collection. The toggle added UI complexity with no immediate value.
**Migration**: The `destination` field is removed from the frontend form. The backend continues to accept it; callers may still POST `destination=knowledge` explicitly.

### Requirement: Domain and topic fields
**Reason**: Free-text domain entry produced inconsistent taxonomy. Topic was unused in practice. Replaced by a predefined domain list (selected before opening the form) and a user-provided title field.
**Migration**: The ingest form now shows a locked domain badge (pre-selected from the sidebar) and a `title` field. The `topic` form field is removed.

### Requirement: Real-time progress list
**Reason**: The bottom-of-form progress list is replaced by an inline result state in the right panel (State 3). The list style conflicted with the new single-context right panel design.
**Migration**: After submitting the form, the right panel transitions to the result state, which polls for completion inline.

### Requirement: Uploaded Files tab with TreeNav
**Reason**: The separate tab is eliminated; file browsing is now persistent in the left sidebar domain tree.
**Migration**: Files are always visible in the left sidebar, grouped by domain.

### Requirement: File list item display
**Reason**: Replaced by the left sidebar file titles and the content viewer right-panel state.
**Migration**: File metadata (domain, chunk count, date) is shown in the content viewer header when a file is selected.

### Requirement: Clickable file names open inline viewer modal
**Reason**: The FileViewer modal is replaced by an inline content viewer as a right-panel state.
**Migration**: Clicking a file title in the left sidebar loads content directly in the right panel (no overlay).

### Requirement: FileViewer component
**Reason**: The modal pattern is retired. Content rendering logic is extracted to `useFileContent.js` composable and consumed inline.
**Migration**: Remove `FileViewer.vue` import from `IngestView.vue`. Content rendering available via `useFileContent` composable.

---

## ADDED Requirements

### Requirement: DOMAINS constant
The system SHALL define a hardcoded ordered list of domain names in `frontend/src/constants/domains.js` exported as `DOMAINS`. The list SHALL be: `['退休规划', '账户类型', '税务策略', '投资品种', '保险规划', '股权激励', '家庭财务', '中美对比', '遗产规划', '其他']`. `'其他'` SHALL always be last and serves as the default catch-all domain.

#### Scenario: DOMAINS exports the full list
- **WHEN** `import { DOMAINS } from '@/constants/domains.js'` is evaluated
- **THEN** `DOMAINS` is an array of exactly 10 strings with `'其他'` as the last element

### Requirement: Left sidebar domain tree
The system SHALL render a persistent left sidebar (≈200px wide) inside `IngestView.vue`. The sidebar SHALL display all 10 DOMAINS as collapsible groups. Each group SHALL show: a chevron icon (▾ expanded / ▸ collapsed), the domain name as a clickable element, and a file count badge (hidden when zero). Under an expanded group, the sidebar SHALL list the `title` (or `orig_name` if `title` is null) of every file in that domain, each as a clickable element. The chevron and domain name MUST be separate click targets.

#### Scenario: All domains are visible on mount
- **WHEN** `IngestView` mounts
- **THEN** all 10 domain names are rendered in the left sidebar

#### Scenario: Expanding a domain shows file titles
- **WHEN** the user clicks the ▸ chevron next to a domain that has files
- **THEN** file titles appear below the domain name

#### Scenario: Collapsing a domain hides file titles
- **WHEN** the user clicks the ▾ chevron next to an expanded domain
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
When `rightPanelState === 'domain'`, the right panel SHALL display: the selected domain name as heading, file count ("N 篇"), a description placeholder ("暂无描述"), a list of file titles in that domain, and a "+ 新建摄入" button. Clicking "+ 新建摄入" SHALL set `rightPanelState` to `'form'` and lock the selected domain into the ingest form.

#### Scenario: Domain info shows file count
- **WHEN** a domain with 3 files is selected
- **THEN** the right panel shows "3 篇" and lists all 3 file titles

#### Scenario: New ingest button transitions to form
- **WHEN** user clicks "+ 新建摄入" on the domain info page
- **THEN** `rightPanelState` becomes `'form'` with `selectedDomain` set to the current domain

### Requirement: Ingest form state (right panel)
When `rightPanelState === 'form'`, the right panel SHALL display the ingest form. The form SHALL contain: a back arrow that returns to `'domain'` state, a read-only domain badge showing `selectedDomain`, a required `title` text input (placeholder: "为这篇内容取个标题…"), a source type toggle with three options (URL / 文件 / 文本, default: URL), the appropriate content input for the selected source type, and an "开始摄入" submit button. The `destination` field SHALL be hardcoded to `'knowledge'` and NOT shown in the UI. No topic field SHALL be present.

The form SHALL validate: `title` is non-empty AND at least one content source is provided. Invalid submissions SHALL show an inline error; the API SHALL NOT be called.

All submissions SHALL use `multipart/form-data` with fields: `source_type`, `destination='knowledge'`, `domain` (the locked domain), `title`, and one of `file`/`source_url`/`content`.

#### Scenario: Domain badge is read-only
- **WHEN** the form is open for domain "退休规划"
- **THEN** a "退休规划" badge is visible and there is no domain dropdown

#### Scenario: Empty title blocks submission
- **WHEN** user clicks "开始摄入" with no title entered
- **THEN** an error message is shown and no API call is made

#### Scenario: Valid submission sends title in FormData
- **WHEN** user enters title "Roth IRA详解", selects URL, enters a URL, and submits
- **THEN** `POST /api/ingest` is called with FormData where `formData.get('title') === 'Roth IRA详解'` and `formData.get('domain') === '退休规划'`

### Requirement: Ingest result state (right panel)
When `rightPanelState === 'result'`, the right panel SHALL display the ingest result inline. It SHALL show the job label (the submitted title), an animated status indicator while `status === 'running'`, "✓ 摄入完成 · N chunks" on completion, or an error message on failure. Polling SHALL use `store.pollJob(job_id)` at 3-second intervals. On completion, the sidebar file list SHALL be refreshed (call `fetchFiles()` again). A "继续摄入" link SHALL be available that resets to `'form'` state for the same domain.

#### Scenario: Result panel shows running state
- **WHEN** `rightPanelState` transitions to `'result'` immediately after form submission
- **THEN** the job title and an animated indicator are visible

#### Scenario: Sidebar refreshes on completion
- **WHEN** polling returns `status='completed'`
- **THEN** `fetchFiles()` is called and the new file title appears in the left sidebar

### Requirement: Content viewer state (right panel)
When `rightPanelState === 'content'`, the right panel SHALL fetch and display the file content inline using `useFileContent` composable (calls `GET /api/files/{file_id}/content`). The header SHALL show the file title (or `orig_name`), domain badge, source type icon, and date. Content rendering SHALL follow the same rules as the retired `FileViewer.vue`: Markdown files rendered as HTML, all other types wrapped in `<pre>` with HTML escaping.

#### Scenario: Clicking file title loads content
- **WHEN** user clicks a file title in the left sidebar
- **THEN** `rightPanelState` becomes `'content'` and the right panel fetches and renders the file content

#### Scenario: Markdown rendered as HTML
- **WHEN** the selected file has `orig_name` ending in `.md`
- **THEN** the rendered output contains HTML heading elements

### Requirement: useFileContent composable
The system SHALL implement `frontend/src/composables/useFileContent.js`. It SHALL export a `useFileContent()` function returning reactive refs: `loading`, `error`, `renderedContent`. It SHALL expose a `load(fileId, filename)` method that fetches `GET /api/files/{fileId}/content` and populates `renderedContent` using the same `renderContent` / `markdownToHtml` / `escapeHtml` logic previously in `FileViewer.vue`.

#### Scenario: Composable fetches and renders content
- **WHEN** `load(fileId, filename)` is called
- **THEN** `loading` is true during fetch, then `renderedContent` is populated on success

### Requirement: Ingest Pinia store — title in job label
The `addJob(job_id, label)` action is unchanged in signature. When called from the ingest form, `label` SHALL be the user-provided `title` (not `orig_name` or URL). The `pollJob` action is unchanged.

#### Scenario: addJob uses title as label
- **WHEN** user submits with title "Roth IRA详解" and `store.addJob(job_id, 'Roth IRA详解')` is called
- **THEN** the job entry has `label: 'Roth IRA详解'`
