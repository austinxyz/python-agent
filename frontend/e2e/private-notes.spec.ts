/**
 * E2E for the /private notes flow.
 *
 * Notes are SQLite-only (not vectorized). They support nested directories
 * (e.g., "退休规划/Roth相关"), so this spec also exercises the recursive
 * DirectoryTreeNode renderer.
 */
import { test, expect } from './auth-fixture'
import {
  cleanupNotes,
  clickSaveAndCaptureNoteId,
  expandDirectoryByName,
  uniqueTitle,
} from './helpers'

const createdNoteIds: string[] = []

test.afterEach(async ({ request }) => {
  await cleanupNotes(request, createdNoteIds)
  createdNoteIds.length = 0
})

test.describe('/private notes flow', () => {
  test('create nested-directory note → tree shows nested → view → edit → delete', async ({
    page,
  }) => {
    const initialTitle = uniqueTitle('roth_note')
    const updatedContent = `# 更新后\n\n这是 ${initialTitle} 的新内容。`

    await page.goto('/private')

    // Click + 新建笔记 → form appears
    await page.click('[data-new-note-btn]')
    await expect(page.locator('[data-panel="new-note"]')).toBeVisible()

    // Fill title, nested directory, content
    await page.fill('[data-note-title]', initialTitle)
    await page.fill('[data-note-directory]', '退休规划/Roth相关')
    await page.fill('[data-note-content]', '# 初始内容\n\n第一段。')

    // Save — capture ID from POST response BEFORE any further assertion
    const newId = await clickSaveAndCaptureNoteId(page)
    createdNoteIds.push(newId)

    // Right panel switches to item-view
    await expect(page.locator('[data-panel="item-view"]')).toBeVisible()
    await expect(page.locator('[data-panel="item-view"]')).toContainText(initialTitle)
    await expect(page.locator('[data-panel="item-view"]')).toContainText('第一段')

    // Sidebar tree: expand 退休规划 → Roth相关 should appear → expand → note visible
    await expandDirectoryByName(page, '退休规划')
    await expandDirectoryByName(page, 'Roth相关')
    await expect(page.locator('[data-item]', { hasText: initialTitle })).toBeVisible()

    // Edit content
    await page.click('[data-edit-item-btn]')
    await expect(page.locator('[data-panel="item-edit"]')).toBeVisible()
    // The note edit panel renders a single textarea for content
    const contentTextarea = page.locator('[data-panel="item-edit"] textarea').first()
    await contentTextarea.fill(updatedContent)
    await page
      .locator('[data-panel="item-edit"]')
      .getByRole('button', { name: /保存/ })
      .click()
    await expect(page.locator('[data-panel="item-view"]')).toContainText('更新后')

    // Delete: accept confirm → note gone from sidebar, panel back to welcome
    page.once('dialog', (dialog) => dialog.accept())
    await page.click('[data-delete-item-btn]')
    await expect(page.locator('[data-item]', { hasText: initialTitle })).toHaveCount(0)
    createdNoteIds.length = 0 // server-deleted, not orphan
    await expect(page.locator('[data-panel="welcome"]')).toBeVisible()
  })

  test('note in a fixed template directory mixes with entries under same directory', async ({
    page,
  }) => {
    const noteTitle = uniqueTitle('mixed_note')
    await page.goto('/private')

    // Create a note in the 退休账户 directory (which is also a template directory)
    await page.click('[data-new-note-btn]')
    await page.fill('[data-note-title]', noteTitle)
    await page.fill('[data-note-directory]', '退休账户')
    await page.fill('[data-note-content]', '随手记录')
    const newId = await clickSaveAndCaptureNoteId(page)
    createdNoteIds.push(newId)

    // Sidebar: expand 退休账户; the note appears as a 📝 leaf
    await expandDirectoryByName(page, '退休账户')
    await expect(page.locator('[data-item]', { hasText: noteTitle })).toBeVisible()
  })
})
