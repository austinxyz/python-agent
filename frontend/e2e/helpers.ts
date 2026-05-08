/**
 * Shared E2E helpers for /private flow tests.
 *
 * Test data isolation convention:
 *   All test-created entry/note titles start with `__e2e_` followed by a
 *   timestamp + random suffix. Each spec file should register an afterEach
 *   hook that calls cleanupEntries(request, ids) so orphans never linger
 *   in the user's SQLite, even when an assertion throws mid-test.
 */
import type { Page, APIRequestContext } from '@playwright/test'

export const E2E_PREFIX = '__e2e_'

export function uniqueTitle(label: string): string {
  return `${E2E_PREFIX}${label}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

export async function expandDirectoryByName(page: Page, name: string): Promise<void> {
  const dirNode = page.locator('[data-directory-name]', { hasText: name }).first()
  await dirNode.click()
}

/**
 * Click the save button on the new-entry form and capture the new entry's ID
 * directly from the POST /api/private/entries response. Reading from a fresh
 * GET would race against any concurrent create and could delete the wrong row
 * in cleanup; reading from the actual response is unambiguous.
 */
export async function clickSaveAndCaptureEntryId(page: Page): Promise<string> {
  const responsePromise = page.waitForResponse(
    (resp) =>
      /\/api\/private\/entries(\?|$)/.test(resp.url()) &&
      resp.request().method() === 'POST' &&
      resp.status() === 201,
    { timeout: 15_000 }
  )
  await page.click('[data-save-entry-btn]')
  const response = await responsePromise
  const created = await response.json()
  if (!created?.id) {
    throw new Error(`POST /api/private/entries returned no id: ${JSON.stringify(created)}`)
  }
  return created.id
}

export async function cleanupEntries(request: APIRequestContext, ids: string[]): Promise<void> {
  for (const id of ids) {
    try {
      await request.delete(`/api/private/entries/${id}`)
    } catch {
      // best-effort cleanup; orphans surface as __e2e_* rows that are easy to spot
    }
  }
}

/**
 * Click the save button on the new-note form and capture the new note's ID
 * directly from the POST /api/private/notes response (same race-free pattern
 * used for entries).
 */
export async function clickSaveAndCaptureNoteId(page: Page): Promise<string> {
  const responsePromise = page.waitForResponse(
    (resp) =>
      /\/api\/private\/notes(\?|$)/.test(resp.url()) &&
      resp.request().method() === 'POST' &&
      resp.status() === 201,
    { timeout: 15_000 }
  )
  await page.click('[data-save-note-btn]')
  const response = await responsePromise
  const created = await response.json()
  if (!created?.id) {
    throw new Error(`POST /api/private/notes returned no id: ${JSON.stringify(created)}`)
  }
  return created.id
}

export async function cleanupNotes(request: APIRequestContext, ids: string[]): Promise<void> {
  for (const id of ids) {
    try {
      await request.delete(`/api/private/notes/${id}`)
    } catch {
      // best-effort cleanup
    }
  }
}
