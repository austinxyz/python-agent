/**
 * E2E auth fixture — multi-user-auth-core.
 *
 * Adopt by replacing
 *
 *   import { test, expect } from '@playwright/test'
 *
 * with
 *
 *   import { test, expect } from './auth-fixture'
 *
 * Behavior: BEFORE each test the fixture establishes a REAL Flask session
 * cookie for a known shared test user (`e2e-shared@example.com`). All
 * subsequent `/api/*` calls in that browser context succeed against the
 * real dev backend, so existing specs (which already mock the endpoints
 * they assert against) keep working unchanged.
 *
 * Why a real session and not just `page.route('/api/auth/me')`: the new
 * axios 401 interceptor in `src/api/index.js` redirects to `/login` on
 * any non-auth 401. Mocking only `/api/auth/me` while leaving every
 * other `/api/*` request session-less makes every read kick the user out.
 *
 * Test user provisioning (one-time per test run): if login fails, the
 * fixture invokes the CLI inside the api container to create the user,
 * accepts the invite via API, then logs in. Subsequent tests skip the
 * provisioning and just log in (~100ms).
 *
 * The new `auth.spec.ts` and `integration.spec.ts` deliberately import
 * directly from `@playwright/test` so they observe the unauthenticated
 * state and exercise the real auth flow themselves.
 */
import { test as base, request as apiRequest } from '@playwright/test'
import { execSync } from 'node:child_process'

const TEST_EMAIL = 'e2e-shared@example.com'
const TEST_PASSWORD = 'pw-e2e-shared-12345678'
const API_CONTAINER = process.env.E2E_API_CONTAINER ?? 'python-agent-dev-api-1'

let userEnsured = false

async function ensureTestUserOnce(baseURL: string): Promise<void> {
  if (userEnsured) return
  const ctx = await apiRequest.newContext({ baseURL })
  try {
    // Try to login — if user already activated from a prior run, we're done.
    const probe = await ctx.post('/api/auth/login', {
      data: { email: TEST_EMAIL, password: TEST_PASSWORD },
    })
    if (probe.status() === 200) {
      userEnsured = true
      return
    }

    // CLI invite. On duplicate email this exits non-zero; we treat that as
    // "user exists but is in a state we can't recover from" — happens when
    // a prior run accepted with a different password. `npm run dev:reset`
    // clears it.
    let cliStdout = ''
    try {
      cliStdout = execSync(
        `docker exec ${API_CONTAINER} python -m app.cli.invite_user "${TEST_EMAIL}" member`,
        { encoding: 'utf8' },
      )
    } catch (e: any) {
      const stderr = String(e.stderr ?? '')
      if (/already exists/.test(stderr)) {
        throw new Error(
          `Shared test user ${TEST_EMAIL} exists but cannot login with the expected password.\n` +
            `Most likely a prior run accepted with different credentials. Fix:\n` +
            `  npm run dev:reset && npm run e2e\n`,
        )
      }
      throw new Error(`CLI invite failed: ${stderr || e.message}`)
    }

    const tokenMatch = cliStdout.match(/Invite URL:[^?]*\?token=(\S+)/)
    if (!tokenMatch) {
      throw new Error(`Could not parse invite URL from CLI output:\n${cliStdout}`)
    }
    const token = tokenMatch[1]

    const accept = await ctx.post('/api/auth/accept-invite', {
      data: { token, password: TEST_PASSWORD },
    })
    if (accept.status() !== 200) {
      throw new Error(
        `accept-invite returned ${accept.status()}: ${await accept.text()}`,
      )
    }
    userEnsured = true
  } finally {
    await ctx.dispose()
  }
}

export const test = base.extend({
  page: async ({ page, baseURL }, use) => {
    await ensureTestUserOnce(baseURL ?? 'http://localhost:3000')
    // Login this browser context — sets a real Flask session cookie.
    const loginResp = await page.request.post('/api/auth/login', {
      data: { email: TEST_EMAIL, password: TEST_PASSWORD },
    })
    if (loginResp.status() !== 200) {
      throw new Error(
        `Login as test user failed (${loginResp.status()}): ${await loginResp.text()}`,
      )
    }
    await use(page)
  },
})

export { expect } from '@playwright/test'
