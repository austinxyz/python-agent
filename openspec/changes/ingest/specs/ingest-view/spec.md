## ADDED Requirements

### Requirement: IngestView two-tab layout
The system SHALL implement `frontend/src/views/IngestView.vue` with two tabs: **New Ingest** (➕) and **Uploaded Files** (🗂). The active tab SHALL be highlighted. Switching tabs SHALL not trigger a page navigation — tabs are rendered within the same route (`/ingest`).

#### Scenario: Both tabs are visible on the ingest page
- **WHEN** the user navigates to `/ingest`
- **THEN** two tab buttons labelled "➕ 新摄入" and "🗂 已摄入文件" are visible

#### Scenario: Clicking a tab switches the content panel
- **WHEN** the user clicks "🗂 已摄入文件"
- **THEN** the file list panel is shown and the new-ingest panel is hidden

### Requirement: Destination toggle
The **New Ingest** tab SHALL include a destination toggle with two options: **公共知识库** (knowledge) and **私有数据** (private). The selected destination SHALL be stored in the `ingest` Pinia store and included in the `POST /api/ingest` request body. The toggle SHALL default to `"knowledge"` on page load.

#### Scenario: Default destination is knowledge
- **WHEN** IngestView is mounted for the first time
- **THEN** the destination toggle shows "公共知识库" as selected

#### Scenario: Toggling destination updates store
- **WHEN** the user clicks "私有数据"
- **THEN** `useIngestStore().destination` equals `"private"`

### Requirement: File drag-and-drop upload input
The **New Ingest** tab SHALL include a drag-and-drop upload zone that accepts file drops and click-to-browse. Accepted MIME types: `application/pdf`, `text/plain`, `text/markdown`. The zone SHALL display the selected filename after a file is chosen. Only one file at a time is accepted.

#### Scenario: Dropped PDF is accepted
- **WHEN** a PDF file is dropped onto the upload zone
- **THEN** the filename is displayed and the file is stored in the component's local state

#### Scenario: Multiple files are rejected
- **WHEN** multiple files are dropped simultaneously
- **THEN** only the first file is accepted and a warning message is shown

### Requirement: URL and text input modes
The **New Ingest** tab SHALL provide two additional input modes selectable via sub-tabs or radio buttons: **URL** (a text input for a single URL) and **Text** (a `<textarea>` for pasting raw content). Exactly one input mode (File / URL / Text) SHALL be active at a time.

#### Scenario: URL mode shows URL input
- **WHEN** the user selects "URL" input mode
- **THEN** a text input placeholder "https://..." is visible and the file drop zone is hidden

#### Scenario: Text mode shows textarea
- **WHEN** the user selects "Text" input mode
- **THEN** a `<textarea>` is visible and the file drop zone is hidden

### Requirement: Domain and topic fields
The **New Ingest** tab SHALL include two optional text fields: **领域** (domain) and **主题** (topic). Their values SHALL be included in the `POST /api/ingest` request. Fields MAY be empty — the pipeline accepts empty strings.

#### Scenario: Domain and topic are submitted with the form
- **WHEN** the user fills in domain "finance" and topic "Roth IRA" and submits
- **THEN** the POST request body contains `domain="finance"` and `topic="Roth IRA"`

### Requirement: Submit button and validation
The **New Ingest** tab SHALL include a **开始摄入** (Start Ingest) submit button. Before calling `POST /api/ingest`, the frontend SHALL validate that an input is provided (a file is selected, or a URL is entered, or text is non-empty). Invalid submissions SHALL show an inline error message; the API SHALL NOT be called.

#### Scenario: Empty submission shows error without API call
- **WHEN** the user clicks "开始摄入" with no file, URL, or text
- **THEN** an error message "请提供摄入内容" is shown and no API call is made

### Requirement: Real-time progress list
The **New Ingest** tab SHALL display a progress list below the form showing all in-progress and recently completed ingest jobs in the current session. Each list item SHALL show: filename/URL/text excerpt, current status (running / completed / error), and chunk count (once completed). The frontend SHALL poll `GET /api/ingest/status/{job_id}` every 2 seconds while status is `"running"`. Polling SHALL stop when status becomes `"completed"` or `"error"`.

#### Scenario: Submitted job appears in progress list immediately
- **WHEN** the user submits a file and receives a `job_id`
- **THEN** a new row appears in the progress list with status "running" within 500 ms

#### Scenario: Completed job shows chunk count
- **WHEN** the polling response returns `status="completed"` with `chunk_count=12`
- **THEN** the row updates to show "✓ completed · 12 chunks" and polling stops

#### Scenario: Error job shows error status
- **WHEN** the polling response returns `status="error"`
- **THEN** the row shows "✗ error" and polling stops

### Requirement: Uploaded Files tab with TreeNav
The **Uploaded Files** tab SHALL display a two-column layout: left column shows a `TreeNav.vue` component rendering the `domain → topic` hierarchy of all ingested files; right column shows the file list for the selected tree node. The file list MUST be populated by `GET /api/files` (stub in V1; real data when files-api is implemented). If no tree node is selected, the right column shows all files.

The `TreeNav.vue` component SHALL be reused as-is from `frontend/src/components/tree-nav/TreeNav.vue` — no duplication of tree logic is permitted.

#### Scenario: TreeNav renders domain → topic hierarchy
- **WHEN** files with `domain="finance"`, `topic="Roth IRA"` and `domain="finance"`, `topic="401k"` are loaded
- **THEN** TreeNav shows a "finance" parent node with "Roth IRA" and "401k" children

#### Scenario: Selecting a tree node filters the file list
- **WHEN** the user clicks "Roth IRA" in the tree
- **THEN** only files with `domain="finance"` and `topic="Roth IRA"` are shown in the right panel

### Requirement: File list item display
Each file in the Uploaded Files tab SHALL display: source icon (📄 file / 🔗 URL / 📝 text), original filename or URL, file size (human-readable), ingest date, chunk count, and domain/topic labels. Each item SHALL include action buttons: **👁 查看** (view raw file) and **🗑 删除** (delete, V1 stub returning a not-implemented toast).

#### Scenario: File list items show correct metadata
- **WHEN** a file with `orig_name="budget.pdf"`, `size_bytes=204800`, `chunk_count=8` is displayed
- **THEN** the row shows the filename, "200 KB", and "8 chunks"

### Requirement: Ingest Pinia store
The system SHALL update `frontend/src/stores/ingest.js` with the following state and actions:
- `state`: `{ destination: "knowledge", jobs: [] }`
- `jobs`: array of `{ job_id, label, status, chunk_count | null, error | null }`
- `actions`: `setDestination(dest)`, `addJob(job_id, label)`, `updateJob(job_id, patch)`, `fetchJobStatus(job_id)` (calls the polling API)

#### Scenario: addJob appends a running job
- **WHEN** `useIngestStore().addJob("abc", "budget.pdf")` is called
- **THEN** `store.jobs` contains `{ job_id: "abc", label: "budget.pdf", status: "running", chunk_count: null, error: null }`
