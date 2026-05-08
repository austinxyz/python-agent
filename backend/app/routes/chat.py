"""Chat API endpoints — POST /api/chat (SSE) + session list/detail."""
from __future__ import annotations

import json
import logging
import queue as _queue_mod
import sqlite3
import threading
import uuid
from typing import Any

from flask import Blueprint, Response, jsonify, request, stream_with_context

from app.graphs.qa_agent import run_agent, stream_response
from app.services.db_service import DatabaseService

logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat", __name__)

_USER_ID = "default"  # V1 single-tenant
_TITLE_MAX_LEN = 60


def _truncate_title(text: str) -> str:
    text = (text or "").strip().replace("\n", " ")
    if len(text) <= _TITLE_MAX_LEN:
        return text
    return text[:_TITLE_MAX_LEN] + "…"


def _row_to_session(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "model": row["model"],
        "created_at": row["created_at"],
    }


def _row_to_message(row: sqlite3.Row) -> dict[str, Any]:
    sources_raw = row["sources"] or "[]"
    try:
        sources = json.loads(sources_raw)
    except (json.JSONDecodeError, TypeError):
        sources = []
    return {
        "id": row["id"],
        "role": row["role"],
        "content": row["content"],
        "sources": sources if isinstance(sources, list) else [],
        "created_at": row["created_at"],
    }


def _load_history(conn: sqlite3.Connection, session_id: str) -> list[dict[str, str]]:
    """Return prior messages in the OpenAI/Anthropic chat shape."""
    rows = conn.execute(
        "SELECT role, content FROM chat_messages"
        " WHERE session_id = ? ORDER BY created_at, id",
        (session_id,),
    ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


@chat_bp.post("", strict_slashes=False)
def post_chat():
    payload = request.get_json(silent=True) or {}
    query = (payload.get("query") or "").strip()
    if not query:
        return jsonify({"error": "query is required"}), 400

    model = (payload.get("model") or "haiku").strip()
    scope = payload.get("scope") or ["knowledge"]
    if not isinstance(scope, list) or not scope:
        return jsonify({"error": "scope must be a non-empty array"}), 400

    incoming_session_id = payload.get("session_id")

    db = DatabaseService()

    # 1) Resolve / create the session row + persist the user message synchronously.
    history: list[dict[str, str]] = []
    with db.connection() as conn:
        if incoming_session_id:
            row = conn.execute(
                "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?",
                (incoming_session_id, _USER_ID),
            ).fetchone()
            if row is None:
                return jsonify({"error": "session not found"}), 404
            session_id = incoming_session_id
            history = _load_history(conn, session_id)
        else:
            session_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO chat_sessions (id, user_id, title, model)"
                " VALUES (?, ?, ?, ?)",
                (session_id, _USER_ID, _truncate_title(query), model),
            )

        user_msg_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO chat_messages (id, session_id, role, content, sources)"
            " VALUES (?, ?, 'user', ?, '[]')",
            (user_msg_id, session_id, query),
        )

    # 2) Run the agent in a background thread, streaming events via a queue.
    event_queue: _queue_mod.Queue = _queue_mod.Queue()
    assistant_chunks: list[str] = []
    final_sources: list[dict[str, Any]] = []

    def _agent_thread():
        try:
            run_agent(
                event_queue,
                query=query,
                scope=scope,
                model=model,
                history=history,
            )
        except Exception as exc:
            event_queue.put({"type": "error", "message": str(exc)})
            event_queue.put(None)

    thread = threading.Thread(target=_agent_thread, daemon=True)
    thread.start()

    # 3) Build the SSE generator. We tee events into the assistant message
    # buffers as we forward them so the assistant message can be persisted
    # after the stream completes — or after the client disconnects mid-stream
    # (the finally block runs on GeneratorExit too, so partial answers still
    # get saved instead of orphaning the user message in session history).
    def _generate():
        try:
            while True:
                ev = event_queue.get()
                if ev is None:
                    break
                if ev.get("type") == "token":
                    assistant_chunks.append(ev.get("content", ""))
                elif ev.get("type") == "done":
                    final_sources.extend(ev.get("sources", []) or [])
                    # Tag the done event with the resolved session_id so the
                    # frontend can wire up `chat_ref` when the user saves
                    # the answer to a private note.
                    ev["session_id"] = session_id
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        finally:
            try:
                db = DatabaseService()
                with db.connection() as conn:
                    conn.execute(
                        "INSERT INTO chat_messages (id, session_id, role, content, sources)"
                        " VALUES (?, ?, 'assistant', ?, ?)",
                        (
                            str(uuid.uuid4()),
                            session_id,
                            "".join(assistant_chunks),
                            json.dumps(final_sources, ensure_ascii=False),
                        ),
                    )
            except Exception:
                # Failing to persist is non-fatal for the user (they have
                # already received the answer in their browser) but it must
                # not be silent — log so post-mortem of any session-history
                # gap is straightforward.
                logger.exception("Failed to persist assistant message for session %s", session_id)

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",  # disable nginx buffering for live streams
    }
    return Response(
        stream_with_context(_generate()),
        mimetype="text/event-stream",
        headers=headers,
    )


@chat_bp.get("/sessions", strict_slashes=False)
def list_sessions():
    db = DatabaseService()
    with db.connection() as conn:
        rows = conn.execute(
            "SELECT id, title, model, created_at FROM chat_sessions"
            " WHERE user_id = ? ORDER BY created_at DESC, id DESC",
            (_USER_ID,),
        ).fetchall()
    return jsonify([_row_to_session(r) for r in rows])


@chat_bp.get("/sessions/<session_id>", strict_slashes=False)
def get_session(session_id: str):
    db = DatabaseService()
    with db.connection() as conn:
        srow = conn.execute(
            "SELECT id, title, model, created_at FROM chat_sessions"
            " WHERE id = ? AND user_id = ?",
            (session_id, _USER_ID),
        ).fetchone()
        if srow is None:
            return jsonify({"error": "session not found"}), 404
        msg_rows = conn.execute(
            "SELECT id, role, content, sources, created_at FROM chat_messages"
            " WHERE session_id = ? ORDER BY created_at, id",
            (session_id,),
        ).fetchall()
    out = _row_to_session(srow)
    out["messages"] = [_row_to_message(r) for r in msg_rows]
    return jsonify(out)
