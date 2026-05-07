## Why

Foundation and Ingest are complete — users can ingest documents into the knowledge base, but the `/wiki` page is a placeholder stub. There is no way to browse, search, or read the content that has been ingested. This change delivers the knowledge browser so the ingested material becomes usable.

## What Changes

- Replace the `WikiView.vue` stub with a functional two-column knowledge browser
- Implement `GET /api/wiki/tree` — returns the full domain → topic → entry tree built from Qdrant `knowledge` collection
- Implement `GET /api/wiki` — filtered entry list by domain / topic
- Implement `GET /api/wiki/{id}` — full entry content with `source_file_id` for linking back to the original file
- Left sidebar: domain → topic → entry tree with real-time search filtering (reuses `TreeNav.vue`)
- Right panel: entry content viewer showing body text, domain/topic tags, timestamp, and a "View original file" link that navigates to `/ingest` with the file selected
- (P2) `DELETE /api/wiki/{id}` — remove entry and its Qdrant vector

## Capabilities

### New Capabilities
- `knowledge-browse`: Backend wiki API endpoints + WikiView.vue two-column browser with tree navigation, search, and entry content viewer

### Modified Capabilities
_(none — no existing spec-level requirements are changing)_

## Impact

- `backend/app/routes/wiki.py` — replace stub with three endpoints
- `backend/app/services/qdrant_service.py` — add `get_tree()`, `list_entries()`, `get_entry()` methods
- `frontend/src/views/WikiView.vue` — full rewrite
- `frontend/src/stores/wiki.js` — new Pinia store (tree, selected entry, search query)
- Qdrant `knowledge` collection queried via scroll + payload filtering (no new collections)
- Requirements addressed: KB-01 · KB-02 · KB-03 · UI-03 · UI-04 · UI-05 · UI-07 · (P2) KB-04 · (P2) UI-06
