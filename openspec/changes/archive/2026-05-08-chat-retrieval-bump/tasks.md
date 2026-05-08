## 1. Bump default top-k

- [x] 1.1 RED — `tests/test_qa_agent_tools.py`: 3 new tests (knowledge default=10, knowledge override works, private default=10)
- [x] 1.2 GREEN — defaults changed in `qa_agent.search_knowledge` and `qa_agent.search_private` from 5 to 10
- [x] 1.3 Run `cd backend && pytest` — full suite green (179 → 182)
- [x] 1.4 Live smoke verified: same FBAR/FATCA question now retrieves `绿卡放弃vs保留分析`, `保留绿卡行动计划`, `资产全景`, `报税表格清单` (entries) plus 6 knowledge sources. The previously-missed private file is now in the LLM context.

## 2. Ship

- [ ] 2.1 Commit + push (with the chat-file-pinning backlog change folder)
- [ ] 2.2 `openspec archive chat-retrieval-bump`
