import { describe, it, expect } from 'vitest'
import { readFileSync, existsSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const FRONTEND = join(__dirname, '..')
const MANIFEST = join(FRONTEND, 'public', 'manifest.json')
const INDEX_HTML = join(FRONTEND, 'index.html')

describe('PWA manifest', () => {
  it('manifest.json exists at frontend/public/', () => {
    expect(existsSync(MANIFEST)).toBe(true)
  })

  it('manifest declares the required fields', () => {
    const m = JSON.parse(readFileSync(MANIFEST, 'utf-8'))
    expect(m.name).toBeTruthy()
    expect(m.short_name).toBeTruthy()
    expect(m.start_url).toBe('/')
    expect(m.display).toBe('standalone')
    expect(m.theme_color).toMatch(/^#[0-9a-fA-F]{3,8}$/)
    expect(m.background_color).toMatch(/^#[0-9a-fA-F]{3,8}$/)
  })

  it('manifest has at least 192/512/maskable icons', () => {
    const m = JSON.parse(readFileSync(MANIFEST, 'utf-8'))
    expect(Array.isArray(m.icons)).toBe(true)
    const sizes = m.icons.map((i) => i.sizes)
    expect(sizes).toContain('192x192')
    expect(sizes).toContain('512x512')
    const maskable = m.icons.filter((i) => (i.purpose || '').includes('maskable'))
    expect(maskable.length).toBeGreaterThanOrEqual(1)
  })

  it('icon files exist at the paths the manifest references', () => {
    const m = JSON.parse(readFileSync(MANIFEST, 'utf-8'))
    for (const icon of m.icons) {
      const p = join(FRONTEND, 'public', icon.src.replace(/^\//, ''))
      expect(existsSync(p), `missing icon file: ${p}`).toBe(true)
    }
  })
})

describe('PWA — index.html links', () => {
  it('index.html links the manifest, apple-touch-icon, and theme-color', () => {
    const html = readFileSync(INDEX_HTML, 'utf-8')
    expect(html).toMatch(/<link\s+rel="manifest"\s+href="\/manifest\.json"/)
    expect(html).toMatch(/<link\s+rel="apple-touch-icon"\s+href="\/icons\//)
    expect(html).toMatch(/<meta\s+name="theme-color"\s+content="#[0-9a-fA-F]{3,8}"/)
  })
})
