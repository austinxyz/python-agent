import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useChatStore } from '../../src/stores/chat.js'

beforeEach(() => {
  setActivePinia(createPinia())
})

// ---------------------------------------------------------------------------
// fetchSessions
// ---------------------------------------------------------------------------

describe('fetchSessions', () => {
  it('calls GET /chat/sessions and populates sessions', async () => {
    const store = useChatStore()
    const sessions = [
      { id: 's1', title: '退休问题', model: 'haiku', created_at: '2026-05-01T10:00:00Z' },
    ]
    store._api = { get: vi.fn().mockResolvedValue({ data: sessions }) }

    await store.fetchSessions()

    expect(store._api.get).toHaveBeenCalledWith('/chat/sessions')
    expect(store.sessions).toEqual(sessions)
  })

  it('records error on failure', async () => {
    const store = useChatStore()
    store._api = { get: vi.fn().mockRejectedValue(new Error('boom')) }

    await store.fetchSessions()

    expect(store.sessions).toEqual([])
    expect(store.error).toBe('boom')
  })
})

// ---------------------------------------------------------------------------
// loadSession
// ---------------------------------------------------------------------------

describe('loadSession', () => {
  it('calls GET /chat/sessions/{id} and populates currentSession', async () => {
    const store = useChatStore()
    const sessionDetail = {
      id: 's1', title: 't', model: 'haiku', created_at: 'x',
      messages: [
        { role: 'user', content: 'Q1', sources: [] },
        { role: 'assistant', content: 'A1', sources: [{ title: 'X', domain: 'D', file_id: 'f' }] },
      ],
    }
    store._api = { get: vi.fn().mockResolvedValue({ data: sessionDetail }) }

    await store.loadSession('s1')

    expect(store._api.get).toHaveBeenCalledWith('/chat/sessions/s1')
    expect(store.currentSession).toEqual(sessionDetail)
  })
})

// ---------------------------------------------------------------------------
// newSession
// ---------------------------------------------------------------------------

describe('newSession', () => {
  it('resets currentSession to null', () => {
    const store = useChatStore()
    store.currentSession = { id: 's1', title: 't', messages: [{ role: 'user', content: 'x' }] }
    store.newSession()
    expect(store.currentSession).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// sendMessage — fetch ReadableStream SSE
// ---------------------------------------------------------------------------

function makeReader(chunks) {
  let i = 0
  const encoder = new TextEncoder()
  return {
    read: vi.fn().mockImplementation(() => {
      if (i >= chunks.length) return Promise.resolve({ done: true, value: undefined })
      const out = encoder.encode(chunks[i++])
      return Promise.resolve({ done: false, value: out })
    }),
    releaseLock: vi.fn(),
  }
}

function mockFetchSSE(chunks) {
  const reader = makeReader(chunks)
  return vi.fn().mockResolvedValue({
    ok: true,
    body: { getReader: () => reader },
  })
}

describe('sendMessage', () => {
  it('appends user message immediately and streams tokens into assistant message', async () => {
    const store = useChatStore()
    store.currentSession = { id: null, title: null, model: 'haiku', messages: [] }

    // Two token events then a done event with one source
    global.fetch = mockFetchSSE([
      'data: {"type":"token","content":"Hello"}\n\n',
      'data: {"type":"token","content":" world"}\n\ndata: {"type":"done","sources":[{"title":"X","domain":"D","file_id":"f1"}]}\n\n',
    ])

    expect(store.streaming).toBe(false)
    const promise = store.sendMessage('hi', { model: 'haiku', scope: ['knowledge'] })
    // Immediately after kicking off, the user message is appended
    await Promise.resolve()
    expect(store.currentSession.messages[0]).toEqual(expect.objectContaining({ role: 'user', content: 'hi' }))
    // streaming flips on
    expect(store.streaming).toBe(true)

    await promise

    // After done, streaming is off
    expect(store.streaming).toBe(false)
    // Assistant message has the streamed tokens concatenated and sources attached
    const assistant = store.currentSession.messages[1]
    expect(assistant.role).toBe('assistant')
    expect(assistant.content).toBe('Hello world')
    expect(assistant.sources).toEqual([{ title: 'X', domain: 'D', file_id: 'f1' }])
  })

  it('passes session_id when continuing an existing session', async () => {
    const store = useChatStore()
    store.currentSession = {
      id: 's1', title: 't', model: 'haiku',
      messages: [
        { role: 'user', content: 'prior', sources: [] },
      ],
    }

    let captured
    global.fetch = vi.fn().mockImplementation((url, opts) => {
      captured = { url, opts }
      const reader = makeReader(['data: {"type":"done","sources":[]}\n\n'])
      return Promise.resolve({ ok: true, body: { getReader: () => reader } })
    })

    await store.sendMessage('next', { model: 'haiku', scope: ['knowledge'] })

    expect(captured.url).toContain('/api/chat')
    const body = JSON.parse(captured.opts.body)
    expect(body.session_id).toBe('s1')
    expect(body.query).toBe('next')
    expect(body.model).toBe('haiku')
    expect(body.scope).toEqual(['knowledge'])
  })

  it('records error on fetch failure', async () => {
    const store = useChatStore()
    store.currentSession = { id: null, title: null, model: 'haiku', messages: [] }
    global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 500, body: null })

    await store.sendMessage('hi', { model: 'haiku', scope: ['knowledge'] })

    expect(store.streaming).toBe(false)
    expect(store.error).toMatch(/500|chat/i)
  })

  it('hydrates currentSession.id from the done event session_id', async () => {
    const store = useChatStore()
    store.currentSession = { id: null, title: null, model: 'haiku', messages: [] }
    global.fetch = mockFetchSSE([
      'data: {"type":"token","content":"ok"}\n\ndata: {"type":"done","sources":[],"session_id":"new-session-001"}\n\n',
    ])
    await store.sendMessage('hi', { model: 'haiku', scope: ['knowledge'] })
    expect(store.currentSession.id).toBe('new-session-001')
  })
})

// ---------------------------------------------------------------------------
// saveMessageToNote — saves an assistant answer as a private note
// ---------------------------------------------------------------------------

describe('saveMessageToNote', () => {
  it('POSTs /private/notes with title, directory, content, chat_ref', async () => {
    const store = useChatStore()
    store.currentSession = {
      id: 'sess-1', title: 't', model: 'haiku',
      messages: [
        { role: 'user', content: '退休问题', sources: [] },
        { role: 'assistant', content: '建议看 401k...', sources: [{ title: '401k', domain: '退休规划', file_id: 'f1', kind: 'knowledge' }] },
      ],
    }
    const created = { id: 'note-1', title: 'x', directory: '对话总结/2026-05-08', content: 'y' }
    store._api = { post: vi.fn().mockResolvedValue({ data: created }) }

    const out = await store.saveMessageToNote(1, {
      title: '退休账户回答',
      directory: '对话总结/2026-05-08',
      content: '# 退休账户\n\n答案内容',
    })

    expect(store._api.post).toHaveBeenCalledWith('/private/notes', expect.objectContaining({
      title: '退休账户回答',
      directory: '对话总结/2026-05-08',
      content: '# 退休账户\n\n答案内容',
      chat_ref: 'sess-1',
    }))
    expect(out).toEqual(created)
  })

  it('records error on save failure and re-throws', async () => {
    const store = useChatStore()
    store.currentSession = {
      id: 'sess-1', messages: [{ role: 'user', content: 'q' }, { role: 'assistant', content: 'a', sources: [] }],
    }
    store._api = { post: vi.fn().mockRejectedValue(new Error('boom')) }
    await expect(store.saveMessageToNote(1, { title: 't', directory: 'd', content: 'c' })).rejects.toThrow('boom')
    expect(store.error).toBe('boom')
  })
})
