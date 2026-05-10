import { defineStore } from 'pinia'
import api from '../api/index.js'

function readError(err) {
  return err?.response?.data?.error ?? err?.message ?? 'Unknown error'
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    currentUser: null, // null = unauthenticated; otherwise {id, email, name, picture_url, role}
    config: null,      // {has_google, google_client_id} after fetchConfig
    loading: false,
    error: null,
    _api: api,
  }),

  getters: {
    isAuthenticated: (s) => s.currentUser !== null,
    isAdmin: (s) => s.currentUser?.role === 'admin',
  },

  actions: {
    /** Hydrate currentUser from server-side session cookie. Silent on 401. */
    async fetchMe() {
      this.loading = true
      this.error = null
      try {
        const resp = await this._api.get('/auth/me')
        this.currentUser = resp?.data?.user ?? null
      } catch (err) {
        // 401 means not authenticated — expected state, don't surface.
        if (err?.response?.status !== 401) {
          this.error = readError(err)
        }
        this.currentUser = null
      } finally {
        this.loading = false
      }
    },

    async fetchConfig() {
      try {
        const resp = await this._api.get('/auth/config')
        this.config = resp?.data ?? null
      } catch (err) {
        this.error = readError(err)
        this.config = null
      }
    },

    async loginWithPassword(email, password) {
      this.error = null
      const resp = await this._api.post('/auth/login', { email, password })
      this.currentUser = resp?.data?.user ?? null
    },

    async loginWithGoogle(idToken) {
      this.error = null
      const resp = await this._api.post('/auth/login/google', { id_token: idToken })
      this.currentUser = resp?.data?.user ?? null
    },

    async fetchInvite(token) {
      const resp = await this._api.get(`/auth/invite/${encodeURIComponent(token)}`)
      return resp?.data ?? { valid: false, expired: false, user: null, inviter: null }
    },

    async acceptInvite(token, password) {
      this.error = null
      const resp = await this._api.post('/auth/accept-invite', { token, password })
      this.currentUser = resp?.data?.user ?? null
    },

    async changePassword(oldPw, newPw) {
      this.error = null
      await this._api.post('/auth/change-password', {
        old_password: oldPw,
        new_password: newPw,
      })
    },

    async logout() {
      try {
        await this._api.post('/auth/logout')
      } finally {
        this.currentUser = null
      }
    },
  },
})
