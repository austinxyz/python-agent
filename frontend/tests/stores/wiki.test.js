import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useWikiStore } from '../../src/stores/wiki.js'

beforeEach(() => {
  setActivePinia(createPinia())
})

// ---------------------------------------------------------------------------
// fetchTree
// ---------------------------------------------------------------------------

describe('fetchTree', () => {
  it('calls GET /wiki/tree and populates tree', async () => {
    const store = useWikiStore()
    const treeData = {
      '退休规划': [{ file_id: 'a', title: 'Roth IRA', orig_name: 'roth.pdf', domain: '退休规划' }],
    }
    store._api = { get: vi.fn().mockResolvedValue({ data: treeData }) }

    await store.fetchTree()

    expect(store._api.get).toHaveBeenCalledWith('/wiki/tree')
    expect(store.tree).toEqual(treeData)
  })

  it('leaves tree empty and sets error on network failure', async () => {
    const store = useWikiStore()
    store._api = { get: vi.fn().mockRejectedValue(new Error('Network error')) }

    await store.fetchTree()

    expect(store.tree).toEqual({})
    expect(store.error).toBe('Network error')
  })

  it('clears error on successful subsequent fetch', async () => {
    const store = useWikiStore()
    store.error = 'previous error'
    store._api = { get: vi.fn().mockResolvedValue({ data: {} }) }

    await store.fetchTree()

    expect(store.error).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// selectFile
// ---------------------------------------------------------------------------

describe('selectFile', () => {
  it('updates selectedFileId', () => {
    const store = useWikiStore()
    store.selectFile('file-abc')
    expect(store.selectedFileId).toBe('file-abc')
  })

  it('can be set to null to deselect', () => {
    const store = useWikiStore()
    store.selectFile('file-abc')
    store.selectFile(null)
    expect(store.selectedFileId).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// filteredTree
// ---------------------------------------------------------------------------

describe('filteredTree', () => {
  function makeStore(treeData) {
    const store = useWikiStore()
    store.tree = treeData
    return store
  }

  const TREE = {
    '退休规划': [
      { file_id: 'a', title: 'Roth IRA Guide', orig_name: 'roth.pdf', domain: '退休规划' },
      { file_id: 'b', title: '401k Plan', orig_name: '401k.pdf', domain: '退休规划' },
    ],
    '税务策略': [
      { file_id: 'c', title: 'Tax Basics', orig_name: 'tax-basics.pdf', domain: '税务策略' },
    ],
  }

  it('returns full tree when searchQuery is empty', () => {
    const store = makeStore(TREE)
    store.searchQuery = ''
    expect(store.filteredTree).toEqual(TREE)
  })

  it('filters entries by title case-insensitively', () => {
    const store = makeStore(TREE)
    store.searchQuery = 'roth'
    const result = store.filteredTree
    expect(result['退休规划']).toHaveLength(1)
    expect(result['退休规划'][0].file_id).toBe('a')
    expect(result['税务策略']).toBeUndefined()
  })

  it('filters entries by orig_name case-insensitively', () => {
    const store = makeStore(TREE)
    store.searchQuery = '401K'
    const result = store.filteredTree
    expect(result['退休规划']).toHaveLength(1)
    expect(result['退休规划'][0].file_id).toBe('b')
  })

  it('hides domains with no matching entries', () => {
    const store = makeStore(TREE)
    store.searchQuery = 'tax'
    const result = store.filteredTree
    expect(Object.keys(result)).toEqual(['税务策略'])
  })

  it('returns empty object when nothing matches', () => {
    const store = makeStore(TREE)
    store.searchQuery = 'zzznomatch'
    expect(store.filteredTree).toEqual({})
  })

  it('restores full tree after clearing searchQuery', () => {
    const store = makeStore(TREE)
    store.searchQuery = 'roth'
    store.searchQuery = ''
    expect(store.filteredTree).toEqual(TREE)
  })
})
