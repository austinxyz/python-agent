/**
 * 10.3 — E2E for the auth flow itself.
 *
 * Imports `test`/`expect` directly from `@playwright/test` (NOT from
 * ./auth-fixture) so the page sees the real unauthenticated state. Each
 * test mocks the specific auth endpoints it needs.
 *
 * Covers:
 *   - logged-out visit to /wiki redirects to /login?redirect=/wiki
 *   - submitting valid credentials lands at the redirect target
 *   - bad credentials surface an inline error
 *   - logout returns the user to /login
 *   - /accept-invite renders inviter context, sets password, redirects to /chat
 *   - expired/used/invalid invite tokens render the right error state
 */
import { test, expect, type Page, type Route } from '@playwright/test'

const ADMIN_USER = {
  id: 'e2e-admin-1',
  email: 'admin@example.com',
  name: 'Admin',
  role: 'admin',
  picture_url: null,
}

const NEW_USER = {
  id: 'e2e-new-1',
  email: 'new@example.com',
  name: null,
  role: 'member',
  picture_url: null,
}

/**
 * Default mocks: /api/auth/me 401 (unauthenticated), /api/auth/config no GSI.
 * Overridable per-test by registering a more specific page.route() AFTER
 * calling this. Last-registered handler wins in Playwright.
 */
async function installLoggedOutMocks(page: Page) {
  await page.route('**/api/auth/me', async (route: Route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'unauthenticated' }),
      })
      return
    }
    await route.continue()
  })
  await page.route('**/api/auth/config', async (route: Route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ has_google: false, google_client_id: null }),
      })
      return
    }
    await route.continue()
  })
}

// ---------------------------------------------------------------------------
// Login redirect + form submit
// ---------------------------------------------------------------------------

test.describe('auth — login redirect', () => {
  test('visiting /wiki while logged-out redirects to /login?redirect=/wiki', async ({ page }) => {
    await installLoggedOutMocks(page)
    await page.goto('/wiki')
    await expect(page).toHaveURL(/\/login\?redirect=(%2F|\/)wiki/)
    await expect(page.locator('[data-login-view]')).toBeVisible()
  })

  test('visiting /private while logged-out redirects to /login?redirect=/private', async ({ page }) => {
    await installLoggedOutMocks(page)
    await page.goto('/private')
    await expect(page).toHaveURL(/\/login\?redirect=(%2F|\/)private/)
  })

  test('submitting valid credentials lands at the ?redirect target', async ({ page }) => {
    await installLoggedOutMocks(page)

    // login: returns the user, then /api/auth/me starts returning that user.
    let loggedIn = false
    await page.route('**/api/auth/login', async (route: Route) => {
      if (route.request().method() === 'POST') {
        loggedIn = true
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ user: ADMIN_USER }),
        })
        return
      }
      await route.continue()
    })
    await page.route('**/api/auth/me', async (route: Route) => {
      if (route.request().method() === 'GET') {
        if (loggedIn) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ user: ADMIN_USER }),
          })
        } else {
          await route.fulfill({
            status: 401,
            contentType: 'application/json',
            body: JSON.stringify({ error: 'unauthenticated' }),
          })
        }
        return
      }
      await route.continue()
    })
    // /chat fetches sessions on mount — return empty so the page doesn't 404.
    await page.route('**/api/chat/sessions', (r) =>
      r.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )

    await page.goto('/chat')
    await expect(page).toHaveURL(/\/login\?redirect=(%2F|\/)chat/)

    await page.fill('[data-login-email]', 'admin@example.com')
    await page.fill('[data-login-password]', 'pw12345678')
    await page.click('[data-login-submit]')

    await expect(page).toHaveURL(/\/chat$/)
  })

  test('bad credentials surface an inline error and stay on /login', async ({ page }) => {
    await installLoggedOutMocks(page)
    await page.route('**/api/auth/login', async (route: Route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'invalid credentials' }),
        })
        return
      }
      await route.continue()
    })

    await page.goto('/login')
    await page.fill('[data-login-email]', 'admin@example.com')
    await page.fill('[data-login-password]', 'wrong')
    await page.click('[data-login-submit]')

    await expect(page.locator('[data-login-error]')).toBeVisible()
    await expect(page).toHaveURL(/\/login(\?|$)/)
  })
})

// ---------------------------------------------------------------------------
// Logout flow
// ---------------------------------------------------------------------------

test.describe('auth — logout', () => {
  test('logout from sidebar pill returns to /login', async ({ page }) => {
    // Start logged-in.
    await page.route('**/api/auth/me', async (route: Route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ user: ADMIN_USER }),
        })
        return
      }
      await route.continue()
    })
    await page.route('**/api/auth/config', (r) =>
      r.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ has_google: false, google_client_id: null }),
      }),
    )
    await page.route('**/api/auth/logout', async (route: Route) => {
      await route.fulfill({ status: 204, body: '' })
    })
    await page.route('**/api/chat/sessions', (r) =>
      r.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )

    await page.goto('/chat')
    await expect(page).toHaveURL(/\/chat$/)

    // Pill is desktop-only — the spec runs at desktop viewport.
    const logoutBtn = page.locator('[data-user-pill-logout]')
    await expect(logoutBtn).toBeVisible()
    await logoutBtn.click()

    await expect(page).toHaveURL(/\/login(\?|$)/)
  })
})

// ---------------------------------------------------------------------------
// Accept-invite flow
// ---------------------------------------------------------------------------

test.describe('auth — accept invite', () => {
  test('valid token: shows inviter banner, accepts password, redirects to /chat', async ({ page }) => {
    await page.route('**/api/auth/invite/tok-good', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          valid: true,
          expired: false,
          user: { email: 'new@example.com', name: null, picture_url: null },
          inviter: { email: 'admin@example.com', name: 'Admin' },
        }),
      })
    })
    let acceptCalled = false
    await page.route('**/api/auth/accept-invite', async (route: Route) => {
      if (route.request().method() === 'POST') {
        acceptCalled = true
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ user: NEW_USER }),
        })
        return
      }
      await route.continue()
    })
    // After accept-invite the router pushes /chat which calls /api/auth/me.
    await page.route('**/api/auth/me', async (route: Route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ user: acceptCalled ? NEW_USER : null }),
        })
        return
      }
      await route.continue()
    })
    await page.route('**/api/auth/config', (r) =>
      r.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ has_google: false, google_client_id: null }),
      }),
    )
    await page.route('**/api/chat/sessions', (r) =>
      r.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )

    await page.goto('/accept-invite?token=tok-good')
    await expect(page.locator('[data-invite-banner]')).toBeVisible()
    await expect(page.locator('[data-invite-banner]')).toContainText('Admin')
    await expect(page.locator('[data-invite-banner]')).toContainText('new@example.com')

    await page.fill('[data-accept-password]', 'newpass1234')
    await page.fill('[data-accept-confirm]', 'newpass1234')
    await page.click('[data-accept-submit]')

    await expect(page).toHaveURL(/\/chat$/)
  })

  test('expired token renders 邀请链接已过期', async ({ page }) => {
    await page.route('**/api/auth/invite/tok-expired', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          valid: false,
          expired: true,
          user: { email: 'x@y.com' },
          inviter: null,
        }),
      })
    })

    await page.goto('/accept-invite?token=tok-expired')
    const errorBlock = page.locator('[data-invite-error]')
    await expect(errorBlock).toBeVisible()
    await expect(errorBlock).toContainText('邀请链接已过期')
  })

  test('used token renders 邀请已激活', async ({ page }) => {
    await page.route('**/api/auth/invite/tok-used', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          valid: false,
          expired: false,
          user: { email: 'x@y.com' },
          inviter: null,
        }),
      })
    })

    await page.goto('/accept-invite?token=tok-used')
    const errorBlock = page.locator('[data-invite-error]')
    await expect(errorBlock).toBeVisible()
    await expect(errorBlock).toContainText('邀请已激活')
  })

  test('invalid token (404) renders 链接无效', async ({ page }) => {
    await page.route('**/api/auth/invite/tok-bad', async (route: Route) => {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'invalid token' }),
      })
    })

    await page.goto('/accept-invite?token=tok-bad')
    const errorBlock = page.locator('[data-invite-error]')
    await expect(errorBlock).toBeVisible()
    await expect(errorBlock).toContainText('链接无效')
  })
})
