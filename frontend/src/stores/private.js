import { defineStore } from 'pinia'
import api from '../api/index.js'

function readError(err) {
  return err?.response?.data?.error ?? err?.message ?? 'Unknown error'
}

// 6 fixed template directories — always seeded into the tree even when empty,
// so the user always sees the structured buckets.
export const FIXED_TEMPLATE_DIRECTORIES = [
  '税务',
  '退休账户',
  '投资持仓',
  '个人基本情况',
  '房产资产',
  '自由格式',
]

function ensureNode(root, segments) {
  let node = root
  for (const seg of segments) {
    if (!seg) continue
    if (!node[seg] || typeof node[seg] !== 'object') {
      node[seg] = {}
    }
    node = node[seg]
  }
  return node
}

function placeItem(root, directory, item) {
  const segments = (directory || '').split('/').map(s => s.trim()).filter(Boolean)
  const node = ensureNode(root, segments)
  if (!Array.isArray(node._items)) node._items = []
  node._items = [...node._items, item]
}

export const usePrivateStore = defineStore('private', {
  state: () => ({
    templates: [],
    entries: [],
    notes: [],
    notesTree: {},
    error: null,
    _api: api,
  }),

  getters: {
    combinedTree(state) {
      const tree = {}
      // Seed fixed directories
      for (const dir of FIXED_TEMPLATE_DIRECTORIES) {
        if (!tree[dir]) tree[dir] = {}
      }
      // Add entries
      for (const e of state.entries) {
        placeItem(tree, e.directory || '', {
          id: e.id,
          kind: 'entry',
          template_type: e.template_type,
          title: e.title,
          directory: e.directory || '',
          content_json: e.content_json,
          created_at: e.created_at,
          updated_at: e.updated_at,
        })
      }
      // Add notes
      for (const n of state.notes) {
        placeItem(tree, n.directory || '', {
          id: n.id,
          kind: 'note',
          title: n.title,
          directory: n.directory || '',
          content: n.content,
          chat_ref: n.chat_ref,
          created_at: n.created_at,
          updated_at: n.updated_at,
        })
      }
      return tree
    },
  },

  actions: {
    async fetchTemplates() {
      this.error = null
      try {
        const resp = await this._api.get('/private/templates')
        this.templates = resp.data
      } catch (err) {
        this.templates = []
        this.error = readError(err)
      }
    },

    async fetchEntries() {
      this.error = null
      try {
        const resp = await this._api.get('/private/entries')
        this.entries = resp.data
      } catch (err) {
        this.entries = []
        this.error = readError(err)
      }
    },

    async createEntry(payload) {
      this.error = null
      try {
        const resp = await this._api.post('/private/entries', payload)
        this.entries = [resp.data, ...this.entries]
        return resp.data
      } catch (err) {
        this.error = readError(err)
        throw err
      }
    },

    async updateEntry(id, payload) {
      this.error = null
      try {
        const resp = await this._api.put(`/private/entries/${id}`, payload)
        this.entries = this.entries.map(e => (e.id === id ? resp.data : e))
        return resp.data
      } catch (err) {
        this.error = readError(err)
        throw err
      }
    },

    async deleteEntry(id) {
      this.error = null
      try {
        await this._api.delete(`/private/entries/${id}`)
        this.entries = this.entries.filter(e => e.id !== id)
      } catch (err) {
        this.error = readError(err)
        throw err
      }
    },

    async fetchNotes() {
      this.error = null
      try {
        const resp = await this._api.get('/private/notes')
        this.notes = resp.data?.notes ?? []
        this.notesTree = resp.data?.tree ?? {}
      } catch (err) {
        this.notes = []
        this.notesTree = {}
        this.error = readError(err)
      }
    },

    async createNote(payload) {
      this.error = null
      try {
        const resp = await this._api.post('/private/notes', payload)
        this.notes = [resp.data, ...this.notes]
        return resp.data
      } catch (err) {
        this.error = readError(err)
        throw err
      }
    },

    async updateNote(id, payload) {
      this.error = null
      try {
        const resp = await this._api.put(`/private/notes/${id}`, payload)
        this.notes = this.notes.map(n => (n.id === id ? resp.data : n))
        return resp.data
      } catch (err) {
        this.error = readError(err)
        throw err
      }
    },

    async deleteNote(id) {
      this.error = null
      try {
        await this._api.delete(`/private/notes/${id}`)
        this.notes = this.notes.filter(n => n.id !== id)
      } catch (err) {
        this.error = readError(err)
        throw err
      }
    },
  },
})
