import { defineStore } from 'pinia'
import api from '../api/index.js'

export const useAdminUsersStore = defineStore('adminUsers', {
  state: () => ({
    users: [],
    loading: false,
    error: null,
    _api: api,
  }),

  actions: {
    async fetchUsers() {
      this.loading = true
      this.error = null
      try {
        const resp = await this._api.get('/admin/users')
        this.users = resp?.data ?? []
      } catch (err) {
        this.error = err?.response?.data?.error ?? err?.message ?? 'Unknown error'
      } finally {
        this.loading = false
      }
    },

    async inviteUser(email, role) {
      try {
        const resp = await this._api.post('/admin/users', { email, role })
        const user = resp?.data?.user
        if (user) this.users.push(user)
        return resp?.data ?? {}
      } catch (err) {
        if (err?.response?.status === 409) {
          return { conflict: err.response.data?.existing ?? null }
        }
        this.error = err?.response?.data?.error ?? err?.message ?? 'Unknown error'
        throw err
      }
    },

    async updateUser(id, patch) {
      try {
        const resp = await this._api.patch(`/admin/users/${id}`, patch)
        const updated = resp?.data
        if (updated) {
          const idx = this.users.findIndex(u => u.id === id)
          if (idx !== -1) this.users[idx] = { ...this.users[idx], ...updated }
        }
        return updated
      } catch (err) {
        this.error = err?.response?.data?.error ?? err?.message ?? 'Unknown error'
        throw err
      }
    },

    async deleteUser(id) {
      await this._api.delete(`/admin/users/${id}`)
      this.users = this.users.filter(u => u.id !== id)
    },

    async resendInvite(id) {
      const resp = await this._api.post(`/admin/users/${id}/resend-invite`, undefined)
      return resp?.data ?? {}
    },
  },
})
