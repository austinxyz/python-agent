## Context

After the top-k bump (`chat-retrieval-bump`, archived 2026-05-08), vector
retrieval covers most cases. What it still can't fix: when the user
explicitly knows which document holds the answer but the agent's
similarity ranking doesn't put that document's relevant chunks high
enough. Pure recall improvements (re-ranking, query rewriting) would
help, but they cost meaningful complexity and the user's mental model
is already "I know which file — just use it".

This change adds the escape hatch.

## Goals / Non-Goals

**Goals:**
- A user-controllable mechanism to pin one or more documents into the
  LLM context for one chat turn
- Pinned content visible in the source-chip output so the user can
  confirm what the LLM actually saw
- Mixed pinning + vector retrieval in the same turn — pinning augments
  rather than replaces the vector search

**Non-Goals:**
- Re-ranking, query rewriting, hybrid search — separate change if A
  (already shipped) and B prove insufficient
- Persistent pin across turns (per-session memory belongs in a
  different change)
- Auto-pinning based on heuristics

## Decisions

### 1. Pinning: full content injection, not "boost similarity"

**Choice:** When a file is pinned, fetch its full text from SQLite (or
disk for knowledge files) and prepend it to the LLM context under a
labeled `【引用文件】` section. Vector search still runs in parallel
and adds its top-k from each scope to the same context block.

**Rationale:**
- "Boosting" the file's chunks in vector search would still miss
  content that doesn't embed well or sits in a chunk that didn't get
  retrieved.
- Full content injection is what the user actually wants when they
  explicitly pin: "use THIS file, all of it". No surprises.
- LLM context windows are large enough; we're nowhere near the budget
  for personal-scale files (max real-world file: 46k chars; the LLM
  has 200k tokens to spare).

**Alternatives considered:**
- Boost the file's vector points by a similarity score offset: doesn't
  actually help if the relevant chunk wasn't retrieved at all.
- Replace vector search entirely when pinned: loses cross-document
  context (sometimes a knowledge-base file has the canonical
  definition the user's private file references).

### 2. Pinned id resolution order: knowledge → private entry → note

**Choice:** `_fetch_pinned_text(file_id)` probes `files`, then
`private_entries`, then `notes`, returning the first match.

**Rationale:**
- IDs are UUIDs, collisions effectively impossible across tables.
- Knowledge first matches user expectation ("if this id is a knowledge
  file, treat it as such") and avoids accidentally leaking a private id
  into a knowledge-only path.
- Returns include `kind` so the source chip routes correctly.

### 3. Pinned files appear in `done` event sources

**Choice:** Pinned files are added to the `done.sources` array with
`kind` matching the underlying source table. The frontend chip can
render them with a third visual style and route to whichever
destination matches.

**Rationale:**
- Without showing them in sources, the user can't verify what the LLM
  actually got.
- Mixing pinned and retrieved sources in one list is fine — the chip's
  destination still depends on the source's underlying type.

### 4. Per-turn pinning, not session-wide

**Choice:** Pinned chips clear after each `sendMessage`. Re-pin per
question.

**Rationale:**
- Most pin scenarios are one-off ("for this question, focus on this
  file"). Session-wide pinning is a different feature (filing the file
  as a permanent context).
- Clearing prevents stale pins from polluting unrelated questions.

**Alternatives considered:**
- Sticky session pin: deferred. If users ask for it after using B for
  a while, easy follow-up.

## Risks / Trade-offs

- **Pin abuse**: nothing stops the user from pinning 10 huge files at
  once. We don't gate this — first principle of personal tools is
  "don't get in the way". If the LLM 4xx's on context length, the
  error event surfaces.
- **Tests for the picker UI**: vitest happy-dom-based. Real picker UX
  (search debouncing, keyboard nav) isn't fully exercised — we add 1
  Playwright spec for the smoke flow.
- **Token cost when pinning a large file**: a 46k-char file is ~15k
  tokens. At Haiku's $0.30/M input, that's about $0.005 extra per
  pinned turn. Negligible at personal scale.
