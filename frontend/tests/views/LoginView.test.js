/**
 * LoginView — Google Sign-In integration tests.
 * Tests the handleGoogleCredential callback and onGoogleSignIn guard.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'

vi.mock('../../src/api/index.js', () => ({
  default: { get: vi.fn(), post: vi.fn() },
}))

import api from '../../src/api/index.js'
import LoginView from '../../src/views/LoginView.vue'

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', component: LoginView },
      { path: '/chat', component: { template: '<div>chat</div>' } },
    ],
  })
}

const CONFIG_WITH_GOOGLE = { has_google: true, google_client_id: 'test-client-id.apps.googleusercontent.com' }

async function mountLogin({ config = CONFIG_WITH_GOOGLE, googleReady = true } = {}) {
  api.get.mockResolvedValue({ data: config })
  setActivePinia(createPinia())
  const router = makeRouter()
  await router.push('/login')

  if (googleReady) {
    window.google = {
      accounts: {
        id: {
          initialize: vi.fn(),
          prompt: vi.fn(),
        },
      },
    }
  } else {
    delete window.google
  }

  const wrapper = mount(LoginView, {
    global: { plugins: [createPinia(), router] },
  })
  await flushPromises()
  return { wrapper, router }
}

describe('LoginView — Google Sign-In', () => {
  afterEach(() => {
    vi.clearAllMocks()
    delete window.google
  })

  it('shows Google button when config.has_google is true and protocol is http (localhost)', async () => {
    const { wrapper } = await mountLogin()
    expect(wrapper.find('[data-google-signin]').exists()).toBe(true)
  })

  it('calls google.accounts.id.prompt() when GSI is ready and button clicked', async () => {
    const { wrapper } = await mountLogin({ googleReady: true })
    await wrapper.find('[data-google-signin]').trigger('click')
    expect(window.google.accounts.id.prompt).toHaveBeenCalled()
  })

  it('shows loading message when GSI not ready and button clicked', async () => {
    const { wrapper } = await mountLogin({ googleReady: false })
    await wrapper.find('[data-google-signin]').trigger('click')
    expect(wrapper.text()).toContain('Google 登录加载中')
  })

  it('loginWithGoogle called and redirects to /chat on valid credential', async () => {
    api.post.mockResolvedValue({ data: { id: 'u1', email: 'a@g.com', role: 'admin' } })
    const { wrapper, router } = await mountLogin({ googleReady: true })

    // Simulate GSI callback firing (as if user selected their Google account)
    const initCall = window.google.accounts.id.initialize.mock.calls[0]?.[0]
    expect(initCall).toBeDefined()
    const callback = initCall.callback
    await callback({ credential: 'fake-id-token' })
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/auth/login/google', { id_token: 'fake-id-token' })
    expect(router.currentRoute.value.path).toBe('/chat')
  })

  it('shows error when loginWithGoogle fails', async () => {
    api.post.mockRejectedValue({ response: { data: { error: 'google account mismatch' } } })
    const { wrapper } = await mountLogin({ googleReady: true })

    const initCall = window.google.accounts.id.initialize.mock.calls[0]?.[0]
    const callback = initCall.callback
    await callback({ credential: 'bad-token' })
    await flushPromises()

    expect(wrapper.text()).toContain('google account mismatch')
  })
})
