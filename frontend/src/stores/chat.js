import { defineStore } from 'pinia'
import api from '../api/index.js'

function readError(err) {
  return err?.response?.data?.error ?? err?.message ?? 'Unknown error'
}

function emptySession(model = 'haiku') {
  return { id: null, title: null, model, created_at: null, messages: [] }
}

// Parse a chunk of SSE bytes into the array of decoded JSON events. Handles
// the common case where multiple events arrive in a single TCP read by
// splitting on the SSE delimiter `\n\n`. Trailing partial events are returned
// as the second array so the caller can prepend them to the next read.
function parseSseChunk(buffered) {
  const events = []
  const pieces = buffered.split('\n\n')
  const tail = pieces.pop() ?? ''
  for (const raw of pieces) {
    const line = raw.trim()
    if (!line.startsWith('data: ')) continue
    try {
      events.push(JSON.parse(line.slice('data: '.length)))
    } catch {
      // skip malformed events
    }
  }
  return { events, tail }
}

export const useChatStore = defineStore('chat', {
  state: () => ({
    sessions: [],
    currentSession: null, // null = empty / new chat; otherwise { id, title, model, messages: [...] }
    streaming: false,
    error: null,
    _api: api,
  }),

  actions: {
    async fetchSessions() {
      this.error = null
      try {
        const resp = await this._api.get('/chat/sessions')
        this.sessions = resp.data
      } catch (err) {
        this.sessions = []
        this.error = readError(err)
      }
    },

    async loadSession(id) {
      this.error = null
      try {
        const resp = await this._api.get(`/chat/sessions/${id}`)
        this.currentSession = resp.data
      } catch (err) {
        this.error = readError(err)
      }
    },

    newSession() {
      this.currentSession = null
      this.error = null
    },

    async saveMessageToNote(messageIndex, { title, directory, content }) {
      // Persist a chat answer as a private note. The API endpoint is the
      // same one PrivateView uses; we just thread `chat_ref` through so
      // the saved note traces back to the originating session.
      this.error = null
      try {
        const resp = await this._api.post('/private/notes', {
          title,
          directory,
          content,
          chat_ref: this.currentSession?.id ?? null,
        })
        return resp.data
      } catch (err) {
        this.error = readError(err)
        throw err
      }
    },

    async sendMessage(query, { model = 'haiku', scope = ['knowledge'] } = {}) {
      this.error = null
      // Make sure we have a working session shell to append messages to.
      if (!this.currentSession) {
        this.currentSession = emptySession(model)
      }
      const session = this.currentSession

      // Append the user message immediately so the UI feels responsive.
      session.messages = [
        ...session.messages,
        { role: 'user', content: query, sources: [] },
      ]

      // Add a placeholder assistant message that the stream will fill in.
      const assistantIdx = session.messages.length
      session.messages = [
        ...session.messages,
        { role: 'assistant', content: '', sources: [] },
      ]

      this.streaming = true
      try {
        const resp = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query,
            model,
            scope,
            session_id: session.id ?? null,
          }),
        })
        if (!resp.ok || !resp.body) {
          throw new Error(`chat request failed (${resp.status})`)
        }
        const reader = resp.body.getReader()
        const decoder = new TextDecoder()
        let buffered = ''
        try {
          while (true) {
            const { done, value } = await reader.read()
            if (done) break
            buffered += decoder.decode(value, { stream: true })
            const { events, tail } = parseSseChunk(buffered)
            buffered = tail
            for (const ev of events) {
              if (ev.type === 'token') {
                // Mutate-then-replace pattern for the assistant message keeps
                // Vue reactivity simple while remaining immutable at the
                // messages-array level.
                const next = [...session.messages]
                next[assistantIdx] = {
                  ...next[assistantIdx],
                  content: (next[assistantIdx].content ?? '') + (ev.content ?? ''),
                }
                session.messages = next
              } else if (ev.type === 'done') {
                const next = [...session.messages]
                next[assistantIdx] = {
                  ...next[assistantIdx],
                  sources: ev.sources ?? [],
                }
                session.messages = next
                // Hydrate the session id when the backend created a new
                // session for this turn — needed for chat_ref when the
                // user later saves the answer to private notes.
                if (ev.session_id && !session.id) {
                  session.id = ev.session_id
                }
              } else if (ev.type === 'error') {
                this.error = ev.message ?? 'Unknown stream error'
              }
            }
          }
        } finally {
          reader.releaseLock?.()
        }
      } catch (err) {
        this.error = readError(err)
      } finally {
        this.streaming = false
      }
    },
  },
})
