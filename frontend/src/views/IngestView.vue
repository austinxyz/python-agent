<template>
  <div class="flex h-screen overflow-hidden bg-gray-50">
    <!-- LEFT SIDEBAR -->
    <aside class="w-60 flex-shrink-0 border-r border-border bg-white overflow-y-auto">
      <div class="px-4 py-3 border-b border-border">
        <h1 class="text-sm font-semibold text-gray-900">知识库</h1>
      </div>
      <div v-for="d in DOMAINS" :key="d">
        <div class="flex items-center px-3 py-2 hover:bg-muted/30">
          <span
            data-domain-name
            class="flex-1 text-sm cursor-pointer text-gray-700 hover:text-primary truncate"
            @click="onDomainNameClick(d)"
          >{{ d }}</span>
          <button
            data-domain-chevron
            class="ml-1 text-xs text-muted-foreground hover:text-foreground transition-transform duration-150"
            :class="expandedDomains[d] ? 'rotate-90' : ''"
            @click.stop="toggleExpand(d)"
          >▶</button>
        </div>
        <div v-if="expandedDomains[d]">
          <button
            v-for="file in filesForDomain(d)"
            :key="file.file_id"
            data-sidebar-file
            class="w-full text-left text-xs px-7 py-1.5 text-primary hover:bg-blue-50 truncate block"
            @click="onFileClick(file)"
          >{{ file.title || file.orig_name }}</button>
        </div>
      </div>
    </aside>

    <!-- RIGHT PANEL -->
    <main class="flex-1 overflow-y-auto">

      <!-- Welcome state -->
      <div v-if="rightPanelState === 'welcome'" data-panel="welcome" class="flex flex-col items-center justify-center h-full text-center p-8">
        <div class="w-16 h-16 bg-gradient-to-br from-blue-100 to-purple-100 rounded-2xl flex items-center justify-center mb-4">
          <span class="text-2xl">📚</span>
        </div>
        <h2 class="text-lg font-semibold text-gray-900 mb-2">欢迎使用知识库</h2>
        <p class="text-sm text-muted-foreground">从左侧点击领域名称开始浏览或新建摄入</p>
      </div>

      <!-- Domain state -->
      <div v-else-if="rightPanelState === 'domain'" data-panel="domain" class="p-8">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-xl font-bold text-gray-900">{{ selectedDomain }}</h2>
          <button
            data-action="new-ingest"
            class="px-4 py-2 bg-primary text-primary-foreground text-sm font-medium rounded-lg hover:bg-primary/90 transition-colors"
            @click="openForm"
          >+ 新建摄入</button>
        </div>
        <div v-if="filesForDomain(selectedDomain).length > 0">
          <p class="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">已上传</p>
          <ul class="space-y-2">
            <li
              v-for="file in filesForDomain(selectedDomain)"
              :key="file.file_id"
              class="bg-white border border-border rounded-lg px-4 py-3 text-sm text-gray-800"
            >{{ file.title || file.orig_name }}</li>
          </ul>
        </div>
        <div v-else class="text-sm text-muted-foreground">该领域暂无文件，点击「新建摄入」添加</div>
      </div>

      <!-- Form state -->
      <div v-else-if="rightPanelState === 'form'" data-panel="form" class="p-8 max-w-lg">
        <div class="flex items-center space-x-3 mb-6">
          <button class="text-sm text-muted-foreground hover:text-foreground" @click="rightPanelState = 'domain'">← 返回</button>
          <span data-domain-badge class="px-3 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded-full">{{ selectedDomain }}</span>
        </div>

        <div class="space-y-4">
          <!-- Title -->
          <div>
            <label class="block text-xs font-medium text-muted-foreground mb-1.5">标题 <span class="text-destructive">*</span></label>
            <input
              data-input="title"
              type="text"
              v-model="formTitle"
              placeholder="输入标题"
              class="w-full px-3 py-2.5 rounded-lg border border-input bg-background text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent transition"
            />
          </div>

          <!-- Source type tabs -->
          <div>
            <label class="block text-xs font-medium text-muted-foreground mb-1.5">摄入方式</label>
            <div class="flex space-x-1 bg-muted rounded-lg p-1 w-fit">
              <button
                data-source-type="url"
                :class="['px-3 py-1.5 rounded-md text-xs font-medium transition-colors', sourceType === 'url' ? 'bg-white shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground']"
                @click="sourceType = 'url'"
              >URL</button>
              <button
                data-source-type="text"
                :class="['px-3 py-1.5 rounded-md text-xs font-medium transition-colors', sourceType === 'text' ? 'bg-white shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground']"
                @click="sourceType = 'text'"
              >文本</button>
              <button
                data-source-type="file"
                :class="['px-3 py-1.5 rounded-md text-xs font-medium transition-colors', sourceType === 'file' ? 'bg-white shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground']"
                @click="sourceType = 'file'"
              >文件</button>
            </div>
          </div>

          <!-- URL input -->
          <div v-if="sourceType === 'url'">
            <label class="block text-xs font-medium text-muted-foreground mb-1.5">URL 地址</label>
            <input
              data-input="source_url"
              type="url"
              v-model="sourceUrl"
              placeholder="https://example.com/article"
              class="w-full px-3 py-2.5 rounded-lg border border-input bg-background text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent transition"
            />
          </div>

          <!-- Text input -->
          <div v-if="sourceType === 'text'">
            <label class="block text-xs font-medium text-muted-foreground mb-1.5">粘贴文本</label>
            <textarea
              data-input="content"
              v-model="textContent"
              placeholder="粘贴文本内容…"
              rows="6"
              class="w-full px-3 py-2.5 rounded-lg border border-input bg-background text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent transition resize-none"
            />
          </div>

          <!-- File upload -->
          <div v-if="sourceType === 'file'">
            <label class="block text-xs font-medium text-muted-foreground mb-1.5">上传文件</label>
            <label class="flex items-center justify-center w-full h-24 border-2 border-dashed border-input rounded-lg cursor-pointer bg-muted/30 hover:bg-muted/50 transition">
              <span class="text-xs text-muted-foreground">{{ selectedFile ? selectedFile.name : '点击或拖拽文件到此处' }}</span>
              <input
                data-input="file"
                type="file"
                class="hidden"
                @change="onFileChange"
              />
            </label>
          </div>

          <!-- Validation error -->
          <p v-if="formError" data-ingest-error class="text-sm text-destructive bg-destructive/10 px-4 py-3 rounded-lg border border-destructive/20">
            {{ formError }}
          </p>

          <!-- Submit -->
          <button
            data-action="submit-ingest"
            :disabled="isSubmitting"
            :class="[
              'w-full py-3 px-6 rounded-xl text-sm font-semibold transition-all',
              isSubmitting
                ? 'bg-muted text-muted-foreground cursor-not-allowed'
                : 'bg-gradient-to-r from-blue-500 to-purple-600 text-white hover:from-blue-600 hover:to-purple-700 shadow-md hover:shadow-lg'
            ]"
            @click="submitForm"
          >{{ isSubmitting ? '摄入中…' : '开始摄入' }}</button>
        </div>
      </div>

      <!-- Result state -->
      <div v-else-if="rightPanelState === 'result'" data-panel="result" class="p-8 max-w-lg">
        <div class="bg-white border border-border rounded-xl p-6 space-y-4">
          <div class="flex items-center space-x-3">
            <div class="w-8 h-8 bg-amber-100 rounded-full flex items-center justify-center">
              <span class="text-amber-600 text-sm">⏳</span>
            </div>
            <div>
              <p class="text-sm font-semibold text-gray-900">{{ submittedTitle }}</p>
              <p class="text-xs text-muted-foreground">摄入进行中…</p>
            </div>
          </div>
          <button
            class="text-xs text-muted-foreground hover:text-foreground"
            @click="rightPanelState = 'domain'"
          >返回领域</button>
        </div>
      </div>

      <!-- Content viewer state -->
      <div v-else-if="rightPanelState === 'content'" data-panel="content" class="p-8">
        <button class="text-sm text-muted-foreground hover:text-foreground mb-4 block" @click="rightPanelState = 'domain'">← 返回</button>
        <div v-if="contentLoading" class="text-sm text-muted-foreground">加载中…</div>
        <div v-else-if="contentError" class="text-sm text-destructive">{{ contentError }}</div>
        <div v-else class="prose max-w-none" v-html="renderedContent" />
      </div>

    </main>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useIngestStore } from '../stores/ingest.js'
import { useFileContent } from '../composables/useFileContent.js'
import { DOMAINS } from '../constants/domains.js'

const store = useIngestStore()

const rightPanelState = ref('welcome')
const selectedDomain = ref('')
const files = ref([])
const expandedDomains = reactive({})

const formTitle = ref('')
const sourceType = ref('url')
const sourceUrl = ref('')
const textContent = ref('')
const selectedFile = ref(null)
const formError = ref('')
const isSubmitting = ref(false)
const submittedTitle = ref('')

const { loading: contentLoading, error: contentError, renderedContent, load: loadContent } = useFileContent()

async function fetchFiles() {
  try {
    const resp = await store._api.get('/files')
    files.value = resp.data
  } catch {
    // leave existing files on error
  }
}

onMounted(fetchFiles)

function filesForDomain(domain) {
  return files.value.filter(f => f.domain === domain)
}

function toggleExpand(domain) {
  expandedDomains[domain] = !expandedDomains[domain]
}

function onDomainNameClick(domain) {
  selectedDomain.value = domain
  rightPanelState.value = 'domain'
}

function openForm() {
  formTitle.value = ''
  sourceType.value = 'url'
  sourceUrl.value = ''
  textContent.value = ''
  selectedFile.value = null
  formError.value = ''
  rightPanelState.value = 'form'
}

function onFileChange(event) {
  selectedFile.value = event.target.files[0] || null
}

function onFileClick(file) {
  rightPanelState.value = 'content'
  loadContent(file.file_id, file.orig_name)
}

async function submitForm() {
  if (isSubmitting.value) return
  formError.value = ''

  if (!formTitle.value.trim()) {
    formError.value = '请输入标题'
    return
  }

  const payload = new FormData()
  payload.append('title', formTitle.value)
  payload.append('destination', 'knowledge')
  payload.append('domain', selectedDomain.value)
  payload.append('source_type', sourceType.value)

  if (sourceType.value === 'url') {
    payload.append('source_url', sourceUrl.value)
  } else if (sourceType.value === 'text') {
    payload.append('content', textContent.value)
  } else if (sourceType.value === 'file' && selectedFile.value) {
    payload.append('file', selectedFile.value)
  }

  isSubmitting.value = true
  try {
    const resp = await store._api.post('/ingest', payload)
    const { job_id } = resp.data
    submittedTitle.value = formTitle.value
    rightPanelState.value = 'result'
    store.addJob(job_id, formTitle.value)
    store.pollJob(job_id, (job) => {
      fetchFiles()
      if (job?.status === 'completed') {
        rightPanelState.value = 'domain'
      } else {
        formError.value = job?.error ?? '摄入失败'
        rightPanelState.value = 'form'
      }
    })
  } catch (err) {
    formError.value = err?.response?.data?.error ?? err.message ?? '摄入失败，请重试'
  } finally {
    isSubmitting.value = false
  }
}
</script>
