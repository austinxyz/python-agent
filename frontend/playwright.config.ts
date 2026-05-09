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
      // Skip the mobile spec on the desktop project — it asserts mobile-only UI
      // (☰ buttons, drawer, bottom-tab nav) which is hidden at md+.
      testIgnore: /mobile\.spec\.ts/,
    },
    {
      name: 'mobile-chrome',
      // iPhone 14 viewport metrics (393×852, mobile UA, touch) but use
      // chromium engine — avoids the webkit download and matches how Chrome
      // DevTools "device toolbar" emulates a phone. Real Safari quirks aren't
      // covered, but layout + touch-event behavior is.
      use: {
        ...devices['Pixel 5'],
        viewport: { width: 393, height: 852 },
        userAgent:
          'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
      },
      // Only run the mobile spec on this project; desktop specs are written
      // for desktop layout and would fail on a phone viewport.
      testMatch: /mobile\.spec\.ts/,
    },
  ],
})
