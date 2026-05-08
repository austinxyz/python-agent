## Why

Even with the top-k bump (delivered in `chat-retrieval-bump`, archived
2026-05-08), vector retrieval still has a fundamental limit: when the
user *knows* which document is relevant but the LLM doesn't surface it
(query keywords too generic, document too long, embedding mismatch),
the user has no way to force-include it.

This change adds an escape hatch: a `📎 引用` picker in the chat UI that
lets the user attach one or more files to a single chat turn. The
backend loads the file's full text content from SQLite / disk and
prepends it to the LLM context, bypassing vector search entirely for
that file. The Anthropic context window (200k tokens for Haiku 4.5)
easily fits even the largest personal-finance document we've seen
(46k chars).

## What Changes

- **API**: `POST /api/chat` accepts an optional `pinned_file_ids: list[str]` in the body. Each id can refer to a knowledge file (`files.id`), a private entry (`private_entries.id`), or a private note (`notes.id`).
- **Agent**: new `_fetch_pinned_text(file_id)` helper probes the three SQLite tables in order. `run_agent` accepts `pinned_file_ids`, fetches each, prepends them under a `【引用文件】` block ahead of the vector-retrieved `【上下文】` block, and includes them in the `done` event's `sources` list (with `kind` matching the source table).
- **Frontend ChatView**: new `📎 引用` button next to `[data-chat-input]` opens a picker modal listing entries + notes (knowledge files optional in V1.1) with a search box. Selected items render as chips above the textarea; ✕ removes a chip; pinned ids are forwarded to `store.sendMessage` and cleared after the stream completes.
- **Pinned source chips**: render alongside knowledge / entry chips in the `done` event sources, with a third visual variant (e.g., `tint-yellow`) so the user can confirm what the LLM actually got.

## Capabilities

### Modified Capabilities

- `qa-agent`: explicit-context injection alongside vector retrieval
- `chat-view`: per-turn pin UX

## Impact

- **Backend**: `qa_agent.py` (new helper + extended `run_agent`); `chat.py` route accepts the new field. SQLite reads only — no schema change.
- **Frontend**: `ChatView.vue` adds picker modal + chip UI; `chat.js` store extends `sendMessage` to forward `pinned_file_ids`.
- **Tests**: ~6 new backend tests (fetch helper, run_agent prepends, route accepts field, source dedupe); ~5 new vitest tests (picker UI, chip render, send payload, post-stream clear); 1 new Playwright E2E for the smoke flow.
- **Costs**: per-turn cost increases when the user pins large files but only when they explicitly opt in. Token budget still well within Haiku's 200k context.

## Non-Goals

- Persistent per-session pin (V1 = per-turn only)
- Pinning entire directories or domains (V1 = per-file id)
- Auto-pinning based on a heuristic
- Re-ranking, query rewriting, hybrid search (separate change if needed)

## Status

**Backlog as of 2026-05-08.** Group A (top-k bump) was delivered in the
predecessor change `chat-retrieval-bump`; that fix alone gave the user
the FBAR/FATCA recall they were missing. B is queued for when the same
recall failure mode reappears or the user wants explicit override of
retrieval ordering.
