## Why

The python-agent now lives on the always-on NAS at `10.0.0.20:8910`, but every view assumes a desktop viewport: `AppLayout.vue` keeps a 224px sidebar, and each view layers a second 240–288px sidebar on top of the gradient header (CLAUDE.md UI 公约). On a 393px iPhone viewport, the inner right panel collapses to ~80px — unusable. The user explicitly wants ChatView ("路上想问 agent 一个问题") to work on phone; PrivateView/IngestView/WikiView "次之". This change makes the whole app mobile-friendly so the NAS instance is genuinely usable from phone on home wifi without reaching for a laptop.

While we're touching `AppLayout.vue` for the bottom-tab refactor, we'll also retire the old blue→purple `bg-gradient-to-r from-blue-600 to-purple-600` logo gradient that predates the Notion design system migration — moving it to `notion-*` tokens that match the rest of the redesigned views.

## What Changes

- **AppLayout responsive split:** below `md` (768px) the left sidebar is replaced by a 56px bottom tab bar with `safe-area-inset-bottom` padding; at `md+` the existing sidebar shape is retained.
- **AppLayout Notion alignment:** the blue→purple gradient logo and `bg-primary/10 text-primary` active state are replaced by Notion design tokens (`bg-notion-tint-lavender text-notion-brand-purple-800` for active, navy monochrome logo).
- **TreeNav becomes a drawer on mobile:** WikiView, IngestView, PrivateView each gain a `☰` header button that opens the existing `TreeNav` as a full-width slide-in drawer; selecting a node closes the drawer.
- **ChatView mobile rework (the flagship flow):**
  - Sessions list moves into a `☰` drawer (top-left), `🆕` button (top-right) opens a fresh session
  - Input box becomes `position: sticky; bottom: 0` with `padding-bottom: env(safe-area-inset-bottom)`; the messages container uses `100dvh` so iOS Safari keyboard pop-ups don't push it
  - Auto-scroll-to-bottom only fires when the user is already near the bottom (don't fight upward reading scroll)
  - Source chips wrap horizontally; deep-links to `/private?entry=…` etc. unchanged
  - Bottom tab bar stays visible (consistency over an extra 56px)
- **Page header simplification on mobile:** the existing gradient header (`from-blue-600 to-purple-600`) collapses to a `h-12` page-title bar at `md-`; gradient retained at `md+`. New tokens: `bg-notion-canvas` + page title in `text-notion-ink`.
- **PWA manifest:** add `frontend/public/manifest.json`, three PNG icons (192/512/maskable), `apple-touch-icon`, `<meta name="theme-color">` so users can "add to home screen" and launch in standalone display mode. No service worker (NAS is always-online; offline caching out of scope).
- **Mobile Playwright coverage:** new test file targeting iPhone-14 viewport (393×852) covering ChatView send-message + sources, PrivateView quick-add entry, IngestView URL submit. Runs in same `npm run e2e` invocation as desktop tests.

## Capabilities

### New Capabilities
None.

### Modified Capabilities

- `frontend-scaffold`: AppLayout gains a responsive bottom-tab variant + Notion design tokens; project gains a PWA manifest and apple touch icon.
- `chat-view`: ChatView renders a single-column mobile layout below `md`, with sessions drawer, sticky input, dvh-aware viewport math, and bottom-aware auto-scroll.
- `ingest-view`: IngestView's left TreeNav becomes a drawer below `md`; right panel takes full viewport width.
- `private-view`: PrivateView's left TreeNav becomes a drawer below `md`; right panel takes full viewport width.
- `knowledge-browse`: WikiView's left TreeNav becomes a drawer below `md`; right panel takes full viewport width.

## Impact

- **Files modified:** `frontend/src/components/AppLayout.vue` (mobile + Notion), `frontend/src/components/TreeNav.vue` (drawer mode), all 4 views in `frontend/src/views/` (responsive layout + ☰ button), `frontend/src/styles/` (Notion token additions if needed), `frontend/index.html` (theme-color meta + apple-touch-icon link).
- **Files added:** `frontend/public/manifest.json`, `frontend/public/icons/{192,512,maskable}.png`, `frontend/e2e/mobile.spec.ts` (Playwright iPhone viewport tests).
- **Files unchanged:** all backend code (no API contract change), all backend tests, the prod docker-compose (the change ships as a new frontend image push).
- **Operational:** `./scripts/build-and-push.sh` then NAS UGOS UI Pull → Apply, like any other frontend update. No data migration. Rollback via tag pin if needed.
- **Out of scope** (deferred): touch-specific gestures (left-swipe-to-delete, long-press menus, pull-to-refresh) — would add disproportionate polish work; revisit after V1 lands. Service worker / offline mode — premature given always-online NAS. iPad-specific layout (treats iPad portrait as mobile via `lg:` breakpoint at 1024).

Design doc: this is a frontend-only refactor; the proposal + design.md + per-capability spec deltas already capture all decisions. No separate `docs/superpowers/specs/` design doc needed.
