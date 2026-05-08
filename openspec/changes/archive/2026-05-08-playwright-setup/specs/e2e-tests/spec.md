## ADDED Requirements

### Requirement: Playwright SHALL be installed as a frontend devDependency
The system SHALL add `@playwright/test` to `frontend/package.json` devDependencies. The Chromium browser binary SHALL be installed via `npx playwright install chromium` (one-time per machine; documented in README).

#### Scenario: Fresh checkout install
- **WHEN** a developer runs `npm install` in `frontend/` followed by `npx playwright install chromium`
- **THEN** Playwright tests are runnable via `npm run e2e`

### Requirement: playwright.config.ts SHALL target the docker-served frontend
The system SHALL configure Playwright with `baseURL: 'http://localhost:3000'`, `testDir: './e2e'`, and a single `chromium` project using `devices['Desktop Chrome']`. The config SHALL NOT define a `webServer` block (tests run against an already-running stack).

#### Scenario: Test execution assumes stack is running
- **WHEN** tests are launched without docker compose having been started
- **THEN** the test fails fast with a connection error (acceptable; not a Playwright config bug)

### Requirement: npm scripts SHALL expose headless and headed modes
The system SHALL add `npm run e2e` (headless) and `npm run e2e:headed` (headed mode for debugging) to `frontend/package.json`.

#### Scenario: Headed mode for debugging
- **WHEN** the user runs `npm run e2e:headed`
- **THEN** Chromium opens visibly and tests run with the browser UI shown

### Requirement: First E2E spec covers the /private flow end-to-end
The system SHALL include `frontend/e2e/private.spec.ts` covering:
- Navigate to `/private`; assert the 6 fixed template directory names appear in the sidebar
- Click `+ 新建条目`; pick the `税务` template; assert directory input pre-fills to `税务`
- Fill title (timestamp-suffixed for isolation) and any one numeric field; click save
- Assert the new entry appears under `税务` in the sidebar tree (after expanding)
- Click the entry; assert the right panel switches to `item-view` showing the entry's title and field values
- Click 编辑; change the title; click save; assert the new title appears in both panel and sidebar
- Click 删除; accept the confirm dialog; assert the entry disappears from the sidebar
- Cleanup hook (afterEach): regardless of pass/fail, DELETE any leftover entries created during the test via `/api/private/entries/{id}`

#### Scenario: All assertions pass against a freshly built stack
- **WHEN** `npm run e2e` is executed against a docker stack built from current code
- **THEN** all assertions in `private.spec.ts` pass

#### Scenario: Cleanup runs even when test fails mid-flow
- **WHEN** an assertion fails in the middle of the spec
- **THEN** the `afterEach` cleanup hook still runs and deletes any entries the test created

### Requirement: E2E test data SHALL be isolated by reserved prefix
All entry/note titles created by E2E tests SHALL be prefixed with `__e2e_` followed by a timestamp + random suffix. The convention SHALL be documented inline in the spec file so future contributors don't accidentally reuse the prefix for human data.

#### Scenario: Test entries are identifiable for cleanup
- **WHEN** an E2E test creates an entry
- **THEN** its title starts with `__e2e_` so a cleanup script can locate orphaned data unambiguously

### Requirement: README SHALL document the E2E workflow
The frontend README (or equivalent doc) SHALL include a short section explaining: (a) `npx playwright install chromium` first-time setup; (b) start docker stack; (c) `npm run e2e` to run; (d) `npm run e2e:headed` for debugging; (e) tests must be re-validated by a human if the underlying UX intent changes — the test only catches regressions, not design flaws.

#### Scenario: New contributor follows the README and gets a green run
- **WHEN** a developer with a fresh checkout follows the README steps in order
- **THEN** `npm run e2e` produces a green test run with no additional setup required
