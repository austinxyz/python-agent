import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ChatView from '../../src/views/ChatView.vue'
import { useChatStore } from '../../src/stores/chat.js'

const SESSIONS_FIXTURE = [
  { id: 's1', title: '退休讨论', model: 'haiku', created_at: '2026-05-08T10:00:00Z' },
  { id: 's2', title: '税务问题', model: 'sonnet', created_at: '2026-05-07T10:00:00Z' },
]

function makeWrapper() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const store = useChatStore(pinia)
  store._api = {
    get: vi.fn().mockImplementation((path) => {
      if (path === '/chat/sessions') return Promise.resolve({ data: SESSIONS_FIXTURE })
      if (path.startsWith('/chat/sessions/')) {
        return Promise.resolve({
          data: {
            id: 's1',
            title: '退休讨论',
            model: 'haiku',
            created_at: '2026-05-08T10:00:00Z',
            messages: [
              { role: 'user', content: '退休账户怎么选', sources: [] },
              { role: 'assistant', content: '建议先看 401k...', sources: [{ title: '401k', domain: '退休规划', file_id: 'f1' }] },
            ],
          },
        })
      }
      return Promise.resolve({ data: [] })
    }),
  }
  const wrapper = mount(ChatView, {
    global: {
      plugins: [pinia],
      stubs: {
        MessageSquare: true, BookOpen: true, Lock: true, Plus: true, Send: true,
        // Stub router-link to a plain anchor that renders default slot —
        // keeps `data-*` attrs and slot text reachable in tests without
        // installing a real router.
        RouterLink: { props: ['to'], template: '<a><slot /></a>' },
      },
    },
  })
  return { wrapper, store }
}

beforeEach(() => {
  vi.restoreAllMocks()
})

// ---------------------------------------------------------------------------
// 6.1a — empty state
// ---------------------------------------------------------------------------

describe('ChatView empty state', () => {
  it('mounts in empty state with prompt cards visible and no messages', async () => {
    const { wrapper } = makeWrapper()
    await flushPromises()
    expect(wrapper.find('[data-empty-state]').exists()).toBe(true)
    expect(wrapper.findAll('[data-assistant-msg]')).toHaveLength(0)
  })

  it('renders 6 prompt cards in the empty state', async () => {
    const { wrapper } = makeWrapper()
    await flushPromises()
    const cards = wrapper.findAll('[data-prompt-card]')
    expect(cards.length).toBe(6)
  })

  it('clicking a prompt card populates the input', async () => {
    const { wrapper } = makeWrapper()
    await flushPromises()
    const firstCard = wrapper.find('[data-prompt-card]')
    await firstCard.trigger('click')
    const input = wrapper.find('[data-chat-input]')
    expect(input.element.value.length).toBeGreaterThan(0)
  })
})

// ---------------------------------------------------------------------------
// 6.1b — sessions list
// ---------------------------------------------------------------------------

describe('ChatView sessions list', () => {
  it('renders session list after fetchSessions', async () => {
    const { wrapper } = makeWrapper()
    await flushPromises()
    const items = wrapper.findAll('[data-session-item]')
    expect(items.length).toBe(2)
    expect(items[0].text()).toContain('退休讨论')
  })

  it('clicking a session calls store.loadSession', async () => {
    const { wrapper, store } = makeWrapper()
    store.loadSession = vi.fn().mockResolvedValue(undefined)
    await flushPromises()
    await wrapper.findAll('[data-session-item]')[0].trigger('click')
    expect(store.loadSession).toHaveBeenCalledWith('s1')
  })

  it('clicking + 新建对话 calls store.newSession', async () => {
    const { wrapper, store } = makeWrapper()
    store.newSession = vi.fn()
    await flushPromises()
    await wrapper.find('[data-new-chat-btn]').trigger('click')
    expect(store.newSession).toHaveBeenCalled()
  })
})

// ---------------------------------------------------------------------------
// 6.1c — model + scope
// ---------------------------------------------------------------------------

describe('ChatView model and scope controls', () => {
  it('model selector defaults to haiku', async () => {
    const { wrapper } = makeWrapper()
    await flushPromises()
    const haikuOption = wrapper.find('[data-model-option="haiku"]')
    expect(haikuOption.classes().join(' ')).toContain('active')
  })

  it('selecting sonnet updates the active class', async () => {
    const { wrapper } = makeWrapper()
    await flushPromises()
    await wrapper.find('[data-model-option="sonnet"]').trigger('click')
    const sonnetOption = wrapper.find('[data-model-option="sonnet"]')
    expect(sonnetOption.classes().join(' ')).toContain('active')
  })

  it('default scope is knowledge active, private inactive', async () => {
    const { wrapper } = makeWrapper()
    await flushPromises()
    const knowledge = wrapper.find('[data-scope-knowledge]')
    const priv = wrapper.find('[data-scope-private]')
    expect(knowledge.classes().join(' ')).toContain('active')
    expect(priv.classes().join(' ')).not.toContain('active')
  })

  it('clicking 私有 activates both scopes', async () => {
    const { wrapper } = makeWrapper()
    await flushPromises()
    await wrapper.find('[data-scope-private]').trigger('click')
    expect(wrapper.find('[data-scope-knowledge]').classes().join(' ')).toContain('active')
    expect(wrapper.find('[data-scope-private]').classes().join(' ')).toContain('active')
  })

  it('cannot deactivate the last active scope', async () => {
    const { wrapper } = makeWrapper()
    await flushPromises()
    // Knowledge starts as the only active scope; clicking it must NOT deactivate
    await wrapper.find('[data-scope-knowledge]').trigger('click')
    expect(wrapper.find('[data-scope-knowledge]').classes().join(' ')).toContain('active')
  })
})

// ---------------------------------------------------------------------------
// 6.1d — submit
// ---------------------------------------------------------------------------

describe('ChatView submit', () => {
  it('submitting calls store.sendMessage with query, model, scope', async () => {
    const { wrapper, store } = makeWrapper()
    store.sendMessage = vi.fn().mockResolvedValue(undefined)
    await flushPromises()
    await wrapper.find('[data-chat-input]').setValue('退休账户问题')
    await wrapper.find('[data-chat-submit]').trigger('click')
    expect(store.sendMessage).toHaveBeenCalled()
    const [query, opts] = store.sendMessage.mock.calls[0]
    expect(query).toBe('退休账户问题')
    expect(opts.model).toBe('haiku')
    expect(opts.scope).toEqual(['knowledge'])
  })

  it('does not submit when input is empty', async () => {
    const { wrapper, store } = makeWrapper()
    store.sendMessage = vi.fn().mockResolvedValue(undefined)
    await flushPromises()
    await wrapper.find('[data-chat-submit]').trigger('click')
    expect(store.sendMessage).not.toHaveBeenCalled()
  })
})

// ---------------------------------------------------------------------------
// 6.1e — streaming + assistant + sources
// ---------------------------------------------------------------------------

describe('ChatView streaming display', () => {
  it('shows loading indicator while streaming=true', async () => {
    const { wrapper, store } = makeWrapper()
    await flushPromises()
    store.currentSession = {
      id: null, title: null, model: 'haiku',
      messages: [
        { role: 'user', content: 'q', sources: [] },
        { role: 'assistant', content: '部分回答…', sources: [] },
      ],
    }
    store.streaming = true
    await flushPromises()
    expect(wrapper.find('[data-streaming-indicator]').exists()).toBe(true)
  })

  it('renders assistant message content and source chips after done', async () => {
    const { wrapper, store } = makeWrapper()
    await flushPromises()
    store.currentSession = {
      id: 's1', title: 't', model: 'haiku',
      messages: [
        { role: 'user', content: 'q', sources: [] },
        { role: 'assistant', content: '完整回答', sources: [{ title: 'X', domain: 'D', file_id: 'f1' }] },
      ],
    }
    store.streaming = false
    await flushPromises()
    expect(wrapper.find('[data-assistant-msg]').text()).toContain('完整回答')
    const chips = wrapper.findAll('[data-source-chip]')
    expect(chips.length).toBe(1)
    expect(chips[0].text()).toContain('X')
  })
})

// ---------------------------------------------------------------------------
// 6.x — save-to-notes UI
// ---------------------------------------------------------------------------

describe('ChatView save-to-notes', () => {
  function withAssistant(store, sources = []) {
    store.currentSession = {
      id: 's1', title: '退休问题', model: 'haiku',
      messages: [
        { role: 'user', content: '退休账户怎么选？', sources: [] },
        { role: 'assistant', content: '建议先看 401k...', sources },
      ],
    }
    store.streaming = false
  }

  it('shows a 保存到笔记 button below each assistant message', async () => {
    const { wrapper, store } = makeWrapper()
    await flushPromises()
    withAssistant(store)
    await flushPromises()
    expect(wrapper.find('[data-save-note-btn]').exists()).toBe(true)
  })

  it('clicking 保存到笔记 expands an inline form pre-filled with title, directory, content', async () => {
    const { wrapper, store } = makeWrapper()
    await flushPromises()
    withAssistant(store, [{ title: '401k', domain: '退休规划', file_id: 'f1', kind: 'knowledge' }])
    await flushPromises()
    await wrapper.find('[data-save-note-btn]').trigger('click')
    const form = wrapper.find('[data-save-note-form]')
    expect(form.exists()).toBe(true)
    // Title pre-fills from the user question (truncated)
    const titleInput = wrapper.find('[data-save-note-title]')
    expect(titleInput.element.value).toContain('退休账户')
    // Directory defaults to 对话总结/<today>
    const dirInput = wrapper.find('[data-save-note-directory]')
    expect(dirInput.element.value).toMatch(/^对话总结\/\d{4}-\d{2}-\d{2}$/)
    // Content is markdown including the question + answer body
    const contentArea = wrapper.find('[data-save-note-content]')
    expect(contentArea.element.value).toContain('退休账户怎么选？')
    expect(contentArea.element.value).toContain('建议先看 401k')
    // Sources list rendered as markdown links to /wiki?file= for knowledge
    expect(contentArea.element.value).toContain('/wiki?file=f1')
    expect(contentArea.element.value).toContain('401k')
  })

  it('private-entry source links go to /private?entry= in the saved markdown', async () => {
    const { wrapper, store } = makeWrapper()
    await flushPromises()
    withAssistant(store, [{ title: '我的税务', domain: '税务', file_id: 'p1', kind: 'entry' }])
    await flushPromises()
    await wrapper.find('[data-save-note-btn]').trigger('click')
    const contentArea = wrapper.find('[data-save-note-content]')
    expect(contentArea.element.value).toContain('/private?entry=p1')
  })

  it('clicking 保存 calls store.saveMessageToNote with the form values', async () => {
    const { wrapper, store } = makeWrapper()
    store.saveMessageToNote = vi.fn().mockResolvedValue({ id: 'note-1', directory: 'X' })
    await flushPromises()
    withAssistant(store)
    await flushPromises()
    await wrapper.find('[data-save-note-btn]').trigger('click')
    await wrapper.find('[data-save-note-title]').setValue('我的总结')
    await wrapper.find('[data-save-note-directory]').setValue('对话总结/test')
    await wrapper.find('[data-save-note-content]').setValue('内容')
    await wrapper.find('[data-save-note-confirm]').trigger('click')
    await flushPromises()
    expect(store.saveMessageToNote).toHaveBeenCalled()
    const [idx, payload] = store.saveMessageToNote.mock.calls[0]
    expect(idx).toBe(1)  // assistant message is at index 1
    expect(payload).toEqual({
      title: '我的总结',
      directory: '对话总结/test',
      content: '内容',
    })
  })

  it('after successful save the form collapses and shows a confirmation', async () => {
    const { wrapper, store } = makeWrapper()
    store.saveMessageToNote = vi.fn().mockResolvedValue({ id: 'note-1', directory: '对话总结/2026-05-08' })
    await flushPromises()
    withAssistant(store)
    await flushPromises()
    await wrapper.find('[data-save-note-btn]').trigger('click')
    await wrapper.find('[data-save-note-confirm]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-save-note-form]').exists()).toBe(false)
    const confirm = wrapper.find('[data-save-note-confirmation]')
    expect(confirm.exists()).toBe(true)
    expect(confirm.text()).toContain('已保存')
    expect(confirm.text()).toContain('对话总结/2026-05-08')
  })

  it('clicking 取消 collapses the form without calling the store', async () => {
    const { wrapper, store } = makeWrapper()
    store.saveMessageToNote = vi.fn()
    await flushPromises()
    withAssistant(store)
    await flushPromises()
    await wrapper.find('[data-save-note-btn]').trigger('click')
    await wrapper.find('[data-save-note-cancel]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-save-note-form]').exists()).toBe(false)
    expect(store.saveMessageToNote).not.toHaveBeenCalled()
  })
})

// ---------------------------------------------------------------------------
// Mobile layout (Group 3 / mobile-friendly change)
// ---------------------------------------------------------------------------

describe('ChatView mobile shape', () => {
  it('desktop sessions sidebar is hidden at md- via Tailwind hidden md:flex', async () => {
    const { wrapper } = makeWrapper()
    await flushPromises()
    const sidebar = wrapper.find('[data-sessions-sidebar]')
    expect(sidebar.exists()).toBe(true)
    const cls = sidebar.classes().join(' ')
    expect(cls).toMatch(/hidden md:flex|md:flex/)
  })

  it('mobile header has ☰ sessions toggle and 🆕 new chat buttons (md:hidden)', async () => {
    const { wrapper } = makeWrapper()
    await flushPromises()
    const toggle = wrapper.find('[data-sessions-toggle]')
    const newChat = wrapper.find('[data-new-chat]')
    expect(toggle.exists()).toBe(true)
    expect(newChat.exists()).toBe(true)
    expect(toggle.classes().join(' ')).toMatch(/md:hidden/)
    expect(newChat.classes().join(' ')).toMatch(/md:hidden/)
  })

  it('☰ opens the sessions drawer; tapping a session closes the drawer', async () => {
    const { wrapper, store } = makeWrapper()
    await flushPromises()
    const toggle = wrapper.find('[data-sessions-toggle]')
    expect(wrapper.find('[data-sessions-drawer]').exists()).toBe(false)
    await toggle.trigger('click')
    const drawer = wrapper.find('[data-sessions-drawer]')
    expect(drawer.exists()).toBe(true)
    // Sessions render inside the drawer too
    const drawerSessions = drawer.findAll('[data-drawer-session]')
    expect(drawerSessions.length).toBe(SESSIONS_FIXTURE.length)
    // Click the first session — drawer should close + loadSession called
    store.loadSession = vi.fn().mockResolvedValue(undefined)
    await drawerSessions[0].trigger('click')
    await flushPromises()
    expect(store.loadSession).toHaveBeenCalledWith('s1')
    expect(wrapper.find('[data-sessions-drawer]').exists()).toBe(false)
  })

  it('🆕 starts a new session without opening the drawer', async () => {
    const { wrapper, store } = makeWrapper()
    await flushPromises()
    store.newSession = vi.fn()
    await wrapper.find('[data-new-chat]').trigger('click')
    expect(store.newSession).toHaveBeenCalled()
    expect(wrapper.find('[data-sessions-drawer]').exists()).toBe(false)
  })

  it('input wrapper has safe-area-inset-bottom and uses dvh viewport', async () => {
    const { wrapper } = makeWrapper()
    await flushPromises()
    const inputWrap = wrapper.find('[data-chat-input-wrap]')
    expect(inputWrap.exists()).toBe(true)
    const cls = inputWrap.classes().join(' ')
    // safe-area-inset-bottom either via env() alone or wrapped in calc with extra clearance
    expect(cls).toMatch(/safe-area-inset-bottom|pb-safe/)
    // The root container uses 100dvh (or h-dvh) so iOS keyboard pop-ups don't overflow.
    const root = wrapper.find('[data-chat-root]')
    expect(root.exists()).toBe(true)
    const rootCls = root.classes().join(' ')
    expect(rootCls).toMatch(/h-\[100dvh\]|h-dvh|min-h-\[100dvh\]/)
  })
})

describe('ChatView auto-scroll behavior', () => {
  it('autoscrolls to bottom when user is already near bottom', async () => {
    const { wrapper, store } = makeWrapper()
    store.fetchSessions = vi.fn().mockResolvedValue(undefined)
    // Seed a session with a long message history.
    store.currentSession = {
      id: 's1',
      title: 't',
      model: 'haiku',
      created_at: '2026-05-08T10:00:00Z',
      messages: Array.from({ length: 30 }, (_, i) => ({
        role: i % 2 === 0 ? 'user' : 'assistant',
        content: 'msg ' + i,
        sources: [],
      })),
    }
    await flushPromises()
    const messagesEl = wrapper.find('[data-messages]').element
    // happy-dom doesn't compute layout, so we patch scrollHeight/scrollTop
    Object.defineProperty(messagesEl, 'scrollHeight', { value: 5000, configurable: true })
    Object.defineProperty(messagesEl, 'clientHeight', { value: 800, configurable: true })
    messagesEl.scrollTop = 4180 // distance from bottom = 5000 - 800 - 4180 = 20px → near bottom
    // Push a new token by appending content; component watches messages length / streaming
    store.currentSession.messages = [...store.currentSession.messages, { role: 'assistant', content: 'new', sources: [] }]
    await flushPromises()
    // After autoscroll, scrollTop should equal scrollHeight - clientHeight (= 4200)
    expect(messagesEl.scrollTop).toBe(4200)
  })

  it('autoscrolls when streaming tokens mutate the last message content (length unchanged)', async () => {
    // Regression for the bug where the watcher only fired on length change.
    // During streaming the chat store appends tokens to messages[last].content
    // in place; the array length stays constant. The autoscroll must still
    // follow that growing content.
    const { wrapper, store } = makeWrapper()
    store.fetchSessions = vi.fn().mockResolvedValue(undefined)
    store.currentSession = {
      id: 's1',
      title: 't',
      model: 'haiku',
      created_at: '2026-05-08T10:00:00Z',
      messages: [
        { role: 'user', content: 'hi', sources: [] },
        { role: 'assistant', content: '', sources: [] },
      ],
    }
    await flushPromises()
    const messagesEl = wrapper.find('[data-messages]').element
    Object.defineProperty(messagesEl, 'scrollHeight', { value: 5000, configurable: true, writable: true })
    Object.defineProperty(messagesEl, 'clientHeight', { value: 800, configurable: true, writable: true })
    messagesEl.scrollTop = 4180 // distance from bottom = 20 → near bottom
    // Mutate the last message's content (token stream simulation) — length stays at 2.
    store.currentSession = {
      ...store.currentSession,
      messages: [
        store.currentSession.messages[0],
        { ...store.currentSession.messages[1], content: 'partial answer…' },
      ],
    }
    await flushPromises()
    expect(messagesEl.scrollTop).toBe(4200)
  })

  it('does NOT autoscroll when user has scrolled up significantly', async () => {
    const { wrapper, store } = makeWrapper()
    store.fetchSessions = vi.fn().mockResolvedValue(undefined)
    store.currentSession = {
      id: 's1',
      title: 't',
      model: 'haiku',
      created_at: '2026-05-08T10:00:00Z',
      messages: Array.from({ length: 30 }, (_, i) => ({
        role: i % 2 === 0 ? 'user' : 'assistant',
        content: 'msg ' + i,
        sources: [],
      })),
    }
    await flushPromises()
    const messagesEl = wrapper.find('[data-messages]').element
    Object.defineProperty(messagesEl, 'scrollHeight', { value: 5000, configurable: true })
    Object.defineProperty(messagesEl, 'clientHeight', { value: 800, configurable: true })
    messagesEl.scrollTop = 1000 // distance from bottom = 5000 - 800 - 1000 = 3200px → far from bottom
    store.currentSession.messages = [...store.currentSession.messages, { role: 'assistant', content: 'new', sources: [] }]
    await flushPromises()
    // scrollTop should NOT have moved.
    expect(messagesEl.scrollTop).toBe(1000)
  })
})
