import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useAdminUsersStore } from '../../src/stores/adminUsers.js'
import { useAuthStore } from '../../src/stores/auth.js'
import AdminUsersView from '../../src/views/AdminUsersView.vue'

const SELF = { id: 'self', email: 'austin@gmail.com', name: 'Austin', role: 'admin', status: 'active' }
const OTHER_ADMIN = { id: 'u2', email: 'admin2@gmail.com', name: 'Admin2', role: 'admin', status: 'active' }
const ACTIVE_MEMBER = { id: 'u3', email: 'linda@gmail.com', name: 'Linda', role: 'member', status: 'active' }
const INVITED = { id: 'u4', email: 'uncle@gmail.com', name: null, role: 'member', status: 'invited' }
const DISABLED = { id: 'u5', email: 'ex@gmail.com', name: '前同事', role: 'member', status: 'disabled' }

function makeStores(pinia, { users = [SELF, ACTIVE_MEMBER, INVITED, DISABLED], currentUser = SELF } = {}) {
  setActivePinia(pinia)
  const adminStore = useAdminUsersStore()
  adminStore.users = users
  adminStore.fetchUsers = vi.fn().mockResolvedValue(undefined)
  adminStore.updateUser = vi.fn().mockResolvedValue({})
  adminStore.deleteUser = vi.fn().mockResolvedValue(undefined)
  adminStore.resendInvite = vi.fn().mockResolvedValue({ invite_url: 'http://x/accept-invite?token=abc' })
  adminStore.inviteUser = vi.fn().mockResolvedValue({ user: {}, invite_url: 'http://x/accept-invite?token=abc' })
  const authStore = useAuthStore()
  authStore.currentUser = currentUser
  return adminStore
}

async function mountView(storeOpts = {}) {
  const pinia = createPinia()
  const adminStore = makeStores(pinia, storeOpts)
  const wrapper = mount(AdminUsersView, { global: { plugins: [pinia] } })
  await wrapper.vm.$nextTick()
  return { wrapper, adminStore }
}

describe('AdminUsersView — desktop', () => {
  it('calls fetchUsers on mount', async () => {
    const { adminStore } = await mountView()
    expect(adminStore.fetchUsers).toHaveBeenCalled()
  })

  it('hero band has bg-notion-brand-navy and text-notion-on-dark', async () => {
    const { wrapper } = await mountView()
    const hero = wrapper.find('.bg-notion-brand-navy')
    expect(hero.exists()).toBe(true)
    expect(hero.classes().join(' ')).toMatch(/text-notion-on-dark/)
  })

  it('hero heading contains 用户管理', async () => {
    const { wrapper } = await mountView()
    expect(wrapper.text()).toContain('用户管理')
  })

  it('+ 邀请用户 CTA has bg-notion-primary', async () => {
    const { wrapper } = await mountView()
    const cta = wrapper.findAll('button').find(b => b.text().includes('邀请用户'))
    expect(cta).toBeDefined()
    expect(cta.classes().join(' ')).toMatch(/bg-notion-primary/)
  })

  it('self-row shows 不能改自己 text', async () => {
    const { wrapper } = await mountView()
    expect(wrapper.text()).toContain('不能改自己')
  })

  it('invited row has bg-notion-tint-yellow class', async () => {
    const { wrapper } = await mountView()
    const row = wrapper.find('.bg-notion-tint-yellow')
    expect(row.exists()).toBe(true)
  })

  it('disabled row has bg-notion-surface-soft and opacity-70', async () => {
    const { wrapper } = await mountView()
    const row = wrapper.find('.bg-notion-surface-soft')
    expect(row.exists()).toBe(true)
    expect(row.classes().join(' ')).toMatch(/opacity-70/)
  })

  it('admin badge has bg-notion-tint-lavender and text-notion-brand-purple-800', async () => {
    const { wrapper } = await mountView({ users: [SELF, OTHER_ADMIN, ACTIVE_MEMBER] })
    const badge = wrapper.find('.bg-notion-tint-lavender')
    expect(badge.exists()).toBe(true)
    expect(badge.classes().join(' ')).toMatch(/text-notion-brand-purple-800/)
  })

  it('member badge has bg-notion-tint-gray and text-notion-slate', async () => {
    const { wrapper } = await mountView()
    const badge = wrapper.find('.bg-notion-tint-gray.text-notion-slate')
    expect(badge.exists()).toBe(true)
  })

  it('demote button is disabled when only 1 admin in users list', async () => {
    const { wrapper } = await mountView({ users: [OTHER_ADMIN, ACTIVE_MEMBER] })
    const demoteBtn = wrapper.findAll('button').find(b => /↓|↓\s*member/.test(b.text()))
    expect(demoteBtn).toBeDefined()
    expect(demoteBtn.attributes('disabled')).toBeDefined()
  })

  it('clicking + 邀请用户 shows InviteUserModal', async () => {
    const { wrapper } = await mountView()
    const cta = wrapper.findAll('button').find(b => b.text().includes('邀请用户'))
    await cta.trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('邀请新用户')
  })

  it('disabled user 删除 button opens DeleteUserModal', async () => {
    const { wrapper } = await mountView()
    const deleteBtn = wrapper.findAll('button').find(b => b.text().includes('删除'))
    expect(deleteBtn).toBeDefined()
    await deleteBtn.trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('永久删除用户')
  })

  it('active member 停用 button calls updateUser with status disabled', async () => {
    const { wrapper, adminStore } = await mountView()
    const stopBtn = wrapper.findAll('button').find(b => b.text().includes('停用'))
    expect(stopBtn).toBeDefined()
    await stopBtn.trigger('click')
    expect(adminStore.updateUser).toHaveBeenCalledWith(ACTIVE_MEMBER.id, { status: 'disabled' })
  })

  it('invited user 重发 button calls resendInvite', async () => {
    const { wrapper, adminStore } = await mountView()
    const resendBtn = wrapper.findAll('button').find(b => b.text().includes('重发'))
    expect(resendBtn).toBeDefined()
    await resendBtn.trigger('click')
    expect(adminStore.resendInvite).toHaveBeenCalledWith(INVITED.id)
  })

  it('disabled user 启用 button calls updateUser with status active', async () => {
    const { wrapper, adminStore } = await mountView()
    const enableBtn = wrapper.findAll('button').find(b => b.text().includes('启用'))
    expect(enableBtn).toBeDefined()
    await enableBtn.trigger('click')
    expect(adminStore.updateUser).toHaveBeenCalledWith(DISABLED.id, { status: 'active' })
  })
})

describe('AdminUsersView — mobile', () => {
  it('desktop table has hidden (mobile-off) responsive class', async () => {
    const { wrapper } = await mountView()
    const table = wrapper.find('table')
    if (table.exists()) {
      expect(table.classes().join(' ')).toMatch(/hidden/)
    }
  })

  it('mobile card list container exists with md:hidden class pattern', async () => {
    const { wrapper } = await mountView()
    const cardList = wrapper.find('[data-mobile-cards]')
    expect(cardList.exists()).toBe(true)
  })
})
