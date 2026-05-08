/**
 * Additional E2E coverage for the /private flow:
 *   - Templates parameterized: each template's default_directory pre-fills correctly
 *   - Custom directory override: a sub-path under a template directory works
 *   - Dirty-check guard: switching from new-entry mid-fill prompts a confirm
 */
import { test, expect } from '@playwright/test'
import {
  cleanupEntries,
  clickSaveAndCaptureEntryId,
  expandDirectoryByName,
  uniqueTitle,
} from './helpers'

const createdEntryIds: string[] = []

test.afterEach(async ({ request }) => {
  await cleanupEntries(request, createdEntryIds)
  createdEntryIds.length = 0
})

// ---------------------------------------------------------------------------
// Test 2: parameterized template directory pre-fill
// ---------------------------------------------------------------------------

const TEMPLATE_DIRECTORY_FIXTURES = [
  { type: 'retirement', dir: '退休账户', label: '退休账户' },
  { type: 'portfolio', dir: '投资持仓', label: '投资持仓' },
  { type: 'personal', dir: '个人基本情况', label: '个人基本情况' },
  { type: 'real_estate', dir: '房产资产', label: '房产资产' },
  { type: 'freeform', dir: '自由格式', label: '自由格式' },
]

for (const fixture of TEMPLATE_DIRECTORY_FIXTURES) {
  test(`new-entry: picking ${fixture.type} pre-fills directory to ${fixture.dir} and creates an entry`, async ({
    page,
  }) => {
    const title = uniqueTitle(fixture.type)
    await page.goto('/private')
    await page.click('[data-new-entry-btn]')
    await page.click(`[data-template-option="${fixture.type}"]`)
    await expect(page.locator('[data-entry-directory]')).toHaveValue(fixture.dir)
    await page.fill('[data-entry-title]', title)
    const newId = await clickSaveAndCaptureEntryId(page)
    createdEntryIds.push(newId)
    await expect(page.locator('[data-panel="item-view"]')).toContainText(title)
    await expandDirectoryByName(page, fixture.dir)
    await expect(page.locator('[data-item]', { hasText: title })).toBeVisible()
  })
}

// ---------------------------------------------------------------------------
// Test 3: custom directory override survives create + appears nested in tree
// ---------------------------------------------------------------------------

test('new-entry: custom sub-directory override creates nested tree node', async ({ page }) => {
  const title = uniqueTitle('tax_2025')
  await page.goto('/private')
  await page.click('[data-new-entry-btn]')
  await page.click('[data-template-option="tax"]')
  // Override the pre-filled directory to a sub-path
  await page.fill('[data-entry-directory]', '税务/2025')
  await page.fill('[data-entry-title]', title)
  const newId = await clickSaveAndCaptureEntryId(page)
  createdEntryIds.push(newId)
  await expect(page.locator('[data-panel="item-view"]')).toContainText('税务/2025')

  // Sidebar: expand 税务 → 2025 sub-directory should appear → expand → entry visible
  await expandDirectoryByName(page, '税务')
  await expandDirectoryByName(page, '2025')
  await expect(page.locator('[data-item]', { hasText: title })).toBeVisible()
})

// ---------------------------------------------------------------------------
// Test 4: dirty-check guard fires confirm when leaving mid-fill new-entry
// ---------------------------------------------------------------------------

test('dirty-check: clicking an existing item mid new-entry prompts confirm; cancel keeps form', async ({
  page,
}) => {
  const draftTitle = uniqueTitle('draft')
  await page.goto('/private')

  // Seed: create one entry first so there's an item to click later
  await page.click('[data-new-entry-btn]')
  await page.click('[data-template-option="tax"]')
  await page.fill('[data-entry-title]', uniqueTitle('seed'))
  const seedId = await clickSaveAndCaptureEntryId(page)
  createdEntryIds.push(seedId)

  // Now open new-entry again and start filling a draft
  await page.click('[data-new-entry-btn]')
  await page.click('[data-template-option="retirement"]')
  await page.fill('[data-entry-title]', draftTitle)

  // Click the seed item → confirm dialog must fire
  let dialogFired = false
  page.once('dialog', (dialog) => {
    dialogFired = true
    expect(dialog.message()).toContain('放弃')
    dialog.dismiss() // cancel — keep the form
  })
  await expandDirectoryByName(page, '税务')
  await page.locator('[data-item]').first().click()
  await page.waitForTimeout(200) // allow the dialog handler to run

  expect(dialogFired).toBe(true)
  // After dismiss the new-entry panel is still visible and draft title preserved
  await expect(page.locator('[data-panel="new-entry"]')).toBeVisible()
  await expect(page.locator('[data-entry-title]')).toHaveValue(draftTitle)
})

test('dirty-check: clicking sidebar mid new-entry then accepting discards the draft', async ({
  page,
}) => {
  const draftTitle = uniqueTitle('discarded')
  await page.goto('/private')

  // Seed: create a real entry first so there's an item to navigate TO after discard.
  // (Items show item-view; empty directories do nothing useful.)
  await page.click('[data-new-entry-btn]')
  await page.click('[data-template-option="tax"]')
  await page.fill('[data-entry-title]', uniqueTitle('seed'))
  const seedId = await clickSaveAndCaptureEntryId(page)
  createdEntryIds.push(seedId)

  // Now open another new-entry, fill draft, then click the seed item
  await page.click('[data-new-entry-btn]')
  await page.click('[data-template-option="retirement"]')
  await page.fill('[data-entry-title]', draftTitle)

  page.once('dialog', (dialog) => dialog.accept()) // discard the draft
  await expandDirectoryByName(page, '税务')
  await page.locator('[data-item]').first().click()

  // Right panel transitions to item-view (draft is gone)
  await expect(page.locator('[data-panel="item-view"]')).toBeVisible()
  await expect(page.locator('[data-panel="new-entry"]')).toHaveCount(0)
})

// ---------------------------------------------------------------------------
// Test 4b: dirty-check fires when clicking + 新建条目 / + 新建笔记 mid-fill too
// ---------------------------------------------------------------------------

test('dirty-check: clicking + 新建笔记 mid new-entry prompts confirm; cancel keeps form', async ({
  page,
}) => {
  const draftTitle = uniqueTitle('keep_entry_draft')
  await page.goto('/private')

  await page.click('[data-new-entry-btn]')
  await page.click('[data-template-option="tax"]')
  await page.fill('[data-entry-title]', draftTitle)

  let dialogFired = false
  page.once('dialog', (dialog) => {
    dialogFired = true
    expect(dialog.message()).toContain('放弃')
    dialog.dismiss() // cancel
  })
  await page.click('[data-new-note-btn]')
  await page.waitForTimeout(200)

  expect(dialogFired).toBe(true)
  // After dismiss the new-entry panel is still visible and draft preserved
  await expect(page.locator('[data-panel="new-entry"]')).toBeVisible()
  await expect(page.locator('[data-entry-title]')).toHaveValue(draftTitle)
})

test('dirty-check: clicking + 新建条目 mid new-note prompts confirm; accept switches to new-entry', async ({
  page,
}) => {
  const draftNoteTitle = uniqueTitle('discarded_note_draft')
  await page.goto('/private')

  await page.click('[data-new-note-btn]')
  await page.fill('[data-note-title]', draftNoteTitle)
  await page.fill('[data-note-content]', '这是要被丢弃的草稿内容')

  let dialogFired = false
  page.once('dialog', (dialog) => {
    dialogFired = true
    expect(dialog.message()).toContain('放弃')
    dialog.accept() // discard
  })
  await page.click('[data-new-entry-btn]')
  await page.waitForTimeout(200)

  expect(dialogFired).toBe(true)
  // After accept the new-entry panel is shown and the prior draft is gone
  await expect(page.locator('[data-panel="new-entry"]')).toBeVisible()
  await expect(page.locator('[data-panel="new-note"]')).toHaveCount(0)
})
