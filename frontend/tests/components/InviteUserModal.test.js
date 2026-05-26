import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useAdminUsersStore } from '../../src/stores/adminUsers.js'
import InviteUserModal from '../../src/components/InviteUserModal.vue'

function makeAdminUsersStore(pinia, overrides = {}) {
  setActivePinia(pinia)
  const store = useAdminUsersStore()
  store.inviteUser = vi.fn()
  store.resendInvite = vi.fn()
  store.updateUser = vi.fn()
  Object.assign(store, overrides)
  return store
}

async function mountModal(storeOverrides = {}) {
  const pinia = createPinia()
  makeAdminUsersStore(pinia, storeOverrides)
  const wrapper = mount(InviteUserModal, {
    global: { plugins: [pinia] },
    props: { modelValue: true },
  })
  await wrapper.vm.$nextTick()
  return wrapper
}

describe('InviteUserModal', () => {
  it('renders heading text 邀请新用户', async () => {
    const wrapper = await mountModal()
    expect(wrapper.text()).toContain('邀请新用户')
  })

  it('form submission calls adminUsers.inviteUser with email and role', async () => {
    const inviteUser = vi.fn().mockResolvedValue({ user: { id: 'u1' }, invite_url: 'http://x/accept-invite?token=abc' })
    const wrapper = await mountModal({ inviteUser })
    const emailInput = wrapper.find('input[type="email"], input[name="email"]')
    await emailInput.setValue('test@example.com')
    await wrapper.find('form').trigger('submit')
    expect(inviteUser).toHaveBeenCalledWith('test@example.com', expect.any(String))
  })

  it('success state shows ✓ 邀请已生成 heading', async () => {
    const inviteUser = vi.fn().mockResolvedValue({
      user: { id: 'u1' },
      invite_url: 'http://localhost/accept-invite?token=abc',
    })
    const wrapper = await mountModal({ inviteUser })
    await wrapper.find('input[type="email"], input[name="email"]').setValue('test@example.com')
    await wrapper.find('form').trigger('submit')
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toMatch(/✓ 邀请已生成/)
  })

  it('success state shows invite_url in code block and copy button', async () => {
    const inviteUser = vi.fn().mockResolvedValue({
      user: { id: 'u1' },
      invite_url: 'http://localhost/accept-invite?token=abc',
    })
    const wrapper = await mountModal({ inviteUser })
    await wrapper.find('input[type="email"], input[name="email"]').setValue('test@example.com')
    await wrapper.find('form').trigger('submit')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('code').exists()).toBe(true)
    const copyBtn = wrapper.find('[data-copy-btn]')
    expect(copyBtn.exists()).toBe(true)
    expect(copyBtn.classes().join(' ')).toMatch(/bg-notion-primary/)
  })

  it('success state shows 7 天后过期 hint text', async () => {
    const inviteUser = vi.fn().mockResolvedValue({
      user: { id: 'u1' },
      invite_url: 'http://localhost/accept-invite?token=abc',
    })
    const wrapper = await mountModal({ inviteUser })
    await wrapper.find('input[type="email"], input[name="email"]').setValue('test@example.com')
    await wrapper.find('form').trigger('submit')
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('7 天后过期')
  })

  it('409 active: shows disabled button 已激活，无需邀请', async () => {
    const inviteUser = vi.fn().mockResolvedValue({
      conflict: { id: 'u2', email: 'e@e.com', status: 'active', role: 'member' },
    })
    const wrapper = await mountModal({ inviteUser })
    await wrapper.find('input[type="email"], input[name="email"]').setValue('e@e.com')
    await wrapper.find('form').trigger('submit')
    await wrapper.vm.$nextTick()
    const btn = wrapper.findAll('button').find(b => b.text().includes('已激活'))
    expect(btn).toBeDefined()
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('409 invited: shows 重发邀请 button that calls resendInvite', async () => {
    const resendInvite = vi.fn().mockResolvedValue({ invite_url: 'http://x/accept-invite?token=new' })
    const inviteUser = vi.fn().mockResolvedValue({
      conflict: { id: 'u3', email: 'f@f.com', status: 'invited', role: 'member' },
    })
    const wrapper = await mountModal({ inviteUser, resendInvite })
    await wrapper.find('input[type="email"], input[name="email"]').setValue('f@f.com')
    await wrapper.find('form').trigger('submit')
    await wrapper.vm.$nextTick()
    const btn = wrapper.findAll('button').find(b => b.text().includes('重发邀请'))
    expect(btn).toBeDefined()
    await btn.trigger('click')
    expect(resendInvite).toHaveBeenCalledWith('u3')
  })

  it('409 disabled: shows 重新启用 button that calls updateUser', async () => {
    const updateUser = vi.fn().mockResolvedValue({ status: 'active' })
    const inviteUser = vi.fn().mockResolvedValue({
      conflict: { id: 'u4', email: 'g@g.com', status: 'disabled', role: 'member' },
    })
    const wrapper = await mountModal({ inviteUser, updateUser })
    await wrapper.find('input[type="email"], input[name="email"]').setValue('g@g.com')
    await wrapper.find('form').trigger('submit')
    await wrapper.vm.$nextTick()
    const btn = wrapper.findAll('button').find(b => b.text().includes('重新启用'))
    expect(btn).toBeDefined()
    await btn.trigger('click')
    expect(updateUser).toHaveBeenCalledWith('u4', { status: 'active' })
  })
})
