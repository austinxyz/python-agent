import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAdminUsersStore } from '../../src/stores/adminUsers.js'

const USER_A = { id: 'u1', email: 'a@b.com', role: 'admin', status: 'active' }
const USER_B = { id: 'u2', email: 'b@b.com', role: 'member', status: 'invited' }

function makeStore(apiBehavior = {}) {
  setActivePinia(createPinia())
  const store = useAdminUsersStore()
  store._api = {
    get: vi.fn().mockImplementation((path) => {
      if (path === '/admin/users' && apiBehavior.list) return apiBehavior.list()
      return Promise.resolve({ data: [] })
    }),
    post: vi.fn().mockImplementation((path, body) => {
      if (path === '/admin/users' && apiBehavior.invite) return apiBehavior.invite(body)
      if (path.match(/\/admin\/users\/.*\/resend-invite/) && apiBehavior.resend) return apiBehavior.resend()
      return Promise.resolve({ data: {} })
    }),
    patch: vi.fn().mockImplementation((path, body) => {
      if (path.startsWith('/admin/users/') && apiBehavior.patch) return apiBehavior.patch(path, body)
      return Promise.resolve({ data: {} })
    }),
    delete: vi.fn().mockImplementation((path) => {
      if (path.startsWith('/admin/users/') && apiBehavior.del) return apiBehavior.del(path)
      return Promise.resolve({ data: {} })
    }),
  }
  return store
}

describe('useAdminUsersStore', () => {
  it('starts with empty users array and null error', () => {
    const store = makeStore()
    expect(store.users).toEqual([])
    expect(store.error).toBeNull()
  })

  it('fetchUsers populates store.users from GET /admin/users', async () => {
    const store = makeStore({
      list: () => Promise.resolve({ data: [USER_A, USER_B] }),
    })
    await store.fetchUsers()
    expect(store._api.get).toHaveBeenCalledWith('/admin/users')
    expect(store.users).toEqual([USER_A, USER_B])
  })

  it('inviteUser posts to /admin/users and pushes user into store.users on success', async () => {
    const newUser = { id: 'u3', email: 'c@b.com', role: 'member', status: 'invited' }
    const store = makeStore({
      invite: () => Promise.resolve({ data: { user: newUser, invite_url: 'http://localhost/accept-invite?token=abc' } }),
    })
    store.users = [USER_A]
    await store.inviteUser('c@b.com', 'member')
    expect(store._api.post).toHaveBeenCalledWith('/admin/users', { email: 'c@b.com', role: 'member' })
    expect(store.users).toContainEqual(newUser)
  })

  it('inviteUser returns {conflict: existing} on 409, does not throw, store.error stays null', async () => {
    const existing = { id: 'u2', email: 'b@b.com', role: 'member', status: 'active' }
    const err = { response: { status: 409, data: { error: 'user already exists', existing } } }
    const store = makeStore({
      invite: () => Promise.reject(err),
    })
    const result = await store.inviteUser('b@b.com', 'member')
    expect(result).toEqual({ conflict: existing })
    expect(store.error).toBeNull()
  })

  it('updateUser patches /admin/users/:id and updates row in store.users in place', async () => {
    const updated = { ...USER_B, status: 'disabled' }
    const store = makeStore({
      patch: () => Promise.resolve({ data: updated }),
    })
    store.users = [USER_A, USER_B]
    await store.updateUser('u2', { status: 'disabled' })
    expect(store._api.patch).toHaveBeenCalledWith('/admin/users/u2', { status: 'disabled' })
    const row = store.users.find(u => u.id === 'u2')
    expect(row.status).toBe('disabled')
  })

  it('deleteUser calls DELETE /admin/users/:id and removes user from store.users', async () => {
    const store = makeStore({
      del: () => Promise.resolve({ data: {} }),
    })
    store.users = [USER_A, USER_B]
    await store.deleteUser('u2')
    expect(store._api.delete).toHaveBeenCalledWith('/admin/users/u2')
    expect(store.users.find(u => u.id === 'u2')).toBeUndefined()
  })

  it('resendInvite posts to /admin/users/:id/resend-invite and returns invite_url', async () => {
    const store = makeStore({
      resend: () => Promise.resolve({ data: { invite_url: 'http://localhost/accept-invite?token=xyz' } }),
    })
    const result = await store.resendInvite('u2')
    expect(store._api.post).toHaveBeenCalledWith('/admin/users/u2/resend-invite', undefined)
    expect(result).toHaveProperty('invite_url')
  })
})
