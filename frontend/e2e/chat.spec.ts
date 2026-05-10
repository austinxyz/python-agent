/**
 * E2E for /chat. The POST /api/chat endpoint is fully mocked with a canned
 * SSE response so the test never hits Anthropic / OpenAI. Same network-mock
 * pattern used in ingest.spec.ts.
 *
 * The save-to-notes flow uses a real-looking POST /api/private/notes mock
 * — we never write to the user's actual notes.
 */
import { test, expect } from './auth-fixture'
import type { Page, Route } from '@playwright/test'

const E2E_PREFIX = '__e2e_'

function uniqueTitle(label: string): string {
  return `${E2E_PREFIX}${label}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

const FAKE_SESSION_ID = 'e2e-chat-session-001'

// SSE stream for a deterministic answer. Sources include both kinds so the
// chip-routing tests work without sending a second request.
function buildFakeSseBody(answer: string, sessionId: string): string {
  const events: string[] = []
  // Stream answer in 3 chunks
  const chunkSize = Math.ceil(answer.length / 3)
  for (let i = 0; i < answer.length; i += chunkSize) {
    const piece = answer.slice(i, i + chunkSize)
    events.push(`data: ${JSON.stringify({ type: 'token', content: piece })}\n\n`)
  }
  events.push(
    `data: ${JSON.stringify({
      type: 'done',
      sources: [
        { title: 'FBAR', domain: '中美对比', file_id: 'k-fbar', kind: 'knowledge' },
        { title: '我的税务', domain: '税务', file_id: 'p-tax', kind: 'entry' },
      ],
      session_id: sessionId,
    })}\n\n`,
  )
  return events.join('')
}

async function mockChatBackend(page: Page, savedNoteIds: string[]) {
  // Sessions list — return a single previous session so the sidebar has content
  // to render (lets us test "click session calls loadSession").
  await page.route('**/api/chat/sessions', async (route: Route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: 'prev-1', title: '先前的对话', model: 'haiku', created_at: '2026-05-01T10:00:00Z' },
        ]),
      })
      return
    }
    await route.continue()
  })

  // Session detail — used by loadSession
  await page.route('**/api/chat/sessions/prev-1', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'prev-1', title: '先前的对话', model: 'haiku', created_at: '2026-05-01T10:00:00Z',
        messages: [
          { role: 'user', content: '什么是 401k', sources: [] },
          { role: 'assistant', content: '401k 是雇主提供的退休账户。', sources: [] },
        ],
      }),
    })
  })

  // POST /api/chat — canned SSE
  await page.route('**/api/chat', async (route: Route) => {
    if (route.request().method() === 'POST') {
      const body = JSON.parse(route.request().postData() || '{}')
      const answer = `根据知识库，${body.query} 的答案是这样的。`
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: buildFakeSseBody(answer, FAKE_SESSION_ID),
      })
      return
    }
    await route.continue()
  })

  // POST /api/private/notes — record + return a fake created note
  await page.route('**/api/private/notes', async (route: Route) => {
    if (route.request().method() === 'POST') {
      const body = JSON.parse(route.request().postData() || '{}')
      const id = `note-${Date.now()}`
      savedNoteIds.push(id)
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id,
          title: body.title,
          directory: body.directory ?? '',
          content: body.content ?? '',
          chat_ref: body.chat_ref ?? null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }),
      })
      return
    }
    await route.continue()
  })
}

// ---------------------------------------------------------------------------
// Empty state + sessions sidebar
// ---------------------------------------------------------------------------

test.describe('/chat empty state', () => {
  test('mounts with prompt cards visible and no messages', async ({ page }) => {
    const saved: string[] = []
    await mockChatBackend(page, saved)
    await page.goto('/chat')
    await expect(page.locator('[data-empty-state]')).toBeVisible()
    await expect(page.locator('[data-prompt-card]')).toHaveCount(6)
    await expect(page.locator('[data-assistant-msg]')).toHaveCount(0)
  })

  test('clicking a prompt card fills the textarea', async ({ page }) => {
    const saved: string[] = []
    await mockChatBackend(page, saved)
    await page.goto('/chat')
    await page.locator('[data-prompt-card]').first().click()
    const input = page.locator('[data-chat-input]')
    const value = await input.inputValue()
    expect(value.length).toBeGreaterThan(10)
  })

  test('sessions list renders the existing session in the sidebar', async ({ page }) => {
    const saved: string[] = []
    await mockChatBackend(page, saved)
    await page.goto('/chat')
    await expect(page.locator('[data-session-item]')).toHaveCount(1)
    await expect(page.locator('[data-session-item]')).toContainText('先前的对话')
  })
})

// ---------------------------------------------------------------------------
// Submit + streamed answer + source chips
// ---------------------------------------------------------------------------

test.describe('/chat submit flow', () => {
  test('submitting a question streams an answer and renders source chips', async ({ page }) => {
    const saved: string[] = []
    await mockChatBackend(page, saved)
    await page.goto('/chat')

    const question = uniqueTitle('退休账户怎么选')
    await page.fill('[data-chat-input]', question)
    await page.click('[data-chat-submit]')

    // Assistant message appears with the streamed text
    await expect(page.locator('[data-assistant-msg]')).toBeVisible()
    await expect(page.locator('[data-assistant-msg]')).toContainText(question)
    await expect(page.locator('[data-assistant-msg]')).toContainText('的答案是这样的')

    // Both source chips appear
    const chips = page.locator('[data-source-chip]')
    await expect(chips).toHaveCount(2)
    await expect(chips.nth(0)).toContainText('FBAR')
    await expect(chips.nth(0)).toContainText('中美对比')
    await expect(chips.nth(1)).toContainText('我的税务')
    await expect(chips.nth(1)).toContainText('税务')
  })
})

// ---------------------------------------------------------------------------
// Source chip routing — kind drives the destination page
// ---------------------------------------------------------------------------

test.describe('/chat source chip routing', () => {
  test('knowledge chip navigates to /wiki?file=<id>', async ({ page }) => {
    const saved: string[] = []
    await mockChatBackend(page, saved)
    // Wiki tree mock so navigating doesn't 404 against the real backend
    await page.route('**/api/wiki/tree', (r) => r.fulfill({
      status: 200, contentType: 'application/json', body: JSON.stringify({}),
    }))
    await page.goto('/chat')
    await page.fill('[data-chat-input]', '问知识库')
    await page.click('[data-chat-submit]')
    await expect(page.locator('[data-source-chip]').first()).toBeVisible()
    await page.locator('[data-source-chip]').first().click()  // FBAR (kind=knowledge)
    await expect(page).toHaveURL(/\/wiki\?file=k-fbar/)
  })

  test('private-entry chip navigates to /private?entry=<id>', async ({ page }) => {
    const saved: string[] = []
    await mockChatBackend(page, saved)
    // PrivateView fetches templates / entries / notes on mount — return empty so the page renders
    await page.route('**/api/private/templates', (r) => r.fulfill({
      status: 200, contentType: 'application/json', body: '[]',
    }))
    await page.route('**/api/private/entries', (r) => r.fulfill({
      status: 200, contentType: 'application/json', body: '[]',
    }))
    await page.route('**/api/private/notes', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({ status: 200, contentType: 'application/json', body: '{"notes":[],"tree":{}}' })
        return
      }
      await route.continue() // keep POST mock from mockChatBackend
    })
    await page.goto('/chat')
    await page.fill('[data-chat-input]', '问私有')
    await page.click('[data-chat-submit]')
    await expect(page.locator('[data-source-chip]').nth(1)).toBeVisible()
    await page.locator('[data-source-chip]').nth(1).click()  // 我的税务 (kind=entry)
    await expect(page).toHaveURL(/\/private\?entry=p-tax/)
  })
})

// ---------------------------------------------------------------------------
// Save-to-notes flow
// ---------------------------------------------------------------------------

test.describe('/chat save-to-notes', () => {
  test('expanding the form pre-fills title, directory and markdown content with deep links', async ({ page }) => {
    const saved: string[] = []
    await mockChatBackend(page, saved)
    await page.goto('/chat')
    await page.fill('[data-chat-input]', '退休账户怎么选')
    await page.click('[data-chat-submit]')
    await expect(page.locator('[data-save-note-btn]')).toBeVisible()
    await page.click('[data-save-note-btn]')
    await expect(page.locator('[data-save-note-form]')).toBeVisible()

    const titleVal = await page.locator('[data-save-note-title]').inputValue()
    expect(titleVal).toContain('退休账户')

    const dirVal = await page.locator('[data-save-note-directory]').inputValue()
    expect(dirVal).toMatch(/^对话总结\/\d{4}-\d{2}-\d{2}$/)

    const contentVal = await page.locator('[data-save-note-content]').inputValue()
    expect(contentVal).toContain('退休账户怎么选') // user question
    expect(contentVal).toContain('的答案是这样的')  // assistant body
    expect(contentVal).toContain('/wiki?file=k-fbar') // knowledge source link
    expect(contentVal).toContain('/private?entry=p-tax') // private entry source link
  })

  test('clicking 保存 POSTs to /private/notes with chat_ref and shows confirmation', async ({ page }) => {
    const saved: string[] = []
    await mockChatBackend(page, saved)
    await page.goto('/chat')
    await page.fill('[data-chat-input]', '保存测试')
    await page.click('[data-chat-submit]')
    await expect(page.locator('[data-save-note-btn]')).toBeVisible()
    await page.click('[data-save-note-btn]')

    const requestPromise = page.waitForRequest((r) =>
      r.url().includes('/api/private/notes') && r.method() === 'POST'
    )
    await page.click('[data-save-note-confirm]')
    const req = await requestPromise

    const body = JSON.parse(req.postData() || '{}')
    expect(body.chat_ref).toBe(FAKE_SESSION_ID)
    expect(body.title).toBeTruthy()
    expect(body.directory).toMatch(/^对话总结\/\d{4}-\d{2}-\d{2}$/)
    expect(body.content).toContain('的答案是这样的')

    // Confirmation appears, form is gone
    await expect(page.locator('[data-save-note-confirmation]')).toBeVisible()
    await expect(page.locator('[data-save-note-confirmation]')).toContainText('已保存')
    await expect(page.locator('[data-save-note-form]')).toHaveCount(0)
    expect(saved.length).toBe(1)
  })

  test('clicking 取消 collapses the form without POSTing', async ({ page }) => {
    const saved: string[] = []
    await mockChatBackend(page, saved)
    await page.goto('/chat')
    await page.fill('[data-chat-input]', '取消测试')
    await page.click('[data-chat-submit]')
    await expect(page.locator('[data-save-note-btn]')).toBeVisible()
    await page.click('[data-save-note-btn]')
    await page.click('[data-save-note-cancel]')
    await expect(page.locator('[data-save-note-form]')).toHaveCount(0)
    expect(saved.length).toBe(0)
  })
})
