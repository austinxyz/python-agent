import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useFileContent } from '@/composables/useFileContent.js'

describe('useFileContent', () => {
  beforeEach(() => {
    global.fetch = vi.fn()
  })

  it('load() for .md file fetches content and renders HTML with h tags', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      text: async () => '# Hello\n\nWorld',
    })

    const { loading, error, renderedContent, load } = useFileContent()
    await load('file-001', 'report.md')

    expect(loading.value).toBe(false)
    expect(error.value).toBe('')
    expect(renderedContent.value).toMatch(/<h1/)
  })

  it('load() for .txt file renders as markdown (paragraphs, not <pre>)', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      text: async () => '# Hello\n\nplain text content',
    })

    const { loading, error, renderedContent, load } = useFileContent()
    await load('file-002', 'report.txt')

    expect(loading.value).toBe(false)
    expect(error.value).toBe('')
    expect(renderedContent.value).toMatch(/<h1/)
    expect(renderedContent.value).toContain('plain text content')
  })

  it('load() fetches the correct URL', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      text: async () => 'content',
    })

    const { load } = useFileContent()
    await load('file-123', 'doc.txt')

    expect(global.fetch).toHaveBeenCalledWith('/api/files/file-123/content')
  })

  it('load() sets error on HTTP failure', async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      status: 404,
    })

    const { error, load } = useFileContent()
    await load('bad-id', 'file.md')

    expect(error.value).not.toBe('')
  })

  it('loading is true during fetch and false after', async () => {
    let resolveText
    const textPromise = new Promise(res => { resolveText = res })
    global.fetch.mockResolvedValue({ ok: true, text: () => textPromise })

    const { loading, load } = useFileContent()
    const promise = load('file-001', 'doc.md')
    expect(loading.value).toBe(true)
    resolveText('# Hello')
    await promise
    expect(loading.value).toBe(false)
  })
})
