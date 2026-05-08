/**
 * E2E for /ingest. Covers the read-side flows (domain navigation, form
 * rendering, source-type switching) against the real backend. The actual
 * POST /ingest path is intercepted with page.route() so the test never
 * triggers the real pipeline (no OpenAI tokens, no Qdrant pollution).
 */
import { test, expect } from '@playwright/test'

const DOMAINS = [
  '退休规划', '账户类型', '税务策略', '投资品种', '保险规划',
  '股权激励', '家庭财务', '中美对比', '遗产规划', '其他',
]

test.describe('/ingest read-side', () => {
  test('mount renders all 10 domain names in the left sidebar', async ({ page }) => {
    await page.goto('/ingest')
    for (const d of DOMAINS) {
      await expect(page.locator('[data-domain-name]', { hasText: d })).toBeVisible()
    }
  })

  test('default state shows the welcome panel', async ({ page }) => {
    await page.goto('/ingest')
    await expect(page.locator('[data-panel="welcome"]')).toBeVisible()
    await expect(page.locator('[data-panel="domain"]')).toHaveCount(0)
  })

  test('clicking a domain name transitions to the domain panel', async ({ page }) => {
    await page.goto('/ingest')
    await page.locator('[data-domain-name]', { hasText: '退休规划' }).first().click()
    await expect(page.locator('[data-panel="domain"]')).toBeVisible()
    await expect(page.locator('[data-panel="domain"]')).toContainText('退休规划')
    await expect(page.locator('[data-panel="domain"]')).toContainText('新建摄入')
  })

  test('chevron click expands file list inline without changing right panel', async ({ page }) => {
    await page.goto('/ingest')
    // welcome stays visible
    await expect(page.locator('[data-panel="welcome"]')).toBeVisible()
    // click the first domain's chevron
    await page.locator('[data-domain-chevron]').first().click()
    // welcome must still be the active right panel
    await expect(page.locator('[data-panel="welcome"]')).toBeVisible()
    await expect(page.locator('[data-panel="domain"]')).toHaveCount(0)
  })

  test('clicking + 新建摄入 opens the form panel with the domain badge', async ({ page }) => {
    await page.goto('/ingest')
    await page.locator('[data-domain-name]', { hasText: '税务策略' }).first().click()
    await page.click('[data-action="new-ingest"]')
    await expect(page.locator('[data-panel="form"]')).toBeVisible()
    await expect(page.locator('[data-domain-badge]')).toHaveText('税务策略')
    // Default source type is URL — its input is visible
    await expect(page.locator('[data-input="source_url"]')).toBeVisible()
  })
})

// ---------------------------------------------------------------------------
// Source-type switching — confirms each tab swaps the correct input
// ---------------------------------------------------------------------------

test.describe('/ingest source-type tabs', () => {
  test('switching to text shows the textarea, switching to file shows the dropzone', async ({ page }) => {
    await page.goto('/ingest')
    await page.locator('[data-domain-name]', { hasText: '退休规划' }).first().click()
    await page.click('[data-action="new-ingest"]')

    // URL is the default
    await expect(page.locator('[data-input="source_url"]')).toBeVisible()
    await expect(page.locator('[data-input="content"]')).toHaveCount(0)

    await page.click('[data-source-type="text"]')
    await expect(page.locator('[data-input="content"]')).toBeVisible()
    await expect(page.locator('[data-input="source_url"]')).toHaveCount(0)

    await page.click('[data-source-type="file"]')
    await expect(page.locator('[data-input="file"]')).toBeAttached()
    await expect(page.locator('[data-input="content"]')).toHaveCount(0)
  })
})

// ---------------------------------------------------------------------------
// Submit path — fully mocked (no real ingest)
// ---------------------------------------------------------------------------

test.describe('/ingest submit (network-mocked)', () => {
  test('valid URL submission switches to the result panel without hitting the real pipeline', async ({ page }) => {
    // Intercept POST /api/ingest before it reaches the real backend
    await page.route('**/api/ingest', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 202,
          contentType: 'application/json',
          body: JSON.stringify({ job_id: 'e2e-fake-job-001' }),
        })
        return
      }
      await route.continue()
    })
    // Intercept the polling endpoint — return a still-running status so
    // the spec doesn't have to handle the completed→result→domain flip.
    await page.route('**/api/ingest/status/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'running' }),
      })
    })

    await page.goto('/ingest')
    await page.locator('[data-domain-name]', { hasText: '其他' }).first().click()
    await page.click('[data-action="new-ingest"]')

    await page.fill('[data-input="title"]', '__e2e_ingest_url')
    // Default source type is URL; fill the URL field
    await page.fill('[data-input="source_url"]', 'https://example.com/article')

    // Capture the POST so we can assert the body before it resolves
    const requestPromise = page.waitForRequest((req) =>
      req.url().includes('/api/ingest') && req.method() === 'POST'
    )
    await page.click('[data-action="submit-ingest"]')
    const req = await requestPromise

    const body = req.postData() ?? ''
    expect(body).toContain('__e2e_ingest_url')
    expect(body).toContain('https://example.com/article')
    expect(body).toContain('其他') // domain
    expect(body).toContain('url')   // source_type

    // After the (mocked) 202 response the panel transitions to result
    await expect(page.locator('[data-panel="result"]')).toBeVisible()
    await expect(page.locator('[data-panel="result"]')).toContainText('__e2e_ingest_url')
    await expect(page.locator('[data-panel="result"]')).toContainText('其他')
  })

  test('empty title shows the validation error and does not POST', async ({ page }) => {
    let postCount = 0
    await page.route('**/api/ingest', async (route) => {
      if (route.request().method() === 'POST') postCount++
      await route.continue()
    })

    await page.goto('/ingest')
    await page.locator('[data-domain-name]', { hasText: '退休规划' }).first().click()
    await page.click('[data-action="new-ingest"]')
    // Don't fill title — submit straight away
    await page.click('[data-action="submit-ingest"]')

    await expect(page.locator('[data-ingest-error]')).toBeVisible()
    await expect(page.locator('[data-ingest-error]')).toContainText('请输入标题')
    expect(postCount).toBe(0)
  })
})
