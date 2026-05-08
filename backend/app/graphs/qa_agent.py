"""QA agent — LangGraph ReAct over Qdrant.

This module exposes three tool functions and (later) a LangGraph that wires
them up. The tool functions are plain Python so unit tests can call them
directly with mocked services.

Conventions:
- `search_knowledge` searches the shared `knowledge` Qdrant collection.
  No `user_id` filter — knowledge is global to all users.
- `search_private` searches the per-user `private` collection. The
  `user_id="default"` filter is mandatory for V1 single-tenant.
- `get_entry` reads the plain-text representation of an ingested document
  from disk (stored at `UPLOADS_PATH/<user_id>/<file_id>/<file_id>.txt`
  for text/url ingestions; PDFs are not yet text-extracted on read).

The agent graph + SSE streaming live below in `run_agent` / `stream_response`.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.services.embedding_service import EmbeddingService
from app.services.qdrant_service import QdrantService

DEFAULT_USER_ID = "default"


def _format_point(p: Any) -> dict[str, Any]:
    """Convert a Qdrant search result point to a flat dict.

    The ingest pipeline writes the chunk text under payload key `text` (see
    ingest_pipeline._embed_node). Earlier private-entries upserts used
    `content` for the embedded body. Read both so the QA agent works against
    either shape — `text` first since that is what knowledge collection
    actually contains.
    """
    payload = getattr(p, "payload", {}) or {}
    return {
        "content": payload.get("text") or payload.get("content") or "",
        "domain": payload.get("domain") or payload.get("template_type") or payload.get("directory") or "",
        "source_file_id": payload.get("source_file_id", ""),
        "score": float(getattr(p, "score", 0.0) or 0.0),
        "title": payload.get("title", ""),
    }


def search_knowledge(
    query: str,
    domain: str | None = None,
    *,
    limit: int = 5,
    embedding: EmbeddingService | None = None,
    qdrant: QdrantService | None = None,
) -> list[dict[str, Any]]:
    """Search the shared knowledge collection. Returns formatted chunks."""
    embedding = embedding or EmbeddingService()
    qdrant = qdrant or QdrantService()
    vector = embedding.embed(query)
    kwargs: dict[str, Any] = {"limit": limit}
    if domain:
        kwargs["domain"] = domain
    points = qdrant.search_knowledge(vector, **kwargs)
    return [_format_point(p) for p in points]


def search_private(
    query: str,
    *,
    limit: int = 5,
    embedding: EmbeddingService | None = None,
    qdrant: QdrantService | None = None,
    user_id: str = DEFAULT_USER_ID,
) -> list[dict[str, Any]]:
    """Search the user's private collection. user_id filter is mandatory."""
    embedding = embedding or EmbeddingService()
    qdrant = qdrant or QdrantService()
    vector = embedding.embed(query)
    points = qdrant.search_private(vector, user_id=user_id, limit=limit)
    return [_format_point(p) for p in points]


def get_entry(file_id: str, *, user_id: str = DEFAULT_USER_ID) -> str:
    """Read the plain-text content of a stored knowledge entry.

    Looks under `UPLOADS_PATH/<user_id>/<file_id>/<file_id>.txt`. Returns
    a human-readable error marker (not an exception) when the file is
    missing — the LLM must keep going and reply gracefully.
    """
    base = Path(os.environ.get("UPLOADS_PATH", "/app/uploads")).resolve()
    candidate = (base / user_id / file_id / f"{file_id}.txt").resolve()
    # Path-traversal guard: refuse paths that escape the base
    try:
        if not candidate.is_relative_to(base):
            return f"Entry {file_id} not found (invalid path)."
    except AttributeError:
        # Older Pythons: fallback to string check
        if not str(candidate).startswith(str(base)):
            return f"Entry {file_id} not found (invalid path)."
    if not candidate.is_file():
        return f"Entry {file_id} not found."
    return candidate.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Orchestration: deterministic RAG chain (V1) — see design.md §2 for the
# rationale for not using LangGraph's create_react_agent in V1.
# ---------------------------------------------------------------------------

import json
import queue as _queue_mod
from typing import Iterable, Iterator

# Default system prompt — terse, RAG-grounded, no-hallucination instruction.
SYSTEM_PROMPT = (
    "你是一个个人金融知识助手。基于提供的【上下文】片段回答用户问题。"
    "如果上下文不足以回答，请明确说明信息不足，不要编造。"
    "回答用中文，简洁清晰，必要时分点列出。"
)


def _build_context_block(chunks: list[dict]) -> str:
    """Render retrieved chunks as a single context string for the LLM."""
    if not chunks:
        return "（无相关上下文）"
    lines: list[str] = []
    for i, c in enumerate(chunks, start=1):
        title = c.get("title") or c.get("source_file_id", "")
        domain = c.get("domain", "")
        content = c.get("content", "")
        lines.append(f"[{i}] {title} · {domain}\n{content}")
    return "\n\n".join(lines)


def _build_messages(query: str, chunks: list[dict], history: list[dict] | None) -> list[dict]:
    """Compose the final messages array for the LLM call."""
    history = history or []
    user_with_context = (
        f"【上下文】\n{_build_context_block(chunks)}\n\n"
        f"【问题】\n{query}"
    )
    return [*history, {"role": "user", "content": user_with_context}]


def _to_source(chunk: dict, titles: dict[str, str] | None = None) -> dict:
    fid = chunk.get("source_file_id", "")
    title_from_db = (titles or {}).get(fid)
    return {
        # Prefer the human-readable title from SQLite (set by the ingest
        # pipeline / private-entry create) over the empty string in the
        # Qdrant payload; fall back to the chunk's own title hint, then to
        # the file_id so the source is still identifiable.
        "title": title_from_db or chunk.get("title") or fid,
        "domain": chunk.get("domain", ""),
        "file_id": fid,
        # `kind` tells the frontend whether to route the chip to /wiki
        # (knowledge file) or /private (private entry). Defaults to
        # knowledge when unset so legacy chunks don't dead-link.
        "kind": chunk.get("_kind") or "knowledge",
    }


def _lookup_titles(file_ids: list[str]) -> dict[str, str]:
    """Return a {file_id: title} mapping by querying SQLite.

    Knowledge file titles live in `files.title` (falling back to `orig_name`).
    Private entry titles live in `private_entries.title`. Unknown ids are
    simply absent from the result so the caller can fall back gracefully.
    """
    if not file_ids:
        return {}
    from app.services.db_service import DatabaseService

    titles: dict[str, str] = {}
    placeholders = ",".join("?" * len(file_ids))
    with DatabaseService().connection() as conn:
        for row in conn.execute(
            f"SELECT id, title, orig_name FROM files WHERE id IN ({placeholders})",
            file_ids,
        ).fetchall():
            fid = row[0]
            titles[fid] = row[1] or row[2] or fid
        for row in conn.execute(
            f"SELECT id, title FROM private_entries WHERE id IN ({placeholders})",
            file_ids,
        ).fetchall():
            fid = row[0]
            titles[fid] = row[1] or titles.get(fid) or fid
    return titles


def run_agent(
    queue,
    query: str,
    scope: list[str],
    *,
    model: str = "haiku",
    history: list[dict] | None = None,
    search_knowledge=search_knowledge,
    search_private=search_private,
    llm=None,
) -> None:
    """Drive a single Q&A turn and push events onto `queue`.

    Event shapes pushed:
        {"type": "token",  "content": "..."}      one per LLM text fragment
        {"type": "done",   "sources": [...]}      single, after the LLM finishes
        {"type": "error",  "message": "..."}      single, on exception
    Then `None` as a sentinel so the SSE generator can finish.

    `scope` is a list of {"knowledge", "private"}. Each scope present triggers
    its corresponding pre-search; `private` is always called with the user_id
    filter via the underlying `search_private` tool function.
    """
    try:
        from app.services.llm_service import LlmService
        llm = llm or LlmService()

        # Pre-search per scope. We tag each chunk with `_kind` so the source
        # chip in the UI can route to the right page (knowledge → /wiki,
        # private entry → /private). The tag is dropped before the LLM sees
        # the context (LLM only cares about content + domain).
        all_chunks: list[dict] = []
        if "knowledge" in scope:
            try:
                for c in (search_knowledge(query) or []):
                    all_chunks.append({**c, "_kind": "knowledge"})
            except Exception as e:
                queue.put({"type": "error", "message": f"search_knowledge failed: {e}"})
                return
        if "private" in scope:
            try:
                for c in (search_private(query) or []):
                    all_chunks.append({**c, "_kind": "entry"})
            except Exception as e:
                queue.put({"type": "error", "message": f"search_private failed: {e}"})
                return

        # Look up the human-readable title for every retrieved file once,
        # then attach it to each source so the UI shows "FBAR" instead of a
        # raw UUID. Best-effort — if SQLite is unavailable we fall back to
        # the file_id, never crash.
        unique_ids = list({c.get("source_file_id", "") for c in all_chunks if c.get("source_file_id")})
        try:
            titles = _lookup_titles(unique_ids)
        except Exception:
            titles = {}

        seen_ids: set[str] = set()
        sources: list[dict] = []
        for c in all_chunks:
            fid = c.get("source_file_id", "")
            if fid in seen_ids:
                continue
            seen_ids.add(fid)
            sources.append(_to_source(c, titles))

        messages = _build_messages(query, all_chunks, history)

        # Stream tokens. Errors mid-stream emit an `error` event and skip done.
        for token in llm.stream_complete(messages, system=SYSTEM_PROMPT, model=model):
            queue.put({"type": "token", "content": token})
        queue.put({"type": "done", "sources": sources})
    except Exception as e:
        queue.put({"type": "error", "message": str(e)})
    finally:
        queue.put(None)


def stream_response(queue) -> Iterator[str]:
    """Flask SSE generator. Reads events from `queue` until None sentinel."""
    while True:
        ev = queue.get()
        if ev is None:
            return
        yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
