## 1. AppLayout — Notion design alignment (no responsive change yet)

- [x] 1.1 RED — `frontend/tests/components/AppLayout.test.js`: 3 cases (no legacy gradient classes, active link has `bg-notion-tint-lavender` + `text-notion-brand-purple-800` + no leftover `bg-primary/10`, nav still has 4 items). 2/3 RED before edit.
- [x] 1.2 GREEN — `AppLayout.vue` rewritten with Notion tokens: logo `bg-notion-brand-navy`, surfaces `bg-notion-canvas`/`bg-notion-surface-soft`, hairlines `border-notion-hairline`, active state `bg-notion-tint-lavender text-notion-brand-purple-800`. Sidebar shape (w-56/w-16) unchanged.
- [x] 1.3 `npm test -- AppLayout` → 3/3. Full vitest → 142 passed (was 139, +3 net), no regressions.
- [x] 1.4 No other view consumer of `bg-primary/10` or `from-blue-500 to-purple-600` (the gradient lives only in view-level page headers per CLAUDE.md, which this change leaves alone at md+).
- [ ] 1.5 Run superpowers:requesting-code-review on the diff for group 1; address CRITICAL/HIGH.

## 2. AppLayout — responsive split (mobile bottom tabs / desktop sidebar)

- [x] 2.1 RED — added 4 cases: aside has `hidden md:flex`, `[data-bottom-tabs]` exists with `md:hidden` + 4 links, bottom-tabs has `pb-[env(safe-area-inset-bottom)]`, both desktop/mobile active links use the same Notion lavender/purple tokens. 3/4 RED before edit.
- [x] 2.2 GREEN — `AppLayout.vue` now renders both variants via Tailwind responsive utilities. `aside` is `hidden md:flex`; `<nav data-bottom-tabs>` is `md:hidden fixed bottom-0` with safe-area padding. Main content gets `pb-[calc(56px+env(safe-area-inset-bottom))] md:pb-0` so content doesn't sit under the tab bar.
- [x] 2.3 Run vitest — 7/7 green.
- [ ] 2.4 Run superpowers:requesting-code-review on the diff for group 2.

## 3. ChatView mobile rework (the flagship)

- [x] 3.1 RED — added 5 mobile-shape test cases in `tests/views/ChatView.test.js`: sessions sidebar hidden at md-, ☰/🆕 visible md:hidden, drawer toggle + drawer-session click closes drawer + loads session, 🆕 creates new session without drawer, input wrapper has `pb-[env(safe-area-inset-bottom)]` + root has `h-[100dvh]`. 5/5 RED.
- [x] 3.2 GREEN — `ChatView.vue` reworked: `data-chat-root` uses `h-[100dvh]`, mobile header has Menu/PlusSquare buttons (`md:hidden`), drawer overlay with backdrop + slide-in animation, `data-chat-input-wrap` has `pb-[env(safe-area-inset-bottom)]`. Send button = icon (`<Send />`) on mobile, "发送" label appears at sm+.
- [x] 3.3 RED — added 2 auto-scroll test cases: near-bottom triggers autoscroll, scrolled-up does NOT. 2/2 RED.
- [x] 3.4 GREEN — added `watch(messages.length)` with `NEAR_BOTTOM_THRESHOLD = 100`: only sets `scrollTop = scrollHeight - clientHeight` when `distanceFromBottom <= threshold`.
- [x] 3.5 Run vitest — 28/28 ChatView green; full suite 153 passed (was 142, +11 net).
- [x] 3.6 UI tokens — drawer/buttons use `notion-*` tokens throughout; mobile toolbar has `flex-wrap` so model/scope chips reflow on narrow screens; `px-4 sm:px-6` and `px-4 sm:px-8` give breathing room on phone.
- [ ] 3.7 Run superpowers:requesting-code-review on the diff for group 3 (this is the flagship, review carefully); address CRITICAL/HIGH.

## 4. Wiki / Private / Ingest mobile pass

- [x] 4.1 RED — added mobile cases to all 3 view tests: `data-tree-inline` hidden via `hidden md:flex`, `data-tree-toggle` md:hidden, drawer opens with `data-tree-drawer`, selecting a node closes drawer + updates right panel. PrivateView extra: `data-new-entry` ＋ button opens form without drawer. 10/10 RED.
- [x] 4.2 GREEN — created `frontend/src/components/MobileDrawer.vue` (generic slide-in panel + backdrop + close button + esc-to-close); wired into WikiView, PrivateView, IngestView with each view's own `drawerOpen` ref + drawer-aware click handlers (`onDrawerEntryClick`, `onDrawerSelectItem`, etc. close the drawer first).
- [x] 4.3 `TreeNav.vue` unmodified — those views never used it; they have inline tree DOM. The drawer renders a thin re-render of the same tree state, sharing `expandedDomains` / `expandedDirs` / store refs so behavior stays consistent.
- [x] 4.4 Full vitest — 163 passed (was 153, +10 net).
- [ ] 4.5 Run superpowers:requesting-code-review on the diff for group 4.

## 5. PWA + mobile Playwright coverage

- [x] 5.1 RED — `frontend/tests/pwa-manifest.test.js` asserts manifest exists, has all required fields (name, short_name, start_url, display, theme_color, background_color), 192/512/maskable icons, icon files exist, and `index.html` links the manifest + apple-touch-icon + theme-color. 5/5 RED.
- [x] 5.2 GREEN — wrote `frontend/public/manifest.json` (theme_color #0a1530 = Notion brand-navy), placeholder PNGs in `frontend/public/icons/`, and updated `index.html` with manifest/apple-touch-icon/theme-color/viewport-fit/apple-mobile-web-app-capable meta tags.
- [x] 5.3 Run vitest — 5/5 green.
- [x] 5.4 RED — `frontend/e2e/mobile.spec.ts` (7 tests covering bottom-tab visibility, ChatView ☰ drawer + 🆕 + send-message-with-streaming-mock, PrivateView ＋ + ☰ drawer, IngestView ☰ drawer). All RED before group 1-4 implementation; now GREEN.
- [x] 5.5 GREEN — used existing UI from groups 1-4. Switched playwright `mobile-chrome` project to chromium-emulating-iPhone-14 (Pixel 5 base + viewport/UA override) instead of webkit so we don't need the webkit browser binary on Windows.
- [x] 5.6 Brought up dev stack with `--build`; `npx playwright test mobile.spec.ts --project=mobile-chrome` → 7/7 green in 8s.
- [ ] 5.7 Run superpowers:requesting-code-review on the diff for group 5.

## 6. Verification and ship

- [x] 6.1 Run full backend pytest → 218 passed, 1 skipped, no regressions.
- [x] 6.2 Run full frontend vitest → 169 passed (was 139 pre-change, +30 net).
- [x] 6.3 Run full Playwright → 35 desktop + 7 mobile = 42 all green.
- [ ] 6.4 Manual smoke on the dev stack at desktop viewport — DEFERRED to user before NAS push.
- [ ] 6.5 Manual smoke on mobile viewport — DEFERRED to user (Chrome DevTools device toolbar).
- [x] 6.6 Verification-before-completion: full tests green; no console.log in frontend/src; spec matches reality.
- [x] 6.7 Final code review found 2 HIGH (safe-area padding stripped on devices without home indicator; auto-scroll watcher missed streaming-token mutations because it only watched messages.length) + 1 MEDIUM (tree DOM duplicated across 3 views — accept short-term, abstract on next tree-touching change) + 1 LOW (Pixel 5 base + iPhone viewport override is functional but cleaner to start from devices['iPhone 14'] — left as-is to avoid webkit dependency on Windows). Both HIGH issues fixed: padding now `pt-3 pb-[calc(12px+env(safe-area-inset-bottom))]`; watcher source now `[messages.length, last.content]` to follow streaming token mutations. Added regression test `autoscrolls when streaming tokens mutate the last message content`. 169 vitest + 7 mobile e2e re-verified green after fixes.

## Ship

- [x] S.1 `./scripts/build-and-push.sh` → tag `v20260508-23592c3` + `:latest` pushed to Docker Hub.
- [ ] S.2 NAS UGOS Docker app → Project python-agent → Pull → Apply. → USER step (UI-only).
- [ ] S.3 Live test on actual phone (user's iPhone via 10.0.0.20:8910 over home wifi). → USER step.
- [x] S.4 git add / commit (commit `23592c3`).
- [x] S.5 `git push`.
- [x] S.6 Update `docs/log/2026-05-08.md` with the deployment summary.
- [ ] S.7 `openspec archive mobile-friendly` — wait for user's S.2 + S.3 to verify before archiving.
