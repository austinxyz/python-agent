/**
 * E2E for /wiki. WikiView is read-only — no write side-effects to worry
 * about. We mock the wiki tree and the per-file content endpoints so the
 * spec doesn't depend on whatever data happens to live in the user's
 * actual knowledge collection.
 */
import { test, expect } from './auth-fixture'

const FIXTURE_TREE = {
  '退休规划': [
    { file_id: 'e2e-wiki-1', title: 'Roth IRA 全攻略', orig_name: 'roth.md', filename: 'roth.md', source_type: 'text', domain: '退休规划', chunk_count: 3, source_url: null },
    { file_id: 'e2e-wiki-2', title: '401k 入门', orig_name: '401k.md', filename: '401k.md', source_type: 'text', domain: '退休规划', chunk_count: 2, source_url: null },
  ],
  '税务策略': [
    { file_id: 'e2e-wiki-3', title: 'AMT 基础', orig_name: 'amt.md', filename: 'amt.md', source_type: 'text', domain: '税务策略', chunk_count: 4, source_url: null },
  ],
}

async function mockWikiBackend(page) {
  await page.route('**/api/wiki/tree', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(FIXTURE_TREE),
    })
  })
  await page.route('**/api/files/e2e-wiki-1/content', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'text/plain; charset=utf-8',
      body: '# Roth IRA 全攻略\n\n这是 Roth IRA 的核心内容。',
    })
  })
}

test.describe('/wiki read-only flow', () => {
  test('mount renders the search input and welcome panel', async ({ page }) => {
    await mockWikiBackend(page)
    await page.goto('/wiki')
    await expect(page.locator('[data-search-input]')).toBeVisible()
    await expect(page.locator('[data-panel="welcome"]')).toBeVisible()
    await expect(page.locator('[data-panel="content"]')).toHaveCount(0)
  })

  test('sidebar shows domains from the tree', async ({ page }) => {
    await mockWikiBackend(page)
    await page.goto('/wiki')
    // tree fetch is async; allow it to resolve
    await expect(page.getByText('退休规划').first()).toBeVisible()
    await expect(page.getByText('税务策略').first()).toBeVisible()
  })

  test('expanding a domain reveals file titles', async ({ page }) => {
    await mockWikiBackend(page)
    await page.goto('/wiki')
    // Wait for the tree to load before clicking
    await expect(page.getByText('退休规划').first()).toBeVisible()
    await page.locator('[data-domain-chevron]').first().click()
    await expect(page.locator('[data-sidebar-file]', { hasText: 'Roth IRA' })).toBeVisible()
    await expect(page.locator('[data-sidebar-file]', { hasText: '401k 入门' })).toBeVisible()
  })

  test('search filters domains; clearing restores full tree', async ({ page }) => {
    await mockWikiBackend(page)
    await page.goto('/wiki')
    await expect(page.getByText('退休规划').first()).toBeVisible()

    await page.fill('[data-search-input]', 'AMT')
    // 退休规划 should drop out, 税务策略 stays
    await expect(page.getByText('退休规划').first()).not.toBeVisible()
    await expect(page.getByText('税务策略').first()).toBeVisible()

    await page.fill('[data-search-input]', '')
    await expect(page.getByText('退休规划').first()).toBeVisible()
    await expect(page.getByText('税务策略').first()).toBeVisible()
  })

  test('clicking a file title loads content in the right panel and adds active class', async ({ page }) => {
    await mockWikiBackend(page)
    await page.goto('/wiki')
    await expect(page.getByText('退休规划').first()).toBeVisible()

    await page.locator('[data-domain-chevron]').first().click()
    await page.locator('[data-sidebar-file]', { hasText: 'Roth IRA' }).click()

    // Right panel switches to content; header shows the title and domain badge
    await expect(page.locator('[data-panel="content"]')).toBeVisible()
    await expect(page.locator('[data-panel="content"]')).toContainText('Roth IRA 全攻略')
    await expect(page.locator('[data-domain-badge]')).toHaveText('退休规划')
    // download button visible with correct href
    const dl = page.locator('[data-download-btn]')
    await expect(dl).toBeVisible()
    await expect(dl).toHaveAttribute('href', '/api/files/e2e-wiki-1/download')

    // Content body rendered (markdown text → escaped HTML; we just check the words)
    await expect(page.locator('[data-panel="content"]')).toContainText('Roth IRA 的核心内容')

    // Active highlight on the selected file (literal `active` class — guarded by tests)
    const activeFile = page.locator('[data-sidebar-file].active')
    await expect(activeFile).toHaveCount(1)
    await expect(activeFile).toContainText('Roth IRA')
  })
})
