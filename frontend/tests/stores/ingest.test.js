import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useIngestStore } from '../../src/stores/ingest.js'

beforeEach(() => {
  setActivePinia(createPinia())
})

// ---------------------------------------------------------------------------
// task 7.1 — destination state
// ---------------------------------------------------------------------------

describe('destination', () => {
  it('defaults to "knowledge"', () => {
    const store = useIngestStore()
    expect(store.destination).toBe('knowledge')
  })

  it('setDestination("private") updates destination', () => {
    const store = useIngestStore()
    store.setDestination('private')
    expect(store.destination).toBe('private')
  })
})

// ---------------------------------------------------------------------------
// task 7.2 — addJob / updateJob
// ---------------------------------------------------------------------------

describe('addJob', () => {
  it('appends a running job entry with all required fields', () => {
    const store = useIngestStore()
    store.addJob('abc', 'budget.pdf')
    expect(store.jobs).toHaveLength(1)
    expect(store.jobs[0]).toEqual({
      job_id: 'abc',
      label: 'budget.pdf',
      status: 'running',
      chunk_count: null,
      error: null,
    })
  })

  it('appending two jobs preserves order', () => {
    const store = useIngestStore()
    store.addJob('id-1', 'a.pdf')
    store.addJob('id-2', 'b.pdf')
    expect(store.jobs[0].job_id).toBe('id-1')
    expect(store.jobs[1].job_id).toBe('id-2')
  })
})

describe('updateJob', () => {
  it('patches the matching entry by job_id', () => {
    const store = useIngestStore()
    store.addJob('abc', 'budget.pdf')
    store.updateJob('abc', { status: 'completed', chunk_count: 8 })
    expect(store.jobs[0].status).toBe('completed')
    expect(store.jobs[0].chunk_count).toBe(8)
    expect(store.jobs[0].label).toBe('budget.pdf')
  })

  it('does not mutate other jobs when patching one', () => {
    const store = useIngestStore()
    store.addJob('id-1', 'a.pdf')
    store.addJob('id-2', 'b.pdf')
    store.updateJob('id-1', { status: 'completed', chunk_count: 3 })
    expect(store.jobs[1].status).toBe('running')
  })
})

// ---------------------------------------------------------------------------
// task 7.3 — fetchJobStatus
// ---------------------------------------------------------------------------

describe('fetchJobStatus', () => {
  it('calls GET /ingest/status/:id and calls updateJob with response body', async () => {
    const store = useIngestStore()
    store.addJob('abc', 'budget.pdf')

    const mockGet = vi.fn().mockResolvedValue({
      data: { status: 'completed', file_id: 'file-xyz', chunk_count: 5 },
    })
    store._api = { get: mockGet }

    await store.fetchJobStatus('abc')

    expect(mockGet).toHaveBeenCalledWith('/ingest/status/abc')
    const job = store.jobs.find(j => j.job_id === 'abc')
    expect(job.status).toBe('completed')
    expect(job.chunk_count).toBe(5)
  })

  it('sets status error when request fails', async () => {
    const store = useIngestStore()
    store.addJob('abc', 'budget.pdf')
    store._api = { get: vi.fn().mockRejectedValue(new Error('Network error')) }

    await store.fetchJobStatus('abc')

    const job = store.jobs.find(j => j.job_id === 'abc')
    expect(job.status).toBe('error')
    expect(job.error).toBe('Network error')
  })
})
