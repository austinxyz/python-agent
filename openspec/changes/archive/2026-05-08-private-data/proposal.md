## Why

The QA agent needs a private data collection to search against, but no UI or API exists yet to create or manage private data. This change delivers the private data management layer — structured template entries (e.g., tax situation, retirement accounts) stored as vectors in Qdrant, plus a free-form notes store — so that users can populate their private context before (and independently of) using the chat feature.

## What Changes

- **New SQLite tables**: `private_entries` (id, user_id, template_type, title, content_json, created_at, updated_at) and `notes` (id, user_id, title, directory, content, chat_ref, created_at, updated_at) — added to `backend/db/schema.sql`, created at startup
- **New private API routes** (`backend/app/routes/private.py`):
  - `GET /api/private/templates` — returns the 6 preset template definitions (tax, retirement accounts, portfolio, personal info, real estate, free-form)
  - `POST /api/private/entries` — creates a structured entry, embeds content, stores vector in Qdrant `private` collection with `user_id` filter
  - `PUT /api/private/entries/{id}` — updates content, re-embeds, updates Qdrant vector
  - `DELETE /api/private/entries/{id}` — removes entry from SQLite and Qdrant
  - `GET /api/private/entries` — lists all entries for the current user
  - `GET /api/private/notes` — returns notes list (flat + tree structure)
  - `POST /api/private/notes` — creates a new note (manual or from chat save)
  - `PUT /api/private/notes/{id}` — edits note content / renames / moves directory
- **Functional PrivateView.vue**: replaces the stub; two-section layout — structured template entries (select template → fill form → save) and private notes tree (collapsible directory tree, click to view content, edit inline)
- **Pinia private store** (`frontend/src/stores/private.js`): templates, entries, notes tree state; actions for CRUD operations
- **Qdrant private collection**: all writes include `user_id = "default"` payload; all reads apply the mandatory `user_id` filter

## Capabilities

### New Capabilities

- `private-entries`: backend API + Qdrant storage for structured template-based private data entries; 6 preset templates; mandatory user_id scoping on all Qdrant operations
- `private-notes`: backend API + SQLite storage for free-form markdown notes; hierarchical directory paths (e.g., "退休规划/Roth相关"); support for manual creation and future chat-save integration
- `private-view`: Vue 3 two-section PrivateView replacing the stub; template entry CRUD UI with form builder; notes tree browser with inline editor

### Modified Capabilities

- `backend-scaffold`: two new SQLite tables (`private_entries`, `notes`) added to `db/schema.sql`; `_ensure_private_tables()` migration called at startup

## Impact

- **Backend**: new `private.py` blueprint registered in `app.py`; `EmbeddingService` used to generate vectors for entries; `QdrantService` extended with `upsert_private_entry` / `delete_private_entry` / `search_private` methods
- **Frontend**: `PrivateView.vue` (currently stub) replaced; `private.js` Pinia store added
- **Dependencies**: no new packages; langchain/qdrant-client/anthropic already installed
- **Requirements addressed**: PRI-01, PRI-02, PRI-03, PRI-04, PRI-05, PRI-06, PRI-07, DATA-02, DATA-06, ARCH-07, UI-24, UI-25, UI-26
- **Design reference**: `docs/superpowers/specs/2026-05-05-knowledge-agent-design.md` section 6.5

## Non-Goals

- Multi-user auth (V1 user_id is always "default")
- Chat integration for saving notes from a chat session (that belongs in the qa-chat change)
- MCP data source ingestion into private collection (separate change)
- Private note versioning or history

---

## Revision 2026-05-07 — UX restructure (directory-driven items)

After the first deploy of the original two-section layout (template entries on top, notes on bottom), the UX was rejected for being inconsistent with the rest of the app. The data model is fundamentally re-shaped to be directory-driven, matching the IngestView two-column pattern.

### Why
- Other views (摄入、知识库) use a two-column layout: left sidebar tree + right detail panel. The original PrivateView didn't, breaking visual continuity.
- The original split (entries vs notes as separate sections) hides the natural commonality — both are "items the user has stored", and both want directory organization.

### Changes
- **Directory becomes the primary navigation axis.** Sidebar shows a unified tree of directories; each directory holds entries (📋, vectorized) and/or notes (📝, not vectorized).
- **Templates bind to default directories.** Each preset template defines a `default_directory` (e.g., `tax` → `税务`). When the user creates an entry, the directory is pre-filled from the template (editable for sub-organization).
- **`private_entries` gains a `directory TEXT NOT NULL DEFAULT ''` column.** Migration is idempotent ALTER TABLE in `_ensure_private_tables`.
- **PrivateView rewritten** as: left sidebar tree (📁 directory + 📋 entry / 📝 note leaves) + right panel state machine (welcome / item-view / item-edit / new-entry-form / new-note-form). Same gradient header and card styles as IngestView.
- **Pinia store** adds `combinedTree` getter that merges entries + notes by directory; existing entry/note actions extended to pass through `directory`.

### What stays
- All backend Qdrant + SQLite infrastructure (Group 1–3 work) — only the entries table gets one new column.
- The 6 template definitions, the embedding pipeline, the user_id isolation invariants — unchanged.
- Notes API — unchanged (already had `directory`).

### Implementation tracking
See `tasks.md` Section 7 for the new RED/GREEN tasks under this revision. Sections 1–6 from the original plan stay marked complete (their backend artifacts are kept); the only sub-tasks marked obsolete (`[~]`) are the original PrivateView UI tasks (5.1–5.5).
