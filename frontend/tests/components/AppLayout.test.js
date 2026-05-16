/**
 * AppLayout responsive + Notion design alignment tests.
 * See openspec/changes/mobile-friendly/specs/frontend-scaffold/spec.md.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'

import AppLayout from '../../src/components/AppLayout.vue'
import { useAuthStore } from '../../src/stores/auth.js'

function makeRouter(initial = '/wiki') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/wiki', component: { template: '<div />' } },
      { path: '/ingest', component: { template: '<div />' } },
      { path: '/chat', component: { template: '<div />' } },
      { path: '/private', component: { template: '<div />' } },
    ],
  })
  router.push(initial)
  return router
}

async function mountLayout(initial = '/wiki', { role } = {}) {
  const router = makeRouter(initial)
  await router.isReady()
  const pinia = createPinia()
  const wrapper = mount(AppLayout, { global: { plugins: [router, pinia] } })
  if (role) {
    const auth = useAuthStore(pinia)
    auth.currentUser = { id: 'u1', email: 'a@b.com', name: 'A', role, picture_url: null }
  }
  await wrapper.vm.$nextTick()
  return wrapper
}

describe('AppLayout — responsive shape', () => {
  it('desktop sidebar carries hidden md:flex (or md+ visibility) class', async () => {
    const wrapper = await mountLayout()
    const aside = wrapper.find('aside')
    expect(aside.exists()).toBe(true)
    const cls = aside.classes().join(' ')
    expect(cls).toMatch(/hidden md:flex|md:flex/)
  })

  it('renders bottom tab nav with 5 items (the 5th is 我), only visible at md-', async () => {
    // multi-user-auth-core: 5th tab "我" added for user/profile menu.
    const wrapper = await mountLayout()
    const bottomNav = wrapper.find('[data-bottom-tabs]')
    expect(bottomNav.exists()).toBe(true)
    const cls = bottomNav.classes().join(' ')
    expect(cls).toMatch(/md:hidden/)
    const tabs = bottomNav.findAll('a')
    expect(tabs.length).toBe(5)
    const text = bottomNav.text()
    for (const label of ['知识库', '摄入', '对话', '私有', '我']) {
      expect(text).toContain(label)
    }
  })

  it('bottom tab nav uses safe-area-inset-bottom padding', async () => {
    const wrapper = await mountLayout()
    const bottomNav = wrapper.find('[data-bottom-tabs]')
    // Either an inline style or a Tailwind class encoding env(safe-area-inset-bottom).
    const styleAttr = bottomNav.attributes('style') || ''
    const cls = bottomNav.classes().join(' ')
    const hasSafeArea =
      /safe-area-inset-bottom/.test(styleAttr) ||
      /pb-safe|pb-\[env\(safe-area-inset-bottom\)\]/.test(cls)
    expect(hasSafeArea, 'bottom tabs must clear the iPhone home indicator').toBe(true)
  })

  it('active state styling is consistent across sidebar and bottom tabs', async () => {
    const wrapper = await mountLayout('/chat')
    const allLinks = wrapper.findAll('a')
    const activeLinks = allLinks.filter(
      (a) => a.attributes('aria-current') === 'page',
    )
    // Both desktop sidebar and bottom tab render an active /chat link.
    expect(activeLinks.length).toBeGreaterThanOrEqual(1)
    for (const link of activeLinks) {
      const cls = link.classes().join(' ')
      expect(cls).toMatch(/bg-notion-tint-lavender/)
      expect(cls).toMatch(/text-notion-brand-purple-800/)
    }
  })
})

describe('AppLayout — admin nav slot (nas-https)', () => {
  it('admin sees 证书与 Tailscale 状态 link to /admin/cert in sidebar', async () => {
    const wrapper = await mountLayout('/wiki', { role: 'admin' })
    const link = wrapper.find('a[href="/admin/cert"]')
    expect(link.exists()).toBe(true)
    expect(link.text()).toContain('证书与 Tailscale 状态')
  })

  it('member does not see /admin/cert link', async () => {
    const wrapper = await mountLayout('/wiki', { role: 'member' })
    expect(wrapper.find('a[href="/admin/cert"]').exists()).toBe(false)
  })
})

describe('AppLayout — Notion design alignment', () => {
  it('logo no longer uses the legacy blue→purple gradient', async () => {
    const wrapper = await mountLayout()
    const html = wrapper.html()
    expect(html).not.toMatch(/from-blue-\d+/)
    expect(html).not.toMatch(/to-purple-\d+/)
  })

  it('active nav item uses Notion lavender/purple tokens, not the legacy primary/10', async () => {
    const wrapper = await mountLayout('/chat')
    // Find the active <router-link> for /chat (has chat icon + label).
    const links = wrapper.findAll('a, [role="link"]')
    const active = links.find((link) =>
      link.attributes('aria-current') === 'page' || link.classes().some((c) => c.includes('lavender')),
    )
    expect(active, 'expected at least one active link with Notion active styling').toBeTruthy()
    const cls = active.classes().join(' ')
    expect(cls).toMatch(/bg-notion-tint-lavender/)
    expect(cls).toMatch(/text-notion-brand-purple-800/)
    // No leftover legacy active-state classes.
    expect(cls).not.toMatch(/bg-primary\/10/)
  })

  it('still renders the four nav items', async () => {
    const wrapper = await mountLayout()
    const text = wrapper.text()
    expect(text).toContain('知识库')
    expect(text).toContain('摄入')
    expect(text).toContain('对话')
    expect(text).toContain('私有')
  })
})
