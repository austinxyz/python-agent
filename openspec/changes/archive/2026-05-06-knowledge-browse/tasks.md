## 1. QdrantService — get_tree method

- [x] 1.1 RED — write failing pytest test for `QdrantService.get_tree()`: mock Qdrant scroll to return points with known `(domain, source_file_id)` pairs; assert returned dict maps domains to correct file_id lists; verify deduplication (same file_id from multiple chunks appears once)
- [x] 1.2 GREEN — implement `get_tree() -> dict[str, list[str]]` in `backend/app/services/qdrant_service.py` using paginated Qdrant scroll (no vector, payload only); collect unique `(domain, source_file_id)` pairs; add TODO comment re: SQLite materialized view for large collections
- [x] 1.3 Run `cd backend && pytest` — all tests green
- [x] 1.4 Run superpowers:requesting-code-review on group 1 diff; address CRITICAL/HIGH findings before moving on

## 2. Backend wiki routes

- [x] 2.1 RED — write failing pytest tests for `GET /api/wiki/tree`: (a) empty collection → `{}`; (b) files across 2 domains → correct grouping; (c) 15 chunks from 1 file → 1 entry (dedup); mock QdrantService.get_tree and DatabaseService
- [x] 2.2 GREEN — implement `GET /api/wiki/tree` in `backend/app/routes/wiki.py`: call `QdrantService().get_tree()`, JOIN with SQLite `files` table for each file_id to fetch `title`, `orig_name`, `filename`, `chunk_count`, `created_at`; return `{domain: [entry_objects]}`
- [x] 2.3 RED — write failing pytest tests for `GET /api/wiki?domain=X`: (a) with domain filter → only matching entries; (b) no filter → all entries; (c) unknown domain → `[]`
- [x] 2.4 GREEN — implement `GET /api/wiki` with optional `domain` query parameter; return flat array ordered by `created_at DESC`
- [x] 2.5 RED — write failing pytest tests for `GET /api/wiki/{file_id}`: (a) valid file_id → 200 with full metadata; (b) unknown id → 404 `{"error": "entry not found"}`
- [x] 2.6 GREEN — implement `GET /api/wiki/{file_id}` querying SQLite `files` table by primary key
- [x] 2.7 Run `cd backend && pytest` — all tests green
- [x] 2.8 Run superpowers:requesting-code-review on group 2 diff; address CRITICAL/HIGH findings before moving on

## 3. Pinia wiki store

- [x] 3.1 RED — write failing vitest tests for `wiki.js` store: (a) `fetchTree()` calls `GET /api/wiki/tree` and populates `tree`; (b) `filteredTree` filters entries by `searchQuery` (case-insensitive, matches title or orig_name); (c) empty searchQuery returns all entries; (d) `selectFile(id)` updates `selectedFileId`
- [x] 3.2 GREEN — implement `frontend/src/stores/wiki.js` with `tree`, `selectedFileId`, `searchQuery` refs; `filteredTree` computed; `fetchTree()` and `selectFile()` actions
- [x] 3.3 Run `cd frontend && npm test` — all tests green
- [x] 3.4 Run superpowers:requesting-code-review on group 3 diff; address CRITICAL/HIGH findings before moving on

## 4. WikiView component

- [x] 4.1 RED — write failing vitest tests for `WikiView.vue`: (a) mounts in welcome state; (b) domain groups visible after fetchTree (domains without files are hidden); (c) chevron toggles domain expand/collapse; (d) search input bound to store.searchQuery — typing filters visible entries and hides empty domains; (e) clearing search restores full tree; (f) clicking file title calls selectFile and transitions to `'content'` state; (g) selected title has active highlight class; (h) content panel renders useFileContent output; (i) no-filename entry shows "无原始文件可预览"; (j) download button href is `/api/files/{id}/download`
- [x] 4.2 GREEN — implement `WikiView.vue` mirroring IngestView two-column pattern: left sidebar with search input (placeholder "搜索知识条目…") + collapsible domain groups (chevron + domain name + badge + file title list); `rightPanelState` with `'welcome'` / `'content'` only; right panel fixed header (gradient, title, domain badge, download button) + scrollable content area via `useFileContent`
- [x] 4.3 Apply UI design system from `docs/frontend-ui-guide.md`: page header gradient, sidebar section header, right-panel fixed header + scrollable body pattern, active/hover list item styles, domain badge pill
- [x] 4.4 Run `cd frontend && npm test` — all tests green
- [x] 4.5 Run superpowers:requesting-code-review on group 4 diff; address CRITICAL/HIGH findings before moving on

## 5. Integration verification and completion

- [x] 5.1 Run `cd backend && pytest` — full backend suite green
- [x] 5.2 Run `cd frontend && npm test` — full frontend suite green
- [x] 5.3 Manual smoke test via Docker: ingest 2 PDFs with different domains → navigate to `/wiki` → both domains appear → click entry → content renders → download button works
- [x] 5.4 Verify no `user_id` filter is applied in wiki routes (knowledge collection is shared — adding user_id filter would be a bug)
- [x] 5.5 Update `docs/log/YYYY-MM-DD.md` with commit hash, features, test count, and any code review findings
- [x] 5.6 Run superpowers:requesting-code-review on full change diff; address all CRITICAL/HIGH findings
