/**
 * Tests for the directory-driven two-column PrivateView (Section 7 revision).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrivateView from '../../src/views/PrivateView.vue'
import { usePrivateStore } from '../../src/stores/private.js'

// PrivateView now uses useRoute() to read ?entry=<id> for chat-source
// deep-linking. Tests don't need real navigation, so stub the module.
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
}))

const TEMPLATES = [
  {
    type: 'tax',
    label: '税务情况',
    default_directory: '税务',
    fields: [
      { key: 'filing_status', label: '申报状态', type: 'text' },
      { key: 'agi', label: 'AGI', type: 'number' },
    ],
  },
  {
    type: 'retirement',
    label: '退休账户',
    default_directory: '退休账户',
    fields: [
      { key: 'k401_balance', label: '401K', type: 'number' },
      { key: 'roth_ira_balance', label: 'Roth IRA', type: 'number' },
    ],
  },
  {
    type: 'portfolio',
    label: '投资持仓',
    default_directory: '投资持仓',
    fields: [{ key: 'brokerage', label: '券商', type: 'text' }],
  },
  {
    type: 'personal',
    label: '个人基本情况',
    default_directory: '个人基本情况',
    fields: [{ key: 'income', label: '收入', type: 'number' }],
  },
  {
    type: 'real_estate',
    label: '房产资产',
    default_directory: '房产资产',
    fields: [{ key: 'address', label: '地址', type: 'text' }],
  },
  {
    type: 'freeform',
    label: '自由格式',
    default_directory: '自由格式',
    fields: [{ key: 'content', label: '内容', type: 'textarea' }],
  },
]

const TAX_ENTRY = {
  id: 'e1',
  template_type: 'tax',
  title: '我的税务',
  directory: '税务',
  content_json: { filing_status: 'Single', agi: 100000 },
  created_at: '2026-05-01T10:00:00Z',
  updated_at: '2026-05-01T10:00:00Z',
}

const RETIRE_NOTE = {
  id: 'n1',
  title: '退休总览',
  directory: '退休规划',
  content: '# 概览\n\n内容…',
  chat_ref: null,
  created_at: '2026-05-02T10:00:00Z',
  updated_at: '2026-05-02T10:00:00Z',
}

function makeWrapper({
  templates = TEMPLATES,
  entries = [TAX_ENTRY],
  notes = [RETIRE_NOTE],
} = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const store = usePrivateStore(pinia)
  store._api = {
    get: vi.fn().mockImplementation((path) => {
      if (path === '/private/templates') return Promise.resolve({ data: templates })
      if (path === '/private/entries') return Promise.resolve({ data: entries })
      if (path === '/private/notes') {
        // Build a minimal flat tree for the legacy notesTree state (unused in new view).
        return Promise.resolve({ data: { notes, tree: {} } })
      }
      return Promise.resolve({ data: {} })
    }),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  }
  const wrapper = mount(PrivateView, {
    global: { plugins: [pinia], stubs: { Lock: true } },
  })
  return { wrapper, store }
}

beforeEach(() => {
  vi.spyOn(window, 'confirm').mockReturnValue(true)
})

// ---------------------------------------------------------------------------
// 7.4a — header + mount fetches
// ---------------------------------------------------------------------------

describe('PrivateView mount', () => {
  it('renders the gradient page header with 私有数据 title', async () => {
    const { wrapper } = makeWrapper()
    await flushPromises()
    expect(wrapper.text()).toContain('私有数据')
  })

  it('calls fetchEntries / fetchNotes / fetchTemplates on mount', async () => {
    const { store } = makeWrapper()
    await flushPromises()
    expect(store._api.get).toHaveBeenCalledWith('/private/templates')
    expect(store._api.get).toHaveBeenCalledWith('/private/entries')
    expect(store._api.get).toHaveBeenCalledWith('/private/notes')
  })
})

// ---------------------------------------------------------------------------
// 7.4b — sidebar shows the 6 fixed template directories
// ---------------------------------------------------------------------------

describe('sidebar tree', () => {
  it('shows the 6 fixed template directories on mount even when DB is empty', async () => {
    const { wrapper } = makeWrapper({ entries: [], notes: [] })
    await flushPromises()
    const text = wrapper.find('[data-sidebar]').text()
    for (const dir of ['税务', '退休账户', '投资持仓', '个人基本情况', '房产资产', '自由格式']) {
      expect(text).toContain(dir)
    }
  })

  it('shows entry items inside their directory after expanding', async () => {
    const { wrapper } = makeWrapper()
    await flushPromises()
    // Find the 税务 directory node and click to expand
    const taxFolder = wrapper.findAll('[data-directory-name]').find(el => el.text().trim() === '税务')
    await taxFolder.trigger('click')
    expect(wrapper.text()).toContain('我的税务')
  })

  it('shows note items under their directory', async () => {
    const { wrapper } = makeWrapper()
    await flushPromises()
    const folder = wrapper.findAll('[data-directory-name]').find(el => el.text().trim() === '退休规划')
    expect(folder).toBeTruthy()
    await folder.trigger('click')
    expect(wrapper.text()).toContain('退休总览')
  })
})

// ---------------------------------------------------------------------------
// 7.4c — clicking item shows item-view in right panel
// ---------------------------------------------------------------------------

describe('item-view panel', () => {
  it('clicking an entry shows its template fields in the right panel', async () => {
    const { wrapper } = makeWrapper()
    await flushPromises()
    const taxFolder = wrapper.findAll('[data-directory-name]').find(el => el.text().trim() === '税务')
    await taxFolder.trigger('click')
    const entryItem = wrapper.findAll('[data-item]').find(el => el.text().includes('我的税务'))
    await entryItem.trigger('click')
    const panel = wrapper.find('[data-panel="item-view"]')
    expect(panel.exists()).toBe(true)
    expect(panel.text()).toContain('申报状态')
    expect(panel.text()).toContain('Single')
    expect(panel.text()).toContain('AGI')
  })

  it('clicking a note shows its content in the right panel', async () => {
    const { wrapper } = makeWrapper()
    await flushPromises()
    const folder = wrapper.findAll('[data-directory-name]').find(el => el.text().trim() === '退休规划')
    await folder.trigger('click')
    const noteItem = wrapper.findAll('[data-item]').find(el => el.text().includes('退休总览'))
    await noteItem.trigger('click')
    const panel = wrapper.find('[data-panel="item-view"]')
    expect(panel.exists()).toBe(true)
    expect(panel.text()).toContain('概览')
  })
})

// ---------------------------------------------------------------------------
// 7.4d — new-entry flow
// ---------------------------------------------------------------------------

describe('new-entry flow', () => {
  it('clicking + 新建条目 switches to new-entry panel', async () => {
    const { wrapper } = makeWrapper()
    await flushPromises()
    await wrapper.find('[data-new-entry-btn]').trigger('click')
    expect(wrapper.find('[data-panel="new-entry"]').exists()).toBe(true)
  })

  it('selecting tax template pre-fills directory to 税务', async () => {
    const { wrapper } = makeWrapper()
    await flushPromises()
    await wrapper.find('[data-new-entry-btn]').trigger('click')
    await wrapper.find('[data-template-option="tax"]').trigger('click')
    const dirInput = wrapper.find('[data-entry-directory]')
    expect(dirInput.element.value).toBe('税务')
  })

  it('submitting the new-entry form calls store.createEntry with directory', async () => {
    const { wrapper, store } = makeWrapper()
    store.createEntry = vi.fn().mockResolvedValue({ id: 'new-id' })
    await flushPromises()
    await wrapper.find('[data-new-entry-btn]').trigger('click')
    await wrapper.find('[data-template-option="retirement"]').trigger('click')
    await wrapper.find('[data-entry-title]').setValue('我的 401k')
    await wrapper.find('[data-save-entry-btn]').trigger('click')
    await flushPromises()
    expect(store.createEntry).toHaveBeenCalled()
    const args = store.createEntry.mock.calls[0][0]
    expect(args.template_type).toBe('retirement')
    expect(args.title).toBe('我的 401k')
    expect(args.directory).toBe('退休账户')
  })
})

// ---------------------------------------------------------------------------
// 7.4e — new-note flow
// ---------------------------------------------------------------------------

describe('new-note flow', () => {
  it('clicking + 新建笔记 switches to new-note panel', async () => {
    const { wrapper } = makeWrapper()
    await flushPromises()
    await wrapper.find('[data-new-note-btn]').trigger('click')
    expect(wrapper.find('[data-panel="new-note"]').exists()).toBe(true)
  })

  it('submitting the new-note form calls store.createNote with directory', async () => {
    const { wrapper, store } = makeWrapper()
    store.createNote = vi.fn().mockResolvedValue({ id: 'note-1' })
    await flushPromises()
    await wrapper.find('[data-new-note-btn]').trigger('click')
    await wrapper.find('[data-note-title]').setValue('Roth 心得')
    await wrapper.find('[data-note-directory]').setValue('退休规划/Roth相关')
    await wrapper.find('[data-note-content]').setValue('# 心得\n\n')
    await wrapper.find('[data-save-note-btn]').trigger('click')
    await flushPromises()
    expect(store.createNote).toHaveBeenCalledWith({
      title: 'Roth 心得',
      directory: '退休规划/Roth相关',
      content: '# 心得\n\n',
    })
  })
})

// ---------------------------------------------------------------------------
// 7.4f — edit and delete from item-view
// ---------------------------------------------------------------------------

describe('edit and delete from item-view', () => {
  it('clicking 编辑 on an entry switches to item-edit', async () => {
    const { wrapper } = makeWrapper()
    await flushPromises()
    const taxFolder = wrapper.findAll('[data-directory-name]').find(el => el.text().trim() === '税务')
    await taxFolder.trigger('click')
    const entryItem = wrapper.findAll('[data-item]').find(el => el.text().includes('我的税务'))
    await entryItem.trigger('click')
    await wrapper.find('[data-edit-item-btn]').trigger('click')
    expect(wrapper.find('[data-panel="item-edit"]').exists()).toBe(true)
  })

  it('clicking 删除 on an entry calls store.deleteEntry after confirm', async () => {
    const { wrapper, store } = makeWrapper()
    store.deleteEntry = vi.fn().mockResolvedValue(undefined)
    await flushPromises()
    const taxFolder = wrapper.findAll('[data-directory-name]').find(el => el.text().trim() === '税务')
    await taxFolder.trigger('click')
    const entryItem = wrapper.findAll('[data-item]').find(el => el.text().includes('我的税务'))
    await entryItem.trigger('click')
    await wrapper.find('[data-delete-item-btn]').trigger('click')
    await flushPromises()
    expect(window.confirm).toHaveBeenCalled()
    expect(store.deleteEntry).toHaveBeenCalledWith('e1')
  })
})
