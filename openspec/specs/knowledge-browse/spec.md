## Purpose

Defines the read-only knowledge browser at `/wiki`: GET /api/wiki/tree backend endpoint plus the WikiView Vue page (two-column desktop layout with TreeNav-style domain tree + content viewer; mobile drawer variant of the tree at md-).
## Requirements
### Requirement: GET /api/wiki/tree — domain tree with file entries
The system SHALL implement `GET /api/wiki/tree` in `backend/app/routes/wiki.py`. The endpoint MUST scroll the Qdrant `knowledge` collection (no vector query, payload-only) to collect all unique `source_file_id` values grouped by `domain`. It MUST then JOIN with the SQLite `files` table to fetch `title`, `orig_name`, `filename`, `chunk_count`, `created_at` for each file. It SHALL return a JSON object mapping each domain to a list of file entry objects. Domains with no files SHALL be omitted from the response. No `user_id` filter SHALL be applied — `knowledge` is a shared collection.

Each entry object SHALL contain: `file_id`, `title` (nullable), `orig_name`, `filename` (nullable), `chunk_count`, `domain`, `created_at`.

#### Scenario: Returns entries grouped by domain
- **WHEN** three files have been ingested — two with domain "退休规划" and one with domain "税务策略"
- **THEN** `GET /api/wiki/tree` returns `{"退休规划": [{...}, {...}], "税务策略": [{...}]}`

#### Scenario: Empty collection returns empty object
- **WHEN** no files have been ingested
- **THEN** `GET /api/wiki/tree` returns HTTP 200 with `{}`

#### Scenario: Multi-chunk file appears as one entry
- **WHEN** a single PDF is ingested and produces 15 chunks in Qdrant
- **THEN** the tree contains exactly one entry for that file under its domain

### Requirement: GET /api/wiki — filtered flat file list
The system SHALL implement `GET /api/wiki` in `backend/app/routes/wiki.py`. It MUST accept an optional `domain` query parameter. When `domain` is provided, it SHALL return only entries from that domain. When omitted, it SHALL return all entries across all domains. The response format is a JSON array of entry objects (same shape as the entries in `/api/wiki/tree`), ordered by `created_at DESC`.

#### Scenario: Filter by domain returns matching entries
- **WHEN** `GET /api/wiki?domain=退休规划` is called and two files exist with that domain
- **THEN** the response is a JSON array with exactly those two entries

#### Scenario: No filter returns all entries
- **WHEN** `GET /api/wiki` is called with no query parameters
- **THEN** the response contains entries from all domains

### Requirement: GET /api/wiki/{file_id} — single entry metadata
The system SHALL implement `GET /api/wiki/{file_id}` in `backend/app/routes/wiki.py`. It MUST look up the file in the SQLite `files` table by `file_id`. It SHALL return the entry object with an additional `chunk_count` field from the `files` table. Returns HTTP 404 with `{"error": "entry not found"}` if the file_id does not exist.

#### Scenario: Existing entry returns metadata
- **WHEN** `GET /api/wiki/<file_id>` is called for a valid file
- **THEN** HTTP 200 with `{file_id, title, orig_name, filename, domain, chunk_count, created_at, source_url, source_type}`

#### Scenario: Unknown file_id returns 404
- **WHEN** `GET /api/wiki/non-existent-id` is called
- **THEN** HTTP 404 with `{"error": "entry not found"}`

### Requirement: QdrantService.get_tree — scroll-based domain grouping
The system SHALL add a `get_tree() -> dict[str, list[str]]` method to `QdrantService` in `backend/app/services/qdrant_service.py`. It MUST scroll the `knowledge` collection using Qdrant's scroll API (no vector, with payload), collecting all unique `(domain, source_file_id)` pairs. It SHALL return a dict mapping domain strings to lists of `source_file_id` strings. The scroll MUST use pagination (limit per page) to handle large collections without loading all points into memory at once.

#### Scenario: Returns correct domain-to-file-id mapping
- **WHEN** the knowledge collection contains 30 chunks from 3 files across 2 domains
- **THEN** `get_tree()` returns a dict with 2 keys, each containing the correct source_file_ids

### Requirement: Pinia wiki store
The system SHALL provide `frontend/src/stores/wiki.js` as a Pinia store. It MUST expose: `tree` (ref, raw API response from `/api/wiki/tree`), `selectedFileId` (ref, nullable string), `searchQuery` (ref, string), `filteredTree` (computed) which filters `tree` entries client-side by matching `searchQuery` (case-insensitive) against `title || orig_name`. It MUST expose a `fetchTree()` action that calls `GET /api/wiki/tree` and populates `tree`. `selectFile(file_id)` action SHALL set `selectedFileId`.

#### Scenario: filteredTree excludes non-matching entries
- **WHEN** `searchQuery` is set to "Roth" and one entry has title "Roth IRA详解" and another has title "社保介绍"
- **THEN** `filteredTree` contains only the "Roth IRA详解" entry

#### Scenario: Empty searchQuery returns all entries
- **WHEN** `searchQuery` is empty string
- **THEN** `filteredTree` equals `tree` (no entries filtered out)

### Requirement: WikiView layout — two-column browser mirroring IngestView
The system SHALL replace the `WikiView.vue` stub with a two-column layout identical in structure to `IngestView.vue`: a fixed left sidebar (≈200px) and a right panel that occupies the remaining width. The overall page structure, header treatment, sidebar section header style, and list item active/hover styles SHALL follow the patterns in `docs/design/notion.md`. The `rightPanelState` ref SHALL have exactly two values: `'welcome'` (default on mount) and `'content'` (file selected). There is no domain-info state and no form state — this page is read-only.

#### Scenario: Default state is welcome
- **WHEN** `WikiView` mounts with no prior selection
- **THEN** `rightPanelState` equals `'welcome'` and a welcome placeholder is shown in the right panel

### Requirement: WikiView left sidebar — search input and collapsible domain groups
The system SHALL render a persistent left sidebar inside `WikiView.vue`. The sidebar SHALL have a search input at the top, bound to `store.searchQuery`, with placeholder "搜索知识条目…". Below the search input, the sidebar SHALL display all domains that have at least one matching file as collapsible groups, sourced from `store.filteredTree`. Each group SHALL show: a chevron icon (rotated when expanded), the domain name as bold text, and a file count badge. Clicking the chevron toggles the group open/closed. Under an expanded group, the sidebar SHALL list the `title` (or `orig_name` if `title` is null) of every matching file entry as a clickable item. Clicking a file title SHALL call `store.selectFile(file_id)` and set `rightPanelState` to `'content'`. The selected file title SHALL be highlighted with the active list-item style from `docs/design/notion.md`.

#### Scenario: Domains with files are visible on mount
- **WHEN** `WikiView` mounts and the tree has files in 3 domains
- **THEN** all 3 domain groups are visible in the sidebar

#### Scenario: Expanding a domain shows file titles
- **WHEN** the user clicks the chevron next to a domain
- **THEN** file titles appear below the domain name

#### Scenario: Search filters entries across all domains
- **WHEN** the user types "Roth" in the search input
- **THEN** only entries whose title or orig_name contains "Roth" (case-insensitive) are shown; domains with no matching entries are hidden from the sidebar

#### Scenario: Clearing search restores full tree
- **WHEN** the user clears the search input
- **THEN** all domains and entries are shown again

#### Scenario: Clicking a file title loads content in right panel
- **WHEN** the user clicks a file title in the sidebar
- **THEN** `selectedFileId` is set, the title is highlighted, and `rightPanelState` becomes `'content'`

#### Scenario: Domains without files are not shown
- **WHEN** a domain has no ingested files
- **THEN** it does not appear in the sidebar

### Requirement: WikiView right panel — content viewer
When `rightPanelState === 'content'`, the right panel SHALL display a fixed header bar (following `docs/design/notion.md` right-panel pattern: bg-canvas with hairline bottom border) showing the entry title (or orig_name) and a domain badge, followed by a scrollable content area. The content area SHALL fetch and render the file content via the `useFileContent` composable (`load(file_id, filename)`). Files with no stored `filename` SHALL show a "无原始文件可预览" placeholder without making a network request. A "下载原文" button in the header SHALL link to `GET /api/files/{file_id}/download` as a download attachment.

#### Scenario: Content loads when file is selected
- **WHEN** a file with a stored filename is selected
- **THEN** the right panel shows the title header and fetches content via useFileContent

#### Scenario: No-filename entry shows placeholder
- **WHEN** a selected file has no stored filename
- **THEN** "无原始文件可预览" is shown and no content fetch is made

#### Scenario: Download button triggers file download
- **WHEN** the user clicks "下载原文"
- **THEN** the browser navigates to `/api/files/{file_id}/download` triggering an attachment download

### Requirement: WikiView renders TreeNav as drawer below md
Below the `md` breakpoint (768px), `WikiView.vue` SHALL hide the inline left TreeNav and expose it via a `☰` button (`data-tree-toggle`) in the page header. Tapping `☰` opens a full-width slide-in drawer with the TreeNav. Selecting a domain or file in the drawer SHALL close the drawer and load that content into the right panel. The right panel SHALL render at full viewport width below `md`.

#### Scenario: Phone viewport hides inline tree
- **WHEN** WikiView renders at viewport 393px
- **THEN** `data-tree-inline` is `display: none`, `data-tree-toggle` is visible in the header, and the article/welcome content takes full width

#### Scenario: Drawer selection loads file content
- **WHEN** the user opens the drawer and taps a file entry
- **THEN** the drawer closes and the right panel renders that file's markdown content at full width

#### Scenario: Desktop layout unchanged
- **WHEN** WikiView renders at viewport 1280px
- **THEN** the inline tree renders as today; no `☰` button is present

