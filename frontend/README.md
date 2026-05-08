# Knowledge Agent — Frontend

Vue 3 + Vite frontend for the Knowledge Agent. UI is served by nginx in the docker compose stack on port 3000; in dev you can run Vite directly with `npm run dev`.

## Setup

```bash
cd frontend
npm install
# One-time: install Chromium for Playwright E2E
npx playwright install chromium
```

## Development

```bash
npm run dev          # Vite dev server (hot reload)
npm run build        # Compile to dist/ (used by docker frontend image)
npm run preview      # Preview the built dist/
```

## Tests

There are two test runners with distinct purposes:

### Component tests — vitest

Fast, in-memory tests with `happy-dom` + `@vue/test-utils`. Run on every code change. They catch wiring bugs (missing `data-*` attributes, store actions not called) but **cannot** validate layout, real-browser behavior, or end-to-end integration.

```bash
npm test              # one-shot
npm test -- --watch   # watch mode
```

### End-to-end tests — Playwright

Real Chromium against the real docker stack. Slow but catch real-browser/integration bugs vitest cannot. Use these to lock in flows that have already been validated by a human.

```bash
# 1. Start the docker stack (in repo root)
docker compose up -d

# 2. Run E2E
npm run e2e             # headless
npm run e2e:headed      # show the browser, useful for debugging
```

E2E tests live in `frontend/e2e/`. Test data is isolated by reserved prefix `__e2e_*`; an `afterEach` hook deletes any entries the test created, even when the test fails.

### When to add an E2E test

- The user has just validated a new UX in their browser.
- A regression is reported and you want to lock it in.

### When NOT to rely on E2E

- E2E catches **regressions**, not design flaws. The first deploy of a new design still requires human eyes — automated tests can only verify that buttons keep working, not that the design is right.

## Reference

- UI design system: `../docs/frontend-ui-guide.md`
- Project pitfalls / conventions: `../CLAUDE.md`
