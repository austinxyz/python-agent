import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright config for the python-agent frontend.
 *
 * Tests run against the user-managed docker stack (see CLAUDE.md), NOT a
 * Playwright-spawned dev server. Bring the stack up with
 *   docker compose up -d
 * before running `npm run e2e`.
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: false, // sequential — single shared backend, avoid data races
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
