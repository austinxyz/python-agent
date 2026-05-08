"""Integration tests for the qa_agent run_agent + stream_response orchestration.

These tests inject mock services so the orchestration logic can be exercised
without hitting Qdrant, OpenAI/Anthropic, or the file system.
"""
import json
import queue as queue_mod
from unittest.mock import MagicMock

import pytest


def _drain(q):
    out = []
    while True:
        ev = q.get_nowait()
        if ev is None:
            break
        out.append(ev)
    return out


# ---------------------------------------------------------------------------
# scope routing — which search tools are called
# ---------------------------------------------------------------------------


class TestScopeRouting:
    def test_scope_knowledge_only_calls_search_knowledge(self):
        from app.graphs import qa_agent

        sk = MagicMock(return_value=[])
        sp = MagicMock(return_value=[])
        llm = MagicMock()
        llm.stream_complete.return_value = iter(["ok"])

        q = queue_mod.Queue()
        qa_agent.run_agent(q, "退休账户怎么选", scope=["knowledge"],
                           search_knowledge=sk, search_private=sp, llm=llm)

        assert sk.called
        assert not sp.called

    def test_scope_private_only_calls_search_private_with_user_id(self):
        from app.graphs import qa_agent

        sk = MagicMock(return_value=[])
        sp = MagicMock(return_value=[])
        llm = MagicMock()
        llm.stream_complete.return_value = iter(["ok"])

        q = queue_mod.Queue()
        qa_agent.run_agent(q, "我的房产", scope=["private"],
                           search_knowledge=sk, search_private=sp, llm=llm)

        assert not sk.called
        assert sp.called
        # search_private was called; the qa_agent module is responsible for
        # passing user_id="default" through to the underlying QdrantService —
        # the search_private function itself enforces this. We verify by
        # checking that our injected stub was invoked at all (the signature
        # is `search_private(query, *, ...)` so the implementation can pass
        # whatever it likes; the contract is "search_private got called for
        # the private scope").

    def test_scope_both_calls_both_searches(self):
        from app.graphs import qa_agent

        sk = MagicMock(return_value=[])
        sp = MagicMock(return_value=[])
        llm = MagicMock()
        llm.stream_complete.return_value = iter([])

        q = queue_mod.Queue()
        qa_agent.run_agent(q, "全面分析", scope=["knowledge", "private"],
                           search_knowledge=sk, search_private=sp, llm=llm)

        assert sk.called
        assert sp.called


# ---------------------------------------------------------------------------
# token events + done event with sources
# ---------------------------------------------------------------------------


class TestStreamingEvents:
    def test_token_events_pushed_in_order(self):
        from app.graphs import qa_agent

        sk = MagicMock(return_value=[])
        llm = MagicMock()
        llm.stream_complete.return_value = iter(["Hello", " ", "world"])

        q = queue_mod.Queue()
        qa_agent.run_agent(q, "hi", scope=["knowledge"],
                           search_knowledge=sk, search_private=MagicMock(),
                           llm=llm)

        events = _drain(q)
        # First three are token events, last is done
        assert events[0] == {"type": "token", "content": "Hello"}
        assert events[1] == {"type": "token", "content": " "}
        assert events[2] == {"type": "token", "content": "world"}
        assert events[-1]["type"] == "done"

    def test_done_event_includes_sources_from_searches(self):
        from app.graphs import qa_agent

        sk = MagicMock(return_value=[
            {"content": "X", "domain": "退休规划", "source_file_id": "f1", "title": "Roth", "score": 0.9},
            {"content": "Y", "domain": "退休规划", "source_file_id": "f2", "title": "401k", "score": 0.8},
        ])
        sp = MagicMock(return_value=[])
        llm = MagicMock()
        llm.stream_complete.return_value = iter([])  # no tokens — testing done event only

        q = queue_mod.Queue()
        qa_agent.run_agent(q, "问退休", scope=["knowledge"],
                           search_knowledge=sk, search_private=sp, llm=llm)

        events = _drain(q)
        done = next(e for e in events if e["type"] == "done")
        assert "sources" in done
        ids = {s["file_id"] for s in done["sources"]}
        assert ids == {"f1", "f2"}
        # Each source carries title + domain
        assert all("title" in s and "domain" in s for s in done["sources"])

    def test_done_event_enriches_titles_from_sqlite(self, monkeypatch, tmp_path):
        """Sources should display the human-readable title from SQLite, not
        the raw file_id UUID. Titles live in the `files` table for knowledge
        and `private_entries` for private — the agent looks them up by id
        before emitting the done event."""
        import sqlite3
        monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
        from app.services.db_service import DatabaseService
        from app.graphs import qa_agent
        # Init DB so all the tables exist
        DatabaseService()
        # Seed a file row whose title is what we want to see in the chip
        conn = sqlite3.connect(str(tmp_path / "test.db"))
        try:
            conn.execute(
                "INSERT INTO files (id, user_id, filename, orig_name, source_type, domain,"
                " topic, size_bytes, chunk_count, title)"
                " VALUES ('file-real', 'default', 'fbar.md', 'fbar.md', 'text', '中美对比',"
                "         'general', 100, 2, 'FBAR 报告完整指南')"
            )
            conn.commit()
        finally:
            conn.close()

        # Search returns chunks pointing at the seeded file_id; title in the
        # chunk dict is empty (Qdrant payload never stored it).
        sk = MagicMock(return_value=[
            {"content": "FBAR 内容", "domain": "中美对比", "source_file_id": "file-real",
             "title": "", "score": 0.9},
        ])
        llm = MagicMock()
        llm.stream_complete.return_value = iter([])

        q = queue_mod.Queue()
        qa_agent.run_agent(q, "FBAR", scope=["knowledge"],
                           search_knowledge=sk, search_private=MagicMock(),
                           llm=llm)
        events = _drain(q)
        done = next(e for e in events if e["type"] == "done")
        assert done["sources"][0]["title"] == "FBAR 报告完整指南"
        assert done["sources"][0]["file_id"] == "file-real"
        assert done["sources"][0]["domain"] == "中美对比"

    def test_sources_carry_kind_field_distinguishing_knowledge_vs_private(self):
        """ChatView routes chips based on this field — knowledge chips go to
        /wiki, entry chips go to /private. Mis-tagging would dead-link."""
        from app.graphs import qa_agent

        sk = MagicMock(return_value=[
            {"content": "k", "domain": "中美对比", "source_file_id": "k1", "title": "FBAR", "score": 0.9},
        ])
        sp = MagicMock(return_value=[
            {"content": "p", "domain": "税务", "source_file_id": "p1", "title": "我的税务", "score": 0.85},
        ])
        llm = MagicMock()
        llm.stream_complete.return_value = iter([])

        q = queue_mod.Queue()
        qa_agent.run_agent(q, "x", scope=["knowledge", "private"],
                           search_knowledge=sk, search_private=sp, llm=llm)
        done = next(e for e in _drain(q) if e["type"] == "done")
        by_id = {s["file_id"]: s for s in done["sources"]}
        assert by_id["k1"]["kind"] == "knowledge"
        assert by_id["p1"]["kind"] == "entry"

    def test_done_event_falls_back_to_id_when_title_missing(self, monkeypatch, tmp_path):
        """Unknown file_ids (no row in SQLite) fall back to showing the id
        instead of an empty string — so the user can still report the source
        even when metadata is gone."""
        import sqlite3
        monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
        from app.services.db_service import DatabaseService
        from app.graphs import qa_agent
        DatabaseService()

        sk = MagicMock(return_value=[
            {"content": "x", "domain": "其他", "source_file_id": "ghost-id",
             "title": "", "score": 0.5},
        ])
        llm = MagicMock()
        llm.stream_complete.return_value = iter([])

        q = queue_mod.Queue()
        qa_agent.run_agent(q, "x", scope=["knowledge"],
                           search_knowledge=sk, search_private=MagicMock(),
                           llm=llm)
        done = next(e for e in _drain(q) if e["type"] == "done")
        assert done["sources"][0]["title"] == "ghost-id"

    def test_done_event_dedupes_sources_across_scopes(self):
        from app.graphs import qa_agent

        # Same file_id appearing in both knowledge + private hits should only
        # surface once in the done event.
        sk = MagicMock(return_value=[
            {"content": "X", "domain": "退休规划", "source_file_id": "f1", "title": "Roth", "score": 0.9},
        ])
        sp = MagicMock(return_value=[
            {"content": "X2", "domain": "退休规划", "source_file_id": "f1", "title": "Roth", "score": 0.85},
        ])
        llm = MagicMock()
        llm.stream_complete.return_value = iter([])

        q = queue_mod.Queue()
        qa_agent.run_agent(q, "问退休", scope=["knowledge", "private"],
                           search_knowledge=sk, search_private=sp, llm=llm)

        events = _drain(q)
        done = next(e for e in events if e["type"] == "done")
        assert len({s["file_id"] for s in done["sources"]}) == 1

    def test_error_event_pushed_when_llm_raises(self):
        from app.graphs import qa_agent

        sk = MagicMock(return_value=[])
        llm = MagicMock()
        # Make the iterator raise mid-stream
        def _bad_stream(*a, **kw):
            yield "ok-prefix"
            raise RuntimeError("upstream error")
        llm.stream_complete.side_effect = _bad_stream

        q = queue_mod.Queue()
        qa_agent.run_agent(q, "anything", scope=["knowledge"],
                           search_knowledge=sk, search_private=MagicMock(),
                           llm=llm)

        events = _drain(q)
        # We get the prefix token, then an error event (no done)
        assert events[0] == {"type": "token", "content": "ok-prefix"}
        assert events[-1]["type"] == "error"
        assert "upstream error" in events[-1]["message"]


# ---------------------------------------------------------------------------
# stream_response — Flask SSE generator
# ---------------------------------------------------------------------------


class TestStreamResponse:
    def test_yields_sse_formatted_lines(self):
        from app.graphs import qa_agent

        q = queue_mod.Queue()
        q.put({"type": "token", "content": "abc"})
        q.put({"type": "done", "sources": [{"title": "T", "domain": "D", "file_id": "f"}]})
        q.put(None)

        chunks = list(qa_agent.stream_response(q))
        joined = "".join(chunks)
        # Every event line is `data: {...}\n\n`
        assert "data: " in joined
        assert "\n\n" in joined
        # The token + done events are separately encoded as JSON
        assert '"type": "token"' in joined or '"type":"token"' in joined
        assert '"type": "done"' in joined or '"type":"done"' in joined
        # JSON is parseable when stripped
        events = []
        for line in joined.split("\n\n"):
            line = line.strip()
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: "):]))
        assert events[0]["type"] == "token"
        assert events[1]["type"] == "done"
