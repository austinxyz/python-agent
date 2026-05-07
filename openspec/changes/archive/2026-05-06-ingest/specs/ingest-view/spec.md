## ADDED Requirements

### Requirement: IngestView two-tab layout
The system SHALL implement `frontend/src/views/IngestView.vue` with two tabs: **新建摄入** (New Ingest) and **已上传文件** (Uploaded Files). The active tab SHALL be highlighted with `bg-primary` styling. Switching tabs SHALL not trigger a page navigation — tabs are rendered within the same route (`/ingest`). The two content panels SHALL be toggled via `:hidden` attribute (not `v-show`) so test runners using happy-dom can use `isVisible()` correctly.

#### Scenario: Both tabs are visible on the ingest page
- **WHEN** the user navigates to `/ingest`
- **THEN** two tab buttons labelled "新建摄入" and "已上传文件" are visible

#### Scenario: Clicking a tab switches the content panel
- **WHEN** the user clicks "已上传文件"
- **THEN** the file list panel is shown and the new-ingest panel is hidden

### Requirement: Destination toggle
The **New Ingest** tab SHALL include a destination toggle with two options: **公共知识库** (knowledge) and **私有数据** (private). The selected destination SHALL be stored in the `ingest` Pinia store and included in the `POST /api/ingest` FormData payload. The toggle SHALL default to `"knowledge"` on page load. The active button SHALL include the literal CSS class `active` in addition to visual styling so that tests can assert on `data-destination`.

#### Scenario: Default destination is knowledge
- **WHEN** IngestView is mounted for the first time
- **THEN** the destination toggle shows "公共知识库" as selected

#### Scenario: Toggling destination updates store
- **WHEN** the user clicks "私有数据"
- **THEN** `useIngestStore().destination` equals `"private"`

### Requirement: Source inputs — URL, text, and file shown simultaneously
The **New Ingest** tab SHALL display all three input modes simultaneously in a single card: a URL text input (`data-input="source_url"`), a text paste `<textarea>` (`data-input="content"`), and a file upload zone (`data-input="file"`). The frontend determines `source_type` by priority at submit time: if a URL is entered, `source_type="url"`; else if a file is selected, `source_type="file"`; else `source_type="text"`. Only the relevant field is appended to the FormData payload for each submission.

The file upload zone SHALL display the selected filename after a file is chosen or "点击或拖拽文件到此处" otherwise.

#### Scenario: URL input present on page load
- **WHEN** the user navigates to `/ingest`
- **THEN** a URL text input, a textarea, and a file input are all visible in the source inputs card

#### Scenario: source_type priority — URL wins over file
- **WHEN** the user has both a URL entered and a file selected, then submits
- **THEN** the FormData payload has `source_type="url"` and contains `source_url` but not `file`

### Requirement: Domain and topic fields
The **New Ingest** tab SHALL include two optional text fields: **领域** (domain, `data-input="domain"`) and **主题** (topic, `data-input="topic"`). Both default to `"general"`. Their values SHALL be appended to the FormData payload for every submission.

#### Scenario: Domain and topic are submitted with the form
- **WHEN** the user fills in domain "finance" and topic "Roth IRA" and submits
- **THEN** the FormData payload contains `domain="finance"` and `topic="Roth IRA"`

### Requirement: All POST /api/ingest requests use multipart/form-data
Every submission from the New Ingest tab MUST be sent as `multipart/form-data` using the browser `FormData` API via the Pinia store's axios instance. JSON bodies MUST NOT be used. The FormData MUST always include `source_type`, `destination`, `domain`, and `topic` fields, plus one of `file`, `source_url`, or `content` depending on the source type.

#### Scenario: URL submission sends FormData
- **WHEN** the user enters a URL and clicks "开始摄入"
- **THEN** `POST /api/ingest` is called with a `FormData` argument where `formData.get('source_type') === 'url'` and `formData.get('source_url')` equals the entered URL

#### Scenario: File submission sends FormData with file attachment
- **WHEN** the user selects a file and clicks "开始摄入"
- **THEN** `POST /api/ingest` is called with a `FormData` argument where `formData.get('source_type') === 'file'` and `formData.get('file')` is a `File` object

### Requirement: Submit button and validation
The **New Ingest** tab SHALL include a **开始摄入** (Start Ingest) submit button (`data-action="submit"`). Before calling `POST /api/ingest`, the frontend SHALL validate that at least one input is provided (a file is selected, or a URL is non-empty, or text content is non-empty). Invalid submissions SHALL show an inline error message (`.error`); the API SHALL NOT be called. While a submission is in flight, the button SHALL be disabled and labelled "摄入中…"; `isSubmitting` SHALL reset to `false` in the `finally` block.

#### Scenario: Empty submission shows error without API call
- **WHEN** the user clicks "开始摄入" with no file, URL, or text
- **THEN** an error message "请提供摄入内容" is shown and no API call is made

### Requirement: Real-time progress list with polling
The **New Ingest** tab SHALL display a progress list below the submit button showing all jobs added in the current session. Each row (`data-job-row`) SHALL show: the job label (filename / URL / text excerpt), a status badge (running / completed / error), and the chunk count when completed. The Pinia store's `pollJob(job_id)` action SHALL be called immediately after `addJob` on a successful POST; it polls `GET /api/ingest/status/{job_id}` every 3 seconds for up to 60 attempts, stopping when status is `"completed"` or `"error"`.

#### Scenario: Submitted job appears in progress list immediately
- **WHEN** the user submits a file and receives a `job_id`
- **THEN** a new row appears in the progress list with status "running"

#### Scenario: Completed job shows chunk count
- **WHEN** the polling response returns `status="completed"` with `chunk_count=12`
- **THEN** the row updates to show status "completed" and "12 chunks"

#### Scenario: Error job shows error status and stops polling
- **WHEN** the polling response returns `status="error"`
- **THEN** the row shows status "error" and polling stops

### Requirement: Uploaded Files tab — fetch and display
The **Uploaded Files** tab SHALL call `GET /api/files` on mount (via `onMounted`) and again whenever the user switches to this tab (via `watch(activeTab)`). The response array is stored locally in the component as `files`. The tab SHALL display a two-column layout: left column shows `TreeNav.vue` rendering unique domain values as tree nodes; right column shows the file list, filtered by the selected tree node when one is selected. If no tree node is selected, all files are shown.

The `TreeNav.vue` component SHALL be reused from `frontend/src/components/tree-nav/TreeNav.vue`.

#### Scenario: Files loaded on mount
- **WHEN** IngestView mounts
- **THEN** `GET /api/files` is called and the response populates the file list

#### Scenario: Files refreshed on tab switch
- **WHEN** the user switches to the "已上传文件" tab
- **THEN** `GET /api/files` is called again and the file list is refreshed

#### Scenario: Selecting a tree node filters the file list
- **WHEN** the user clicks a domain node in TreeNav
- **THEN** only files matching that domain are shown in the right panel

### Requirement: Clickable file names open inline viewer modal
Each file row in the Uploaded Files tab SHALL render the `orig_name` as a clickable `<button>` that sets `viewingFile` to the selected file object. When `viewingFile` is non-null, the `FileViewer.vue` modal SHALL be rendered. Closing the modal (via the X button or clicking the backdrop) sets `viewingFile` back to `null`.

#### Scenario: Clicking a filename opens FileViewer
- **WHEN** the user clicks a filename in the file list
- **THEN** the `FileViewer` modal is shown with the correct `fileId` and `filename` props

#### Scenario: Closing the modal clears viewingFile
- **WHEN** the user clicks the close button in FileViewer
- **THEN** the modal is removed from the DOM

### Requirement: FileViewer component
The system SHALL implement `frontend/src/components/FileViewer.vue`. It SHALL render as a fixed full-screen backdrop modal. On mount it SHALL fetch `/api/files/{fileId}/content` using the browser `fetch()` API. The response text SHALL be rendered:
- If `filename` ends with `.md` or `.markdown`: render as Markdown HTML using a basic regex-based `markdownToHtml` function (headings, bold, italic, inline code, code blocks, unordered lists, paragraphs)
- Otherwise: wrap in `<pre class="whitespace-pre-wrap ...">` with HTML-escaped content

Loading state SHALL show a spinner; error state SHALL show the error message. Clicking the backdrop (`@click.self`) SHALL emit `close`.

#### Scenario: Loads and renders file content
- **WHEN** FileViewer mounts with `fileId` and `filename`
- **THEN** it fetches `/api/files/<fileId>/content` and displays the returned text

#### Scenario: Markdown file is rendered as HTML
- **WHEN** `filename` ends with `.md`
- **THEN** the rendered output contains HTML elements (e.g., `<h1>`, `<strong>`)

### Requirement: Ingest Pinia store
The system SHALL update `frontend/src/stores/ingest.js` with the following state and actions:
- `state`: `{ destination: "knowledge", jobs: [] }`
- `jobs`: array of `{ job_id, label, status, chunk_count | null, error | null }`
- `actions`:
  - `setDestination(dest)` — updates `destination`
  - `addJob(job_id, label)` — appends `{ job_id, label, status: "running", chunk_count: null, error: null }`
  - `updateJob(job_id, patch)` — merges `patch` into the matching job
  - `fetchJobStatus(job_id)` — calls `GET /api/ingest/status/{job_id}` and calls `updateJob` with the response
  - `pollJob(job_id, intervalMs = 3000, maxAttempts = 60)` — calls `fetchJobStatus` via `setTimeout` loop; stops when status is `"completed"` or `"error"`, or after `maxAttempts` attempts

#### Scenario: addJob appends a running job
- **WHEN** `useIngestStore().addJob("abc", "budget.pdf")` is called
- **THEN** `store.jobs` contains `{ job_id: "abc", label: "budget.pdf", status: "running", chunk_count: null, error: null }`

#### Scenario: pollJob stops on completed status
- **WHEN** `fetchJobStatus` returns `{ status: "completed", chunk_count: 5 }` on the first poll
- **THEN** no further `setTimeout` callbacks are scheduled
