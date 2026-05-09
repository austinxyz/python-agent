/**
 * RED-phase tests for the redesigned IngestView (tasks 4.1–4.6).
 * All tests should fail until IngestView.vue is rewritten in task 4.7.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import IngestView from '../../src/views/IngestView.vue'
import { useIngestStore } from '../../src/stores/ingest.js'
import { DOMAINS } from '../../src/constants/domains.js'

const MOCK_FILES = [
  { file_id: 'f1', title: 'Roth IRA详解', orig_name: 'roth.pdf', domain: '退休规划', source_type: 'file', orig_name_display: 'roth.pdf' },
  { file_id: 'f2', title: null, orig_name: 'notes.txt', domain: '其他', source_type: 'text' },
]

function makeWrapper(files = []) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const store = useIngestStore(pinia)
  store._api = {
    get: vi.fn().mockResolvedValue({ data: files }),
    post: vi.fn().mockResolvedValue({ data: { job_id: 'job-001' } }),
  }
  const wrapper = mount(IngestView, { global: { plugins: [pinia] } })
  return { wrapper, store }
}

// ---------------------------------------------------------------------------
// 4.1 — sidebar domains and default welcome state
// ---------------------------------------------------------------------------

describe('4.1 sidebar and welcome state', () => {
  it('renders all 10 domain names in the left sidebar on mount', async () => {
    const { wrapper } = makeWrapper()
    await flushPromises()
    for (const d of DOMAINS) {
      expect(wrapper.text()).toContain(d)
    }
  })

  it('rightPanelState defaults to welcome — welcome panel is visible', async () => {
    const { wrapper } = makeWrapper()
    expect(wrapper.find('[data-panel="welcome"]').exists()).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// 4.2 — domain click sets state; chevron toggles file list
// ---------------------------------------------------------------------------

describe('4.2 domain name click and chevron toggle', () => {
  it('clicking domain name transitions rightPanelState to domain', async () => {
    const { wrapper } = makeWrapper()
    await wrapper.find('[data-domain-name]').trigger('click')
    expect(wrapper.find('[data-panel="domain"]').exists()).toBe(true)
    expect(wrapper.find('[data-panel="welcome"]').exists()).toBe(false)
  })

  it('clicking domain name shows domain heading and + 新建摄入 button', async () => {
    const { wrapper } = makeWrapper()
    await wrapper.find('[data-domain-name]').trigger('click')
    const panel = wrapper.find('[data-panel="domain"]')
    expect(panel.text()).toContain('新建摄入')
  })

  it('clicking chevron toggles file list visibility without changing rightPanelState', async () => {
    const { wrapper } = makeWrapper(MOCK_FILES)
    await flushPromises()
    // Files are hidden by default (collapsed)
    const chevron = wrapper.find('[data-domain-chevron]')
    await chevron.trigger('click')
    // After expanding, file items should appear inside the sidebar domain
    expect(wrapper.find('[data-sidebar-file]').exists()).toBe(true)
    // rightPanelState should still be 'welcome'
    expect(wrapper.find('[data-panel="welcome"]').exists()).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// 4.3 — + 新建摄入 opens form with locked domain badge, no destination, no topic
// ---------------------------------------------------------------------------

describe('4.3 new ingest button opens form', () => {
  async function openForm(wrapper, domainIndex = 0) {
    const domainNames = wrapper.findAll('[data-domain-name]')
    await domainNames[domainIndex].trigger('click')
    const btn = wrapper.find('[data-action="new-ingest"]')
    await btn.trigger('click')
  }

  it('clicking + 新建摄入 sets rightPanelState to form', async () => {
    const { wrapper } = makeWrapper()
    await openForm(wrapper)
    expect(wrapper.find('[data-panel="form"]').exists()).toBe(true)
  })

  it('form shows read-only domain badge matching the selected domain', async () => {
    const { wrapper } = makeWrapper()
    const firstDomain = DOMAINS[0]
    await openForm(wrapper, 0)
    const formPanel = wrapper.find('[data-panel="form"]')
    expect(formPanel.find('[data-domain-badge]').text()).toBe(firstDomain)
  })

  it('form has no destination toggle', async () => {
    const { wrapper } = makeWrapper()
    await openForm(wrapper)
    expect(wrapper.find('[data-destination]').exists()).toBe(false)
  })

  it('form has no topic input', async () => {
    const { wrapper } = makeWrapper()
    await openForm(wrapper)
    expect(wrapper.find('[data-input="topic"]').exists()).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// 4.4 — form validation and valid submission
// ---------------------------------------------------------------------------

describe('4.4 form validation and submission', () => {
  async function openForm(wrapper) {
    await wrapper.find('[data-domain-name]').trigger('click')
    await wrapper.find('[data-action="new-ingest"]').trigger('click')
  }

  it('submitting with empty title shows error and does not call POST', async () => {
    const { wrapper, store } = makeWrapper()
    await openForm(wrapper)
    await wrapper.find('[data-action="submit-ingest"]').trigger('click')
    expect(wrapper.find('[data-ingest-error]').exists()).toBe(true)
    expect(store._api.post).not.toHaveBeenCalled()
  })

  it('submitting with title + URL calls POST /ingest with correct FormData', async () => {
    const { wrapper, store } = makeWrapper()
    await openForm(wrapper)

    await wrapper.find('[data-input="title"]').setValue('Roth IRA详解')
    // Select URL source type
    const urlTab = wrapper.find('[data-source-type="url"]')
    await urlTab.trigger('click')
    await wrapper.find('[data-input="source_url"]').setValue('https://example.com/article')
    await wrapper.find('[data-action="submit-ingest"]').trigger('click')
    await flushPromises()

    expect(store._api.post).toHaveBeenCalledWith('/ingest', expect.any(FormData))
    const [, fd] = store._api.post.mock.calls[0]
    expect(fd.get('title')).toBe('Roth IRA详解')
    expect(fd.get('destination')).toBe('knowledge')
    expect(fd.get('source_type')).toBe('url')
  })
})

// ---------------------------------------------------------------------------
// 4.5 — result state, pollJob called, fetchFiles on completion
// ---------------------------------------------------------------------------

describe('4.5 result state after submission', () => {
  async function submitForm(wrapper, store) {
    await wrapper.find('[data-domain-name]').trigger('click')
    await wrapper.find('[data-action="new-ingest"]').trigger('click')
    await wrapper.find('[data-input="title"]').setValue('Test Title')
    const urlTab = wrapper.find('[data-source-type="url"]')
    await urlTab.trigger('click')
    await wrapper.find('[data-input="source_url"]').setValue('https://example.com')
    store.pollJob = vi.fn()
    await wrapper.find('[data-action="submit-ingest"]').trigger('click')
    await flushPromises()
  }

  it('successful submit transitions rightPanelState to result', async () => {
    const { wrapper, store } = makeWrapper()
    await submitForm(wrapper, store)
    expect(wrapper.find('[data-panel="result"]').exists()).toBe(true)
  })

  it('result panel shows the submitted title', async () => {
    const { wrapper, store } = makeWrapper()
    await submitForm(wrapper, store)
    expect(wrapper.find('[data-panel="result"]').text()).toContain('Test Title')
  })

  it('store.pollJob is called with the job_id after submit', async () => {
    const { wrapper, store } = makeWrapper()
    await submitForm(wrapper, store)
    expect(store.pollJob).toHaveBeenCalledWith('job-001', expect.anything())
  })
})

// ---------------------------------------------------------------------------
// 4.6 — clicking file title sets content state
// ---------------------------------------------------------------------------

describe('4.6 file title click opens content viewer', () => {
  it('clicking a file title in sidebar sets rightPanelState to content', async () => {
    const { wrapper } = makeWrapper(MOCK_FILES)
    await flushPromises()
    // Expand the domain that has files
    const chevrons = wrapper.findAll('[data-domain-chevron]')
    // Find the one for '退休规划' (first domain, has f1)
    const firstChevron = chevrons[0]
    await firstChevron.trigger('click')
    await wrapper.vm.$nextTick()

    const fileLink = wrapper.find('[data-sidebar-file]')
    await fileLink.trigger('click')
    expect(wrapper.find('[data-panel="content"]').exists()).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// Mobile drawer (mobile-friendly change)
// ---------------------------------------------------------------------------

describe('IngestView mobile shape', () => {
  it('inline tree is hidden md- via hidden md:flex', async () => {
    const { wrapper } = makeWrapper(MOCK_FILES)
    await flushPromises()
    const inline = wrapper.find('[data-tree-inline]')
    expect(inline.exists()).toBe(true)
    expect(inline.classes().join(' ')).toMatch(/hidden md:flex/)
  })

  it('header has ☰ tree-toggle (md:hidden)', async () => {
    const { wrapper } = makeWrapper(MOCK_FILES)
    await flushPromises()
    const toggle = wrapper.find('[data-tree-toggle]')
    expect(toggle.exists()).toBe(true)
    expect(toggle.classes().join(' ')).toMatch(/md:hidden/)
  })

  it('☰ opens drawer; selecting a domain closes it and shows the domain panel', async () => {
    const { wrapper } = makeWrapper(MOCK_FILES)
    await flushPromises()
    expect(wrapper.find('[data-tree-drawer]').exists()).toBe(false)
    await wrapper.find('[data-tree-toggle]').trigger('click')
    const drawer = wrapper.find('[data-tree-drawer]')
    expect(drawer.exists()).toBe(true)
    const domains = drawer.findAll('[data-drawer-domain]')
    expect(domains.length).toBeGreaterThan(0)
    // Click first domain's name
    await domains[0].find('span').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-tree-drawer]').exists()).toBe(false)
  })
})
