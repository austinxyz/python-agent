"""LangGraph IngestPipeline: Source Router → Fetch → Clean → Chunk → Embed → Store → Summary."""
import io
import re
import uuid
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import TypedDict

import fitz
import httpx
from langgraph.graph import END, StateGraph
from qdrant_client.http.models import PointStruct

from app.services.db_service import DatabaseService
from app.services.embedding_service import EmbeddingService
from app.services.file_service import FileService
from app.services.qdrant_service import QdrantService

CHUNK_SIZE = 2000
CHUNK_OVERLAP = 200
_SUPPORTED_SOURCES = {"file", "url", "text", "mcp"}


class IngestState(TypedDict):
    source_type: str
    destination: str
    user_id: str
    content: str | None
    file_content: bytes | None
    source_url: str | None
    filename: str | None
    orig_name: str
    domain: str
    topic: str
    title: str | None
    raw_content: str | None
    chunks: list[dict] | None
    vectors: list[list[float]] | None
    file_id: str
    job_id: str
    chunk_count: int
    size_bytes: int
    status: str
    error: str | None


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def source_router_node(state: IngestState) -> dict:
    if state["source_type"] not in _SUPPORTED_SOURCES:
        return {
            "status": "error",
            "error": f"unsupported source_type: {state['source_type']}",
        }
    return {}


def fetch_node(state: IngestState) -> dict:
    source_type = state["source_type"]
    try:
        if source_type == "text":
            return {"raw_content": state["content"] or ""}

        if source_type == "mcp":
            return {"status": "error", "error": "mcp not yet implemented"}

        if source_type == "file":
            raw = _extract_file_text(state["file_content"], state["filename"])
            return {"raw_content": raw}

        if source_type == "url":
            raw = _fetch_url_text(state["source_url"])
            return {"raw_content": raw}

    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    return {}


def _extract_file_text(content: bytes, filename: str | None) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        with fitz.open(stream=io.BytesIO(content), filetype="pdf") as doc:
            return "\n".join(page.get_text() for page in doc)
    import chardet
    detected = chardet.detect(content)
    encoding = detected.get("encoding") or "utf-8"
    return content.decode(encoding, errors="replace")


import ipaddress as _ipaddress

_BLOCKED_NETWORKS = [
    _ipaddress.ip_network("127.0.0.0/8"),
    _ipaddress.ip_network("10.0.0.0/8"),
    _ipaddress.ip_network("172.16.0.0/12"),
    _ipaddress.ip_network("192.168.0.0/16"),
    _ipaddress.ip_network("169.254.0.0/16"),
    _ipaddress.ip_network("::1/128"),
    _ipaddress.ip_network("fc00::/7"),
]


def _validate_url(url: str) -> None:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Only http/https URLs are allowed, got: {parsed.scheme!r}")
    host = (parsed.hostname or "").lower()
    if host in ("localhost", "localhost.localdomain"):
        raise ValueError(f"Requests to internal hosts are not allowed: {host!r}")
    try:
        addr = _ipaddress.ip_address(host)
        if any(addr in net for net in _BLOCKED_NETWORKS):
            raise ValueError(f"Requests to internal hosts are not allowed: {host!r}")
    except ValueError as exc:
        if "not allowed" in str(exc):
            raise
        # host is a hostname, not a raw IP — allow it


def _fetch_url_text(url: str) -> str:
    _validate_url(url)
    response = httpx.get(url, timeout=15.0, follow_redirects=True)
    # Validate the final URL after redirects to prevent SSRF via open redirects
    _validate_url(str(response.url))
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    raw = response.text[:1_048_576]
    if "html" in content_type:
        return _html_to_text(raw)
    return raw


class _HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            stripped = data.strip()
            if stripped:
                self._parts.append(stripped)

    def get_text(self) -> str:
        return " ".join(self._parts)


def _html_to_text(html: str) -> str:
    extractor = _HTMLTextExtractor()
    extractor.feed(html)
    return extractor.get_text()


def clean_node(state: IngestState) -> dict:
    text = state["raw_content"] or ""
    text = text.strip()
    # Remove non-printable control characters except newline (\n) and tab (\t)
    text = re.sub(r"[^\S\n\t]+", " ", text)           # collapse horizontal whitespace
    text = re.sub(r"[^\x09\x0a\x20-\x7e-￿]", "", text)  # strip control chars / null
    text = re.sub(r"\n{3,}", "\n\n", text)              # collapse 3+ blank lines → one
    text = text.strip()
    return {"raw_content": text}


def chunk_node(state: IngestState) -> dict:
    raw = state["raw_content"] or ""
    if len(raw) <= CHUNK_SIZE:
        return {"chunks": [{"text": raw, "chunk_index": 0}]}

    paragraphs = raw.split("\n\n")
    chunks: list[dict] = []
    current_parts: list[str] = []
    current_len = 0

    prev_tail = ""
    for para in paragraphs:
        para_parts = _split_paragraph(para)
        for part in para_parts:
            part_len = len(part)
            if current_len + part_len > CHUNK_SIZE and current_parts:
                body = "\n\n".join(current_parts).strip()
                chunk_text = prev_tail + body if prev_tail else body
                chunks.append({"text": chunk_text, "chunk_index": len(chunks)})
                prev_tail = chunk_text[-CHUNK_OVERLAP:] if len(chunk_text) >= CHUNK_OVERLAP else chunk_text
                current_parts = [part]
                current_len = part_len
            else:
                current_parts.append(part)
                current_len += part_len

    if current_parts:
        body = "\n\n".join(current_parts).strip()
        chunk_text = prev_tail + body if prev_tail else body
        chunks.append({"text": chunk_text, "chunk_index": len(chunks)})

    return {"chunks": chunks}


def _split_paragraph(para: str) -> list[str]:
    if len(para) <= CHUNK_SIZE:
        return [para]
    parts: list[str] = []
    sentences = re.split(r"(?<=[.?!])\s+", para)
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 > CHUNK_SIZE and current:
            parts.append(current.strip())
            current = sentence
        else:
            current = (current + " " + sentence).strip() if current else sentence
    if current:
        parts.append(current.strip())
    return parts or [para]


_SUPPORTED_DESTINATIONS = {"knowledge", "private"}


def embed_node(state: IngestState) -> dict:
    try:
        svc = EmbeddingService()
        chunks = state["chunks"] or []
        vectors = [svc.embed(chunk["text"]) for chunk in chunks]
        return {"vectors": vectors}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def store_node(state: IngestState) -> dict:
    try:
        destination = state["destination"]
        if destination not in _SUPPORTED_DESTINATIONS:
            return {"status": "error", "error": f"unsupported destination: {destination}"}

        qdrant = QdrantService()
        chunks = state["chunks"] or []
        vectors = state["vectors"] or []
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        file_id = state["file_id"]

        points = []
        for chunk, vector in zip(chunks, vectors):
            payload: dict = {
                "text": chunk["text"],
                "source_file_id": file_id,
                "chunk_index": chunk["chunk_index"],
                "domain": state["domain"],
                "topic": state["topic"],
                "updated_at": now,
            }
            if destination == "private":
                payload["user_id"] = state["user_id"]
            else:
                payload["status"] = "draft"

            points.append(PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload=payload,
            ))

        if destination == "private":
            qdrant.upsert_private(points)
        else:
            qdrant.upsert_knowledge(points)

        db = DatabaseService()
        file_svc = FileService()
        if state["source_type"] == "file" and state["file_content"]:
            file_svc.save(
                user_id=state["user_id"],
                file_id=file_id,
                filename=state["filename"] or f"{file_id}.bin",
                content=state["file_content"],
            )
        with db.connection() as conn:
            file_svc.register(
                conn,
                user_id=state["user_id"],
                file_id=file_id,
                orig_name=state["orig_name"],
                source_type=state["source_type"],
                source_url=state["source_url"],
                domain=state["domain"],
                topic=state["topic"],
                size_bytes=state["size_bytes"] or 0,
                chunk_count=len(chunks),
                filename=state["filename"],
                title=state.get("title"),
            )

        return {"chunk_count": len(chunks)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def summary_node(state: IngestState) -> dict:
    if state["status"] == "error":
        return {
            "status": "error",
            "error": state.get("error"),
            "file_id": None,
        }
    return {
        "status": "completed",
        "file_id": state["file_id"],
        "chunk_count": state["chunk_count"],
    }


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

def _should_continue(state: IngestState) -> str:
    return "summary" if state.get("status") == "error" else "continue"


def build_graph() -> StateGraph:
    graph = StateGraph(IngestState)

    graph.add_node("source_router", source_router_node)
    graph.add_node("fetch", fetch_node)
    graph.add_node("clean", clean_node)
    graph.add_node("chunk", chunk_node)
    graph.add_node("embed", embed_node)
    graph.add_node("store", store_node)
    graph.add_node("summary", summary_node)

    graph.set_entry_point("source_router")

    graph.add_conditional_edges(
        "source_router",
        _should_continue,
        {"summary": "summary", "continue": "fetch"},
    )
    graph.add_conditional_edges(
        "fetch",
        _should_continue,
        {"summary": "summary", "continue": "clean"},
    )
    graph.add_conditional_edges(
        "clean",
        _should_continue,
        {"summary": "summary", "continue": "chunk"},
    )
    graph.add_conditional_edges(
        "chunk",
        _should_continue,
        {"summary": "summary", "continue": "embed"},
    )
    graph.add_conditional_edges(
        "embed",
        _should_continue,
        {"summary": "summary", "continue": "store"},
    )
    graph.add_conditional_edges(
        "store",
        _should_continue,
        {"summary": "summary", "continue": "summary"},
    )
    graph.add_edge("summary", END)

    return graph


class IngestPipeline:
    def __init__(self) -> None:
        self._app = build_graph().compile()

    def run(
        self,
        source_type: str,
        destination: str,
        user_id: str,
        orig_name: str = "",
        domain: str = "general",
        topic: str = "general",
        title: str | None = None,
        content: str | None = None,
        file_content: bytes | None = None,
        filename: str | None = None,
        source_url: str | None = None,
        job_id: str | None = None,
        file_id: str | None = None,
    ) -> dict:
        if destination not in _SUPPORTED_DESTINATIONS:
            return {"status": "error", "error": f"unsupported destination: {destination}", "file_id": None}
        if destination == "private" and not user_id:
            return {"status": "error", "error": "user_id is required for private destination", "file_id": None}

        initial: IngestState = {
            "source_type": source_type,
            "destination": destination,
            "user_id": user_id,
            "content": content,
            "file_content": file_content,
            "source_url": source_url,
            "filename": filename,
            "orig_name": orig_name or filename or source_url or "",
            "domain": domain,
            "topic": topic,
            "title": title,
            "raw_content": None,
            "chunks": None,
            "vectors": None,
            "file_id": file_id or str(uuid.uuid4()),
            "job_id": job_id or str(uuid.uuid4()),
            "chunk_count": 0,
            "size_bytes": len(file_content) if file_content else len(content or ""),
            "status": "running",
            "error": None,
        }
        return self._app.invoke(initial)
