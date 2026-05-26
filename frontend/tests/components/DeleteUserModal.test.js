import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useAdminUsersStore } from '../../src/stores/adminUsers.js'
import DeleteUserModal from '../../src/components/DeleteUserModal.vue'

const USER = { id: 'u1', email: 'ex@gmail.com', role: 'member', status: 'disabled' }

function makeAdminUsersStore(pinia, overrides = {}) {
  setActivePinia(pinia)
  const store = useAdminUsersStore()
  store.deleteUser = vi.fn()
  Object.assign(store, overrides)
  return store
}

async function mountModal(user = USER, storeOverrides = {}) {
  const pinia = createPinia()
  makeAdminUsersStore(pinia, storeOverrides)
  const wrapper = mount(DeleteUserModal, {
    global: { plugins: [pinia] },
    props: { modelValue: true, user },
  })
  await wrapper.vm.$nextTick()
  return wrapper
}

describe('DeleteUserModal', () => {
  it('renders heading ⚠ 永久删除用户 with text-notion-error class', async () => {
    const wrapper = await mountModal()
    const heading = wrapper.find('h2, h3, [data-heading]')
    expect(heading.text()).toContain('⚠ 永久删除用户')
    expect(heading.classes().join(' ')).toMatch(/text-notion-error/)
  })

  it('warning box has bg-notion-tint-rose class', async () => {
    const wrapper = await mountModal()
    const box = wrapper.find('[data-warning-box], .bg-notion-tint-rose')
    expect(box.exists()).toBe(true)
    expect(box.classes().join(' ')).toMatch(/bg-notion-tint-rose/)
  })

  it('destructive button has bg-notion-error class', async () => {
    const wrapper = await mountModal()
    const btn = wrapper.findAll('button').find(b => b.classes().join(' ').includes('bg-notion-error'))
    expect(btn).toBeDefined()
    expect(btn.classes().join(' ')).toMatch(/bg-notion-error/)
  })

  it('destructive button is disabled when input is empty', async () => {
    const wrapper = await mountModal()
    const btn = wrapper.findAll('button').find(b => b.classes().join(' ').includes('bg-notion-error'))
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('destructive button is disabled when input does not match local part', async () => {
    const wrapper = await mountModal()
    const input = wrapper.find('input[type="text"], input:not([type="email"])')
    await input.setValue('wrong')
    const btn = wrapper.findAll('button').find(b => b.classes().join(' ').includes('bg-notion-error'))
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('destructive button is enabled when input equals local part of email', async () => {
    const wrapper = await mountModal()
    const input = wrapper.find('input[type="text"], input:not([type="email"])')
    await input.setValue('ex')
    const btn = wrapper.findAll('button').find(b => b.classes().join(' ').includes('bg-notion-error'))
    expect(btn.attributes('disabled')).toBeUndefined()
  })

  it('clicking destructive button calls adminUsers.deleteUser with user id', async () => {
    const deleteUser = vi.fn().mockResolvedValue(undefined)
    const wrapper = await mountModal(USER, { deleteUser })
    const input = wrapper.find('input[type="text"], input:not([type="email"])')
    await input.setValue('ex')
    const btn = wrapper.findAll('button').find(b => b.classes().join(' ').includes('bg-notion-error'))
    await btn.trigger('click')
    expect(deleteUser).toHaveBeenCalledWith('u1')
  })

  it('shows user email in the modal body', async () => {
    const wrapper = await mountModal()
    expect(wrapper.text()).toContain('ex@gmail.com')
  })
})
