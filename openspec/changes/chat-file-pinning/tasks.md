## 1. Backend: fetch helper

- [ ] 1.1 RED — `tests/test_qa_agent_tools.py`: `_fetch_pinned_text` returns `{kind, title, domain, file_id, content}` for a knowledge file (mock `files` row + on-disk text), a private entry (mock `private_entries` row, `derive_text_for_embedding` produces the content), and a note (mock `notes` row); returns `None` for unknown id
- [ ] 1.2 GREEN — add `_fetch_pinned_text(file_id, *, user_id="default")` in `qa_agent.py`; probe `files` (use `FileService.resolve` + read `<file_id>.txt`), then `private_entries` (use `derive_text_for_embedding` on parsed content_json), then `notes` (raw content)
- [ ] 1.3 Run pytest — green

## 2. Backend: run_agent injects pinned content

- [ ] 2.1 RED — `tests/test_qa_agent_run.py`: with mock `_fetch_pinned_text` returning a known body, assert (a) the messages passed to the LLM contain "【引用文件】" + the body; (b) the `done` event's sources include the pinned item with `kind` matching the source table; (c) duplicate id (same file appears as both pinned and in vector results) appears once in `sources`; (d) unknown pinned id is silently skipped
- [ ] 2.2 GREEN — add `pinned_file_ids: list[str] = []` to `run_agent`; resolve via `_fetch_pinned_text`; prepend a `【引用文件】` block to messages ahead of `【上下文】`; merge into the deduped sources list
- [ ] 2.3 Run pytest — green

## 3. Backend: route accepts the field

- [ ] 3.1 RED — `tests/test_chat_routes.py`: assert `POST /api/chat` with `pinned_file_ids: ["abc"]` calls `run_agent` with that list (use side_effect of the existing `_fake_agent_streaming_run` pattern + a kwarg capture)
- [ ] 3.2 GREEN — `routes/chat.py::post_chat` reads `pinned_file_ids` from JSON body (default `[]`), passes through to `run_agent`
- [ ] 3.3 Run pytest — green

## 4. Frontend store

- [ ] 4.1 RED — `tests/stores/chat.test.js`: `sendMessage(query, { pinnedFileIds: ["a","b"] })` puts `pinned_file_ids: ["a","b"]` in the POST body; without `pinnedFileIds` the field is absent or empty
- [ ] 4.2 GREEN — extend `chat.js::sendMessage` signature to accept `pinnedFileIds`; include in POST body
- [ ] 4.3 Run vitest — green

## 5. Frontend ChatView

- [ ] 5.1 RED — `tests/views/ChatView.test.js`: (a) `data-pin-btn` visible; (b) clicking opens `data-pin-picker` with rows from `store.entries` + `store.notes`; (c) typing in `data-pin-search` filters the list; (d) clicking an item adds a `data-pin-chip`; (e) `✕` on chip removes it; (f) clicking send forwards the pinned ids to `store.sendMessage`; (g) chips clear after the stream completes
- [ ] 5.2 GREEN — implement picker UI, chip render, search filter, pinnedItems ref, integration with `submit()`; clear pins after `sendMessage` resolves
- [ ] 5.3 Apply UI design — buttons match `notion-*` token vocabulary; modal uses `bg-notion-canvas` + hairline border; chips use `bg-notion-tint-yellow` (3rd variant alongside lavender/mint)
- [ ] 5.4 Run vitest — full frontend green

## 6. E2E

- [ ] 6.1 Add a Playwright test in `e2e/chat.spec.ts`: open picker, pin one entry, send, verify the POST body contains `pinned_file_ids`; verify pin chips clear after streaming

## 7. Verification

- [ ] 7.1 Run full backend pytest, full vitest, full Playwright — all green
- [ ] 7.2 Live smoke: pin `绿卡放弃 vs 保留分析` and ask the FBAR/FATCA question; confirm the answer cites that file's content (not generic guidance)
- [ ] 7.3 Update dev log with pinning summary
- [ ] 7.4 superpowers:requesting-code-review on the diff; address CRITICAL/HIGH

## Ship

- [ ] S.1 Commit + push
- [ ] S.2 `openspec archive chat-file-pinning`
