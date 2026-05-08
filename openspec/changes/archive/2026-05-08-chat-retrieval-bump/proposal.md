## Why

The QA agent's vector search retrieves only top-5 chunks per scope.
A real-use failure on 2026-05-08: user asked "我更新了很多个人信息，
你再看看我需要怎么处理FBAR/FATCA"; the answer-bearing file
`绿卡放弃 vs 保留分析` (46k chars, ~25 chunks, FBAR mentioned in 2
paragraphs) had the relevant content but FBAR-specific chunks were
beaten in top-5 by green-card-decision content with higher topic
similarity to the query's first half. The LLM said "信息不足"
because the chunks it actually saw didn't contain the answer.

This change is the cheap half of the recall fix: bump default top-k
from 5 to 10. The expensive half (explicit per-turn file pinning)
sits as a backlog change `chat-file-pinning`.

## What Changes

- `qa_agent.search_knowledge(..., limit=10)` and
  `search_private(..., limit=10)` defaults change from 5 to 10.
  Tests updated. Callers can still override per-call.
- No frontend change. No API contract change. Costs ≈ +1-2s latency
  and ~10k extra context tokens per turn — negligible at personal
  scale.

## Capabilities

### Modified Capabilities

- `qa-agent`: retrieval breadth doubled

## Impact

- **Backend**: 2 default-arg changes in `qa_agent.py`; 3 new pytest
  cases; existing tests unaffected.
- **Frontend**: nothing.
- **Live verified 2026-05-08**: same FBAR/FATCA query now retrieves
  the previously-missed `绿卡放弃vs保留分析`, `保留绿卡行动计划`,
  `资产全景`, `报税表格清单` private entries plus 6 knowledge sources
  (FATCA / FBAR / Form-8938 / 跨境资产申报与处理 / PFIC /
  Foreign-Tax-Credit). The LLM context now contains the user's
  actual personal info on the topic.

## Non-Goals

- Re-ranking, query rewriting, hybrid search (separate change if A
  proves insufficient)
- Bumping limit further (15+) — diminishing returns; revisit if more
  failure cases appear
- Explicit per-turn file pinning — lives in `chat-file-pinning`
  (backlog as of 2026-05-08)
