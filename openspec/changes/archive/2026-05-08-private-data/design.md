## Context

The `private` Qdrant collection already exists and is configured in `QdrantService`. The embedding pipeline is also in place. This change wires up the user-facing layer: an API to create/update/delete structured private entries (which get embedded into Qdrant) and free-form notes (stored only in SQLite, not vectorized in V1). The PrivateView stub in the frontend gets replaced with a functional two-section page.

All private Qdrant operations MUST include `user_id = "default"` — this is the isolation invariant for V1. The data model is intentionally simple: the full entry content is stored as JSON in SQLite, and the combined text representation is what gets embedded.

## Goals / Non-Goals

**Goals:**
- CRUD API for structured template entries (embed → Qdrant + metadata → SQLite)
- CRUD API for markdown notes (SQLite only, hierarchical directory paths)
- Functional PrivateView.vue with template form builder and notes directory tree
- Enforce user_id filter on every private Qdrant operation

**Non-Goals:**
- Vectorizing notes (notes are stored only in SQLite in V1; QA agent searches entries, not notes)
- Chat integration for note saving (qa-chat change)
- Multi-user auth
- Attachment/file uploads to private entries

## Decisions

### 1. Private entries: SQLite for metadata + Qdrant for vectors

**Choice:** Store the full structured content as a JSON blob in SQLite `private_entries.content_json`; derive a plain-text representation from the JSON fields and embed it; store the Qdrant point ID as the SQLite `id` (same UUID).

**Rationale:** Keeps the source of truth for structured data in SQLite (easy queries, no Qdrant scroll needed for listing). Qdrant only stores the vector + minimal payload (`user_id`, `template_type`, `title`, `source_file_id = id`). On update, delete the old Qdrant point and upsert a new one with the same ID.

**Alternatives considered:**
- Storing everything in Qdrant payload: payload size limits + harder to query structured fields without vector search
- SQLAlchemy ORM: unnecessary overhead; raw sqlite3 is consistent with the rest of the project

### 2. Notes: SQLite only (no embedding in V1)

**Choice:** Notes stored in `notes` table; NOT embedded into Qdrant.

**Rationale:** Notes are the output of chat sessions — they are already derived from retrieved knowledge. Embedding them would create circular retrieval loops with diminishing returns. The QA agent searches `private_entries` for factual personal context (income, accounts, holdings). Notes are browseable but not searchable via vector in V1.

**Alternatives considered:**
- Embed notes into `private` collection: deferred to V2 when the value is clearer

### 3. Directory paths as strings

**Choice:** `notes.directory` stored as a path string like `"退休规划/Roth相关"`. No separate directory table.

**Rationale:** Hierarchical paths are simple to store and reconstruct on the frontend. The tree is derived by splitting on `/` at read time. No need for parent FK references for a personal notes app.

### 4. Template definitions are server-side constants (not DB rows)

**Choice:** The 6 preset templates are defined as Python constants in `private.py` (or a `templates.py` module). `GET /api/private/templates` returns them directly.

**Rationale:** Templates are not user-configurable in V1. Keeping them as code constants avoids a DB migration whenever a template changes. A future DB-backed template system would be a separate change.

**V1 templates:**
1. `tax` — 税务情况 (filing status, tax bracket, AGI, FBAR/FATCA)
2. `retirement` — 退休账户 (401K, Roth IRA, Traditional IRA)
3. `portfolio` — 投资持仓 (brokerage, holdings, cost basis)
4. `personal` — 个人基本情况 (income, family, goals)
5. `real_estate` — 房产资产 (properties, mortgages, equity)
6. `freeform` — 自由格式 (plain Markdown text field)

### 5. Qdrant upsert pattern for entries

**Choice:** On create: generate UUID → embed text → `qdrant.upsert(points=[PointStruct(id=uuid, vector=..., payload={user_id, template_type, title, source_file_id=uuid})])`. On update: same upsert with same UUID (Qdrant upsert is idempotent by ID). On delete: `qdrant.delete(points_selector=PointIdsList(points=[uuid]))`.

**Rationale:** Qdrant upsert by ID avoids the need to track separate Qdrant IDs; the SQLite primary key IS the Qdrant point ID.

### 6. Frontend form builder — JSON schema driven

**Choice:** Each template definition includes a `fields` array of `{key, label, type, placeholder}` objects. The form renders fields dynamically from this schema. No separate form component per template.

**Rationale:** 6 templates × custom forms = unmaintainable. One generic `PrivateEntryForm.vue` component that reads template fields is far simpler.

## Risks / Trade-offs

- **No note vectorization**: QA agent cannot search notes in V1. Mitigated by noting this explicitly in the UI ("笔记不参与 AI 检索").
- **Embedding cost on every update**: each entry update re-embeds. For personal data (small, infrequent updates) this is negligible.
- **JSON blob in SQLite**: structured querying of entry fields is not possible without parsing JSON. Acceptable for V1 personal-scale data.

---

## Revision 2026-05-07 — Decision 7: Directory-template binding (option A)

**Choice:** Each preset template carries a `default_directory` constant; entries store a `directory` column in SQLite. When the user creates an entry, the picked template pre-fills the directory but the user can override (e.g., put a tax entry in `税务/2025`).

**Rationale:** The user wants the sidebar to navigate by directory, not by entry vs note. Binding templates to default directories keeps the model intuitive — "tax stuff lives in 税务" — while leaving the directory string free for sub-folder organization.

**Default directory map:**
| template_type | default_directory |
|---|---|
| `tax` | `税务` |
| `retirement` | `退休账户` |
| `portfolio` | `投资持仓` |
| `personal` | `个人基本情况` |
| `real_estate` | `房产资产` |
| `freeform` | `自由格式` |

**Tree structure (combined entries + notes):**
- Frontend builds the tree by splitting each item's `directory` on `/` and grouping items at each node.
- A node has `_items: [...]` (mixed entries and notes, with `kind` discriminator) plus child directory keys.
- Empty template directories are shown by default so the user always sees the 6 base buckets.

## Revision 2026-05-07 — Decision 8: SQLite migration via idempotent ALTER

**Choice:** Add `directory` column via `ALTER TABLE private_entries ADD COLUMN directory TEXT NOT NULL DEFAULT ''`, wrapped in a try/except for `duplicate column name` like the existing `_ensure_title_column()` pattern.

**Rationale:** Keeps the same migration idiom as the rest of the codebase. Existing rows backfill to `''`, which is fine — there are zero production rows yet.

## Revision 2026-05-07 — Decision 9: View state machine

**Choice:** Right-panel state machine: `welcome` → `item-view` → `item-edit` (or back to `welcome`) → `new-entry` → `new-note`. Each item knows its `kind` (`entry` | `note`) so the renderer/editor switches accordingly.

**Rationale:** Matches IngestView's `welcome | domain | form | result | content` pattern. State stored as a single ref, predictable transitions, no nested modals.
