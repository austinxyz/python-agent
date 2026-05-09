/**
 * AppLayout responsive + Notion design alignment tests.
 * See openspec/changes/mobile-friendly/specs/frontend-scaffold/spec.md.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'

import AppLayout from '../../src/components/AppLayout.vue'

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

async function mountLayout(initial = '/wiki') {
  const router = makeRouter(initial)
  await router.isReady()
  return mount(AppLayout, {
    global: { plugins: [router, createPinia()] },
  })
}

describe('AppLayout — responsive shape', () => {
  it('desktop sidebar carries hidden md:flex (or md+ visibility) class', async () => {
    const wrapper = await mountLayout()
    const aside = wrapper.find('aside')
    expect(aside.exists()).toBe(true)
    const cls = aside.classes().join(' ')
    expect(cls).toMatch(/hidden md:flex|md:flex/)
  })

  it('renders bottom tab nav with 4 items, only visible at md-', async () => {
    const wrapper = await mountLayout()
    const bottomNav = wrapper.find('[data-bottom-tabs]')
    expect(bottomNav.exists()).toBe(true)
    const cls = bottomNav.classes().join(' ')
    // Bottom tabs are mobile-only: visible at md-, hidden at md+.
    expect(cls).toMatch(/md:hidden/)
    // 4 tab items.
    const tabs = bottomNav.findAll('a')
    expect(tabs.length).toBe(4)
    const text = bottomNav.text()
    for (const label of ['知识库', '摄入', '对话', '私有']) {
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
