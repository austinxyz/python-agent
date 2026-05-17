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
      accounts: { id: { initialize: vi.fn(), renderButton: vi.fn(), prompt: vi.fn() } },
    }
    // Pre-inject the script tag so loadGsi() calls initGsi() immediately
    // (happy-dom never fires onload for external scripts).
    if (!document.getElementById('gsi-script')) {
      const s = document.createElement('script')
      s.id = 'gsi-script'
      document.head.appendChild(s)
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
    document.getElementById('gsi-script')?.remove()
  })

  it('shows Google button when config.has_google is true and protocol is http (localhost)', async () => {
    const { wrapper } = await mountLogin()
    expect(wrapper.find('[data-google-signin]').exists()).toBe(true)
  })

  it('calls google.accounts.id.renderButton() when GSI is ready', async () => {
    await mountLogin({ googleReady: true })
    expect(window.google.accounts.id.renderButton).toHaveBeenCalled()
  })

  it('shows loading text when GSI not ready', async () => {
    const { wrapper } = await mountLogin({ googleReady: false })
    const btn = wrapper.find('[data-google-signin]')
    expect(btn.text()).toContain('Google 登录加载中')
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
