/**
 * 3.2 RED — AdminCertView token + text assertions.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../../src/api/index.js', () => ({
  default: { get: vi.fn() },
}))

import api from '../../src/api/index.js'
import AdminCertView from '../../src/views/AdminCertView.vue'

const HEALTHY = {
  hostname: 'python-agent.tail-test.ts.net',
  cert_expiry_iso: '2026-08-14T06:00:00+00:00',
  days_remaining: 90,
  tailscale_status: 'online',
  last_renew_iso: '2026-05-16T06:00:00+00:00',
}
const WARNING = {
  hostname: 'python-agent.tail-test.ts.net',
  cert_expiry_iso: '2026-05-31T00:00:00+00:00',
  days_remaining: 15,
  tailscale_status: 'online',
  last_renew_iso: '2026-05-10T00:00:00+00:00',
}
const OFFLINE = {
  hostname: 'python-agent.tail-test.ts.net',
  cert_expiry_iso: null,
  days_remaining: null,
  tailscale_status: 'offline',
  last_renew_iso: null,
}
const EXPIRED = {
  hostname: 'python-agent.tail-test.ts.net',
  cert_expiry_iso: '2026-05-10T00:00:00+00:00',
  days_remaining: -3,
  tailscale_status: 'online',
  last_renew_iso: '2026-02-10T00:00:00+00:00',
}

async function mountView(data) {
  api.get.mockResolvedValue({ data })
  setActivePinia(createPinia())
  const wrapper = mount(AdminCertView, { global: { plugins: [createPinia()] } })
  await flushPromises()
  return wrapper
}

describe('AdminCertView', () => {
  afterEach(() => vi.clearAllMocks())

  it('card title includes 证书与 Tailscale 状态', async () => {
    const wrapper = await mountView(HEALTHY)
    expect(wrapper.text()).toContain('证书与 Tailscale 状态')
  })

  it('row labels include all four required fields', async () => {
    const wrapper = await mountView(HEALTHY)
    const text = wrapper.text()
    for (const label of ['Tailnet 主机名', '证书到期', 'Tailscale 连接', '上次 renew']) {
      expect(text).toContain(label)
    }
  })

  it('healthy state: header pill mint/green + text 健康', async () => {
    const wrapper = await mountView(HEALTHY)
    const pill = wrapper.find('[data-overall-pill]')
    expect(pill.classes()).toContain('bg-notion-tint-mint')
    expect(pill.classes()).toContain('text-notion-brand-green')
    expect(pill.text()).toBe('健康')
  })

  it('healthy state: days badge has bg-notion-tint-mint', async () => {
    const wrapper = await mountView(HEALTHY)
    const badge = wrapper.find('[data-days-badge]')
    expect(badge.classes()).toContain('bg-notion-tint-mint')
  })

  it('warning state (7-30d): header pill yellow/warning + text 即将到期', async () => {
    const wrapper = await mountView(WARNING)
    const pill = wrapper.find('[data-overall-pill]')
    expect(pill.classes()).toContain('bg-notion-tint-yellow')
    expect(pill.classes()).toContain('text-notion-warning')
    expect(pill.text()).toBe('即将到期')
  })

  it('offline state: header pill rose/error + text 异常', async () => {
    const wrapper = await mountView(OFFLINE)
    const pill = wrapper.find('[data-overall-pill]')
    expect(pill.classes()).toContain('bg-notion-tint-rose')
    expect(pill.classes()).toContain('text-notion-error')
    expect(pill.text()).toBe('异常')
  })

  it('expired cert (negative days, online): header pill rose/error + text 异常', async () => {
    const wrapper = await mountView(EXPIRED)
    const pill = wrapper.find('[data-overall-pill]')
    expect(pill.classes()).toContain('bg-notion-tint-rose')
    expect(pill.classes()).toContain('text-notion-error')
    expect(pill.text()).toBe('异常')
  })

  it('transient poll failure after first success: shows rows + stale-data banner', async () => {
    vi.useFakeTimers()
    // First fetch succeeds.
    api.get.mockResolvedValueOnce({ data: HEALTHY })
    // Second fetch (60s later) fails.
    api.get.mockRejectedValueOnce(new Error('network timeout'))

    setActivePinia(createPinia())
    const wrapper = mount(AdminCertView, { global: { plugins: [createPinia()] } })
    await flushPromises() // first fetch: status=HEALTHY, fetchError=false

    // Advance timer to trigger the interval poll.
    vi.advanceTimersByTime(60_000)
    await flushPromises()

    // Rows should still be visible (stale data preserved).
    expect(wrapper.text()).toContain('Tailnet 主机名')
    // Stale-data banner should appear.
    expect(wrapper.text()).toContain('上次刷新失败')
    // Full-error block should NOT replace the card.
    expect(wrapper.text()).not.toContain('无法获取状态')

    vi.useRealTimers()
  })
})
