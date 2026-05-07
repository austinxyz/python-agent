import { defineStore } from 'pinia'
import api from '../api/index.js'

export const useWikiStore = defineStore('wiki', {
  state: () => ({
    tree: {},
    selectedFileId: null,
    searchQuery: '',
    error: null,
    _api: api,
  }),

  getters: {
    filteredTree(state) {
      const q = state.searchQuery.trim().toLowerCase()
      if (!q) return { ...state.tree }
      const result = {}
      for (const [domain, entries] of Object.entries(state.tree)) {
        if (!Array.isArray(entries)) continue
        const matched = entries.filter(e =>
          (e.title || '').toLowerCase().includes(q) ||
          (e.orig_name || '').toLowerCase().includes(q)
        )
        if (matched.length) result[domain] = matched
      }
      return result
    },
  },

  actions: {
    async fetchTree() {
      this.error = null
      try {
        const resp = await this._api.get('/wiki/tree')
        this.tree = resp.data
      } catch (err) {
        this.tree = {}
        this.error = err?.response?.data?.error ?? err.message ?? 'Unknown error'
      }
    },

    selectFile(id) {
      this.selectedFileId = id
    },
  },
})
