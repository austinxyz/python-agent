## Context

The current `IngestView.vue` implements a two-tab layout: "新建摄入" (new ingest form) and "已上传文件" (uploaded files list with TreeNav). Files are tagged with free-text `domain` and `topic` fields; files are browsed via a modal (`FileViewer.vue`) launched from the files tab.

This design describes how to replace that with a single-page left-right knowledge browser: a persistent domain tree on the left, and a four-state right panel (domain info / ingest form / ingest result / content viewer). The brainstorming mockups are in `docs/superpowers/specs/2026-05-06-ingest-redesign-design.md`.

## Goals / Non-Goals

**Goals:**
- Unified page: browse and ingest in the same view without tab switching
- Predefined domain taxonomy (10 domains) as the primary organising axis
- User-provided `title` displayed in left sidebar instead of raw filename/URL
- Inline content viewer (no modal) integrated as a right-panel state
- Non-breaking DB migration (`ALTER TABLE` adds nullable column)

**Non-Goals:**
- Private destination (`destination="private"` removed from UI; backend unchanged)
- Domain description editing, file deletion, domain reordering
- PDF rendering (content viewer shows extracted text, not the rendered PDF)
- Changes to ingest pipeline logic (`IngestPipeline`, `JobRegistry`, embedding, Qdrant storage)

## Decisions

### 1. Right panel as a state machine, not tabs or routing

**Decision:** A single `rightPanelState` ref in `IngestView.vue` drives which content block renders in the right column: `'welcome' | 'domain' | 'form' | 'result' | 'content'`. No Vue Router sub-routes; no additional tabs.

**Alternatives considered:**
- *Sub-routes (`/ingest/:domain`, `/ingest/new`)* — adds router complexity, breaks back-button expectations for an in-page interaction
- *Two-column with tabs inside right panel* — user explicitly rejected; the goal is one clear context at a time

**Rationale:** The five states are sequential in the user's mental model (browse domain → decide to add → fill form → see result → browse another file). A simple ref is easier to test and reason about than router state.

### 2. Predefined domain list as a JS constant (not API-driven)

**Decision:** `frontend/src/constants/domains.js` exports `DOMAINS` as a hardcoded array. The backend continues to store whatever string is sent as `domain`; no backend validation against the list.

**Alternatives considered:**
- *`GET /api/domains` endpoint* — over-engineered for V1; domain list changes infrequently and only by developer intent
- *Read domains from distinct values in `GET /api/files`* — would omit empty domains, making the UX inconsistent when a domain has no files yet

**Rationale:** Hardcoded constant is the simplest mechanism that satisfies "configurable by developer". It can be promoted to a DB table + API in V2 without changing the frontend contract (the value sent to the backend is already a plain string).

### 3. `title` stored as a new nullable column, not repurposing `topic`

**Decision:** `ALTER TABLE files ADD COLUMN title TEXT` (nullable). Left sidebar displays `file.title ?? file.orig_name`.

**Alternatives considered:**
- *Repurpose `topic` for title* — semantically wrong; `topic` has existing meaning in Qdrant payloads; risks confusing historical data
- *Store title in `orig_name`* — `orig_name` is set by the pipeline to the actual filename/URL; overwriting it loses provenance

**Rationale:** A dedicated `title` column is unambiguous and non-breaking. Existing rows have `title = NULL` and gracefully fall back to `orig_name`.

### 4. FileViewer.vue retired; content rendering inlined

**Decision:** `FileViewer.vue` modal is no longer used. Its `renderContent` / `markdownToHtml` / `escapeHtml` functions are extracted to `frontend/src/composables/useFileContent.js` and consumed by `IngestView.vue`'s content-viewer state.

**Alternatives considered:**
- *Keep `FileViewer.vue` and mount it inside the right panel instead of as a modal* — works, but the component's fixed-overlay CSS would need fighting; simpler to extract the logic
- *Use a full Markdown library (e.g., `marked`)* — adds a dependency for functionality already covered by the existing regex parser; not needed in V1

**Rationale:** The content-rendering logic is ~30 lines; extracting it to a composable keeps `IngestView.vue` readable without adding a new npm dependency.

### 5. Domain tree built in IngestView, not extending TreeNav

**Decision:** The left sidebar domain tree is implemented directly in `IngestView.vue` (expand/collapse state per domain, click handlers). `TreeNav.vue` is not extended or reused here.

**Alternatives considered:**
- *Extend `TreeNav.vue` with chevron+click-domain semantics* — `TreeNav.vue` is also used by `WikiView.vue`; adding ingest-specific click semantics risks breaking the wiki tree or creating a confusing API
- *New `DomainTree.vue` component* — valid, but the tree is simple enough (~50 lines of template) that a component boundary adds overhead without clarity benefit

**Rationale:** The tree logic (10 domains, expand/collapse, two click targets per row) is simple and ingest-specific. Keeping it in `IngestView.vue` avoids polluting the shared `TreeNav` contract.

## Risks / Trade-offs

- **SQLite migration on container start** — `ALTER TABLE files ADD COLUMN title TEXT` must run before the Flask app serves requests. Risk: if the app starts before migration completes (race condition in Docker Compose). Mitigation: run migration in `DatabaseService.__init__` or the Flask `create_app` function using `IF NOT EXISTS`-style check (`PRAGMA table_info` or `ALTER TABLE … IGNORE`).

- **Right panel state lost on page refresh** — `rightPanelState` is a Vue ref; refreshing the page resets to `'welcome'`. This is acceptable for V1 (the page is a tool, not a document), but noted as a limitation.

- **Left sidebar file list staleness** — files are fetched once on mount. After a successful ingest (State 3 → result), the sidebar must re-fetch to show the new title. Mitigation: call `fetchFiles()` again in the result handler when `status === 'completed'`.

- **`topic` field now orphaned in UI** — historical files have a non-null `topic` value that is no longer surfaced in the UI. These values remain in SQLite and Qdrant payloads; they just aren't displayed. No data loss; the field is kept for future use.

## Migration Plan

1. Backend: add `_ensure_title_column()` call in `DatabaseService` (runs `ALTER TABLE files ADD COLUMN title TEXT` if column absent — safe to call repeatedly via `PRAGMA table_info` check).
2. Backend: update `FileService.register()` signature and `POST /api/ingest` route to accept `title`.
3. Backend: update `GET /api/files` to include `title` in the response.
4. Frontend: implement new `IngestView.vue` and `useFileContent.js`.
5. Frontend: add `frontend/src/constants/domains.js`.
6. Tests: update backend route tests; rewrite frontend `IngestView` tests.
7. Retire `FileViewer.vue` (keep file, remove import/usage — can delete in a follow-up cleanup).

Rollback: revert frontend files; `title` column is additive and does not affect any existing query.

## Open Questions

*(none — all design decisions resolved through brainstorming session)*
