## 1. Backend — SQLite Migration and FileService

- [x] 1.1 RED — write failing pytest test in `backend/tests/test_db_service.py`: calling `DatabaseService()` on a DB without a `title` column adds the column; calling it again on a DB that already has it does not raise
- [x] 1.2 GREEN — add `_ensure_title_column()` to `DatabaseService` using `PRAGMA table_info(files)` check; call it in `__init__`; verify test passes
- [x] 1.3 RED — write failing pytest test in `backend/tests/test_file_service.py`: `FileService().register(..., title="Roth IRA详解")` stores `title` correctly; `register(..., title=None)` stores NULL
- [x] 1.4 GREEN — add `title: str | None = None` parameter to `FileService.register()`; update INSERT statement to include `title`; verify tests pass
- [x] 1.5 Run superpowers:requesting-code-review on the diff for group 1; address CRITICAL/HIGH findings before moving on

## 2. Backend — Ingest Route and Files Route

- [x] 2.1 RED — write failing pytest test in `backend/tests/test_ingest_routes.py`: `POST /api/ingest` with `title="Roth IRA详解"` results in the `files` table row having `title='Roth IRA详解'` (mock pipeline, check DB after job completes synchronously in test)
- [x] 2.2 GREEN — update `ingest_post()` to read `title = request.form.get("title")` and pass it through to `IngestPipeline.run()` and ultimately `FileService.register()`; update `IngestPipeline` to accept and forward `title`; verify test passes
- [x] 2.3 RED — write failing pytest test in `backend/tests/test_files_routes.py`: `GET /api/files` response includes `title` field; file ingested with title returns the title; file ingested without title returns `null`
- [x] 2.4 GREEN — update the `SELECT` in `GET /api/files` route to include `title`; verify test passes
- [x] 2.5 Update `backend/db/schema.sql` to include `title TEXT` in the `files` table definition (for fresh installs)
- [x] 2.6 Run superpowers:requesting-code-review on the diff for group 2; address CRITICAL/HIGH findings before moving on

## 3. Frontend — Constants and Composable

- [x] 3.1 Create `frontend/src/constants/domains.js` exporting `DOMAINS` array with all 10 domain names; `'其他'` last
- [x] 3.2 RED — write failing vitest test in `frontend/tests/constants/domains.test.js`: `DOMAINS` has exactly 10 items; last item is `'其他'`; all items are non-empty strings
- [x] 3.3 GREEN — verify test passes with no changes (constant already written)
- [x] 3.4 RED — write failing vitest test in `frontend/tests/composables/useFileContent.test.js`: calling `load(fileId, 'report.md')` fetches `/api/files/<fileId>/content` and populates `renderedContent` with HTML containing `<h` tags; calling `load(fileId, 'report.txt')` wraps content in `<pre>`
- [x] 3.5 GREEN — create `frontend/src/composables/useFileContent.js` extracting `renderContent`, `markdownToHtml`, `escapeHtml` from `FileViewer.vue`; expose `{ loading, error, renderedContent, load }`; verify tests pass
- [x] 3.6 Run superpowers:requesting-code-review on the diff for group 3; address CRITICAL/HIGH findings before moving on

## 4. Frontend — IngestView Rewrite

- [x] 4.1 RED — write failing vitest test in `frontend/tests/views/IngestView.test.js`: on mount, all 10 domain names from `DOMAINS` are rendered in the sidebar; `rightPanelState` defaults to `'welcome'`
- [x] 4.2 RED — write failing vitest test: clicking a domain name sets `rightPanelState` to `'domain'` and the right panel shows the domain heading and "+ 新建摄入" button; clicking the chevron toggles file list visibility without changing `rightPanelState`
- [x] 4.3 RED — write failing vitest test: clicking "+ 新建摄入" sets `rightPanelState` to `'form'`; form shows domain badge matching the clicked domain; no destination toggle; no topic field
- [x] 4.4 RED — write failing vitest test: submitting form with empty title shows error and does not call `POST /api/ingest`; submitting with title + URL calls `POST /api/ingest` with FormData where `formData.get('title')` equals the entered title and `formData.get('destination') === 'knowledge'`
- [x] 4.5 RED — write failing vitest test: after successful submit, `rightPanelState` becomes `'result'`; result panel shows the submitted title; `store.pollJob` is called; on `status='completed'` the sidebar calls `fetchFiles()` again
- [x] 4.6 RED — write failing vitest test: clicking a file title in the sidebar sets `rightPanelState` to `'content'` and the content panel calls `load(fileId, filename)` from `useFileContent`
- [x] 4.7 GREEN — rewrite `frontend/src/views/IngestView.vue`: left sidebar domain tree (DOMAINS constant, per-domain expand/collapse ref, file titles from `files` ref); right panel with five states driven by `rightPanelState`; ingest form with `title` field, locked domain badge, source type toggle, no topic, `destination='knowledge'`; result state with inline polling; content viewer state using `useFileContent`; verify all RED tests 4.1–4.6 pass
- [x] 4.8 Inspect: `grep -rn "console.log" frontend/src/` — assert zero debug statements
- [x] 4.9 Run superpowers:requesting-code-review on the diff for group 4; address CRITICAL/HIGH findings before moving on

## 5. Cleanup and Verification

- [x] 5.1 Remove `FileViewer.vue` import from `IngestView.vue` (component still exists on disk; leave deletion for a future cleanup commit to avoid breaking potential other importers)
- [x] 5.2 Run `cd backend && pytest` — assert all backend tests pass with exit code 0
- [x] 5.3 Run `cd frontend && npm test` — assert all frontend vitest tests pass with exit code 0
- [ ] 5.4 Run superpowers:verification-before-completion: full test suites; `grep -rn "console.log" frontend/src/` confirm zero; inspect that `GET /api/files` response includes `title` field; confirm no private-collection query is missing `user_id` filter
- [ ] 5.5 Manual smoke test: `docker compose up --build`; open `http://localhost:3000/ingest`; click a domain → verify domain info panel; click "+ 新建摄入" → verify form with domain badge; enter title + URL → submit → verify result panel reaches "摄入完成"; verify new title appears in left sidebar; click the title → verify content viewer loads inline
- [x] 5.6 Run superpowers:requesting-code-review on the complete ingest-redesign diff; address all CRITICAL/HIGH findings
- [ ] 5.7 Commit with `feat: redesign ingest page as left-right knowledge browser with title field`
- [ ] 5.8 Update dev log at `docs/log/2026-05-06.md` with this feature batch
