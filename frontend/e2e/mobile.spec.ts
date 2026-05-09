/**
 * E2E for mobile-friendly viewport (iPhone 14, 393x852).
 * Asserts the mobile-specific UI: bottom tab nav, ☰ tree drawers, ChatView
 * sessions drawer + sticky input, PrivateView ＋ button, IngestView ☰ tree.
 *
 * Backend API calls are mocked the same way chat.spec.ts mocks them, so this
 * test never hits Anthropic / OpenAI and never writes real DB rows.
 */
import { test, expect, type Page, type Route } from '@playwright/test'

const E2E_PREFIX = '__e2e_'
const FAKE_SESSION_ID = 'e2e-mobile-session-001'

function uniqueTitle(label: string): string {
  return `${E2E_PREFIX}${label}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

function buildFakeSseBody(answer: string, sessionId: string): string {
  const events: string[] = []
  events.push(`data: ${JSON.stringify({ type: 'token', content: answer })}\n\n`)
  events.push(
    `data: ${JSON.stringify({
      type: 'done',
      sources: [
        { title: '401k', domain: '退休规划', file_id: 'k-401k', kind: 'knowledge' },
      ],
      session_id: sessionId,
    })}\n\n`,
  )
  return events.join('')
}

async function mockChatBackend(page: Page) {
  await page.route('**/api/chat/sessions', async (route: Route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: 'm-prev-1', title: '手机端历史会话', model: 'haiku', created_at: '2026-05-01T10:00:00Z' },
        ]),
      })
      return
    }
    await route.continue()
  })
  await page.route('**/api/chat', async (route: Route) => {
    if (route.request().method() === 'POST') {
      const body = JSON.parse(route.request().postData() || '{}')
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: buildFakeSseBody(`关于「${body.query}」，简要回答如下。`, FAKE_SESSION_ID),
      })
      return
    }
    await route.continue()
  })
}

async function mockIngestBackend(page: Page) {
  await page.route('**/api/files', async (route: Route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      })
      return
    }
    await route.continue()
  })
  await page.route('**/api/ingest', async (route: Route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 202,
        contentType: 'application/json',
        body: JSON.stringify({ job_id: 'job-mobile-001' }),
      })
      return
    }
    await route.continue()
  })
  // Job polling — return immediate success.
  await page.route(/\/api\/ingest\/jobs\/.*/, async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        job_id: 'job-mobile-001',
        status: 'completed',
        progress: 100,
        result: { file_id: 'm-fake-file', title: 'mobile-e2e' },
      }),
    })
  })
}

// ---------------------------------------------------------------------------
// Bottom tab bar (AppLayout)
// ---------------------------------------------------------------------------

test.describe('mobile bottom tab nav', () => {
  test('bottom tabs visible at iPhone 14 viewport, sidebar hidden', async ({ page }) => {
    await mockChatBackend(page)
    await page.goto('/chat')
    const bottomTabs = page.locator('[data-bottom-tabs]')
    await expect(bottomTabs).toBeVisible()
    await expect(bottomTabs.locator('a')).toHaveCount(4)
    // Desktop sidebar (<aside>) is hidden via Tailwind hidden md:flex.
    await expect(page.locator('aside')).toBeHidden()
  })
})

// ---------------------------------------------------------------------------
// ChatView mobile
// ---------------------------------------------------------------------------

test.describe('ChatView mobile', () => {
  test('☰ opens sessions drawer with previous session listed', async ({ page }) => {
    await mockChatBackend(page)
    await page.goto('/chat')
    await expect(page.locator('[data-sessions-toggle]')).toBeVisible()
    await page.click('[data-sessions-toggle]')
    const drawer = page.locator('[data-sessions-drawer]')
    await expect(drawer).toBeVisible()
    await expect(drawer.locator('[data-drawer-session]')).toHaveCount(1)
  })

  test('🆕 starts a new session and reveals empty state', async ({ page }) => {
    await mockChatBackend(page)
    await page.goto('/chat')
    await page.click('[data-new-chat]')
    await expect(page.locator('[data-empty-state]')).toBeVisible()
  })

  test('typing a message and submitting streams a fake assistant response', async ({ page }) => {
    await mockChatBackend(page)
    await page.goto('/chat')
    await page.fill('[data-chat-input]', '什么是 401k')
    await page.click('[data-chat-submit]')
    await expect(page.locator('[data-assistant-msg]').first()).toContainText('简要回答')
    await expect(page.locator('[data-source-chip]').first()).toBeVisible()
  })
})

// ---------------------------------------------------------------------------
// PrivateView mobile
// ---------------------------------------------------------------------------

test.describe('PrivateView mobile', () => {
  test('＋ in header reveals new-entry form without opening drawer', async ({ page }) => {
    await page.goto('/private')
    await expect(page.locator('[data-new-entry]')).toBeVisible()
    await page.click('[data-new-entry]')
    await expect(page.locator('[data-tree-drawer]')).toBeHidden()
    await expect(page.locator('[data-panel="new-entry"]')).toBeVisible()
  })

  test('☰ opens directory drawer', async ({ page }) => {
    await page.goto('/private')
    await page.click('[data-tree-toggle]')
    await expect(page.locator('[data-tree-drawer]')).toBeVisible()
  })
})

// ---------------------------------------------------------------------------
// IngestView mobile
// ---------------------------------------------------------------------------

test.describe('IngestView mobile', () => {
  test('☰ opens domain drawer; selecting a domain closes it', async ({ page }) => {
    await mockIngestBackend(page)
    await page.goto('/ingest')
    await page.click('[data-tree-toggle]')
    const drawer = page.locator('[data-tree-drawer]')
    await expect(drawer).toBeVisible()
    const firstDomain = drawer.locator('[data-drawer-domain]').first()
    await firstDomain.locator('span').first().click()
    await expect(drawer).toBeHidden()
  })
})
