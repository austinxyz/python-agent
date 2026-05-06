import { describe, it, expect } from 'vitest'
import { DOMAINS } from '@/constants/domains.js'

describe('DOMAINS constant', () => {
  it('has exactly 10 items', () => {
    expect(DOMAINS).toHaveLength(10)
  })

  it('last item is 其他', () => {
    expect(DOMAINS[DOMAINS.length - 1]).toBe('其他')
  })

  it('all items are non-empty strings', () => {
    for (const d of DOMAINS) {
      expect(typeof d).toBe('string')
      expect(d.length).toBeGreaterThan(0)
    }
  })
})
