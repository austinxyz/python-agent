import { defineStore } from 'pinia'
import api from '../api/index.js'

const VALID_DESTINATIONS = new Set(['knowledge', 'private'])

export const useIngestStore = defineStore('ingest', {
  state: () => ({
    destination: 'knowledge',
    jobs: [],
    _api: api,  // test seam: replace with { get: mockFn } in tests
  }),

  actions: {
    setDestination(dest) {
      if (!VALID_DESTINATIONS.has(dest)) {
        throw new Error(`Invalid destination: "${dest}". Must be one of: ${[...VALID_DESTINATIONS].join(', ')}`)
      }
      this.destination = dest
    },

    addJob(job_id, label) {
      if (this.jobs.some(j => j.job_id === job_id)) return
      this.jobs.push({ job_id, label, status: 'running', chunk_count: null, error: null })
    },

    updateJob(job_id, patch) {
      const idx = this.jobs.findIndex(j => j.job_id === job_id)
      if (idx !== -1) {
        this.jobs = this.jobs.map((j, i) => i === idx ? { ...j, ...patch } : j)
      }
    },

    async fetchJobStatus(job_id) {
      try {
        const resp = await this._api.get(`/ingest/status/${job_id}`)
        this.updateJob(job_id, resp.data)
      } catch (err) {
        this.updateJob(job_id, {
          status: 'error',
          error: err?.response?.data?.error ?? err.message ?? 'Unknown error',
        })
      }
    },

    pollJob(job_id, onComplete = null, intervalMs = 3000, maxAttempts = 60) {
      let attempts = 0
      const tick = async () => {
        await this.fetchJobStatus(job_id)
        const job = this.jobs.find(j => j.job_id === job_id)
        attempts++
        if (job && job.status === 'running' && attempts < maxAttempts) {
          setTimeout(tick, intervalMs)
        } else if (typeof onComplete === 'function') {
          const terminal = (job && job.status !== 'running') ? job : { status: 'error', error: '摄入超时' }
          onComplete(terminal)
        }
      }
      setTimeout(tick, intervalMs)
    },
  },
})
