import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import IngestView from '../../src/views/IngestView.vue'
import { useIngestStore } from '../../src/stores/ingest.js'

function makeWrapper(props = {}) {
  return mount(IngestView, {
    global: { plugins: [createPinia()] },
    ...props,
  })
}

beforeEach(() => {
  setActivePinia(createPinia())
})

// ---------------------------------------------------------------------------
// task 8.1 — two tab buttons
// ---------------------------------------------------------------------------

describe('tab navigation', () => {
  it('renders two tab buttons with correct labels', () => {
    const wrapper = makeWrapper()
    const tabs = wrapper.findAll('[data-tab]')
    expect(tabs).toHaveLength(2)
    const labels = tabs.map(t => t.text())
    expect(labels).toContain('新建摄入')
    expect(labels).toContain('已上传文件')
  })

  it('clicking the second tab shows files panel and hides ingest panel', async () => {
    const wrapper = makeWrapper()
    const tabs = wrapper.findAll('[data-tab]')
    await tabs[1].trigger('click')
    expect(wrapper.find('[data-panel="files"]').isVisible()).toBe(true)
    expect(wrapper.find('[data-panel="ingest"]').isVisible()).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// task 8.2 — destination toggle
// ---------------------------------------------------------------------------

describe('destination toggle', () => {
  it('defaults to "公共知识库" selected', () => {
    const wrapper = makeWrapper()
    const btns = wrapper.findAll('[data-destination]')
    const active = btns.find(b => b.attributes('data-destination') === 'knowledge')
    expect(active.classes()).toContain('active')
  })

  it('clicking "私有数据" updates store destination to "private"', async () => {
    const pinia = createPinia()
    const wrapper = mount(IngestView, { global: { plugins: [pinia] } })
    const store = useIngestStore(pinia)
    const privateBtn = wrapper.find('[data-destination="private"]')
    await privateBtn.trigger('click')
    expect(store.destination).toBe('private')
  })
})

// ---------------------------------------------------------------------------
// task 8.3 — submit validation
// ---------------------------------------------------------------------------

describe('submit validation', () => {
  it('shows error and does not call POST when no content provided', async () => {
    const mockPost = vi.fn()
    vi.stubGlobal('fetch', mockPost)
    const pinia = createPinia()
    const wrapper = mount(IngestView, { global: { plugins: [pinia] } })
    const store = useIngestStore(pinia)
    store._api = { post: mockPost }

    const submitBtn = wrapper.find('[data-action="submit"]')
    await submitBtn.trigger('click')

    expect(wrapper.text()).toContain('请提供摄入内容')
    expect(mockPost).not.toHaveBeenCalled()
  })
})

// ---------------------------------------------------------------------------
// task 8.4 — valid URL submission
// ---------------------------------------------------------------------------

describe('URL submission', () => {
  it('submitting a valid URL calls POST /ingest and adds a running job', async () => {
    const pinia = createPinia()
    const wrapper = mount(IngestView, { global: { plugins: [pinia] } })
    const store = useIngestStore(pinia)

    const mockPost = vi.fn().mockResolvedValue({ data: { job_id: 'test-job-1' } })
    store._api = { post: mockPost, get: vi.fn() }

    const urlInput = wrapper.find('[data-input="source_url"]')
    await urlInput.setValue('https://example.com/report')
    await wrapper.find('[data-action="submit"]').trigger('click')
    await wrapper.vm.$nextTick()

    expect(mockPost).toHaveBeenCalledWith('/ingest', expect.objectContaining({
      source_url: 'https://example.com/report',
      source_type: 'url',
    }))
    expect(store.jobs).toHaveLength(1)
    expect(store.jobs[0].status).toBe('running')

    const progressRows = wrapper.findAll('[data-job-row]')
    expect(progressRows).toHaveLength(1)
  })
})
