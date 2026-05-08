"""Shared text chunker used by knowledge ingest and private entries.

The algorithm is paragraph-aware (split on `\n\n` first), falls back to
sentence-level splitting for any single paragraph longer than CHUNK_SIZE,
and emits character-level overlap (CHUNK_OVERLAP) between adjacent chunks
so retrieval doesn't sever a passage right at a chunk boundary.

This was originally inline in `ingest_pipeline.chunk_node` and was lifted
out here when private entries needed the same algorithm to avoid the
8192-token embedding cap on long personal-finance documents.
"""
from __future__ import annotations

import re

CHUNK_SIZE = 2000
CHUNK_OVERLAP = 200


def chunk_text(content: str, *, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """Split `content` into character-bounded chunks with overlap.

    Returns `[{"text": str, "chunk_index": int}, ...]`. Always returns at
    least one chunk (even for empty input) so callers can iterate without
    a None check.
    """
    raw = content or ""
    if len(raw) <= size:
        return [{"text": raw, "chunk_index": 0}]

    paragraphs = raw.split("\n\n")
    chunks: list[dict] = []
    current_parts: list[str] = []
    current_len = 0
    prev_tail = ""

    for para in paragraphs:
        para_parts = _split_paragraph(para, size=size)
        for part in para_parts:
            part_len = len(part)
            if current_len + part_len > size and current_parts:
                body = "\n\n".join(current_parts).strip()
                chunk_text_val = prev_tail + body if prev_tail else body
                chunks.append({"text": chunk_text_val, "chunk_index": len(chunks)})
                prev_tail = chunk_text_val[-overlap:] if len(chunk_text_val) >= overlap else chunk_text_val
                current_parts = [part]
                current_len = part_len
            else:
                current_parts.append(part)
                current_len += part_len

    if current_parts:
        body = "\n\n".join(current_parts).strip()
        chunk_text_val = prev_tail + body if prev_tail else body
        chunks.append({"text": chunk_text_val, "chunk_index": len(chunks)})

    return chunks


def _split_paragraph(para: str, *, size: int = CHUNK_SIZE) -> list[str]:
    if len(para) <= size:
        return [para]
    parts: list[str] = []
    sentences = re.split(r"(?<=[.?!])\s+", para)
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 > size and current:
            parts.append(current.strip())
            current = sentence
        else:
            current = (current + " " + sentence).strip() if current else sentence
    if current:
        parts.append(current.strip())
    return parts or [para]
