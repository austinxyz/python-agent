/**
 * 6.5 RED — router auth guard.
 *
 * `src/router/index.js` registers a global `beforeEach` that:
 *   - allows `meta.public` routes (`/login`, `/accept-invite`) without auth
 *   - calls `auth.fetchMe()` once when `currentUser === null`
 *   - redirects unauthenticated users to `/login?redirect=<originalPath>`
 *   - redirects non-admin users away from `/admin/*` to `/chat`
 *   - leaves `/` redirecting to `/chat` (NOT `/wiki` like before)
 *
 * The production router uses `createWebHistory`. It works under happy-dom
 * because window.history is provided. We override the auth store's `_api`
 * before any navigation so `fetchMe` doesn't hit the network.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import router from '../src/router/index.js'
import { useAuthStore } from '../src/stores/auth.js'

const fakeUser = (overrides = {}) => ({
  id: 'u1',
  email: 'a@b.com',
  name: 'A',
  role: 'member',
  picture_url: null,
  ...overrides,
})

function setupAuth({ user = null } = {}) {
  setActivePinia(createPinia())
  const auth = useAuthStore()
  // Stub _api so fetchMe never hits the network. fetchMe sets currentUser
  // from response.data.user; if user is null we resolve `{ user: null }`
  // which the store treats as "unauthenticated" (via the `?? null` fallback).
  auth._api = {
    get: vi.fn().mockResolvedValue({ data: { user } }),
    post: vi.fn().mockResolvedValue({ data: {} }),
  }
  // For tests that want to simulate an already-loaded user, prepopulate.
  if (user) {
    auth.currentUser = user
  }
  return auth
}

async function pushAndSettle(target) {
  await router.push(target).catch(() => {})
  await router.isReady()
  return router.currentRoute.value
}

describe('router guard — public routes', () => {
  beforeEach(() => {
    setupAuth({ user: null })
  })

  it('reaches /login without auth', async () => {
    const r = await pushAndSettle('/login')
    expect(r.path).toBe('/login')
  })

  it('reaches /accept-invite without auth', async () => {
    const r = await pushAndSettle('/accept-invite?token=abc')
    expect(r.path).toBe('/accept-invite')
    expect(r.query.token).toBe('abc')
  })
})

describe('router guard — protected routes when logged out', () => {
  beforeEach(() => {
    setupAuth({ user: null })
  })

  it('redirects /private to /login with redirect=/private', async () => {
    const r = await pushAndSettle('/private')
    expect(r.path).toBe('/login')
    expect(r.query.redirect).toBe('/private')
  })

  it('redirects /chat to /login with redirect=/chat', async () => {
    const r = await pushAndSettle('/chat')
    expect(r.path).toBe('/login')
    expect(r.query.redirect).toBe('/chat')
  })

  it('redirects /wiki to /login with redirect=/wiki', async () => {
    const r = await pushAndSettle('/wiki')
    expect(r.path).toBe('/login')
    expect(r.query.redirect).toBe('/wiki')
  })

  it('redirects /change-password to /login (auth-only route)', async () => {
    const r = await pushAndSettle('/change-password')
    expect(r.path).toBe('/login')
    expect(r.query.redirect).toBe('/change-password')
  })

  it('redirects /me to /login (auth-only route)', async () => {
    const r = await pushAndSettle('/me')
    expect(r.path).toBe('/login')
    expect(r.query.redirect).toBe('/me')
  })
})

describe('router guard — root redirect', () => {
  it('/ redirects to /chat (NOT /wiki) — multi-user-auth-core landing change', async () => {
    setupAuth({ user: fakeUser() })
    const r = await pushAndSettle('/')
    // The static redirect rule sends / to /chat regardless of auth state;
    // an authenticated user lands on /chat. (The logged-out half of this
    // behavior — that the guard kicks in once on /chat — is already
    // covered by the "/chat → /login when logged out" case above.)
    expect(r.path).toBe('/chat')
  })
})

describe('router guard — logged-in user', () => {
  it('member can reach /chat / /wiki / /private / /me', async () => {
    setupAuth({ user: fakeUser({ role: 'member' }) })
    for (const path of ['/chat', '/wiki', '/private', '/me']) {
      const r = await pushAndSettle(path)
      expect(r.path, `should reach ${path}`).toBe(path)
    }
  })

  it('member navigating to /admin/users is redirected to /chat', async () => {
    setupAuth({ user: fakeUser({ role: 'member' }) })
    const r = await pushAndSettle('/admin/users')
    expect(r.path).toBe('/chat')
  })

  it('admin role passes the /admin/ guard (no redirect)', async () => {
    setupAuth({ user: fakeUser({ role: 'admin' }) })
    // /admin/users is not registered in core (lands with admin-ui change),
    // so vue-router resolves it to a no-match record. We assert the guard
    // itself does NOT redirect to /chat — i.e. path stays /admin/users.
    const r = await pushAndSettle('/admin/users')
    expect(r.path).toBe('/admin/users')
  })
})

describe('router guard — /admin/cert (nas-https)', () => {
  beforeEach(async () => {
    // Reset router away from /admin/cert so each test triggers beforeEach freshly.
    await router.push('/login').catch(() => {})
  })

  it('admin reaches /admin/cert', async () => {
    setupAuth({ user: fakeUser({ role: 'admin' }) })
    const r = await pushAndSettle('/admin/cert')
    expect(r.path).toBe('/admin/cert')
  })

  it('member is redirected to /chat', async () => {
    setupAuth({ user: fakeUser({ role: 'member' }) })
    const r = await pushAndSettle('/admin/cert')
    expect(r.path).toBe('/chat')
  })

  it('logged-out is redirected to /login with redirect=/admin/cert', async () => {
    setupAuth({ user: null })
    const r = await pushAndSettle('/admin/cert')
    expect(r.path).toBe('/login')
    expect(r.query.redirect).toBe('/admin/cert')
  })
})

describe('router guard — fetchMe is called when currentUser is null', () => {
  it('fetchMe runs once on first protected navigation', async () => {
    setActivePinia(createPinia())
    const auth = useAuthStore()
    const fetchMe = vi.fn().mockResolvedValue({ data: { user: null } })
    auth._api = { get: fetchMe, post: vi.fn() }

    await pushAndSettle('/private')
    expect(fetchMe).toHaveBeenCalled()
    // /auth/me is the first call the guard triggers
    expect(fetchMe.mock.calls[0][0]).toBe('/auth/me')
  })
})
