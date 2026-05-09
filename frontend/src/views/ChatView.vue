<template>
  <!--
    ChatView — qa-chat (2026-05-08) + mobile-friendly (2026-05-08).
    Desktop (md+): two-column layout (sessions sidebar + chat area).
    Mobile (md-): single column, ☰ drawer for sessions, 🆕 for new chat,
    sticky input with safe-area-inset-bottom, dvh-based viewport.
  -->
  <div data-chat-root class="h-[100dvh] flex flex-col bg-notion-surface-soft text-notion-ink">

    <!-- Page Header -->
    <div class="bg-notion-brand-navy text-notion-on-dark px-6 py-5 flex-shrink-0">
      <div class="flex items-center gap-3">
        <button
          data-sessions-toggle
          class="md:hidden p-2 -ml-2 rounded-md hover:bg-white/10 text-notion-on-dark"
          aria-label="历史对话"
          @click="drawerOpen = true"
        >
          <Menu class="w-5 h-5" />
        </button>
        <div class="w-9 h-9 rounded-md bg-white/10 flex items-center justify-center">
          <MessageSquare class="w-5 h-5" />
        </div>
        <div class="flex-1">
          <h1 class="text-xl font-semibold tracking-tight leading-tight">智能对话</h1>
          <p class="text-[13px] text-notion-on-dark-muted mt-0.5 hidden sm:block">基于知识库 + 私有数据的 RAG 问答</p>
        </div>
        <button
          data-new-chat
          class="md:hidden p-2 -mr-2 rounded-md hover:bg-white/10 text-notion-on-dark"
          aria-label="新对话"
          @click="onNewChat"
        >
          <PlusSquare class="w-5 h-5" />
        </button>
      </div>
    </div>

    <div v-if="store.error" class="bg-notion-tint-rose border-b border-notion-hairline px-6 py-2 text-[13px] text-notion-error flex-shrink-0">
      {{ store.error }}
    </div>

    <div class="flex-1 flex overflow-hidden">

      <!-- DESKTOP LEFT SIDEBAR — session history -->
      <div data-sessions-sidebar class="w-72 flex-shrink-0 bg-notion-canvas border-r border-notion-hairline hidden md:flex flex-col">
        <div class="px-4 py-3 border-b border-notion-hairline-soft flex items-center justify-between">
          <h2 class="text-[11px] font-semibold uppercase tracking-[0.08em] text-notion-steel">历史对话</h2>
          <span class="text-[11px] text-notion-stone">{{ store.sessions.length }} 条</span>
        </div>
        <div class="flex-shrink-0 p-3 border-b border-notion-hairline-soft">
          <button
            data-new-chat-btn
            class="w-full h-9 bg-notion-primary hover:bg-notion-primary-pressed text-notion-on-primary text-[13px] font-medium rounded-md transition-colors"
            @click="onNewChat"
          >+ 新建对话</button>
        </div>
        <div class="flex-1 overflow-y-auto py-1">
          <div v-if="store.sessions.length === 0" class="px-4 py-3 text-[12px] text-notion-stone italic">
            暂无历史
          </div>
          <button
            v-for="s in store.sessions"
            :key="s.id"
            data-session-item
            :class="[
              'w-full text-left px-3 py-2 cursor-pointer transition-colors block',
              store.currentSession?.id === s.id
                ? 'bg-notion-surface border-l-2 border-l-notion-primary text-notion-ink font-medium'
                : 'text-notion-charcoal hover:bg-notion-surface'
            ]"
            @click="onLoadSession(s.id)"
          >
            <p class="text-[13px] truncate">{{ s.title }}</p>
            <p class="text-[11px] text-notion-stone mt-0.5">{{ formatDate(s.created_at) }} · {{ s.model }}</p>
          </button>
        </div>
      </div>

      <!-- RIGHT — chat area -->
      <div class="flex-1 flex flex-col bg-notion-surface-soft overflow-hidden">

        <!-- Toolbar -->
        <div class="bg-notion-canvas border-b border-notion-hairline px-4 sm:px-6 py-3 flex flex-wrap items-center justify-between gap-3 flex-shrink-0">
          <div class="flex items-center gap-2">
            <span class="text-[11px] font-semibold uppercase tracking-[0.08em] text-notion-steel">模型</span>
            <button
              v-for="opt in ['haiku', 'sonnet']"
              :key="opt"
              :data-model-option="opt"
              :class="[
                'h-7 px-2.5 text-[12px] font-medium rounded-md transition-colors',
                model === opt
                  ? 'bg-notion-ink-deep text-notion-on-dark active'
                  : 'bg-transparent text-notion-charcoal border border-notion-hairline-strong hover:bg-notion-surface'
              ]"
              @click="model = opt"
            >{{ opt === 'haiku' ? 'Haiku' : 'Sonnet' }}</button>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-[11px] font-semibold uppercase tracking-[0.08em] text-notion-steel">范围</span>
            <button
              data-scope-knowledge
              :class="[
                'h-7 px-2.5 text-[12px] font-medium rounded-full transition-colors',
                scope.includes('knowledge')
                  ? 'bg-notion-ink-deep text-notion-on-dark active'
                  : 'bg-transparent text-notion-charcoal border border-notion-hairline-strong hover:bg-notion-surface'
              ]"
              @click="toggleScope('knowledge')"
            >知识库</button>
            <button
              data-scope-private
              :class="[
                'h-7 px-2.5 text-[12px] font-medium rounded-full transition-colors',
                scope.includes('private')
                  ? 'bg-notion-ink-deep text-notion-on-dark active'
                  : 'bg-transparent text-notion-charcoal border border-notion-hairline-strong hover:bg-notion-surface'
              ]"
              @click="toggleScope('private')"
            >私有</button>
          </div>
        </div>

        <!-- Messages or empty state -->
        <div data-messages ref="messagesRef" class="flex-1 overflow-y-auto px-4 sm:px-8 py-6">
          <div v-if="!hasMessages" data-empty-state class="max-w-3xl mx-auto">
            <div class="text-center mb-6">
              <h2 class="text-lg font-semibold text-notion-ink mb-1">问点什么？</h2>
              <p class="text-[13px] text-notion-slate">从下方推荐问题开始，或直接在底部输入。</p>
            </div>
            <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
              <button
                v-for="(p, idx) in promptCards"
                :key="idx"
                data-prompt-card
                :class="[
                  'text-left p-3 rounded-lg transition-colors hover:ring-2 hover:ring-notion-primary',
                  PROMPT_TINTS[idx % PROMPT_TINTS.length],
                ]"
                @click="usePrompt(p)"
              >
                <p class="text-[13px] font-semibold text-notion-charcoal">{{ p.title }}</p>
                <p class="text-[12px] text-notion-slate mt-1 line-clamp-2">{{ p.text }}</p>
              </button>
            </div>
          </div>

          <div v-else class="max-w-3xl mx-auto space-y-4">
            <template v-for="(msg, idx) in messages" :key="idx">
              <div v-if="msg.role === 'user'" class="flex justify-end">
                <div class="max-w-[80%] bg-notion-primary text-notion-on-primary px-4 py-2.5 rounded-lg whitespace-pre-line text-[14px]">
                  {{ msg.content }}
                </div>
              </div>
              <div v-else class="flex flex-col items-start gap-2">
                <div
                  data-assistant-msg
                  class="max-w-[80%] bg-notion-canvas text-notion-ink border border-notion-hairline px-4 py-2.5 rounded-lg text-[14px] leading-relaxed"
                >
                  <div
                    v-if="msg.content"
                    class="prose prose-sm max-w-none prose-headings:text-notion-ink prose-strong:text-notion-ink prose-a:text-notion-link-blue prose-code:text-notion-brand-purple-800 prose-code:bg-notion-tint-lavender prose-code:px-1 prose-code:rounded"
                    v-html="renderMd(msg.content)"
                  />
                  <div
                    v-else-if="store.streaming && idx === messages.length - 1"
                    class="text-notion-stone italic"
                  >思考中…</div>
                </div>
                <div v-if="msg.sources && msg.sources.length" class="flex flex-wrap gap-1.5 max-w-[80%]">
                  <router-link
                    v-for="(src, sidx) in msg.sources"
                    :key="sidx"
                    data-source-chip
                    :to="sourceLink(src)"
                    :class="[
                      'px-2 py-0.5 text-[11px] font-medium rounded-md transition-colors',
                      src.kind === 'entry'
                        ? 'bg-notion-tint-mint text-notion-brand-green hover:bg-notion-tint-yellow'
                        : 'bg-notion-tint-lavender text-notion-brand-purple-800 hover:bg-notion-brand-purple-300',
                    ]"
                    :title="`查看 ${src.title}`"
                  >{{ src.title }} · {{ src.domain }}</router-link>
                </div>

                <!-- Save-to-notes affordance: only after the LLM has finished streaming this turn -->
                <template v-if="msg.content && !(store.streaming && idx === messages.length - 1)">
                  <!-- Idle: just the trigger -->
                  <button
                    v-if="saveState[idx] === undefined || saveState[idx]?.phase === 'idle'"
                    data-save-note-btn
                    class="text-[11px] text-notion-steel hover:text-notion-primary transition-colors"
                    @click="openSaveForm(idx)"
                  >📥 保存到笔记</button>

                  <!-- Editing inline form -->
                  <div
                    v-else-if="saveState[idx]?.phase === 'editing'"
                    data-save-note-form
                    class="w-full max-w-[80%] bg-notion-canvas border border-notion-hairline rounded-lg p-3 space-y-2"
                  >
                    <div>
                      <label class="block text-[10px] font-semibold uppercase tracking-[0.08em] text-notion-steel mb-1">标题</label>
                      <input
                        data-save-note-title
                        v-model="saveState[idx].title"
                        type="text"
                        class="w-full h-8 px-2 bg-notion-canvas border border-notion-hairline-strong text-notion-ink text-[13px] rounded-md focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary"
                      />
                    </div>
                    <div>
                      <label class="block text-[10px] font-semibold uppercase tracking-[0.08em] text-notion-steel mb-1">目录</label>
                      <input
                        data-save-note-directory
                        v-model="saveState[idx].directory"
                        type="text"
                        class="w-full h-8 px-2 bg-notion-canvas border border-notion-hairline-strong text-notion-ink text-[13px] rounded-md focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary"
                      />
                    </div>
                    <div>
                      <label class="block text-[10px] font-semibold uppercase tracking-[0.08em] text-notion-steel mb-1">内容（Markdown）</label>
                      <textarea
                        data-save-note-content
                        v-model="saveState[idx].content"
                        rows="8"
                        class="w-full px-2 py-1.5 bg-notion-canvas border border-notion-hairline-strong text-notion-ink text-[12px] font-mono rounded-md focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary resize-y"
                      />
                    </div>
                    <div class="flex gap-2 pt-1">
                      <button
                        data-save-note-confirm
                        :disabled="saveState[idx].submitting"
                        :class="[
                          'h-8 px-3 rounded-md text-[12px] font-medium transition-colors',
                          saveState[idx].submitting
                            ? 'bg-notion-hairline text-notion-muted-text cursor-not-allowed'
                            : 'bg-notion-primary hover:bg-notion-primary-pressed text-notion-on-primary',
                        ]"
                        @click="confirmSaveNote(idx)"
                      >{{ saveState[idx].submitting ? '保存中…' : '保存' }}</button>
                      <button
                        data-save-note-cancel
                        class="h-8 px-3 bg-transparent hover:bg-notion-surface text-notion-charcoal text-[12px] font-medium rounded-md border border-notion-hairline-strong"
                        @click="cancelSaveNote(idx)"
                      >取消</button>
                    </div>
                    <p v-if="saveState[idx].error" class="text-[11px] text-notion-error">{{ saveState[idx].error }}</p>
                  </div>

                  <!-- Saved confirmation -->
                  <div
                    v-else-if="saveState[idx]?.phase === 'saved'"
                    data-save-note-confirmation
                    class="text-[11px] text-notion-success"
                  >✓ 已保存到「{{ saveState[idx].savedDirectory }}」</div>
                </template>
              </div>
            </template>
            <div v-if="store.streaming" data-streaming-indicator class="text-[12px] text-notion-stone italic">
              正在生成…
            </div>
          </div>
        </div>

        <!-- Input area -->
        <div data-chat-input-wrap class="bg-notion-canvas border-t border-notion-hairline px-4 sm:px-6 pt-3 pb-[calc(12px+env(safe-area-inset-bottom))] flex-shrink-0">
          <div class="max-w-3xl mx-auto flex items-end gap-2">
            <textarea
              data-chat-input
              v-model="inputText"
              placeholder="问点什么…"
              rows="2"
              :disabled="store.streaming"
              class="flex-1 px-3 py-2 bg-notion-canvas border border-notion-hairline-strong text-notion-ink text-[14px] rounded-md placeholder:text-notion-stone focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary resize-none"
              @keydown.enter.prevent="onEnter"
            />
            <button
              data-chat-submit
              :disabled="store.streaming || !inputText.trim()"
              :aria-label="'发送'"
              :class="[
                'h-10 px-3 sm:px-4 rounded-md text-[14px] font-medium transition-colors flex items-center gap-1',
                (store.streaming || !inputText.trim())
                  ? 'bg-notion-hairline text-notion-muted-text cursor-not-allowed'
                  : 'bg-notion-primary hover:bg-notion-primary-pressed text-notion-on-primary'
              ]"
              @click="submit"
            >
              <Send class="w-4 h-4" />
              <span class="hidden sm:inline">发送</span>
            </button>
          </div>
        </div>

      </div>
    </div>

    <!-- MOBILE SESSIONS DRAWER (md-) -->
    <div
      v-if="drawerOpen"
      class="md:hidden fixed inset-0 z-50 flex"
      @keydown.esc="drawerOpen = false"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black/40" @click="drawerOpen = false"></div>
      <!-- Panel -->
      <div data-sessions-drawer class="relative w-[85%] max-w-sm h-full bg-notion-canvas shadow-xl flex flex-col animate-slide-in-left">
        <div class="flex items-center justify-between px-4 py-3 border-b border-notion-hairline">
          <h2 class="text-[13px] font-semibold text-notion-ink">历史对话</h2>
          <button
            class="p-1.5 rounded-md hover:bg-notion-tint-gray text-notion-steel"
            aria-label="关闭"
            @click="drawerOpen = false"
          >
            <X class="w-4 h-4" />
          </button>
        </div>
        <div class="p-3 border-b border-notion-hairline-soft">
          <button
            class="w-full h-9 bg-notion-primary hover:bg-notion-primary-pressed text-notion-on-primary text-[13px] font-medium rounded-md transition-colors"
            @click="onNewChatFromDrawer"
          >+ 新建对话</button>
        </div>
        <div class="flex-1 overflow-y-auto py-1">
          <div v-if="store.sessions.length === 0" class="px-4 py-3 text-[12px] text-notion-stone italic">
            暂无历史
          </div>
          <button
            v-for="s in store.sessions"
            :key="s.id"
            data-drawer-session
            :class="[
              'w-full text-left px-3 py-2 cursor-pointer transition-colors block',
              store.currentSession?.id === s.id
                ? 'bg-notion-surface border-l-2 border-l-notion-primary text-notion-ink font-medium'
                : 'text-notion-charcoal hover:bg-notion-surface'
            ]"
            @click="onLoadSessionFromDrawer(s.id)"
          >
            <p class="text-[13px] truncate">{{ s.title }}</p>
            <p class="text-[11px] text-notion-stone mt-0.5">{{ formatDate(s.created_at) }} · {{ s.model }}</p>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick, watch } from 'vue'
import { MessageSquare, Menu, PlusSquare, Send, X } from 'lucide-vue-next'
import { useChatStore } from '../stores/chat.js'
import { markdownToHtml } from '../composables/useFileContent.js'

const store = useChatStore()

// Reuse the same marked + DOMPurify pipeline that WikiView and PrivateView
// use, so assistant answers render headings / lists / links / code blocks
// instead of showing raw `## ` and `**bold**` literally.
function renderMd(text) {
  if (!text) return ''
  return markdownToHtml(String(text))
}

const inputText = ref('')
const model = ref('haiku')
const scope = ref(['knowledge'])
const drawerOpen = ref(false)
const messagesRef = ref(null)

const PROMPT_TINTS = [
  'bg-notion-tint-lavender',
  'bg-notion-tint-mint',
  'bg-notion-tint-sky',
  'bg-notion-tint-peach',
  'bg-notion-tint-cream',
  'bg-notion-tint-yellow',
]

const promptCards = [
  { title: '退休账户', text: '我应该如何在 401k / Roth IRA / Traditional IRA 之间分配？' },
  { title: '税务策略', text: 'AMT 是怎么计算的，对我有什么影响？' },
  { title: '股权激励', text: 'RSU 和 ISO 在税务处理上有什么区别？' },
  { title: '投资品种', text: 'Bond ladder 和 Total Bond Index 哪个更适合我？' },
  { title: '中美对比', text: 'FBAR 和 FATCA 报告我需要怎么处理？' },
  { title: '家庭财务', text: '529 账户和 UTMA 哪个更适合给孩子存学费？' },
]

const messages = computed(() => store.currentSession?.messages ?? [])
const hasMessages = computed(() => messages.value.length > 0)

// Auto-scroll: only follow new tokens if the user is already near the bottom.
// If they've scrolled up to read history, don't yank them back.
//
// Watch BOTH the message count (new turns) and the last message's content
// (streaming token-by-token grows .content in place — length stays the same).
// Without the second watch source, the assistant's answer would silently
// scroll off-screen during streaming.
const NEAR_BOTTOM_THRESHOLD = 100
watch(
  () => [messages.value.length, messages.value[messages.value.length - 1]?.content],
  () => {
    nextTick(() => {
      const el = messagesRef.value
      if (!el) return
      const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
      if (distanceFromBottom <= NEAR_BOTTOM_THRESHOLD) {
        el.scrollTop = el.scrollHeight - el.clientHeight
      }
    })
  },
)

onMounted(() => {
  store.fetchSessions()
})

function formatDate(iso) {
  if (!iso) return ''
  return iso.slice(0, 10)
}

function sourceLink(src) {
  // Knowledge chunks live in /wiki; private entries live in /private.
  // The deep-link query param is read by the destination view on mount.
  if (src.kind === 'entry') {
    return { path: '/private', query: { entry: src.file_id } }
  }
  return { path: '/wiki', query: { file: src.file_id } }
}

// ===== Save-to-notes =====
const saveState = reactive({})

function todayIso() {
  const d = new Date()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

function defaultTitleForMessage(idx) {
  const userMsg = idx > 0 ? messages.value[idx - 1] : null
  const text = userMsg?.role === 'user' ? userMsg.content : ''
  return (text || '').trim().slice(0, 40)
}

function buildDefaultMarkdown(idx) {
  const userMsg = idx > 0 ? messages.value[idx - 1] : null
  const assistantMsg = messages.value[idx]
  const question = userMsg?.role === 'user' ? userMsg.content : ''
  const answer = assistantMsg?.content ?? ''
  const sources = assistantMsg?.sources ?? []
  const sourceLines = sources.map((s) => {
    const path = s.kind === 'entry' ? `/private?entry=${s.file_id}` : `/wiki?file=${s.file_id}`
    return `- [${s.title}](${path}) · ${s.domain}`
  })
  const parts = []
  if (question) parts.push(`> **问**：${question}`, '')
  parts.push(answer || '')
  if (sourceLines.length) {
    parts.push('', '## 参考来源', ...sourceLines)
  }
  return parts.join('\n')
}

function openSaveForm(idx) {
  saveState[idx] = {
    phase: 'editing',
    title: defaultTitleForMessage(idx) || '未命名笔记',
    directory: `对话总结/${todayIso()}`,
    content: buildDefaultMarkdown(idx),
    submitting: false,
    error: '',
    savedDirectory: '',
  }
}

function cancelSaveNote(idx) {
  saveState[idx] = { phase: 'idle' }
}

async function confirmSaveNote(idx) {
  const s = saveState[idx]
  if (!s || s.submitting) return
  s.submitting = true
  s.error = ''
  try {
    const created = await store.saveMessageToNote(idx, {
      title: s.title.trim() || '未命名笔记',
      directory: s.directory.trim(),
      content: s.content,
    })
    saveState[idx] = {
      phase: 'saved',
      savedDirectory: created?.directory || s.directory,
    }
  } catch (err) {
    s.submitting = false
    s.error = store.error || err?.message || '保存失败'
  }
}

function onNewChat() {
  store.newSession()
  inputText.value = ''
}

function onNewChatFromDrawer() {
  drawerOpen.value = false
  onNewChat()
}

async function onLoadSession(id) {
  await store.loadSession(id)
}

async function onLoadSessionFromDrawer(id) {
  drawerOpen.value = false
  await store.loadSession(id)
}

function toggleScope(name) {
  const has = scope.value.includes(name)
  if (has && scope.value.length === 1) {
    return
  }
  scope.value = has
    ? scope.value.filter(s => s !== name)
    : [...scope.value, name]
}

function usePrompt(p) {
  inputText.value = p.text
  nextTick(() => {
    const el = document.querySelector('[data-chat-input]')
    el?.focus()
  })
}

async function submit() {
  const q = inputText.value.trim()
  if (!q || store.streaming) return
  inputText.value = ''
  await store.sendMessage(q, { model: model.value, scope: scope.value })
  await store.fetchSessions()
}

function onEnter(event) {
  if (event.shiftKey) {
    inputText.value += '\n'
    return
  }
  submit()
}
</script>

<style>
@keyframes slide-in-left {
  from { transform: translateX(-100%); }
  to { transform: translateX(0); }
}
.animate-slide-in-left {
  animation: slide-in-left 0.18s ease-out;
}
</style>
