## Context

The frontend has component-level tests via vitest + happy-dom but no real-browser end-to-end coverage. The `private-data` change exposed this gap — a stub layout passed all vitest assertions but failed first contact with the user. We need a regression net so each validated UX gets locked in.

Playwright is the natural choice: same Node ecosystem, no extra runtime, hits real Chromium with real network requests against the running Flask backend. It complements vitest rather than replacing it.

## Goals / Non-Goals

**Goals:**
- One working E2E test that exercises the `/private` flow end-to-end against the real docker stack
- A reproducible setup that future contributors (or future Claude sessions) can extend without re-deciding fundamentals
- Tests isolated by data: never collide with the user's actual entries; clean up even when the test fails

**Non-Goals:**
- CI integration (no GitHub Actions yet)
- Mocked backend mode (the whole point is to catch integration bugs vitest misses)
- Visual regression / screenshot diffing
- Cross-browser

## Decisions

### 1. Tests run against the user-managed docker stack, not auto-spawned

**Choice:** `playwright.config.ts` does NOT use `webServer` to spin up the frontend. The user runs `docker compose up -d` themselves; tests assume `http://localhost:3000` is reachable.

**Rationale:** Dev-loop friendly. The user already has the stack running for manual development; reusing it is faster than tearing down/starting on every test. CI can override later. Auto-spawning compose from a test runner is fragile (port conflicts, healthcheck timing, container build cache warming) — defer that complexity.

**Alternatives considered:**
- `webServer: { command: 'docker compose up' }` — slow first run (build), brittle teardown, requires shutdown logic on test interrupt
- A Vite dev-server mode — wouldn't match the deployed nginx/dist artifact, defeating part of the point

### 2. Real backend, no mocks

**Choice:** Tests hit the real Flask `/api/private/*` endpoints; the real Qdrant container; the real SQLite volume.

**Rationale:** vitest already covers the mocked path. Playwright's value is exercising integration — embedding calls, Qdrant upserts, SQLite writes, nginx proxy. A mocked Playwright suite would just duplicate vitest at higher cost.

**Risk:** tests can pollute the user's SQLite. Mitigated by Decision 3.

### 3. Test data isolation via unique titles + always-clean teardown

**Choice:** Each test generates entry titles like `__e2e_${Date.now()}_${nanoid()}` and notes likewise. `afterEach` calls `DELETE /api/private/entries/{id}` for every entry created during the test. The teardown runs even when the test body throws (Playwright `test.afterEach` always runs).

**Rationale:** Lightweight, no test database needed. The `__e2e_` prefix makes orphaned data trivially identifiable if cleanup ever fails. Avoids the complexity of a separate test-mode SQLite or fixture reset.

**Alternatives considered:**
- A separate test-mode SQLite path: requires backend changes to honor an env-var override at request time (it already does honor `SQLITE_PATH`, but switching it requires container restart — too slow per-test)
- Truncating the table before each test: dangerous if anyone ever runs E2E against prod data
- Snapshot/restore SQLite file: complex; brittle with the WAL journal mode the backend uses

### 4. Single `chromium` browser, headless by default

**Choice:** `playwright.config.ts` lists only `{ name: 'chromium', use: devices['Desktop Chrome'] }`. Headed mode toggled via `--headed` flag (`npm run e2e:headed`).

**Rationale:** Single-developer project; Vue 3 + Tailwind has no known browser-specific quirks the user cares about in V1. Adding Firefox/Safari triples test runtime for negligible value. Easy to add later.

### 5. E2E tests live in `frontend/e2e/`, vitest stays in `frontend/tests/`

**Choice:** Two top-level test directories. Playwright's `testDir: './e2e'` keeps it from scanning vitest specs (and vice versa).

**Rationale:** Different runners with different APIs (`describe` from vitest vs `test.describe` from Playwright; different `expect` bindings). Mixing them in the same dir invites accidental cross-imports. `frontend/tests/` already exists for vitest; staying out of it preserves established structure.

### 6. Selector strategy: `data-*` attributes already in place

**Choice:** Use the existing `data-new-entry-btn` / `data-template-option` / `data-entry-title` / `data-entry-directory` / `data-save-entry-btn` / `data-item` / `data-edit-item-btn` / `data-delete-item-btn` etc. Same selectors vitest uses.

**Rationale:** They were added during `private-data` precisely to enable testing. Reusing them keeps the contract single-sourced — if a refactor breaks a `data-*` attribute, both vitest and Playwright catch it.

## Risks / Trade-offs

- **First `npx playwright install` downloads ~150 MB of Chromium** — one-time cost, but worth flagging in the README
- **Tests are slow vs vitest** (real browser, real network): expect ~10–30s per spec vs ~50ms in vitest. Acceptable given they only run on demand, not on every save
- **Tests will fail if the user's `private` data already contains an entry titled `__e2e_*`** — extremely unlikely (the prefix is reserved by convention)
- **The chevron / sidebar icons depend on emoji rendering** — Playwright/Chromium render emoji consistently across Linux/macOS/Windows, but if a future change uses platform-specific glyphs, screenshot comparisons would diverge
