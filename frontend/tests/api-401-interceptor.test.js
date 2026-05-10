/**
 * 6.3 RED — axios 401 response interceptor.
 *
 * `src/api/index.js` registers a single response interceptor that, on a 401,
 * calls `_onUnauthorized` (set via `registerOnUnauthorized`) so `main.js` can
 * clear `auth.currentUser` and push `/login`.
 *
 * Endpoints under `/auth/*` are exempt — a 401 from `/auth/login` is the
 * caller's signal that credentials were wrong; redirecting to `/login`
 * while the user is already on the login page would be a flicker loop.
 *
 * These tests stub axios's underlying adapter so we never hit the network.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import api, { registerOnUnauthorized } from '../src/api/index.js'

/**
 * Replace api.defaults.adapter with a stub that resolves a 401 response for
 * the given URL substring, so the interceptor's error path runs.
 *
 * Returns a teardown function that restores the original adapter.
 */
function stub401(matchUrl) {
  const original = api.defaults.adapter
  api.defaults.adapter = (config) => {
    if (config.url.includes(matchUrl)) {
      // axios treats non-2xx as an error and rejects with an AxiosError
      // carrying { response: { status, data, ... }, config }.
      const err = new Error('Request failed with status code 401')
      err.response = { status: 401, data: { error: 'unauthorized' }, config, headers: {} }
      err.config = config
      err.isAxiosError = true
      return Promise.reject(err)
    }
    return Promise.resolve({ status: 200, data: {}, config, headers: {} })
  }
  return () => {
    api.defaults.adapter = original
  }
}

describe('axios 401 interceptor', () => {
  beforeEach(() => {
    // Reset the registered handler between cases.
    registerOnUnauthorized(null)
  })

  it('calls onUnauthorized handler when a non-auth endpoint returns 401', async () => {
    const handler = vi.fn()
    registerOnUnauthorized(handler)
    const restore = stub401('/private/entries')
    try {
      await expect(api.get('/private/entries')).rejects.toMatchObject({
        response: { status: 401 },
      })
    } finally {
      restore()
    }
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('does NOT call onUnauthorized when /auth/login returns 401', async () => {
    const handler = vi.fn()
    registerOnUnauthorized(handler)
    const restore = stub401('/auth/login')
    try {
      await expect(api.post('/auth/login', { email: 'a@b.com', password: 'wrong' })).rejects.toMatchObject({
        response: { status: 401 },
      })
    } finally {
      restore()
    }
    expect(handler).not.toHaveBeenCalled()
  })

  it('does NOT call onUnauthorized when /auth/me returns 401 (initial fetchMe is allowed to fail silently)', async () => {
    const handler = vi.fn()
    registerOnUnauthorized(handler)
    const restore = stub401('/auth/me')
    try {
      await expect(api.get('/auth/me')).rejects.toMatchObject({
        response: { status: 401 },
      })
    } finally {
      restore()
    }
    expect(handler).not.toHaveBeenCalled()
  })

  it('still rejects to the caller (interceptor does not swallow errors)', async () => {
    registerOnUnauthorized(vi.fn())
    const restore = stub401('/private/entries')
    try {
      let caught = null
      try {
        await api.get('/private/entries')
      } catch (err) {
        caught = err
      }
      expect(caught).toBeTruthy()
      expect(caught.response.status).toBe(401)
    } finally {
      restore()
    }
  })

  it('does nothing when no handler is registered (does not throw inside the interceptor)', async () => {
    // Explicitly leave handler null.
    const restore = stub401('/private/entries')
    try {
      await expect(api.get('/private/entries')).rejects.toMatchObject({
        response: { status: 401 },
      })
    } finally {
      restore()
    }
  })

  it('non-401 errors do not invoke the handler', async () => {
    const handler = vi.fn()
    registerOnUnauthorized(handler)
    const original = api.defaults.adapter
    api.defaults.adapter = (config) => {
      const err = new Error('Server error')
      err.response = { status: 500, data: {}, config, headers: {} }
      err.config = config
      err.isAxiosError = true
      return Promise.reject(err)
    }
    try {
      await expect(api.get('/private/entries')).rejects.toMatchObject({
        response: { status: 500 },
      })
    } finally {
      api.defaults.adapter = original
    }
    expect(handler).not.toHaveBeenCalled()
  })
})
