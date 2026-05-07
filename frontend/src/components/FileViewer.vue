<template>
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
    @click.self="$emit('close')"
  >
    <div class="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[80vh] flex flex-col mx-4">
      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-border flex-shrink-0">
        <div class="flex items-center space-x-2 min-w-0">
          <FileText class="w-4 h-4 text-muted-foreground flex-shrink-0" />
          <span class="text-sm font-medium text-gray-800 truncate">{{ filename }}</span>
        </div>
        <button
          @click="$emit('close')"
          class="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors flex-shrink-0 ml-4"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-auto p-6">
        <div v-if="loading" class="flex items-center justify-center h-32 text-muted-foreground">
          <Loader2 class="w-6 h-6 animate-spin mr-2" />
          <span class="text-sm">加载中…</span>
        </div>
        <div v-else-if="error" class="text-sm text-destructive">{{ error }}</div>
        <div
          v-else
          class="prose prose-sm max-w-none text-gray-800"
          v-html="renderedContent"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { FileText, X, Loader2 } from 'lucide-vue-next'

const props = defineProps({
  fileId: { type: String, required: true },
  filename: { type: String, required: true },
})

defineEmits(['close'])

const loading = ref(true)
const error = ref('')
const renderedContent = ref('')

onMounted(async () => {
  try {
    const resp = await fetch(`/api/files/${props.fileId}/content`)
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const text = await resp.text()
    renderedContent.value = renderContent(text, props.filename)
  } catch (e) {
    error.value = e.message ?? '加载失败'
  } finally {
    loading.value = false
  }
})

function renderContent(text, name) {
  if (name.endsWith('.md') || name.endsWith('.markdown')) {
    return markdownToHtml(text)
  }
  // plain text: wrap in <pre>
  return `<pre class="whitespace-pre-wrap break-words text-sm font-mono">${escapeHtml(text)}</pre>`
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function markdownToHtml(md) {
  return md
    // headings
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    // bold / italic
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // inline code
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // code blocks
    .replace(/```[\w]*\n([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
    // unordered lists
    .replace(/^[-*] (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>')
    // blank lines → paragraphs
    .replace(/\n\n+/g, '</p><p>')
    .replace(/^(?!<[a-z])(.+)$/gm, (_, line) => line ? line : '')
    // wrap in paragraph
    .replace(/^(.+)/, '<p>$1')
    .replace(/(.+)$/, '$1</p>')
}
</script>
