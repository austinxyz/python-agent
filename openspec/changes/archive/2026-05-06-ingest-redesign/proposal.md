## Why

The current `/ingest` page splits "new ingest" and "uploaded files" into two separate tabs (UI-08), making it impossible to browse existing knowledge and add new content in the same mental context. Users must also manually type free-text domain and topic labels, with no guidance on the taxonomy that actually organises the knowledge base. The page is optimised for the act of uploading rather than for managing a growing personal knowledge library.

## What Changes

- **Remove** the two-tab layout; replace with a single left-right knowledge browser
- **Add** a persistent domain tree on the left (collapsible groups with file counts and file titles)
- **Add** predefined domain list (`退休规划`, `账户类型`, `税务策略`, `投资品种`, `保险规划`, `股权激励`, `家庭财务`, `中美对比`, `遗产规划`, `其他`) — no free-text entry
- **Add** user-provided `title` field on the ingest form; title is the label displayed in the sidebar
- **Remove** destination toggle (V1 ingest always targets `knowledge`)
- **Remove** topic free-text field (domain alone is sufficient for V1 taxonomy)
- **Remove** progress list below the form; result is shown inline in the right panel after submit
- **Change** file content viewer from a modal (`FileViewer.vue`) to an inline right-panel state
- **Add** domain info page as a right-panel state: shows file count, description placeholder, and "+ 新建摄入" button
- **Add** `title` column to SQLite `files` table; `POST /api/ingest` and `GET /api/files` updated accordingly

## Capabilities

### New Capabilities

*(none — all changes are modifications to existing capabilities)*

### Modified Capabilities

- `ingest-view`: Complete redesign of `IngestView.vue`. Replaces UI-08, UI-09, UI-11, UI-12, UI-13 with a unified left-right knowledge browser. Right panel has four states: domain info, ingest form, ingest result, content viewer.
- `ingest-api`: Add optional `title` field to `POST /api/ingest` (stored in `files` table) and include `title` in `GET /api/files` response. Requires `ALTER TABLE files ADD COLUMN title TEXT`.

## Impact

- **Frontend**: `IngestView.vue` fully rewritten; `FileViewer.vue` retired as modal (content rendering logic inlined); `stores/ingest.js` minor update; new `frontend/src/constants/domains.js`
- **Backend**: `POST /api/ingest` and `GET /api/files` accept/return `title`; `FileService.register()` gains `title` parameter; `backend/db/schema.sql` adds `title` column
- **Database**: Non-breaking `ALTER TABLE` migration (nullable column); existing rows display `orig_name` as fallback
- **Tests**: Frontend vitest tests for `IngestView.vue` and `ingest` store updated; backend pytest tests for ingest routes updated
- **No breaking API changes** for other consumers; `title` is optional in POST, additive in GET response

## Non-Goals

- Domain description editing (placeholder only in V1)
- Deleting files from the UI
- Reordering or configuring domains via the UI (constant in code)
- Private destination in ingest form (always `knowledge` in this redesign)
- Download button in inline content viewer
- MCP source type in ingest form (stub only, unchanged)
