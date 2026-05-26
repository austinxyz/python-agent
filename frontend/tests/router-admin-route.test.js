import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import router from '../src/router/index.js'
import { useAuthStore } from '../src/stores/auth.js'

function setupAuth({ user = null } = {}) {
  setActivePinia(createPinia())
  const auth = useAuthStore()
  auth._api = {
    get: vi.fn().mockResolvedValue({ data: { user } }),
    post: vi.fn().mockResolvedValue({ data: {} }),
  }
  if (user) auth.currentUser = user
  return auth
}

const adminUser = { id: 'u1', email: 'a@b.com', name: 'A', role: 'admin', picture_url: null }
const memberUser = { id: 'u2', email: 'b@b.com', name: 'B', role: 'member', picture_url: null }

async function push(target) {
  await router.push(target).catch(() => {})
  await router.isReady()
  return router.currentRoute.value
}

describe('/admin/users route registration and guard', () => {
  beforeEach(async () => {
    await router.push('/login').catch(() => {})
  })


  it('route /admin/users is registered with meta.requiresAdmin: true', () => {
    const route = router.getRoutes().find(r => r.path === '/admin/users')
    expect(route, '/admin/users route must be registered').toBeDefined()
    expect(route.meta.requiresAdmin).toBe(true)
  })

  it('admin can navigate to /admin/users', async () => {
    setupAuth({ user: adminUser })
    const r = await push('/admin/users')
    expect(r.path).toBe('/admin/users')
  })

  it('member navigating to /admin/users is redirected to /chat', async () => {
    setupAuth({ user: memberUser })
    const r = await push('/admin/users')
    expect(r.path).toBe('/chat')
  })

  it('unauthenticated navigating to /admin/users redirected to /login with redirect query', async () => {
    setupAuth({ user: null })
    const r = await push('/admin/users')
    expect(r.path).toBe('/login')
    expect(r.query.redirect).toBe('/admin/users')
  })
})
