## Why

The project relies on vitest + happy-dom + `@vue/test-utils` for frontend tests. These verify component behavior (data attributes wired up, store actions called) but cannot detect layout regressions, real-browser bugs, or end-to-end flow breakage. As `CLAUDE.md` notes (Frontend UI Validation), the original `PrivateView` 5.x stub passed all 11 vitest tests and was rejected on first sight — the tests confirmed buttons existed, not that the page was usable.

Once a UX is validated by the user, that flow should be locked in by an automated regression test that runs against the real built frontend talking to the real backend in docker. Playwright is the standard tool for this in the JS ecosystem.

## What Changes

- **New dev dependency**: `@playwright/test` in `frontend/package.json`
- **New config**: `frontend/playwright.config.ts` configured to talk to the local docker stack at `http://localhost:3000`
- **New test directory**: `frontend/e2e/` (separate from vitest's `tests/`)
- **First E2E spec**: `e2e/private.spec.ts` — covers the `/private` user flow validated in `private-data` change: open page → see the 6 fixed template directories → click `+ 新建条目` → pick `税务` template → directory pre-fills → fill title + AGI → save → entry appears under 税务 in sidebar → click to view → click 编辑 → change title → save → click 删除 → confirm → entry gone
- **npm script**: `npm run e2e` (runs against an already-running docker stack); optional `npm run e2e:headed` for debugging
- **README addition**: short section on running E2E
- **Test data isolation**: E2E test uses unique titles (timestamp-suffixed) to avoid collision with user data; cleans up after itself even on failure

## Capabilities

### New Capabilities

- `e2e-tests`: Playwright-based regression tests for critical user flows. V1 covers `/private` only; future flows (`/ingest`, `/wiki`, `/chat`) added incrementally as they stabilize.

## Impact

- **Frontend**: new `e2e/` directory; `playwright.config.ts`; updated `package.json` (devDependency + script)
- **Tests**: vitest unchanged; new Playwright suite runs separately
- **CI**: out of scope for V1 (no GitHub Actions config yet); future change can wire it in
- **Dependencies**: `@playwright/test` (~50 MB browser bundle on first install — `npx playwright install chromium` runs once)
- **Docker**: tests run against the **already-running** docker stack (user starts it manually); the test suite does NOT start/stop containers itself in V1 — keeps the test runner simple and matches the user's actual development workflow

## Non-Goals

- CI integration (manual `npm run e2e` only in V1)
- Full coverage of all routes (`/ingest`, `/wiki`, `/chat`) — added in subsequent changes once each is stable
- Visual regression / screenshot diffing (Playwright supports it; defer until baseline is settled)
- Cross-browser testing (chromium only in V1)
- Mocked backend mode — tests hit the real Flask + Qdrant stack to catch integration bugs the vitest suite cannot
