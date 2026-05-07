## Context

Foundation and Ingest are complete. The `knowledge` Qdrant collection now contains chunks from ingested files, each with payload fields: `text`, `source_file_id`, `chunk_index`, `domain`, `topic`, `updated_at`, `status`.

The current `IngestView.vue` redesign removed the `topic` field from the ingest form — all chunks are stored with `topic="general"`. The wiki browser must account for this.

`WikiView.vue` is currently a stub returning `{"status": "ok", "stub": true}`. No wiki API routes exist beyond the stub.

Existing reusable pieces: `useFileContent` composable (fetches `/api/files/{id}/content`), `GET /api/files/{id}/download`, and `GET /api/files/{id}/content` (all implemented).

## Goals / Non-Goals

**Goals:**
- Browse all ingested files organised by domain in a left-right two-column layout
- Search/filter entries by title in real time (client-side)
- View file content inline in the right panel
- Link back to the original file via download

**Non-Goals:**
- Full-text semantic search (that is chat-qa scope)
- Three-level domain → topic → entry tree (topic is always "general" in V1; extend later if topic field is re-added to ingest)
- Editing entries or re-ingesting from the wiki page
- P2: DELETE /api/wiki/{id}, wikilinks (`[[entry name]]`)

## Decisions

### 1. Entry unit = File (source_file_id), not Chunk

**Decision:** The wiki tree groups by `source_file_id`, showing one entry per ingested document regardless of chunk count.

**Rationale:** A 20-chunk PDF is one document to the user, not 20 entries. Showing chunks as separate entries would be confusing and cluttered.

**Alternative considered:** Show each Qdrant point as an entry. Rejected — meaningless to the user; the chunk boundary is an implementation detail.

**Implementation:** `GET /api/wiki/tree` uses Qdrant scroll with no vector query (payload-only), collects unique `source_file_id` values per domain, then JOINs with SQLite `files` table to fetch `title`, `orig_name`, `filename`, `chunk_count`, `created_at`.

### 2. Two-level tree: domain → entries (topic collapsed in V1)

**Decision:** The sidebar shows domain groups with files directly underneath. The `topic` level is omitted because all chunks have `topic="general"`.

**Rationale:** Adding a "general" heading between domain and files adds visual noise with no value. When topic is re-introduced to the ingest form in a future iteration, the tree can be extended to three levels.

**Alternative considered:** Three-level tree where "general" appears as a topic node. Rejected — redundant and ugly.

### 3. Qdrant scroll (no embedding) for browsing

**Decision:** All wiki API reads use Qdrant's scroll API (payload filter + no vector), never semantic search.

**Rationale:** This is a browse/navigation feature, not a retrieval feature. Generating an embedding just to list entries by domain would be wasteful and wrong semantically.

**No user_id filter on `knowledge` collection:** Correct — `knowledge` is shared across all users. User_id filter is only mandatory for `private` collection queries (ARCH-07); it MUST NOT be applied here.

### 4. Reuse existing content infrastructure

**Decision:** Right-panel content viewer calls `GET /api/files/{file_id}/content` via the existing `useFileContent` composable. No new content endpoint is added.

**Rationale:** The content endpoint and composable already handle local file serving, URL fallback with HTML extraction, and markdown rendering. Duplicating this logic in a wiki-specific endpoint would violate DRY.

### 5. Pinia wiki store (client-side search)

**Decision:** A `wiki.js` Pinia store fetches the tree once on mount and holds `tree` (all domains + entries), `selectedFileId`, and `searchQuery`. Filtering is done client-side by matching `searchQuery` against entry titles.

**Rationale:** The dataset is small (personal knowledge base). A server round-trip per keystroke is unnecessary and adds latency.

**Alternative considered:** Server-side search via `GET /api/wiki?q=`. Rejected for V1 — adds endpoint complexity for minimal benefit at this scale.

### 6. WikiView UI mirrors IngestView two-column layout

**Decision:** `WikiView.vue` uses the identical two-column layout pattern as `IngestView.vue`: fixed left sidebar (≈200px) with collapsible domain groups + file title list; right panel with `rightPanelState` (`'welcome'` / `'content'`). Same Tailwind classes, same chevron expand/collapse behavior, same active item highlight style.

**Rationale:** Consistent UX — the user already knows how the IngestView sidebar works. Re-using the same pattern means zero learning curve for the wiki browser. No domain-info intermediate state is needed because the wiki is read-only (no "+ 新建" button).

**Right panel states (2 only):** `'welcome'` → `'content'`. Unlike IngestView's 5-state machine, wiki has no form, result, or domain-info states.

## Risks / Trade-offs

- **Qdrant scroll performance at scale**: Scrolling all points to build the tree is O(n). For a personal KB (< 10k chunks) this is fine. If the collection grows large, a SQLite-side materialized view of `(file_id, domain)` pairs would be faster. → Mitigation: add a TODO comment in `QdrantService.get_tree()`.
- **Stale tree after new ingest**: The wiki store fetches on mount; if the user ingests a file and then navigates to `/wiki` without a page reload, they may not see the new entry. → Mitigation: refetch tree when `WikiView` is mounted (Vue lifecycle) and add a manual refresh button if needed in a future iteration.
- **topic="general" assumption**: If a future ingest adds a real topic value, the two-level tree will silently collapse all "general" entries together with properly-named topic entries under the same domain. → Mitigation: the design doc explicitly states topic is always "general" in V1 and the tree must be extended when topic field is reintroduced.

## Open Questions

_(none — design is fully specified for V1 scope)_
