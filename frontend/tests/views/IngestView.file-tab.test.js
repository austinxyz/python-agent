import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import IngestView from '../../src/views/IngestView.vue'

const MOCK_FILES = [
  { file_id: 'f1', domain: 'finance', topic: 'budget', orig_name: 'budget.pdf' },
  { file_id: 'f2', domain: 'finance', topic: 'report', orig_name: 'report.pdf' },
  { file_id: 'f3', domain: 'health', topic: 'diet', orig_name: 'diet.txt' },
]

async function mountFilesTab(files = MOCK_FILES) {
  const pinia = createPinia()
  const wrapper = mount(IngestView, {
    global: { plugins: [pinia] },
    props: { initialFiles: files },
  })
  const tabs = wrapper.findAll('[data-tab]')
  await tabs[1].trigger('click')
  return { wrapper, pinia }
}

beforeEach(() => {
  setActivePinia(createPinia())
})

// ---------------------------------------------------------------------------
// task 8.6 — file list tab with TreeNav
// ---------------------------------------------------------------------------

describe('Uploaded Files tab', () => {
  it('renders TreeNav with domain-level items from file list', async () => {
    const { wrapper } = await mountFilesTab()
    const treeNav = wrapper.findComponent({ name: 'TreeNav' })
    expect(treeNav.exists()).toBe(true)
    const items = treeNav.props('items')
    const domainLabels = items.map(i => i.label)
    expect(domainLabels).toContain('finance')
    expect(domainLabels).toContain('health')
  })

  it('shows all file rows by default', async () => {
    const { wrapper } = await mountFilesTab()
    const rows = wrapper.findAll('[data-file-row]')
    expect(rows).toHaveLength(3)
  })

  it('selecting a tree node filters visible file rows to that domain', async () => {
    const { wrapper } = await mountFilesTab()
    const treeNav = wrapper.findComponent({ name: 'TreeNav' })
    await treeNav.vm.$emit('select', { label: 'finance' })
    const rows = wrapper.findAll('[data-file-row]')
    expect(rows).toHaveLength(2)
    const rowTexts = rows.map(r => r.text())
    expect(rowTexts.some(t => t.includes('budget.pdf'))).toBe(true)
    expect(rowTexts.some(t => t.includes('report.pdf'))).toBe(true)
    expect(rowTexts.some(t => t.includes('diet.txt'))).toBe(false)
  })
})
