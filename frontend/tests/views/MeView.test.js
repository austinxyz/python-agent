/**
 * 3.9 RED — MeView admin section (nas-https).
 */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '../../src/stores/auth.js'
import MeView from '../../src/views/MeView.vue'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

const RouterLinkStub = { template: '<a :href="to"><slot /></a>', props: ['to'] }

function mountMe(role) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const auth = useAuthStore(pinia)
  auth.currentUser = { id: 'u1', email: 'a@b.com', name: 'A', role, picture_url: null }
  return mount(MeView, {
    global: { plugins: [pinia], stubs: { RouterLink: RouterLinkStub } },
  })
}

describe('MeView — admin cert link', () => {
  it('admin sees 证书与 Tailscale 状态 link to /admin/cert', () => {
    const wrapper = mountMe('admin')
    const link = wrapper.find('a[href="/admin/cert"]')
    expect(link.exists()).toBe(true)
    expect(link.text()).toContain('证书与 Tailscale 状态')
  })

  it('member does not see /admin/cert link', () => {
    const wrapper = mountMe('member')
    expect(wrapper.find('a[href="/admin/cert"]').exists()).toBe(false)
  })
})
