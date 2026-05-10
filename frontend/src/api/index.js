import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// 401 interceptor: clear auth state and redirect to /login.
// Imported lazily via getter callbacks so this module doesn't directly
// depend on the auth store / router (avoids circular imports).
//
// Endpoints under /auth/* are exempt: a 401 from /auth/login itself is the
// caller's signal that credentials were wrong — we don't want to redirect
// to /login when we're already there.
let _onUnauthorized = null

export function registerOnUnauthorized(handler) {
  _onUnauthorized = handler
}

api.interceptors.response.use(
  (resp) => resp,
  (err) => {
    const status = err?.response?.status
    const url = err?.config?.url ?? ''
    const isAuthEndpoint = url.startsWith('/auth/') || url.includes('/api/auth/')
    if (status === 401 && !isAuthEndpoint && _onUnauthorized) {
      try {
        _onUnauthorized()
      } catch {
        /* never swallow user notification, just suppress in interceptor */
      }
    }
    return Promise.reject(err)
  }
)

export default api
