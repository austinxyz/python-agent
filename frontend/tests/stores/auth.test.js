import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '../../src/stores/auth.js'

function makeStore(apiBehavior = {}) {
  setActivePinia(createPinia())
  const store = useAuthStore()
  store._api = {
    get: vi.fn().mockImplementation((path) => {
      if (path === '/auth/me' && apiBehavior.me) return apiBehavior.me()
      if (path === '/auth/config' && apiBehavior.config) return apiBehavior.config()
      if (path.startsWith('/auth/invite/') && apiBehavior.invite) return apiBehavior.invite()
      return Promise.resolve({ data: {} })
    }),
    post: vi.fn().mockImplementation((path, body) => {
      if (path === '/auth/login' && apiBehavior.login) return apiBehavior.login(body)
      if (path === '/auth/login/google' && apiBehavior.loginGoogle) return apiBehavior.loginGoogle(body)
      if (path === '/auth/accept-invite' && apiBehavior.acceptInvite) return apiBehavior.acceptInvite(body)
      if (path === '/auth/change-password' && apiBehavior.changePassword) return apiBehavior.changePassword(body)
      if (path === '/auth/logout' && apiBehavior.logout) return apiBehavior.logout()
      return Promise.resolve({ data: {} })
    }),
  }
  return store
}

describe('useAuthStore', () => {
  it('starts with currentUser=null and config=null', () => {
    const store = makeStore()
    expect(store.currentUser).toBeNull()
    expect(store.config).toBeNull()
  })

  it('fetchMe populates currentUser on 200', async () => {
    const fakeUser = { id: 'u1', email: 'a@b.com', name: 'A', role: 'admin', picture_url: null }
    const store = makeStore({
      me: () => Promise.resolve({ data: { user: fakeUser } }),
    })
    await store.fetchMe()
    expect(store.currentUser).toEqual(fakeUser)
  })

  it('fetchMe sets currentUser to null on 401', async () => {
    const err = { response: { status: 401 } }
    const store = makeStore({
      me: () => Promise.reject(err),
    })
    await store.fetchMe()
    expect(store.currentUser).toBeNull()
  })

  it('fetchConfig populates config', async () => {
    const store = makeStore({
      config: () => Promise.resolve({ data: { has_google: true, google_client_id: 'abc' } }),
    })
    await store.fetchConfig()
    expect(store.config).toEqual({ has_google: true, google_client_id: 'abc' })
  })

  it('loginWithPassword posts and stores user on success', async () => {
    const fakeUser = { id: 'u1', email: 'a@b.com', role: 'member', name: 'A', picture_url: null }
    const store = makeStore({
      login: () => Promise.resolve({ data: { user: fakeUser } }),
    })
    await store.loginWithPassword('a@b.com', 'pw12345')
    expect(store._api.post).toHaveBeenCalledWith('/auth/login', { email: 'a@b.com', password: 'pw12345' })
    expect(store.currentUser).toEqual(fakeUser)
  })

  it('loginWithPassword surfaces error on 401', async () => {
    const store = makeStore({
      login: () => Promise.reject({ response: { status: 401, data: { error: 'invalid credentials' } } }),
    })
    await expect(store.loginWithPassword('x', 'y')).rejects.toMatchObject({ response: { status: 401 } })
    expect(store.currentUser).toBeNull()
  })

  it('loginWithGoogle posts id_token and stores user', async () => {
    const fakeUser = { id: 'u2', email: 'g@b.com', role: 'member', name: 'G', picture_url: 'http://pic' }
    const store = makeStore({
      loginGoogle: () => Promise.resolve({ data: { user: fakeUser } }),
    })
    await store.loginWithGoogle('fake-id-token')
    expect(store._api.post).toHaveBeenCalledWith('/auth/login/google', { id_token: 'fake-id-token' })
    expect(store.currentUser).toEqual(fakeUser)
  })

  it('logout clears currentUser', async () => {
    const fakeUser = { id: 'u1', email: 'a@b.com', role: 'admin', name: 'A', picture_url: null }
    const store = makeStore({
      me: () => Promise.resolve({ data: { user: fakeUser } }),
      logout: () => Promise.resolve({ status: 204 }),
    })
    await store.fetchMe()
    expect(store.currentUser).not.toBeNull()
    await store.logout()
    expect(store.currentUser).toBeNull()
  })

  it('acceptInvite posts token + password', async () => {
    const fakeUser = { id: 'u3', email: 'new@b.com', role: 'member', name: null, picture_url: null }
    const store = makeStore({
      acceptInvite: () => Promise.resolve({ data: { user: fakeUser } }),
    })
    await store.acceptInvite('tok', 'newpass1234')
    expect(store._api.post).toHaveBeenCalledWith('/auth/accept-invite', { token: 'tok', password: 'newpass1234' })
    expect(store.currentUser).toEqual(fakeUser)
  })

  it('changePassword posts old + new', async () => {
    const store = makeStore({
      changePassword: () => Promise.resolve({ status: 200 }),
    })
    await store.changePassword('old12345', 'new54321')
    expect(store._api.post).toHaveBeenCalledWith('/auth/change-password', {
      old_password: 'old12345',
      new_password: 'new54321',
    })
  })

  it('fetchInvite fetches token info', async () => {
    const store = makeStore({
      invite: () =>
        Promise.resolve({
          data: { user: { email: 'x@y.com' }, valid: true, expired: false, inviter: { email: 'a@b.com' } },
        }),
    })
    const res = await store.fetchInvite('tok-xyz')
    expect(res.valid).toBe(true)
    expect(res.user.email).toBe('x@y.com')
  })
})
