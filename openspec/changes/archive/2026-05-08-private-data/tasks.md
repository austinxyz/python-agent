## 1. SQLite private tables

- [x] 1.1 RED — write failing pytest test for `_ensure_private_tables()`: assert `private_entries` and `notes` tables exist in a fresh SQLite DB; assert idempotent on second call; assert column names match schema
- [x] 1.2 GREEN — add `_ensure_private_tables()` to `DatabaseService` in `backend/app/services/db_service.py`; add tables to `backend/db/schema.sql`; call from Flask app factory alongside existing `_ensure_*` calls
- [x] 1.3 Run `cd backend && pytest` — all tests green
- [x] 1.4 Run superpowers:requesting-code-review on the diff for group 1; address CRITICAL/HIGH findings before moving on

## 2. Private entries API

- [x] 2.1 RED — write failing pytest tests for `GET /api/private/templates`: assert response is array of 6 objects; assert each has `type`, `label`, `fields`; assert field types are correct
- [x] 2.2 RED — write failing pytest tests for `GET /api/private/entries`: (a) empty DB → `[]`; (b) two entries → ordered by `created_at DESC`; (c) only returns entries for `user_id="default"`
- [x] 2.3 RED — write failing pytest tests for `POST /api/private/entries`: (a) valid payload → 201, row in SQLite, Qdrant upsert called with correct user_id payload; (b) missing `template_type` → 400; (c) missing `title` → 400
- [x] 2.4 RED — write failing pytest tests for `PUT /api/private/entries/{id}`: (a) valid update → 200, Qdrant upsert called again, `updated_at` changed; (b) unknown id → 404
- [x] 2.5 RED — write failing pytest tests for `DELETE /api/private/entries/{id}`: (a) valid id → 200, row gone from SQLite, Qdrant delete called; (b) unknown id → 404
- [x] 2.6 GREEN — implement `backend/app/routes/private.py` blueprint with all 5 entry endpoints; use `EmbeddingService.embed()` + `QdrantService` upsert/delete for Qdrant operations; register blueprint in `app.py`; remove `/api/private` from STUB_ROUTES in `test_app_factory.py`
- [x] 2.7 Run `cd backend && pytest` — all tests green
- [x] 2.8 Run superpowers:requesting-code-review on the diff for group 2; address CRITICAL/HIGH findings before moving on

## 3. Private notes API

- [x] 3.1 RED — write failing pytest tests for `GET /api/private/notes`: (a) empty DB → `{"notes": [], "tree": {}}`; (b) notes in two directories → flat list + correct tree nesting; (c) root notes appear in tree at top level
- [x] 3.2 RED — write failing pytest tests for `POST /api/private/notes`: (a) with title and content → 201, row in SQLite with `user_id="default"`; (b) with `chat_ref` → stored; (c) missing title → 400; (d) notes are NOT upserted to Qdrant (assert Qdrant upsert not called)
- [x] 3.3 RED — write failing pytest tests for `PUT /api/private/notes/{id}`: (a) update content → 200, `updated_at` refreshed; (b) update directory → stored; (c) unknown id → 404
- [x] 3.4 GREEN — add note endpoints to `backend/app/routes/private.py`; implement `_build_tree(notes)` helper to convert flat list + directory paths into nested dict
- [x] 3.5 Run `cd backend && pytest` — all tests green
- [x] 3.6 Run superpowers:requesting-code-review on the diff for group 3; address CRITICAL/HIGH findings before moving on

## 4. Pinia private store

- [x] 4.1 RED — write failing vitest tests for `private.js` store: (a) `fetchTemplates()` calls `GET /api/private/templates` and populates `templates`; (b) `fetchEntries()` populates `entries`; (c) `createEntry()` calls POST and prepends to `entries` immutably (spread, not push); (d) `deleteEntry(id)` calls DELETE and filters `entries` immutably; (e) `updateEntry(id, payload)` calls PUT and replaces the matching entry immutably; (f) `fetchNotes()` populates `notes` and `notesTree`; (g) `createNote()` calls POST and prepends to `notes`
- [x] 4.2 GREEN — implement `frontend/src/stores/private.js` (Pinia options API); ensure all state mutations use spread/filter (immutable pattern); import and use `api` from `../api/index.js`
- [x] 4.3 Run `cd frontend && npm test` — all tests green
- [x] 4.4 Run superpowers:requesting-code-review on the diff for group 4; address CRITICAL/HIGH findings before moving on

## 5. PrivateView component

- [~] 5.1 RED — write failing vitest tests for `PrivateView.vue`: (a) mounts and calls `fetchEntries()` + `fetchNotes()` + `fetchTemplates()` on mount; (b) entry cards visible after fetch; (c) "新建条目" button shows template selector; (d) selecting template renders the correct number of form fields; (e) submitting form calls `store.createEntry()`; (f) clicking "删除" on entry calls `store.deleteEntry(id)` after confirm; (g) notes tree renders directory nodes from `store.notesTree`; (h) clicking note title displays content panel; (i) clicking "编辑" in content panel switches to textarea; (j) saving calls `store.updateNote(id, {content})` _(SUPERSEDED by 7.4.x — old layout obsolete; stub two-section UI never validated in production)_
- [~] 5.2 GREEN — implement `frontend/src/views/PrivateView.vue`: gradient header; upper section — entries list (`data-entry-card`) + new entry flow (`data-new-entry-btn`, `data-template-selector`, `data-entry-form`, `data-save-entry-btn`); lower section — notes tree (`data-notes-tree`, `data-note-item`, `data-note-folder`) + content panel (`data-note-content`, `data-edit-note-btn`, `data-note-textarea`, `data-save-note-btn`); "新建笔记" button (`data-new-note-btn`) _(SUPERSEDED by 7.4.x)_
- [~] 5.3 Apply UI design system from `docs/frontend-ui-guide.md`: section headers, card styles, tree node styles, form styling consistent with IngestView _(rolled into 7.4.3)_
- [x] 5.4 Run `cd frontend && npm test` — all tests green
- [x] 5.5 Run superpowers:requesting-code-review on the diff for group 5; address CRITICAL/HIGH findings before moving on

## 6. Integration verification and completion

- [x] 6.1 Run `cd backend && pytest` — full backend suite green (127 passed)
- [x] 6.2 Run `cd frontend && npm test` — full frontend suite green (89 passed)
- [x] 6.3 Verify user_id isolation: grep all `private` Qdrant query paths; confirm every search and upsert includes `user_id = "default"`; confirm notes API never queries Qdrant
- [~] 6.4 Manual smoke test via Docker: create one entry per template type → entries appear in list → edit one → delete one → create a note with directory → note appears in tree → edit note content _(deferred until after 7.x restructure)_
- [x] 6.5 Update `docs/log/2026-05-06.md` with commit hash, features, test counts, and code review findings
- [x] 6.6 Run superpowers:requesting-code-review on the full private-data diff; address all CRITICAL/HIGH findings

## 7. UX restructure — directory-driven items (Revision 2026-05-07)

Original 5.x PrivateView is replaced. Backend infrastructure from 1–4 is reused; only the schema gets one new column.

### 7.1 Backend: directory column on private_entries

- [x] 7.1.1 RED — pytest test asserting `private_entries.directory` column exists after `_ensure_private_tables()`; test `''` default for backfilled rows; test idempotent on a DB whose table predates the column
- [x] 7.1.2 GREEN — extend `_ensure_private_tables()` with idempotent `ALTER TABLE … ADD COLUMN directory TEXT NOT NULL DEFAULT ''` (mirroring `_ensure_title_column` pattern); update `db/schema.sql`
- [x] 7.1.3 Run `cd backend && pytest tests/test_db_service.py` — green

### 7.2 Backend: template default_directory + entries API directory

- [x] 7.2.1 RED — pytest tests in `test_private_entries.py`: (a) `GET /api/private/templates` returns each template with `default_directory` matching the spec map; (b) `POST /api/private/entries` with no `directory` stores the template's default; (c) `POST` with explicit `directory` stores that value; (d) `GET /api/private/entries` returns `directory` field on each row
- [x] 7.2.2 GREEN — add `default_directory` to each `PRIVATE_TEMPLATES` entry in `private_templates.py`; extend `private.py` create_entry/update_entry/list_entries/`_row_to_entry` to read/write `directory`
- [x] 7.2.3 RED — pytest test for `PUT /api/private/entries/{id}` updating `directory` and re-upserting Qdrant payload with new directory
- [x] 7.2.4 GREEN — extend update_entry to accept and persist `directory`; include `directory` in Qdrant upsert payload
- [x] 7.2.5 Run `cd backend && pytest` — full suite green (135 passed)

### 7.3 Frontend: store updates (combinedTree + directory pass-through)

- [x] 7.3.1 RED — vitest tests for `private.js`: (a) `combinedTree` getter merges entries + notes by directory with `kind` discriminator; (b) the 6 fixed template directories are seeded as keys even when entries/notes are empty; (c) `createEntry` passes `directory` through to POST; (d) `updateEntry` passes `directory` through to PUT
- [x] 7.3.2 GREEN — add `combinedTree` getter, update `createEntry`/`updateEntry` action signatures
- [x] 7.3.3 Run `cd frontend && npm test -- tests/stores/private.test.js` — green (17 passed)

### 7.4 Frontend: PrivateView two-column rewrite

- [x] 7.4.1 RED — vitest tests for new layout in `tests/views/PrivateView.test.js` (rewrite the file): (a) renders gradient header; (b) sidebar shows the 6 fixed template directories on mount; (c) clicking a directory expands it and reveals items; (d) clicking an entry switches right panel to `item-view` and shows template fields; (e) clicking a note shows note content; (f) clicking "+ 新建条目" switches to `new-entry`; selecting `tax` template pre-fills directory `税务`; submit calls `createEntry`; (g) clicking "+ 新建笔记" switches to `new-note`; submit calls `createNote`; (h) clicking 编辑 on an item switches to `item-edit`; (i) clicking 删除 calls store.delete after confirm and returns to welcome
- [x] 7.4.2 GREEN — rewrite `frontend/src/views/PrivateView.vue` with two-column layout (sidebar tree + right panel state machine: welcome / item-view / item-edit / new-entry / new-note)
- [x] 7.4.3 Apply UI design system from `docs/frontend-ui-guide.md`: gradient header, sidebar section header, list item active/hover states, card styles, form input/textarea styling consistent with IngestView
- [x] 7.4.4 Run `cd frontend && npm test` — full frontend suite green (100 passed)

### 7.5 Integration verification

- [x] 7.5.1 Run `cd backend && pytest` — full backend suite green (135 passed)
- [x] 7.5.2 Run `cd frontend && npm test` — full frontend suite green (100 passed)
- [x] 7.5.3 Update `docs/log/2026-05-07.md` (new file) with the restructure summary, test counts, code review findings
- [x] 7.5.4 Run superpowers:requesting-code-review on the 7.x diff; address CRITICAL/HIGH findings (1 HIGH found and fixed: dirty-check guard on `selectItem` to prevent silent draft loss)
- [x] 7.5.5 Hot-swap backend Python files into `python-agent-api-1`; rebuild `python-agent-frontend` via `docker compose up --build frontend -d` — done via `docker compose up --build -d`; backend curl smoke test confirmed POST entry → 201 with `directory='退休账户'` auto-filled, DELETE → 200
- [x] 7.5.6 Manual smoke test in browser — confirmed by user. Legacy `San Jose自助房` (real_estate) entry surfaced correctly under `房产资产` after the migration backfill. Chevron + sidebar layout match IngestView style.
