import { ref } from 'vue'

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
  return escapeHtml(md)
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/```[\w]*\n([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
    .replace(/^[-*] (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>')
    .replace(/\n\n+/g, '</p><p>')
    .replace(/^(?!<[a-z])(.+)$/gm, (_, line) => line ? line : '')
    .replace(/^(.+)/, '<p>$1')
    .replace(/(.+)$/, '$1</p>')
}
