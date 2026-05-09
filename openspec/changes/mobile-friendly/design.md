## Context

The 4 views all follow the same desktop pattern (CLAUDE.md UI 公约): outer `AppLayout` sidebar (`w-56`/`w-16`) + inner gradient header + inner left sidebar (`w-60`–`w-72`) + flex-1 right panel. On a 393px iPhone, this stack collapses the right panel to ~80px. The NAS is now always-on at `10.0.0.20:8910` and the user wants to use the agent from phone — primarily ChatView for "路上问一个问题" flows.

This change is frontend-only. No backend, no API, no schema. The work breaks into infrastructure (AppLayout, TreeNav drawer mode) + per-view mobile passes, with ChatView getting the most polish.

## Goals / Non-Goals

**Goals:**
- 393×852 (iPhone 14) viewport: every view is usable; no horizontal scroll
- ChatView mobile feels native: sticky input, keyboard-aware viewport, master-detail sessions drawer
- Bottom tab nav replaces the desktop sidebar at `md-`; sidebar retained at `md+`
- Notion design system applied consistently — no leftover blue→purple gradient in nav chrome
- "Add to home screen" works (PWA manifest)
- Playwright mobile-viewport tests lock the critical flows

**Non-Goals:**
- Touch gestures (swipe-to-delete, long-press menus, pull-to-refresh) — V2
- Offline mode / service worker — NAS is always-on
- iPad-tuned layout — iPad portrait (768) treated as mobile per user direction; iPad landscape (1024) goes desktop
- Touch-only experience — keep the experience working on desktop unchanged
- Migrating away from Tailwind responsive utilities

## Decisions

### 1. Breakpoint at `md` (768px), not `sm` (640px) or `lg` (1024px)

**Choice:** `md-` = mobile layout, `md+` = desktop layout.

**Alternatives considered:**
- *`sm` (640) breakpoint*: phone landscape (~660–740) would land on desktop side, but desktop layout needs ~1000+ to look right. Bad.
- *`lg` (1024) breakpoint*: would treat iPad landscape as mobile too. The user said "iPad 当大手机吧但暂时不重要" — iPad portrait (768) goes mobile, but iPad landscape rarely sees this app and isn't worth a third layout. Going to `md` keeps it at two layouts.

**Why `md` wins:** matches the natural Tailwind breakpoint, gives iPad portrait a usable single-column experience, and avoids re-engineering desktop to fit smaller widths.

### 2. Bottom tab bar, not slide-out drawer for primary nav

**Choice:** below `md` the AppLayout sidebar becomes a 56px bottom tab bar.

**Alternatives considered:**
- *Hamburger drawer for AppLayout*: every primary nav action requires a tap-to-open. Two extra taps per page switch. Mobile users expect bottom tab bars in chat-style apps.
- *Top tab bar*: easy to mis-tap when reaching across the screen one-handed. Bottom is the iOS/Android norm for primary nav.

**Why bottom tabs win:** 4 nav items (知识库 / 摄入 / 对话 / 私有) is exactly within iOS HIG's recommended 3–5 tabs. Single tap navigation. Works one-handed.

### 3. TreeNav becomes a slide-in drawer for secondary nav (not bottom-sheet, not list-then-detail routes)

**Choice:** in WikiView/IngestView/PrivateView, a `☰` button in the page header opens the existing `TreeNav` as a full-width drawer that slides in from the left. Selecting a node closes the drawer and updates the right panel state-machine ref (the existing pattern).

**Alternatives considered:**
- *Bottom sheet*: trendy in Material Design, but cuts content height and doesn't fit a deep tree.
- *Master-detail with separate routes*: e.g., `/private` shows tree, `/private/:id` shows detail. Cleaner conceptually but requires touching every view's routing + back-button handling. The drawer pattern reuses the existing state-machine-ref convention with minimal change.
- *Always-collapsed accordion at top of page*: no drawer, just collapsed section. Worse: each tree-tap pushes content down, fighting scroll.

**Why drawer wins:** smallest deviation from the existing component (TreeNav unchanged at the API level — only its host view decides whether it lives inline or in a drawer), preserves the state-machine pattern, and matches the user's existing Notion-style UI vocabulary.

### 4. ChatView sessions go in `☰` drawer, NOT a dedicated `/chat/sessions` route

**Choice:** the sessions list is exposed via a `☰` drawer in the ChatView header on mobile. Active session URL stays `/chat/:id`. New session via `🆕` button (top-right).

**Alternatives considered:**
- *Separate `/chat/sessions` list page*: master-detail at the route level. More "native-app" feeling but adds a new view file, more router config, and the back button has to know what to go back to.
- *Drawer with both sessions + new-chat affordance*: pile both into the drawer. But "new chat" is the most-frequent action — burying it costs taps.

**Why this wins:** new-chat lives at `🆕` (one tap, always reachable); sessions list is one extra tap behind `☰`. Matches WhatsApp / Messenger layout conventions.

### 5. Sticky input + `100dvh`, not JS keyboard handlers

**Choice:** the messages container uses `h-[100dvh]` (dynamic viewport height — modern Safari/Chrome support); input is `position: sticky; bottom: 0` with `padding-bottom: env(safe-area-inset-bottom)`. No `visualViewport` JS event listeners.

**Alternatives considered:**
- *`window.visualViewport` events to manually adjust input position when keyboard pops*: works on iOS but flaky; Android handles `dvh` natively.
- *`100vh`*: classic broken-on-iOS-Safari pattern (vh doesn't shrink with keyboard). Replaced by `dvh`/`svh` precisely for this case.

**Why dvh wins:** zero JS, supported across iOS 16.4+ / Chrome 108+ / Safari 15.4+ — well within target audience. Falls back to `100vh` on older browsers (degraded but not broken).

### 6. Auto-scroll-to-bottom only when user is already near the bottom

**Choice:** when a new token streams in, scroll to bottom only if the user's scroll position is within ~100px of the bottom. Otherwise leave them where they are.

**Alternatives considered:**
- *Always scroll to bottom on new token*: breaks reading the middle of a long answer.
- *Never auto-scroll*: user has to manually chase tokens. Annoying.
- *Scroll-to-bottom floating button when scrolled up*: adds chrome. Maybe V2.

**Why this wins:** matches every modern chat client (iMessage, WhatsApp, Telegram). 

### 7. PWA manifest, no service worker

**Choice:** ship `manifest.json` + 3 icon PNGs + theme-color meta. No service worker.

**Alternatives considered:**
- *Full PWA with offline caching*: NAS is always-on at home wifi; offline mode would just confuse (data inconsistency between cached UI and real DB).
- *No PWA at all (just responsive web)*: misses the "add to home screen → launches like an app" affordance, which is a noticeable UX upgrade for ~30 min of work.

**Why minimal PWA wins:** captures the visible benefit (icon on home screen, hides browser chrome) without taking on cache-invalidation complexity.

## Risks / Trade-offs

- **iOS Safari `dvh` quirks** → fallback to `100vh` should still work; manual smoke test on iPhone Safari before ship.
- **Bottom tab bar overlapping chat input** → the input is `bottom: 0` of its container, the tab bar is `bottom: 0` of the layout — z-index needs explicit care; tested with Playwright mobile viewport.
- **TreeNav drawer animation jank on low-end Android** → use `transform: translateX` (GPU-accelerated) not `left`; defer if profiling shows it's a real issue.
- **Existing Playwright tests use desktop viewport** → mobile tests are additive; they don't replace desktop tests. Both run in `npm run e2e`.
- **Notion token rename if AppLayout's old `bg-primary/10` mapped to something else elsewhere** → audit `frontend/src/` for any other consumer of the old `primary` Tailwind class before removing it.
- **PWA icon design effort** → simple navy "知" character on lavender background; ~10 minutes in any image editor. Not blocking.

## Migration Plan

This is a frontend-only refactor — no data migration. Ship via the existing flow:

1. Implement the 5 task groups (AppLayout-Notion → AppLayout-responsive → ChatView-mobile → other-views-mobile → PWA + tests)
2. `./scripts/build-and-push.sh` — pushes `xuaustin/python-agent-frontend:vYYYYMMDD-<sha>`
3. NAS UGOS Docker UI → Project python-agent → Pull → Apply
4. Live test on phone (the user's iPhone via 10.0.0.20:8910 over home wifi); on desktop the layout should be unchanged

**Rollback:** if a regression appears, edit `docker-compose.yml` on NAS via UGOS file manager, pin `xuaustin/python-agent-frontend` to the previous `:vYYYYMMDD-<sha>` tag. Apply.

## Open Questions

None blocking. Two soft items:

1. Whether to add a "scroll to bottom" floating action button when chat is scrolled up. Defer to a follow-up if it bugs the user in actual use.
2. Whether to expose dark mode along with the Notion alignment work. Not in scope; would be its own change.
