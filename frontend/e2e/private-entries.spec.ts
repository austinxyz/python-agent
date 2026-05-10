/**
 * E2E for the /private entries flow.
 *
 * Runs against the user-managed docker stack (see playwright.config.ts).
 * See helpers.ts for the data-isolation convention.
 */
import { test, expect } from './auth-fixture'
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

test.describe('/private entries flow', () => {
  test('create → view → edit → delete a tax entry', async ({ page }) => {
    const initialTitle = uniqueTitle('tax')
    const updatedTitle = `${initialTitle}_edited`

    await page.goto('/private')

    // 6 fixed template directories visible in the sidebar
    for (const dir of ['税务', '退休账户', '投资持仓', '个人基本情况', '房产资产', '自由格式']) {
      await expect(page.locator('[data-sidebar]')).toContainText(dir)
    }

    // + 新建条目 → pick tax → directory pre-fills
    await page.click('[data-new-entry-btn]')
    await page.click('[data-template-option="tax"]')
    await expect(page.locator('[data-entry-directory]')).toHaveValue('税务')

    // Fill form and save — capture ID before any further assertion
    await page.fill('[data-entry-title]', initialTitle)
    const agiField = page
      .locator('[data-entry-field]')
      .filter({ hasText: 'AGI' })
      .locator('input, textarea')
      .first()
    await agiField.fill('123456')
    const newId = await clickSaveAndCaptureEntryId(page)
    createdEntryIds.push(newId)

    // Item-view panel shows
    await expect(page.locator('[data-panel="item-view"]')).toBeVisible()

    // Entry visible under 税务 after expand; AGI value rendered
    await expandDirectoryByName(page, '税务')
    await expect(page.locator('[data-item]', { hasText: initialTitle })).toBeVisible()
    await expect(page.locator('[data-panel="item-view"]')).toContainText(initialTitle)
    await expect(page.locator('[data-panel="item-view"]')).toContainText('123456')

    // 编辑 → change title → save
    await page.click('[data-edit-item-btn]')
    await expect(page.locator('[data-panel="item-edit"]')).toBeVisible()
    const editTitleInput = page.locator('[data-panel="item-edit"] input').first()
    await editTitleInput.fill(updatedTitle)
    await page
      .locator('[data-panel="item-edit"]')
      .getByRole('button', { name: /保存/ })
      .click()
    await expect(page.locator('[data-panel="item-view"]')).toContainText(updatedTitle)
    await expect(page.locator('[data-item]', { hasText: updatedTitle })).toBeVisible()

    // 删除 → accept confirm → entry gone, back to welcome
    page.once('dialog', (dialog) => dialog.accept())
    await page.click('[data-delete-item-btn]')
    await expect(page.locator('[data-item]', { hasText: updatedTitle })).toHaveCount(0)
    createdEntryIds.length = 0 // server-deleted, not orphan
    await expect(page.locator('[data-panel="welcome"]')).toBeVisible()
  })
})
