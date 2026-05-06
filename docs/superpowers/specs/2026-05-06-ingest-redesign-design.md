# IngestView Redesign Design

**Date:** 2026-05-06  
**Scope:** `frontend/src/views/IngestView.vue` and related components/backend  
**Goal:** Replace the two-tab layout with a single-page left-right knowledge browser

---

## Overview

The current `/ingest` page has two tabs: "新建摄入" and "已上传文件". This redesign merges them into a single left-right layout — a persistent domain tree on the left, and a context-sensitive right panel that shows domain info, the ingest form, ingest results, or file content depending on what the user clicked.

---

## Layout

```
┌────────┬─────────────────────┬──────────────────────────────────────┐
│ App    │   Domain tree        │   Right panel (context-sensitive)    │
│ nav    │   (200px)            │   (flex-1)                           │
│ (48px) │                     │                                      │
│        │  退休规划    ▾  2   │   [ depends on selection ]          │
│        │    Roth IRA详解      │                                      │
│        │    401k规则          │                                      │
│        │  账户类型    ▸  5   │                                      │
│        │  税务策略    ▸  3   │                                      │
│        │  …                  │                                      │
└────────┴─────────────────────┴──────────────────────────────────────┘
```

The global app nav sidebar (existing `AppLayout.vue`) is unchanged.

---

## Left Sidebar — Domain Tree

### Predefined domains (ordered)

Sourced from `C:\Users\lorra\projects\personal\wealth\wiki\`:

1. 退休规划
2. 账户类型
3. 税务策略
4. 投资品种
5. 保险规划
6. 股权激励
7. 家庭财务
8. 中美对比
9. 遗产规划
10. 其他 *(default / catch-all)*

The list is hardcoded in the frontend as a constant. Domains with no files are still shown (so the user can add content to any domain). The file count badge is hidden when zero.

### Interaction rules

| User action | Result |
|---|---|
| Click **▾/▸** chevron | Toggle expand/collapse of file list under that domain |
| Click **domain name** | Right panel → Domain Info state |
| Click **file title** | Right panel → Content Viewer state |

The chevron and domain name are separate click targets so collapsing a domain doesn't accidentally navigate away from the current right panel.

### File display

Each file under a domain shows its `title` (user-provided). If `title` is null, falls back to `orig_name`. Icon prefix: 📄 for file, 🔗 for URL, 📝 for text.

---

## Right Panel — Four States

### State 1: Domain Info (default when domain is selected)

Shown when the user clicks a domain name.

- Domain name as heading
- File count ("N 篇")
- Description field: placeholder text for now ("暂无描述"), designed for future editing
- List of top files in this domain (same display as sidebar)
- **"+ 新建摄入" button** → transitions to State 2

### State 2: Ingest Form

Shown after clicking "+ 新建摄入" on a domain info page.

Fields:
- **Back arrow** — returns to Domain Info (State 1) for the same domain
- **Domain badge** (read-only, locked) — shows which domain this will be filed under
- **标题** (required) — user-provided title; this is what appears in the left sidebar
- **来源类型 toggle** — three mutually exclusive options: URL / 文件 / 文本 (default: URL)
- **Content input** — URL text field, file drop zone, or textarea depending on source type
- **开始摄入 button** — submits the form; button disabled while submitting

No destination toggle (always "knowledge"). No topic field. No domain dropdown (already locked).

### State 3: Ingest Result

Shown immediately after clicking "开始摄入", replacing the form in-place.

- Shows job label (the user's title)
- Animated status indicator while running
- On completion: "✓ 摄入完成 · N chunks"
- On error: error message in red
- The new file title appears in the left sidebar as soon as the job completes (sidebar re-fetches)
- A "继续摄入" link returns to State 2 (form) for the same domain

### State 4: Content Viewer

Shown when the user clicks a file title in the left sidebar.

- File title and domain badge as header
- Metadata: date, chunk count, source type
- Inline content rendered in the panel (no modal)
  - PDF/file: fetched from `GET /api/files/{file_id}/content`, rendered as text
  - URL: same endpoint re-fetches original URL, rendered as plain text
  - Markdown files: basic HTML rendering (headings, bold, code)
- No download button in V1 (can be added later)

### Default state (nothing selected)

When the page first loads with no selection, show an empty/welcome state in the right panel: a subtle prompt such as "选择左侧领域，开始浏览或摄入内容".

---

## Data Model Changes

### SQLite migration

Add nullable `title` column to the `files` table:

```sql
ALTER TABLE files ADD COLUMN title TEXT;
```

No default value. Existing rows will have `title = NULL` (displayed via fallback to `orig_name`).

### API changes

**`POST /api/ingest`** — accept optional `title` field in the `multipart/form-data` payload. Store in `files` table via `FileService.register()`.

**`GET /api/files`** — include `title` in the JSON response for each row.

**`FileService.register()`** — add `title: str | None = None` parameter.

### Frontend

The `topic` field is no longer sent from the frontend (the `topic` column is kept in the DB for historical rows). The `domain` field is still sent as before, using the predefined domain name string.

---

## Component Changes

### `IngestView.vue` — full rewrite

- Remove two-tab layout
- Left panel: new domain tree (replaces `TreeNav` usage)
- Right panel: conditional rendering based on `rightPanelState` ref (`'welcome' | 'domain' | 'form' | 'result' | 'content'`)
- Domain list: imported from a `DOMAINS` constant array
- On mount: fetch `GET /api/files` to populate file counts and titles per domain
- Store `selectedDomain`, `selectedFile`, `currentJob` in component refs

### `FileViewer.vue` — retired as modal

The existing `FileViewer.vue` modal component is no longer used. Its content-fetching and rendering logic (`renderContent`, `markdownToHtml`, `escapeHtml`) is moved inline into `IngestView.vue`'s State 4 section (or extracted to a small composable `useFileContent.js` if cleaner).

### `stores/ingest.js` — minor update

- `addJob(job_id, label)` — unchanged; `label` is now the user-provided title
- No other store changes needed; the polling logic is unchanged

### New constant file

`frontend/src/constants/domains.js`:

```js
export const DOMAINS = [
  '退休规划', '账户类型', '税务策略', '投资品种',
  '保险规划', '股权激励', '家庭财务', '中美对比',
  '遗产规划', '其他',
]
```

---

## What Is Removed

- Two-tab UI (tab buttons, `activeTab` ref, `watch(activeTab)`)
- Destination toggle (always "knowledge")
- Domain text input (replaced by predefined list)
- Topic text input (dropped entirely)
- Progress list below the form (replaced by inline result State 3)
- `FileViewer.vue` modal pattern (replaced by inline State 4)
- `viewingFile` ref and modal overlay

---

## Out of Scope (V1)

- Domain description editing
- Deleting files
- Reordering domains
- Domain configuration UI (the `DOMAINS` constant is the config mechanism for now)
- Download button in content viewer
