## 1. Install and configure Playwright

- [x] 1.1 Add `@playwright/test` to `frontend/package.json` devDependencies; run `npm install` in `frontend/`
- [x] 1.2 Run `npx playwright install chromium` (one-time browser binary download)
- [x] 1.3 Create `frontend/playwright.config.ts` with `baseURL: 'http://localhost:3000'`, `testDir: './e2e'`, single chromium project; no `webServer` block (per design Decision 1)
- [x] 1.4 Add `npm run e2e` and `npm run e2e:headed` scripts to `frontend/package.json`
- [x] 1.5 Add `frontend/e2e/` to `.gitignore` only for the artifacts dir (`test-results/`, `playwright-report/`); keep spec files in git

## 2. First E2E spec — /private flow

- [x] 2.1 RED — write `frontend/e2e/private.spec.ts` covering: visit `/private` → 6 fixed directories visible → click `+ 新建条目` → pick `税务` → directory pre-fills to `税务` → fill title (`__e2e_${Date.now()}`) and AGI → save → entry visible under `税务` after sidebar expand → click entry → item-view panel shows title and AGI value → click 编辑 → change title → save → updated title visible → click 删除 → accept confirm → entry no longer in sidebar
- [x] 2.2 Add `test.afterEach()` cleanup hook: collect created entry IDs in a test-scoped array; iterate and `request.delete('/api/private/entries/${id}')` regardless of test outcome
- [x] 2.3 Confirm RED — bring up docker stack (`docker compose up -d`); run `npm run e2e`; verify the spec runs against the real backend (it should pass since `/private` already works) — passed in 7.5s first run, 2.8s on rerun
- [x] 2.4 Sanity-check teardown — temporarily inject a failing assertion mid-test; verify cleanup still deletes the entry; revert the injection — verified zero `__e2e_*` orphans after a forced-failure run

## 3. Documentation

- [x] 3.1 Add `frontend/README.md` (create if absent) with sections: Setup (npm install + playwright install), Run vitest (`npm test`), Run E2E (`npm run e2e`), Debugging (`npm run e2e:headed`), Caveat (E2E catches regression, not design flaws — first deploy of a new design still requires human validation)
- [x] 3.2 Update root project `CLAUDE.md` "Frontend UI Validation" section to point at the new `npm run e2e` command instead of saying "Playwright not yet wired up"

## 4. Verification

- [x] 4.1 Full flow: `docker compose up -d` → `cd frontend && npm run e2e` → all green (4.1s)
- [x] 4.2 Force a regression: temporarily break a `data-*` attribute (e.g., remove `data-new-entry-btn`); confirm `private.spec.ts` fails with a clear error pointing at the missing selector; revert — verified with `data-new-entry-btn-MISSING`, error: `Test timeout … waiting for locator(...)`
- [x] 4.3 Confirm vitest still passes alongside (`npm test`); two test runners coexist without interference — required adding `'e2e/**'` to `vite.config.js` `test.exclude`; vitest 100/100 + Playwright 1/1
- [x] 4.4 Update `docs/log/2026-05-07.md` with commit hash, setup notes, and known caveats
- [x] 4.5 Run superpowers:requesting-code-review on the diff; address any CRITICAL/HIGH findings — 2 HIGH found in `captureCreatedId` (race + missing-cleanup window); fixed by replacing API-poll with `page.waitForResponse(POST /api/private/entries 201)` to read the new ID directly from the create response, recorded BEFORE any further assertions
