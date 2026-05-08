## ADDED Requirements

### Requirement: POST /api/chat SHALL accept pinned_file_ids
The `POST /api/chat` request body SHALL accept an optional field `pinned_file_ids: list[str]`. Each id MAY refer to a knowledge file (`files.id`), a private entry (`private_entries.id`), or a private note (`notes.id`). When present, the corresponding files' full text content SHALL be included in the LLM context for that turn alongside the vector-retrieved chunks.

#### Scenario: pinned ids are forwarded to run_agent
- **WHEN** `POST /api/chat` is called with `pinned_file_ids: ["abc"]`
- **THEN** `run_agent` is invoked with `pinned_file_ids=["abc"]`

#### Scenario: missing pinned_file_ids is treated as empty list
- **WHEN** `POST /api/chat` is called without the field
- **THEN** `run_agent` receives `pinned_file_ids=[]` (no behavior change vs. legacy callers)

### Requirement: _fetch_pinned_text resolves an id across the three SQLite tables
A helper `_fetch_pinned_text(file_id) -> dict | None` SHALL probe `files`, `private_entries`, and `notes` in that order, returning the first match as `{"kind": "knowledge"|"entry"|"note", "title": str, "domain": str, "file_id": str, "content": str}` or `None` when no row matches. For knowledge files the content is the plain-text representation stored at `UPLOADS_PATH/<user_id>/<file_id>/<file_id>.txt`; for private entries it is the derived text via `derive_text_for_embedding`; for notes it is the `notes.content` column.

#### Scenario: knowledge file id resolves to its on-disk text
- **WHEN** `_fetch_pinned_text("k1")` is called for an id present in `files`
- **THEN** the returned `kind` is `"knowledge"`, `content` is the file's text, and `domain` matches the row's domain

#### Scenario: private entry id resolves to derived text
- **WHEN** `_fetch_pinned_text("p1")` is called for an id present in `private_entries` only
- **THEN** the returned `kind` is `"entry"` and `content` is the derived embedding text

#### Scenario: note id resolves to raw note content
- **WHEN** `_fetch_pinned_text("n1")` is called for an id present in `notes` only
- **THEN** the returned `kind` is `"note"` and `content` is the markdown body

#### Scenario: unknown id returns None
- **WHEN** `_fetch_pinned_text("ghost")` is called for an id not in any of the three tables
- **THEN** the function returns `None`

### Requirement: run_agent SHALL prepend pinned content to the LLM context
`run_agent` SHALL accept `pinned_file_ids: list[str] = []`. For each id it SHALL call `_fetch_pinned_text` and prepend successful matches to the LLM context block under a `【引用文件】` heading, ahead of the vector-retrieved `【上下文】` section. Pinned items SHALL also appear in the `done` event's `sources` list with `kind` matching the underlying source table (knowledge / entry / note) so the UI can render and route them.

#### Scenario: pinned file content reaches the LLM
- **WHEN** `run_agent(queue, query, scope=["knowledge"], pinned_file_ids=["abc"])` is called and `_fetch_pinned_text("abc")` returns content `"PINNED BODY"`
- **THEN** the messages passed to the LLM include `"PINNED BODY"` in their context block under a `【引用文件】` section

#### Scenario: pinned files dedupe with vector-retrieved sources
- **WHEN** the same id appears both as a pinned id and in the vector search results
- **THEN** the `done` event's `sources` list includes the file exactly once

#### Scenario: unknown pinned ids are skipped silently
- **WHEN** a pinned id has no matching SQLite row
- **THEN** `run_agent` continues without raising; the unknown id is omitted from the context and from `done.sources`
