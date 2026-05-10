/**
 * Tests for `safeRedirect()` — the open-redirect guard added after the
 * 2026-05-10 multi-user-auth-core code review.
 */
import { describe, it, expect } from 'vitest'
import { safeRedirect } from '../../src/utils/safe-redirect.js'

describe('safeRedirect', () => {
  it('passes a clean relative path', () => {
    expect(safeRedirect('/wiki')).toBe('/wiki')
    expect(safeRedirect('/private?entry=abc')).toBe('/private?entry=abc')
    expect(safeRedirect('/me#section')).toBe('/me#section')
  })

  it('falls back to /chat on missing / non-string input', () => {
    expect(safeRedirect(undefined)).toBe('/chat')
    expect(safeRedirect(null)).toBe('/chat')
    expect(safeRedirect('')).toBe('/chat')
    expect(safeRedirect(['/wiki'])).toBe('/chat')
    expect(safeRedirect({ path: '/wiki' })).toBe('/chat')
  })

  it('rejects absolute https / http URLs', () => {
    expect(safeRedirect('https://evil.example')).toBe('/chat')
    expect(safeRedirect('http://evil.example/')).toBe('/chat')
    expect(safeRedirect('https://evil.example/wiki')).toBe('/chat')
  })

  it('rejects protocol-relative URLs', () => {
    expect(safeRedirect('//evil.example/wiki')).toBe('/chat')
    expect(safeRedirect('//evil.example')).toBe('/chat')
  })

  it('rejects javascript: and data: schemes', () => {
    expect(safeRedirect('javascript:alert(1)')).toBe('/chat')
    expect(safeRedirect('JAVASCRIPT:alert(1)')).toBe('/chat')
    expect(safeRedirect('data:text/html,<script>alert(1)</script>')).toBe('/chat')
    expect(safeRedirect('vbscript:msgbox(1)')).toBe('/chat')
  })

  it('rejects relative paths that do not start with /', () => {
    expect(safeRedirect('wiki')).toBe('/chat')
    expect(safeRedirect('../etc/passwd')).toBe('/chat')
    expect(safeRedirect('?redirect=/wiki')).toBe('/chat')
  })

  it('preserves query and hash on a relative path', () => {
    expect(safeRedirect('/private?entry=abc&filter=tax')).toBe('/private?entry=abc&filter=tax')
    expect(safeRedirect('/wiki#heading-1')).toBe('/wiki#heading-1')
  })
})
