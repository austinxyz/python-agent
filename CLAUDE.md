# Knowledge Agent

General-purpose personal knowledge base agent. Ingests raw knowledge into a vector database and answers questions via RAG. V1 use case: personal finance.

## Tech Stack

- **Frontend**: Vue 3 + Vite (`frontend/`)
- **Backend**: Python + Flask + LangGraph (`backend/`)
- **Vector DB**: Qdrant (Docker container, port 6333)
- **LLM**: Claude Haiku/Sonnet (Anthropic API, configurable)
- **Embeddings**: OpenAI text-embedding-3-small
- **Metadata**: SQLite (file registry, notes)
- **Deployment**: Docker Compose → NAS → Railway

## Project Structure

```
backend/app/
  routes/          # Flask blueprints (ingest / wiki / chat / private / files / prompts)
  graphs/          # LangGraph (ingest_pipeline.py · qa_agent.py)
  services/        # Qdrant · File · LLM services
  models/          # SQLite data models

frontend/src/
  views/           # WikiView · IngestView · ChatView · PrivateView
  components/      # TreeNav · ChatMessage · PromptLibrary · SaveNoteModal
```

## Core Design Decisions

**Two LangGraph graphs:**
- `IngestPipeline`: deterministic pipeline — Source Router → Fetch → Clean → Chunk → Embed → Store
- `QAAgent`: ReAct agent with tools: `search_knowledge` / `search_private` / `get_entry`

**Two Qdrant collections:**
- `knowledge`: shared across all users
- `private`: per-user; every query must include a `user_id` filter; V1 uses `user_id="default"`

**Raw files are kept permanently:** stored at `/app/uploads/{user_id}/{file_id}/` after ingestion; SQLite `files` table records metadata.

**SQLite is the source of truth; Qdrant only holds vectors.** Every write path MUST commit to SQLite first, then call Qdrant. A failed Qdrant call leaves a row whose vector can be rebuilt by a re-index job; the reverse (Qdrant succeeds, SQLite fails) leaves an orphan vector with no way to manage it. See `private.py::create_entry / update_entry / delete_entry` for the canonical pattern: SQL INSERT/UPDATE/DELETE inside `with db.connection():` block (which commits on `__exit__`), then Qdrant call **outside** the block.

## Development Conventions

- Private data queries must always include `user_id` filter — never omit it
- SSE streaming responses use Flask `Response(stream_with_context(...))`
- LLM and Embedding providers are switched via environment variables, never hardcoded
- `TreeNav.vue` is a shared component for both the knowledge browser and file management — do not duplicate it
- **Two-column layout is the project's UI convention.** All major views (`IngestView`, `WikiView`, `PrivateView`) follow the same shape: gradient header (`bg-gradient-to-r from-blue-600 to-purple-600`) → flex row → fixed-width left sidebar (`w-60` ~ `w-72`, white bg, shadow) → flex-1 right panel driven by a state-machine ref (`welcome` / `domain` / `form` / `content` / `item-view` / etc.). When adding a new top-level view, follow this shape — don't invent a new layout. Shared chevron pattern: SVG `polyline 9 18 15 12 9 6` with `rotate-90` when expanded; row click toggles. See `IngestView.vue` for the canonical reference.

## Environment Variables (.env)

```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-haiku-4-5-20251001

EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small

QDRANT_HOST=qdrant
QDRANT_PORT=6333

FLASK_SECRET_KEY=...
```

## Design Documents

- Architecture & requirements: `docs/superpowers/specs/2026-05-05-knowledge-agent-design.md`
- Frontend UI design system: `docs/frontend-ui-guide.md`

## Known Pitfalls (past mistakes)

### Windows Environment

- **Bash tool cannot use Windows paths**: `cd C:\Users\...` fails in the Bash tool (Git Bash strips backslashes). For any shell operation involving Windows paths, use the **PowerShell tool**.
- **docker cp path format**: In PowerShell use `docker cp "C:/Users/.../file.py" container:/path/file.py` (forward slashes, quoted). Do not run this with the Bash tool.

### Docker Deployment

- **Frontend changes are not hot-reloaded**: nginx serves the compiled `dist/`. After editing Vue files you must run `docker compose up --build frontend -d`, then hard-refresh the browser with `Ctrl+Shift+R`. Do not keep inspecting the code assuming a bug.
- **Backend Python files can be hot-swapped**: `docker cp` the new file into the container then `docker restart python-agent-api-1` — no image rebuild needed.
- **SQLite env var is `SQLITE_PATH`**, not `DATABASE_PATH`. Debug scripts must use `os.environ.get('SQLITE_PATH', 'knowledge_agent.db')`; otherwise they open an empty database.

### Ingest Pipeline

- **text / url ingestions do not automatically save content to disk**: The original design only called `file_svc.save()` for `source_type=file`. For `text` and `url`, the cleaned content (`raw_content`) must be explicitly saved in `store_node` as `{file_id}.txt`; otherwise the `/content` endpoint returns 404.
- **`_SAFE_COMPONENT` regex blocks non-ASCII characters**: The path guard regex `^[a-zA-Z0-9_\-. ]+$` rejects Chinese characters, so Chinese titles cannot be used as filenames. Always use `{file_id}.txt` as the stored filename for text/url ingestions.
- **URL `/content` endpoint returning raw HTML**: The old implementation returned `resp.text` directly; the frontend then displayed HTML source in `<pre>`. The correct approach: serve the local file first if it exists; fall back to re-fetching the URL and running `_html_to_text()` before returning `text/plain`.

### Database Migrations

- **Backfill in the same migration step**: When adding a SQLite column whose value drives UI placement or filtering (e.g., `private_entries.directory` controls which sidebar tree node an entry appears under), the migration MUST do BOTH `ALTER TABLE ADD COLUMN` AND `UPDATE … WHERE column IS NULL OR column = ''` to backfill legacy rows from a derivation rule. Otherwise existing rows land at `''` / `NULL` and silently disappear from the user's expected location. Pattern: `_ensure_private_entries_directory_column` in `db_service.py` — PRAGMA check → ALTER TABLE → UPDATE per derivation map (e.g., `TEMPLATE_DEFAULT_DIRECTORIES`). Idempotent; safe to run on every startup.
- **Qdrant payloads are NOT auto-backfilled by SQLite migrations**: only the SQLite column is touched. If a future feature filters Qdrant by the new field, write a separate one-shot Qdrant `set_payload` migration. For fields that are eventually overwritten on the next user edit (like `directory`), eventual consistency is acceptable — note the gap explicitly.

### Frontend UI Validation

- **vitest + happy-dom catches behavior, not layout.** Component tests with `@vue/test-utils` verify `data-*` selectors and store calls; they cannot tell you whether the layout is right. The original 5.x `PrivateView` passed all 11 vitest tests but was rejected on first sight after deploy — the tests verified that buttons existed and called the right actions, not that the page looked usable. Lesson: for any UX-touching change, treat the deploy + browser walkthrough as a required step, not an optional QA phase.
- **Once a UX is validated, lock the flow in with Playwright.** The project has Playwright wired up at `frontend/e2e/` (`npm run e2e` headless, `npm run e2e:headed` for debugging). Tests run against the user-managed docker stack — bring it up first with `docker compose up -d`. Test data is isolated by the reserved `__e2e_*` title prefix and cleaned up via `afterEach`, even on failure. **Workflow:** first deploy = human eyes; once UX is signed off, add a Playwright spec covering that flow before moving on. Playwright catches regressions; it does NOT validate fresh designs.

### Git

- **Local changes may be left uncommitted across sessions**: Always run `git status` before pushing to confirm no unstaged files were left over from a previous session.

## Dev Log Practice

**After each feature batch, update the day's dev log.**

Log path: `docs/log/YYYY-MM-DD.md` (create if it doesn't exist for the day)

### Each log entry contains

```markdown
### N. Feature Name
**Commit:** `<git hash>`

**Features:**
- Concise bullet points describing what was done

**Code review findings (if any):**
| Level | Issue | Fix |

**Tests:** X tests all passing (Y new)
```

### Rules

- Update the log **after each commit** (or at the end of each feature batch)
- Pending items use `- [ ]`, completed items use `- [x]`
- Keep a "Pending" section at the end listing the next batch or known issues
- Always include **`update log`** as a step in the task list
