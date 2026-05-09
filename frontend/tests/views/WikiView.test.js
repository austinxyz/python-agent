import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import WikiView from '../../src/views/WikiView.vue'
import { useWikiStore } from '../../src/stores/wiki.js'

// Stub vue-router for WikiView — it now uses useRoute() to read ?file=<id>
// for source-chip deep-linking. Tests don't need real navigation.
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
}))

const MOCK_TREE = {
  '退休规划': [
    { file_id: 'f1', title: 'Roth IRA指南', orig_name: 'roth.pdf', domain: '退休规划', filename: 'roth.pdf' },
    { file_id: 'f2', title: '401k规划', orig_name: '401k.pdf', domain: '退休规划', filename: '401k.pdf' },
  ],
  '税务策略': [
    { file_id: 'f3', title: null, orig_name: 'tax-notes.txt', domain: '税务策略', filename: 'tax-notes.txt' },
  ],
}

function makeWrapper(tree = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const store = useWikiStore(pinia)
  store._api = { get: vi.fn().mockResolvedValue({ data: tree }) }
  const wrapper = mount(WikiView, { global: { plugins: [pinia] } })
  return { wrapper, store }
}

// ---------------------------------------------------------------------------
// 4.1a — mounts in welcome state
// ---------------------------------------------------------------------------

describe('welcome state', () => {
  it('mounts with rightPanelState=welcome — welcome panel is visible', () => {
    const { wrapper } = makeWrapper()
    expect(wrapper.find('[data-panel="welcome"]').exists()).toBe(true)
    expect(wrapper.find('[data-panel="content"]').exists()).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// 4.1b — domain groups visible after fetchTree; empty domains hidden
// ---------------------------------------------------------------------------

describe('domain groups after fetchTree', () => {
  it('renders domain names present in filteredTree', async () => {
    const { wrapper } = makeWrapper(MOCK_TREE)
    await flushPromises()
    expect(wrapper.text()).toContain('退休规划')
    expect(wrapper.text()).toContain('税务策略')
  })

  it('does not render domains absent from filteredTree', async () => {
    const { wrapper } = makeWrapper({ '退休规划': [MOCK_TREE['退休规划'][0]] })
    await flushPromises()
    expect(wrapper.text()).not.toContain('税务策略')
  })
})

// ---------------------------------------------------------------------------
// 4.1c — chevron toggles domain expand/collapse
// ---------------------------------------------------------------------------

describe('chevron toggle', () => {
  it('file items are hidden before chevron click', async () => {
    const { wrapper } = makeWrapper(MOCK_TREE)
    await flushPromises()
    expect(wrapper.find('[data-sidebar-file]').exists()).toBe(false)
  })

  it('clicking chevron reveals file items for that domain', async () => {
    const { wrapper } = makeWrapper(MOCK_TREE)
    await flushPromises()
    await wrapper.find('[data-domain-chevron]').trigger('click')
    expect(wrapper.find('[data-sidebar-file]').exists()).toBe(true)
  })

  it('clicking chevron again collapses the domain', async () => {
    const { wrapper } = makeWrapper(MOCK_TREE)
    await flushPromises()
    const chevron = wrapper.find('[data-domain-chevron]')
    await chevron.trigger('click')
    await chevron.trigger('click')
    expect(wrapper.find('[data-sidebar-file]').exists()).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// 4.1d — search input bound to store.searchQuery
// ---------------------------------------------------------------------------

describe('search input', () => {
  it('search input is present', async () => {
    const { wrapper } = makeWrapper(MOCK_TREE)
    await flushPromises()
    expect(wrapper.find('[data-search-input]').exists()).toBe(true)
  })

  it('typing into search input updates store.searchQuery', async () => {
    const { wrapper, store } = makeWrapper(MOCK_TREE)
    await flushPromises()
    await wrapper.find('[data-search-input]').setValue('roth')
    expect(store.searchQuery).toBe('roth')
  })

  it('searching filters domains — domains with no matches are hidden', async () => {
    const { wrapper } = makeWrapper(MOCK_TREE)
    await flushPromises()
    await wrapper.find('[data-search-input]').setValue('tax')
    // 退休规划 has no tax match, only 税务策略 does
    expect(wrapper.text()).toContain('税务策略')
    expect(wrapper.text()).not.toContain('退休规划')
  })

  it('clearing search restores all domains', async () => {
    const { wrapper } = makeWrapper(MOCK_TREE)
    await flushPromises()
    await wrapper.find('[data-search-input]').setValue('tax')
    await wrapper.find('[data-search-input]').setValue('')
    expect(wrapper.text()).toContain('退休规划')
    expect(wrapper.text()).toContain('税务策略')
  })
})

// ---------------------------------------------------------------------------
// 4.1f/g — clicking file title calls selectFile and transitions to content
// ---------------------------------------------------------------------------

describe('file title click', () => {
  async function expandAndClickFile(wrapper) {
    await flushPromises()
    await wrapper.find('[data-domain-chevron]').trigger('click')
    await wrapper.find('[data-sidebar-file]').trigger('click')
    await wrapper.vm.$nextTick()
  }

  it('clicking file title transitions rightPanelState to content', async () => {
    const { wrapper } = makeWrapper(MOCK_TREE)
    await expandAndClickFile(wrapper)
    expect(wrapper.find('[data-panel="content"]').exists()).toBe(true)
    expect(wrapper.find('[data-panel="welcome"]').exists()).toBe(false)
  })

  it('clicking file title calls store.selectFile with the file_id', async () => {
    const { wrapper, store } = makeWrapper(MOCK_TREE)
    store.selectFile = vi.fn()
    await expandAndClickFile(wrapper)
    expect(store.selectFile).toHaveBeenCalledWith('f1')
  })

  it('selected file title has active highlight class', async () => {
    const { wrapper } = makeWrapper(MOCK_TREE)
    await expandAndClickFile(wrapper)
    const activeFile = wrapper.find('[data-sidebar-file].active')
    expect(activeFile.exists()).toBe(true)
  })

  it('unselected files do NOT have active class before any selection', async () => {
    const { wrapper } = makeWrapper(MOCK_TREE)
    await flushPromises()
    await wrapper.find('[data-domain-chevron]').trigger('click')
    const allFiles = wrapper.findAll('[data-sidebar-file]')
    allFiles.forEach(btn => expect(btn.classes()).not.toContain('active'))
  })
})

// ---------------------------------------------------------------------------
// 4.1h — content panel renders useFileContent output
// ---------------------------------------------------------------------------

describe('content panel', () => {
  async function openContent(wrapper) {
    await flushPromises()
    await wrapper.find('[data-domain-chevron]').trigger('click')
    await wrapper.find('[data-sidebar-file]').trigger('click')
    await wrapper.vm.$nextTick()
  }

  it('content panel shows the file title in the fixed header', async () => {
    const { wrapper } = makeWrapper(MOCK_TREE)
    await openContent(wrapper)
    const panel = wrapper.find('[data-panel="content"]')
    expect(panel.text()).toContain('Roth IRA指南')
  })

  it('content panel shows the domain badge', async () => {
    const { wrapper } = makeWrapper(MOCK_TREE)
    await openContent(wrapper)
    const panel = wrapper.find('[data-panel="content"]')
    expect(panel.find('[data-domain-badge]').exists()).toBe(true)
    expect(panel.find('[data-domain-badge]').text()).toBe('退休规划')
  })

  it('content panel has a download button with correct href', async () => {
    const { wrapper } = makeWrapper(MOCK_TREE)
    await openContent(wrapper)
    const panel = wrapper.find('[data-panel="content"]')
    const downloadBtn = panel.find('[data-download-btn]')
    expect(downloadBtn.exists()).toBe(true)
    expect(downloadBtn.attributes('href')).toBe('/api/files/f1/download')
  })
})

// ---------------------------------------------------------------------------
// 4.1i — no-filename entry shows placeholder text
// ---------------------------------------------------------------------------

describe('no-filename entry', () => {
  it('shows 无原始文件可预览 when entry has no filename', async () => {
    const noFileTree = {
      '税务策略': [
        { file_id: 'f3', title: 'Tax Notes', orig_name: 'notes', domain: '税务策略', filename: null },
      ],
    }
    const { wrapper } = makeWrapper(noFileTree)
    await flushPromises()
    await wrapper.find('[data-domain-chevron]').trigger('click')
    await wrapper.find('[data-sidebar-file]').trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-panel="content"]').text()).toContain('无原始文件可预览')
  })
})

// ---------------------------------------------------------------------------
// Mobile drawer (mobile-friendly change)
// ---------------------------------------------------------------------------

describe('WikiView mobile shape', () => {
  it('inline tree is hidden md- via hidden md:flex', async () => {
    const { wrapper } = makeWrapper(MOCK_TREE)
    await flushPromises()
    const inline = wrapper.find('[data-tree-inline]')
    expect(inline.exists()).toBe(true)
    expect(inline.classes().join(' ')).toMatch(/hidden md:flex/)
  })

  it('header has ☰ tree-toggle button (md:hidden)', async () => {
    const { wrapper } = makeWrapper(MOCK_TREE)
    await flushPromises()
    const toggle = wrapper.find('[data-tree-toggle]')
    expect(toggle.exists()).toBe(true)
    expect(toggle.classes().join(' ')).toMatch(/md:hidden/)
  })

  it('☰ opens drawer; selecting a file in the drawer closes it', async () => {
    const { wrapper } = makeWrapper(MOCK_TREE)
    await flushPromises()
    expect(wrapper.find('[data-tree-drawer]').exists()).toBe(false)
    await wrapper.find('[data-tree-toggle]').trigger('click')
    const drawer = wrapper.find('[data-tree-drawer]')
    expect(drawer.exists()).toBe(true)
    // Drawer renders the same domain tree
    const drawerDomains = drawer.findAll('[data-drawer-domain]')
    expect(drawerDomains.length).toBeGreaterThan(0)
    // Expand a domain to reveal a file
    await drawer.find('[data-drawer-chevron]').trigger('click')
    await drawer.find('[data-drawer-file]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-tree-drawer]').exists()).toBe(false)
  })
})
