/**
 * E2E for the admin → member management flow — multi-user-auth-admin-ui.
 *
 * Scenarios:
 *   1. Admin invites a new user via /admin/users web UI → user accepts invite
 *      in a separate browser context → admin sees user as active.
 *   2. Admin disables a user then re-enables them (PATCH flow).
 *   3. Admin disables then deletes a user with the type-to-confirm gate.
 *
 * Pre-requisites (same as integration.spec.ts):
 *   - Dev stack running: `npm run dev:up`
 *   - `INITIAL_ADMIN_EMAIL` set in .env so bootstrap created an admin
 *   - Admin has accepted their bootstrap invite and set a password
 *
 * Admin credentials for E2E are stored in env vars:
 *   E2E_ADMIN_EMAIL    (default: e2e-admin@example.com)
 *   E2E_ADMIN_PASSWORD (default: pw-e2e-admin-12345678)
 *
 * One-time setup: if the admin test user doesn't exist, the spec creates
 * them via CLI with role=admin, then accepts the invite. Run `npm run dev:reset`
 * to clear all state if credentials drift.
 *
 * Test user cleanup: all invited test users use `__e2e_` prefix in email
 * localpart; afterEach disables then deletes them even on failure.
 */
import { test, expect, type Browser, type BrowserContext } from '@playwright/test'
import { execSync } from 'node:child_process'

const API_CONTAINER = process.env.E2E_API_CONTAINER ?? 'python-agent-dev-api-1'
const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL ?? 'e2e-admin@example.com'
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? 'pw-e2e-admin-12345678'
const STAMP = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

let adminEnsured = false

function cliInvite(email: string, role: 'admin' | 'member' = 'member'): string {
  const stdout = execSync(
    `docker exec ${API_CONTAINER} python -m app.cli.invite_user "${email}" ${role}`,
    { encoding: 'utf8' },
  )
  const match = stdout.match(/Invite URL:\s*(\S+)/)
  if (!match) throw new Error(`CLI did not print an invite URL.\nstdout: ${stdout}`)
  return match[1]
}

function acceptPath(url: string): string {
  const u = new URL(url)
  return `${u.pathname}${u.search}`
}

async function ensureAdminUser(baseURL: string): Promise<void> {
  if (adminEnsured) return
  const { request } = await import('@playwright/test')
  const ctx = await request.newContext({ baseURL })
  try {
    const probe = await ctx.post('/api/auth/login', {
      data: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD },
    })
    if (probe.status() === 200) { adminEnsured = true; return }

    let inviteUrl: string
    try {
      inviteUrl = cliInvite(ADMIN_EMAIL, 'admin')
    } catch (e: any) {
      if (/already exists/.test(String(e.stderr ?? ''))) {
        throw new Error(
          `Admin test user ${ADMIN_EMAIL} exists but login failed. Run: npm run dev:reset && npm run e2e`,
        )
      }
      throw e
    }
    const u = new URL(inviteUrl)
    const accept = await ctx.post('/api/auth/accept-invite', {
      data: { token: u.searchParams.get('token'), password: ADMIN_PASSWORD },
    })
    if (accept.status() !== 200) {
      throw new Error(`accept-invite returned ${accept.status()}: ${await accept.text()}`)
    }
    adminEnsured = true
  } finally {
    await ctx.dispose()
  }
}

async function loginAdmin(context: BrowserContext): Promise<void> {
  const resp = await context.request.post('/api/auth/login', {
    data: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD },
  })
  if (resp.status() !== 200) {
    throw new Error(`Admin login failed (${resp.status()}): ${await resp.text()}`)
  }
}

async function cleanupUser(context: BrowserContext, userId: string): Promise<void> {
  try {
    // Must disable before delete; ignore 400 if already disabled.
    await context.request.patch(`/api/admin/users/${userId}`, {
      data: { status: 'disabled' },
    })
    await context.request.delete(`/api/admin/users/${userId}`)
  } catch {
    // best-effort
  }
}

test.describe.configure({ mode: 'serial' })

test.describe('admin-flow — invite + accept', () => {
  let invitedUserId = ''

  test.beforeEach(async ({ page, context, baseURL }) => {
    await ensureAdminUser(baseURL ?? 'http://localhost:3000')
    await loginAdmin(context)
  })

  test.afterEach(async ({ context }) => {
    if (invitedUserId) {
      await cleanupUser(context, invitedUserId)
      invitedUserId = ''
    }
  })

  test('admin invites user via web UI; new user accepts; admin sees them active', async ({
    page,
    browser,
  }) => {
    const newEmail = `__e2e_${STAMP}_invite@example.com`
    const newPassword = 'pw-e2e-new-12345678'

    // Navigate to /admin/users
    await page.goto('/admin/users')
    await expect(page).toHaveURL(/\/admin\/users/)
    await expect(page.getByRole('heading', { name: '用户管理' })).toBeVisible()

    // Open invite modal
    await page.click('button:has-text("邀请用户")')
    await expect(page.locator('h2:has-text("邀请新用户")')).toBeVisible()

    // Fill form and submit
    await page.fill('input[type="email"]', newEmail)
    const submitPromise = page.waitForResponse(
      (r) => r.url().includes('/api/admin/users') && r.request().method() === 'POST',
    )
    await page.click('button[type="submit"]:has-text("发送邀请"), button[type="submit"]:has-text("邀请")')
    const inviteResp = await submitPromise
    expect(inviteResp.status()).toBe(201)
    const inviteBody = await inviteResp.json()
    invitedUserId = inviteBody.user?.id ?? ''

    // Success state shows invite URL
    await expect(page.locator('h2:has-text("邀请已生成")')).toBeVisible()
    const codeEl = page.locator('code')
    const inviteUrl = await codeEl.textContent()
    expect(inviteUrl).toMatch(/\/accept-invite\?token=/)

    // Accept invite in a separate browser context (different storage = different user)
    const newCtx: BrowserContext = await browser.newContext()
    try {
      const newPage = await newCtx.newPage()
      await newPage.goto(acceptPath(inviteUrl!))
      await expect(newPage.locator('[data-accept-password], input[placeholder*="密码"], input[type="password"]').first()).toBeVisible()
      await newPage.fill('input[type="password"]', newPassword)
      const confirmInput = await newPage.$('input[data-accept-confirm], input[placeholder*="确认"]')
      if (confirmInput) await confirmInput.fill(newPassword)
      await newPage.click('[data-accept-submit], button[type="submit"]')
      await expect(newPage).toHaveURL(/\/chat$/, { timeout: 10_000 })
    } finally {
      await newCtx.close()
    }

    // Admin refreshes /admin/users and sees new user as active
    await page.reload()
    await expect(page.locator(`text=${newEmail}`).first()).toBeVisible({ timeout: 5_000 })
  })
})

test.describe('admin-flow — PATCH disable/re-enable', () => {
  let targetUserId = ''
  let targetEmail = ''

  test.beforeAll(async ({ browser }) => {
    const ctx = await browser.newContext()
    await ensureAdminUser('http://localhost:3000')
    await ctx.request.post('/api/auth/login', {
      data: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD },
    })
    // Create a member to manipulate
    targetEmail = `__e2e_${STAMP}_patch@example.com`
    const r = await ctx.request.post('/api/admin/users', {
      data: { email: targetEmail, role: 'member' },
    })
    if (r.status() === 201) {
      const body = await r.json()
      targetUserId = body.user?.id ?? ''
      // Accept invite so user is active
      const inviteUrl = body.invite_url ?? ''
      if (inviteUrl) {
        await ctx.request.post('/api/auth/accept-invite', {
          data: { token: new URL(inviteUrl).searchParams.get('token'), password: 'pw-e2e-patch-1' },
        })
      }
    }
    await ctx.close()
  })

  test.afterAll(async ({ browser }) => {
    if (!targetUserId) return
    const ctx = await browser.newContext()
    await ctx.request.post('/api/auth/login', { data: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD } })
    await cleanupUser(ctx, targetUserId)
    await ctx.close()
  })

  test.beforeEach(async ({ context }) => {
    await loginAdmin(context)
  })

  test('admin disables a user then re-enables them', async ({ page }) => {
    if (!targetUserId) test.skip()

    await page.goto('/admin/users')
    await expect(page.locator(`text=${targetEmail}`).first()).toBeVisible({ timeout: 8_000 })

    // Click disable button for target user row
    const row = page.locator(`[data-user-row]:has-text("${targetEmail}")`).first()
    await row.locator('button:has-text("停用"), button:has-text("禁用")').click()
    const disableResp = page.waitForResponse(
      (r) => r.url().includes(`/api/admin/users/${targetUserId}`) && r.request().method() === 'PATCH',
    )
    expect((await disableResp).status()).toBe(200)

    // Re-enable
    await page.reload()
    await expect(page.locator(`text=${targetEmail}`).first()).toBeVisible({ timeout: 8_000 })
    const row2 = page.locator(`[data-user-row]:has-text("${targetEmail}")`).first()
    await row2.locator('button:has-text("启用")').click()
    const enableResp = page.waitForResponse(
      (r) => r.url().includes(`/api/admin/users/${targetUserId}`) && r.request().method() === 'PATCH',
    )
    expect((await enableResp).status()).toBe(200)
  })
})

test.describe('admin-flow — DELETE with type-to-confirm', () => {
  let targetUserId = ''
  let targetEmail = ''

  test.beforeAll(async ({ browser }) => {
    const ctx = await browser.newContext()
    await ensureAdminUser('http://localhost:3000')
    await ctx.request.post('/api/auth/login', { data: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD } })
    targetEmail = `__e2e_${STAMP}_del@example.com`
    const r = await ctx.request.post('/api/admin/users', {
      data: { email: targetEmail, role: 'member' },
    })
    if (r.status() === 201) {
      const body = await r.json()
      targetUserId = body.user?.id ?? ''
      // Disable immediately (delete requires disabled status)
      if (targetUserId) {
        await ctx.request.patch(`/api/admin/users/${targetUserId}`, {
          data: { status: 'disabled' },
        })
      }
    }
    await ctx.close()
  })

  test.beforeEach(async ({ context }) => {
    await loginAdmin(context)
  })

  test('admin deletes a disabled user with type-to-confirm gate', async ({ page }) => {
    if (!targetUserId) test.skip()

    await page.goto('/admin/users')
    await expect(page.locator(`text=${targetEmail}`).first()).toBeVisible({ timeout: 8_000 })

    const row = page.locator(`[data-user-row]:has-text("${targetEmail}")`).first()
    await row.locator('button:has-text("删除")').click()

    // Delete modal appears
    await expect(page.locator('h2:has-text("永久删除用户")')).toBeVisible()

    // Confirm input is required; delete button disabled until localpart typed
    const confirmInput = page.locator('input[type="text"]:not([type="email"])').first()
    const deleteBtn = page.locator('button:has-text("永久删除")').first()
    await expect(deleteBtn).toBeDisabled()

    const localpart = targetEmail.split('@')[0]
    await confirmInput.fill(localpart)
    await expect(deleteBtn).toBeEnabled()

    const deleteResp = page.waitForResponse(
      (r) => r.url().includes(`/api/admin/users/${targetUserId}`) && r.request().method() === 'DELETE',
    )
    await deleteBtn.click()
    expect((await deleteResp).status()).toBe(204)

    // User no longer in list
    await expect(page.locator(`text=${targetEmail}`)).not.toBeVisible({ timeout: 5_000 })
    targetUserId = '' // cleared so afterAll cleanup skips
  })
})
