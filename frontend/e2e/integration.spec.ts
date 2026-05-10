/**
 * E2E integration spec — multi-user-auth-core group 9 automated.
 *
 * UNLIKE the other specs in this directory, this one talks to the REAL
 * dev backend (no `auth-fixture`, no `page.route()` mocks). It exercises
 * the actual `/api/auth/*` endpoints, the real CLI invite tool inside
 * the api container, and the real SQLite/Qdrant migration paths.
 *
 * Replaces the manual "group 9" smoke checklist in
 * `openspec/changes/multi-user-auth-core/tasks.md`:
 *   - 9.1: bootstrap migration runs + login redirect (covered by pytest +
 *          the redirect-to-/login assertion below)
 *   - 9.2: CLI-invite a member, accept invite, land on /chat
 *   - 9.4: cross-user private-data isolation
 *   - 9.5: Google login — skipped (only relevant when GOOGLE_CLIENT_ID set)
 *   - 9.3: shared knowledge — skipped (real ingestion costs OpenAI tokens;
 *          coverage is provided by pytest unit tests instead)
 *
 * Pre-requisite: dev stack rebuilt with the auth code, e.g.
 *   docker compose -p python-agent-dev up --build -d
 *
 * If `INITIAL_ADMIN_EMAIL` is unset in `.env`, the api logs a warning and
 * every authenticated request 401s. The first test below pings
 * `/api/auth/config` to fail fast with a clear message in that case.
 */
import { test, expect, type Page } from '@playwright/test'
import { execSync } from 'node:child_process'

const API_CONTAINER = process.env.E2E_API_CONTAINER ?? 'python-agent-dev-api-1'

// Unique emails per run so the spec is re-runnable without `dev:reset`.
// Each test gets its own pair derived from this stamp.
const STAMP = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

function inviteUser(email: string, role: 'admin' | 'member' = 'member'): string {
  // Run the CLI inside the api container; capture stdout that includes
  // the line "Invite URL: <url>".
  const stdout = execSync(
    `docker exec ${API_CONTAINER} python -m app.cli.invite_user "${email}" ${role}`,
    { encoding: 'utf8' },
  )
  const match = stdout.match(/Invite URL:\s*(\S+)/)
  if (!match) {
    throw new Error(
      `CLI did not print an invite URL.\nstdout: ${stdout}\n` +
        `Hint: ensure the dev stack is rebuilt with the auth code:\n` +
        `  docker compose -p python-agent-dev up --build -d`,
    )
  }
  return match[1]
}

function acceptInvitePath(url: string): string {
  // Strip protocol+host so page.goto uses Playwright's baseURL (localhost:3000),
  // robust against APP_BASE_URL pointing somewhere else (e.g. NAS).
  const u = new URL(url)
  return `${u.pathname}${u.search}`
}

async function activateAndAssertChat(page: Page, inviteUrl: string, password: string) {
  await page.goto(acceptInvitePath(inviteUrl))
  await expect(page.locator('[data-invite-banner]')).toBeVisible()
  await page.fill('[data-accept-password]', password)
  await page.fill('[data-accept-confirm]', password)
  await page.click('[data-accept-submit]')
  await expect(page).toHaveURL(/\/chat$/, { timeout: 10_000 })
}

async function logout(page: Page) {
  // Hit the API directly to clear the session cookie. Faster + works
  // independently of which page we're on.
  await page.request.post('/api/auth/logout')
  // Drop the cookies the request context just received in case the next
  // test reuses this page.
  await page.context().clearCookies()
}

test.describe.configure({ mode: 'serial' })

// ---------------------------------------------------------------------------
// 9.1 — sanity check: stack is auth-aware
// ---------------------------------------------------------------------------

test.describe('integration — stack readiness', () => {
  test('GET /api/auth/config responds (auth code is deployed)', async ({ page }) => {
    const resp = await page.request.get('/api/auth/config')
    expect(resp.status(), `If this is 404 the dev frontend/api is stale — rebuild with: docker compose -p python-agent-dev up --build -d`).toBe(200)
    const body = await resp.json()
    expect(body).toHaveProperty('has_google')
  })

  test('protected route while logged-out redirects to /login', async ({ page }) => {
    await page.goto('/private')
    // vue-router emits the query without re-encoding the slash, so the
    // URL bar reads `redirect=/private` (not `%2Fprivate`).
    await expect(page).toHaveURL(/\/login\?redirect=(%2F|\/)private/, { timeout: 10_000 })
  })
})

// ---------------------------------------------------------------------------
// 9.2 — CLI invite + accept-invite + login
// ---------------------------------------------------------------------------

test.describe('integration — invite flow', () => {
  test('CLI invites a member; accept-invite lands on /chat with a real session', async ({ page, context }) => {
    const email = `e2e-${STAMP}-member1@example.com`
    const password = 'pw-e2e-12345678'

    const url = inviteUser(email, 'member')
    expect(url).toMatch(/\/accept-invite\?token=/)

    await activateAndAssertChat(page, url, password)

    // Session cookie set; /me returns the new user.
    const me = await page.request.get('/api/auth/me')
    expect(me.status()).toBe(200)
    const meBody = await me.json()
    expect(meBody.user.email).toBe(email.toLowerCase().trim())
    expect(meBody.user.role).toBe('member')
  })

  test('logout returns to /login and re-login via /api/auth/login works', async ({ page }) => {
    const email = `e2e-${STAMP}-member2@example.com`
    const password = 'pw-e2e-87654321'

    const url = inviteUser(email, 'member')
    await activateAndAssertChat(page, url, password)

    // Logout via the desktop sidebar pill.
    const logoutBtn = page.locator('[data-user-pill-logout]')
    await expect(logoutBtn).toBeVisible()
    await logoutBtn.click()
    await expect(page).toHaveURL(/\/login(\?|$)/)

    // Re-login via the form.
    await page.fill('[data-login-email]', email)
    await page.fill('[data-login-password]', password)
    await page.click('[data-login-submit]')
    await expect(page).toHaveURL(/\/chat$/, { timeout: 10_000 })
  })
})

// ---------------------------------------------------------------------------
// 9.4 — private-data isolation across two users
// ---------------------------------------------------------------------------

test.describe('integration — private-data isolation', () => {
  test('member A cannot see member B private note', async ({ page, browser }) => {
    // Use notes (SQLite-only) instead of entries to avoid the OpenAI
    // embedding cost on each test run. Isolation logic is identical:
    // both queries scope by `WHERE user_id = ?`.
    const emailA = `e2e-${STAMP}-isolA@example.com`
    const emailB = `e2e-${STAMP}-isolB@example.com`
    const password = 'pw-e2e-isolated-1'

    const urlA = inviteUser(emailA, 'member')
    const urlB = inviteUser(emailB, 'member')

    // ---- Activate B first, create a private note under their account ----
    await activateAndAssertChat(page, urlB, password)
    const noteTitle = `__e2e_isol_${STAMP}_B`
    const createResp = await page.request.post('/api/private/notes', {
      data: {
        title: noteTitle,
        directory: '__e2e__',
        content: 'B-only content',
      },
    })
    expect(createResp.status(), `B's create-note failed: ${await createResp.text()}`).toBe(201)
    const created = await createResp.json()

    // B sees the note in their list.
    const listB = await page.request.get('/api/private/notes')
    expect(listB.status()).toBe(200)
    const bodyB = await listB.json()
    const titlesB: string[] = (bodyB.notes ?? []).map((n: any) => n.title)
    expect(titlesB).toContain(noteTitle)

    // Logout B from this browser context.
    await logout(page)

    // ---- New browser context for A so cookies are isolated ----
    const ctxA = await browser.newContext()
    const pageA = await ctxA.newPage()
    try {
      await activateAndAssertChat(pageA, urlA, password)

      const listA = await pageA.request.get('/api/private/notes')
      expect(listA.status()).toBe(200)
      const bodyA = await listA.json()
      const titlesA: string[] = (bodyA.notes ?? []).map((n: any) => n.title)
      expect(
        titlesA,
        `A should NOT see B's private note ${noteTitle}, got: ${titlesA.join(', ')}`,
      ).not.toContain(noteTitle)
    } finally {
      await ctxA.close()

      // Best-effort cleanup: re-auth as B and delete the note. Test users
      // accumulate (one pair per run) — admin can prune by email prefix
      // later if needed.
      const ctxCleanup = await browser.newContext()
      const pageCleanup = await ctxCleanup.newPage()
      try {
        await pageCleanup.request.post('/api/auth/login', {
          data: { email: emailB, password },
        })
        await pageCleanup.request.delete(`/api/private/notes/${created.id}`)
      } catch {
        // ignore
      } finally {
        await ctxCleanup.close()
      }
    }
  })
})
