import { ref } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

export function useFileContent() {
  const loading = ref(false)
  const error = ref('')
  const renderedContent = ref('')

  async function load(fileId, filename) {
    loading.value = true
    error.value = ''
    renderedContent.value = ''
    try {
      const resp = await fetch(`/api/files/${fileId}/content`)
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const text = await resp.text()
      renderedContent.value = renderContent(text, filename)
    } catch (e) {
      error.value = e.message ?? '加载失败'
    } finally {
      loading.value = false
    }
  }

  return { loading, error, renderedContent, load }
}

export function renderContent(text, name) {
  if (name.endsWith('.md') || name.endsWith('.markdown')) {
    return markdownToHtml(text)
  }
  return `<pre class="whitespace-pre-wrap break-words text-sm font-mono">${escapeHtml(text)}</pre>`
}

export function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

export function markdownToHtml(md) {
  const raw = marked.parse(md)
  return DOMPurify.sanitize(raw)
}
