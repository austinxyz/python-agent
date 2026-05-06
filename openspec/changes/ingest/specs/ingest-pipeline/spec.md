## ADDED Requirements

### Requirement: LangGraph IngestPipeline graph
The system SHALL implement a `IngestPipeline` class in `backend/app/graphs/ingest_pipeline.py` using `langgraph.graph.StateGraph`. The graph MUST execute nodes in fixed order: Source Router → Fetch → Clean → Chunk → Embed → Store → Summary. The graph state SHALL be a typed dict containing at minimum: `source_type`, `destination`, `user_id`, `raw_content`, `chunks`, `vectors`, `file_id`, `job_id`, `chunk_count`, `status`, `error`.

#### Scenario: Pipeline runs to completion for file source
- **WHEN** `IngestPipeline().run(source_type="file", content=<bytes>, filename="doc.pdf", destination="knowledge", user_id="default")` is called
- **THEN** the graph traverses all seven nodes without error and returns a state dict with `status="completed"`, `chunk_count >= 1`, and a non-null `file_id`

#### Scenario: Pipeline sets status to error on fetch failure
- **WHEN** the Fetch Node raises an exception (e.g., PDF parse error, unreachable URL)
- **THEN** the pipeline catches the exception, sets `status="error"` and `error=<message>` in the final state, and does not raise to the caller

### Requirement: Source Router node
The Source Router SHALL inspect `source_type` in the graph state and branch to the appropriate fetch strategy. Supported values: `file`, `url`, `text`, `mcp`. Unrecognised values SHALL set `status="error"` with a descriptive message and terminate the graph.

The `mcp` route is architecturally wired in this change so that V2 MCP implementation requires only filling in the Fetch Node — no graph restructuring. In this change the `mcp` Fetch branch returns `status="error"` with `"mcp not yet implemented"`.

#### Scenario: File, URL, and text source types are routed without error
- **WHEN** `source_type` is one of `"file"`, `"url"`, `"text"`
- **THEN** the Source Router sets the routing key and the graph proceeds to Fetch

#### Scenario: MCP source type is accepted but not yet implemented
- **WHEN** `source_type` is `"mcp"`
- **THEN** the Source Router routes to the MCP Fetch branch, which sets `status="error"` with message containing `"mcp not yet implemented"`

#### Scenario: Unrecognised source type terminates with error
- **WHEN** `source_type` is any value other than `"file"`, `"url"`, `"text"`, `"mcp"`
- **THEN** the pipeline returns `status="error"` with message containing `"unsupported source_type"`

### Requirement: Fetch Node
The Fetch Node SHALL extract raw text content according to `source_type`:
- `file`: extract text from the uploaded file bytes; PDF files MUST use PyMuPDF (`fitz`); `.txt` and `.md` files MUST detect encoding with `chardet` before decoding
- `url`: fetch the URL with `httpx` (5 s timeout); extract visible text from HTML using `html.parser`; non-HTML responses store raw text up to 1 MB
- `text`: pass `content` through directly as raw text
- `mcp`: set `status="error"` with `"mcp not yet implemented"` (stub; V2 will call MCP Client here)

#### Scenario: PDF text extraction succeeds
- **WHEN** source_type is `"file"` and the content is a valid PDF
- **THEN** Fetch Node populates `raw_content` with the concatenated text of all pages

#### Scenario: URL fetch respects timeout
- **WHEN** source_type is `"url"` and the remote server does not respond within 5 seconds
- **THEN** Fetch Node sets `status="error"` with a timeout message

#### Scenario: MCP fetch returns not-implemented error
- **WHEN** source_type is `"mcp"`
- **THEN** Fetch Node sets `status="error"` with message `"mcp not yet implemented"`

### Requirement: Clean Node
The Clean Node SHALL normalise `raw_content`: collapse runs of blank lines to a single blank line, strip leading/trailing whitespace, remove non-printable control characters (except newline and tab). The result SHALL be stored back into `raw_content`.

#### Scenario: Multiple blank lines are collapsed
- **WHEN** `raw_content` contains three or more consecutive blank lines
- **THEN** Clean Node reduces them to exactly one blank line

### Requirement: Chunk Node
The Chunk Node SHALL split `raw_content` into overlapping chunks targeting approximately 2 000 characters (≈ 512 tokens). The algorithm MUST:
1. Split on double-newlines (`\n\n`) first
2. If a paragraph exceeds 2 000 characters, split further at sentence boundaries (`.`, `?`, `!`)
3. Prepend the last 200 characters of the previous chunk to the next chunk (overlap)
4. Documents with total length ≤ 2 000 characters MUST produce exactly one chunk (no splitting)

Each chunk SHALL be stored in `chunks` as a list of dicts: `{text: str, chunk_index: int}`.

#### Scenario: Short document produces single chunk
- **WHEN** `raw_content` is 500 characters
- **THEN** `chunks` contains exactly one entry with `chunk_index=0`

#### Scenario: Long document produces multiple chunks with overlap
- **WHEN** `raw_content` contains three paragraphs each of 1 500 characters
- **THEN** `chunks` contains at least 2 entries; each entry after the first begins with the last 200 characters of the preceding chunk

### Requirement: Embed Node
The Embed Node SHALL call `EmbeddingService().embed(chunk["text"])` for each chunk in `chunks` and store the resulting 1536-float vector alongside the chunk. If embedding fails for any chunk, the pipeline SHALL set `status="error"` and stop.

#### Scenario: All chunks are embedded
- **WHEN** EmbeddingService returns successfully for each chunk
- **THEN** `vectors` contains one 1536-float list per chunk, in the same order as `chunks`

### Requirement: Store Node
The Store Node SHALL upsert each (chunk, vector) pair into the Qdrant collection specified by `destination`:
- `destination="knowledge"`: store in `knowledge` collection; payload MUST include `domain`, `topic`, `source_file_id`, `chunk_index`, `updated_at`, `status="draft"`, `text`
- `destination="private"`: store in `private` collection; payload MUST include `user_id` (from graph state), `topic`, `source_file_id`, `chunk_index`, `updated_at`, `text`; the `user_id` field MUST be set — it is never optional

The Store Node SHALL also call `FileService.register(...)` to insert a row into the SQLite `files` table and save the original content to `/app/uploads/{user_id}/{file_id}/`.

#### Scenario: Knowledge chunks stored without user_id
- **WHEN** `destination="knowledge"`
- **THEN** Qdrant upsert payload does NOT contain a `user_id` field

#### Scenario: Private chunks always carry user_id
- **WHEN** `destination="private"` and `user_id="default"`
- **THEN** every Qdrant upsert payload contains `user_id="default"` and `QdrantService.search_private` would find these chunks when called with `user_id="default"`

#### Scenario: File metadata registered in SQLite
- **WHEN** the Store Node completes successfully
- **THEN** a row exists in the `files` table with the correct `file_id`, `source_type`, `chunk_count`, and `user_id`

### Requirement: Summary Node
The Summary Node SHALL assemble and return the final pipeline result: `{job_id, file_id, chunk_count, status: "completed"}`. If any prior node set `status="error"`, Summary SHALL return `{job_id, status: "error", error: <message>}` without a `file_id` or `chunk_count`.

#### Scenario: Successful summary contains all fields
- **WHEN** all prior nodes succeed
- **THEN** Summary returns a dict with non-null `job_id`, `file_id`, `chunk_count >= 1`, `status="completed"`
