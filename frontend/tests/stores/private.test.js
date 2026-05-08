import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { usePrivateStore } from '../../src/stores/private.js'

beforeEach(() => {
  setActivePinia(createPinia())
})

// ---------------------------------------------------------------------------
// fetchTemplates
// ---------------------------------------------------------------------------

describe('fetchTemplates', () => {
  it('calls GET /private/templates and populates templates', async () => {
    const store = usePrivateStore()
    const templates = [
      { type: 'tax', label: '税务情况', fields: [] },
      { type: 'retirement', label: '退休账户', fields: [] },
    ]
    store._api = { get: vi.fn().mockResolvedValue({ data: templates }) }

    await store.fetchTemplates()

    expect(store._api.get).toHaveBeenCalledWith('/private/templates')
    expect(store.templates).toEqual(templates)
  })

  it('records error and leaves templates empty on failure', async () => {
    const store = usePrivateStore()
    store._api = { get: vi.fn().mockRejectedValue(new Error('boom')) }

    await store.fetchTemplates()

    expect(store.templates).toEqual([])
    expect(store.error).toBe('boom')
  })
})

// ---------------------------------------------------------------------------
// fetchEntries
// ---------------------------------------------------------------------------

describe('fetchEntries', () => {
  it('calls GET /private/entries and populates entries', async () => {
    const store = usePrivateStore()
    const entries = [{ id: 'e1', title: 'a', template_type: 'tax', content_json: {} }]
    store._api = { get: vi.fn().mockResolvedValue({ data: entries }) }

    await store.fetchEntries()

    expect(store._api.get).toHaveBeenCalledWith('/private/entries')
    expect(store.entries).toEqual(entries)
  })
})

// ---------------------------------------------------------------------------
// createEntry — must prepend immutably (spread, not push)
// ---------------------------------------------------------------------------

describe('createEntry', () => {
  it('calls POST and prepends new entry immutably', async () => {
    const store = usePrivateStore()
    const existing = { id: 'e1', title: 'old', template_type: 'tax', content_json: {} }
    store.entries = [existing]
    const original = store.entries
    const created = { id: 'e2', title: 'new', template_type: 'tax', content_json: {} }
    store._api = { post: vi.fn().mockResolvedValue({ data: created }) }

    await store.createEntry({ template_type: 'tax', title: 'new', content_json: {} })

    expect(store._api.post).toHaveBeenCalledWith('/private/entries', {
      template_type: 'tax',
      title: 'new',
      content_json: {},
    })
    expect(store.entries).toEqual([created, existing])
    expect(store.entries).not.toBe(original) // new array reference
  })
})

// ---------------------------------------------------------------------------
// updateEntry — must replace target immutably
// ---------------------------------------------------------------------------

describe('updateEntry', () => {
  it('calls PUT and replaces matching entry immutably', async () => {
    const store = usePrivateStore()
    const a = { id: 'e1', title: 'a', template_type: 'tax', content_json: {} }
    const b = { id: 'e2', title: 'b', template_type: 'tax', content_json: {} }
    store.entries = [a, b]
    const original = store.entries
    const updated = { id: 'e1', title: 'A!', template_type: 'tax', content_json: { x: 1 } }
    store._api = { put: vi.fn().mockResolvedValue({ data: updated }) }

    await store.updateEntry('e1', { title: 'A!', content_json: { x: 1 } })

    expect(store._api.put).toHaveBeenCalledWith('/private/entries/e1', {
      title: 'A!',
      content_json: { x: 1 },
    })
    expect(store.entries).toEqual([updated, b])
    expect(store.entries).not.toBe(original)
  })
})

// ---------------------------------------------------------------------------
// deleteEntry — must filter immutably
// ---------------------------------------------------------------------------

describe('deleteEntry', () => {
  it('calls DELETE and filters out the deleted id immutably', async () => {
    const store = usePrivateStore()
    const a = { id: 'e1', title: 'a' }
    const b = { id: 'e2', title: 'b' }
    store.entries = [a, b]
    const original = store.entries
    store._api = { delete: vi.fn().mockResolvedValue({ data: { ok: true } }) }

    await store.deleteEntry('e1')

    expect(store._api.delete).toHaveBeenCalledWith('/private/entries/e1')
    expect(store.entries).toEqual([b])
    expect(store.entries).not.toBe(original)
  })
})

// ---------------------------------------------------------------------------
// fetchNotes
// ---------------------------------------------------------------------------

describe('fetchNotes', () => {
  it('populates notes and notesTree', async () => {
    const store = usePrivateStore()
    const payload = {
      notes: [{ id: 'n1', title: 't', directory: '退休规划', content: 'x' }],
      tree: { '退休规划': { _notes: [{ id: 'n1', title: 't' }] } },
    }
    store._api = { get: vi.fn().mockResolvedValue({ data: payload }) }

    await store.fetchNotes()

    expect(store._api.get).toHaveBeenCalledWith('/private/notes')
    expect(store.notes).toEqual(payload.notes)
    expect(store.notesTree).toEqual(payload.tree)
  })
})

// ---------------------------------------------------------------------------
// createNote — prepends immutably
// ---------------------------------------------------------------------------

describe('createNote', () => {
  it('calls POST and prepends note immutably', async () => {
    const store = usePrivateStore()
    const existing = { id: 'n1', title: 'old', directory: '', content: 'x' }
    store.notes = [existing]
    const original = store.notes
    const created = { id: 'n2', title: 'new', directory: '', content: 'y' }
    store._api = { post: vi.fn().mockResolvedValue({ data: created }) }

    await store.createNote({ title: 'new', content: 'y' })

    expect(store._api.post).toHaveBeenCalledWith('/private/notes', {
      title: 'new',
      content: 'y',
    })
    expect(store.notes).toEqual([created, existing])
    expect(store.notes).not.toBe(original)
  })
})

// ---------------------------------------------------------------------------
// updateNote — replaces immutably
// ---------------------------------------------------------------------------

describe('updateNote', () => {
  it('calls PUT and replaces matching note immutably', async () => {
    const store = usePrivateStore()
    const a = { id: 'n1', title: 'a', directory: '', content: 'x' }
    const b = { id: 'n2', title: 'b', directory: '', content: 'y' }
    store.notes = [a, b]
    const original = store.notes
    const updated = { id: 'n1', title: 'a', directory: '', content: 'XXX' }
    store._api = { put: vi.fn().mockResolvedValue({ data: updated }) }

    await store.updateNote('n1', { content: 'XXX' })

    expect(store._api.put).toHaveBeenCalledWith('/private/notes/n1', { content: 'XXX' })
    expect(store.notes).toEqual([updated, b])
    expect(store.notes).not.toBe(original)
  })
})

describe('deleteNote', () => {
  it('calls DELETE and removes the note from state immutably', async () => {
    const store = usePrivateStore()
    const a = { id: 'n1', title: 'a' }
    const b = { id: 'n2', title: 'b' }
    store.notes = [a, b]
    const original = store.notes
    store._api = { delete: vi.fn().mockResolvedValue({ data: { ok: true } }) }

    await store.deleteNote('n1')

    expect(store._api.delete).toHaveBeenCalledWith('/private/notes/n1')
    expect(store.notes).toEqual([b])
    expect(store.notes).not.toBe(original)
  })

  it('records error and re-throws when API fails', async () => {
    const store = usePrivateStore()
    store.notes = [{ id: 'n1', title: 'a' }]
    store._api = { delete: vi.fn().mockRejectedValue(new Error('boom')) }

    await expect(store.deleteNote('n1')).rejects.toThrow('boom')
    expect(store.error).toBe('boom')
    // Notes stay untouched on failure
    expect(store.notes).toEqual([{ id: 'n1', title: 'a' }])
  })
})

// ---------------------------------------------------------------------------
// 7.3 — combinedTree getter and directory pass-through
// ---------------------------------------------------------------------------

describe('combinedTree getter', () => {
  it('seeds the 6 fixed template directories even when entries/notes are empty', () => {
    const store = usePrivateStore()
    store.entries = []
    store.notes = []
    const tree = store.combinedTree
    expect(Object.keys(tree).sort()).toEqual([
      '个人基本情况',
      '投资持仓',
      '房产资产',
      '税务',
      '自由格式',
      '退休账户',
    ].sort())
  })

  it('groups entries under their directory with kind=entry', () => {
    const store = usePrivateStore()
    store.entries = [
      { id: 'e1', template_type: 'tax', title: '税', directory: '税务', content_json: {} },
    ]
    store.notes = []
    const taxNode = store.combinedTree['税务']
    expect(taxNode._items).toHaveLength(1)
    expect(taxNode._items[0]).toMatchObject({ id: 'e1', kind: 'entry', title: '税' })
  })

  it('groups notes under their directory with kind=note', () => {
    const store = usePrivateStore()
    store.entries = []
    store.notes = [
      { id: 'n1', title: '总览', directory: '退休规划', content: '' },
    ]
    const node = store.combinedTree['退休规划']
    expect(node._items).toHaveLength(1)
    expect(node._items[0]).toMatchObject({ id: 'n1', kind: 'note', title: '总览' })
  })

  it('builds nested directories from slash-separated paths', () => {
    const store = usePrivateStore()
    store.entries = []
    store.notes = [
      { id: 'n1', title: 'roth', directory: '退休规划/Roth相关', content: '' },
    ]
    const node = store.combinedTree['退休规划']['Roth相关']
    expect(node._items).toHaveLength(1)
    expect(node._items[0].id).toBe('n1')
  })

  it('places items with empty directory under the _items key at root', () => {
    const store = usePrivateStore()
    store.entries = []
    store.notes = [
      { id: 'n1', title: '随手记', directory: '', content: '' },
    ]
    const tree = store.combinedTree
    expect(tree._items).toBeDefined()
    expect(tree._items[0].id).toBe('n1')
  })

  it('mixes entries and notes under the same directory', () => {
    const store = usePrivateStore()
    store.entries = [
      { id: 'e1', template_type: 'retirement', title: '401k', directory: '退休账户', content_json: {} },
    ]
    store.notes = [
      { id: 'n1', title: '心得', directory: '退休账户', content: '' },
    ]
    const items = store.combinedTree['退休账户']._items
    expect(items.map(i => i.kind).sort()).toEqual(['entry', 'note'])
  })
})

describe('createEntry passes directory through', () => {
  it('forwards directory in the POST body', async () => {
    const store = usePrivateStore()
    store._api = { post: vi.fn().mockResolvedValue({ data: { id: 'e1', directory: '税务/2025' } }) }

    await store.createEntry({
      template_type: 'tax',
      title: '我的税务',
      directory: '税务/2025',
      content_json: {},
    })

    expect(store._api.post).toHaveBeenCalledWith('/private/entries', {
      template_type: 'tax',
      title: '我的税务',
      directory: '税务/2025',
      content_json: {},
    })
  })
})

describe('updateEntry passes directory through', () => {
  it('forwards directory in the PUT body', async () => {
    const store = usePrivateStore()
    store.entries = [{ id: 'e1', template_type: 'tax', title: 'x', directory: '税务', content_json: {} }]
    store._api = { put: vi.fn().mockResolvedValue({ data: { id: 'e1', directory: '税务/历史' } }) }

    await store.updateEntry('e1', { directory: '税务/历史' })

    expect(store._api.put).toHaveBeenCalledWith('/private/entries/e1', { directory: '税务/历史' })
  })
})
