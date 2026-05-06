<template>
  <div class="h-screen flex flex-col bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50">

    <!-- Page Header -->
    <div class="bg-gradient-to-r from-blue-600 to-purple-600 shadow-lg px-6 py-4 flex-shrink-0">
      <h1 class="text-2xl font-bold text-white">原始材料库</h1>
      <p class="text-xs text-blue-100 mt-1">摄入文件、网页或文本，按领域分类管理</p>
    </div>

    <!-- Main: Two-column layout -->
    <div class="flex-1 flex overflow-hidden">

      <!-- LEFT SIDEBAR -->
      <div class="w-60 flex-shrink-0 bg-white border-r border-gray-200 flex flex-col shadow-lg">
        <!-- Sidebar header -->
        <div class="px-4 py-3 border-b border-gray-200 bg-gradient-to-r from-indigo-500 to-purple-500">
          <h2 class="text-sm font-semibold text-white">📚 领域分类</h2>
          <p class="text-xs text-indigo-100 mt-0.5">共 {{ files.length }} 个文件</p>
        </div>

        <!-- Domain list -->
        <div class="flex-1 overflow-y-auto">
          <div v-for="d in DOMAINS" :key="d">

            <!-- Domain row -->
            <div
              :class="[
                'flex items-center gap-2 px-3 py-3 border-b border-gray-100 cursor-pointer transition-all duration-200',
                selectedDomain === d && rightPanelState !== 'welcome'
                  ? 'bg-gradient-to-r from-blue-50 to-purple-50 border-l-4 border-l-blue-600 shadow-sm'
                  : 'hover:bg-gradient-to-r hover:from-gray-50 hover:to-blue-50 hover:shadow-sm'
              ]"
            >
              <span
                data-domain-name
                class="flex-1 text-sm font-bold text-gray-800 truncate"
                @click="onDomainNameClick(d)"
              >{{ d }}</span>

              <!-- File count badge -->
              <span
                v-if="filesForDomain(d).length > 0"
                class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-indigo-100 text-indigo-600 flex-shrink-0"
              >{{ filesForDomain(d).length }} 篇</span>

              <!-- SVG chevron -->
              <button
                data-domain-chevron
                class="flex-shrink-0 text-gray-300 hover:text-indigo-500 transition-colors p-0.5"
                @click.stop="toggleExpand(d)"
              >
                <svg
                  class="w-3.5 h-3.5 transition-transform duration-200"
                  :class="expandedDomains[d] ? 'rotate-90' : ''"
                  viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
                >
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              </button>
            </div>

            <!-- Expanded file list -->
            <div v-if="expandedDomains[d]" class="bg-gray-50 border-b border-gray-100">
              <div v-if="filesForDomain(d).length === 0" class="px-6 py-2.5 text-xs text-gray-400 italic">
                暂无文件
              </div>
              <button
                v-for="file in filesForDomain(d)"
                :key="file.file_id"
                data-sidebar-file
                :class="[
                  'w-full text-left px-5 py-2 text-xs transition-all duration-200 block border-b border-gray-100 last:border-0',
                  viewingFileId === file.file_id
                    ? 'bg-gradient-to-r from-indigo-50 to-purple-50 text-indigo-700 font-semibold border-l-2 border-l-indigo-500'
                    : 'text-gray-600 hover:bg-white hover:text-indigo-600'
                ]"
                @click="onFileClick(file)"
              >
                <span class="truncate block leading-relaxed">{{ file.title || file.orig_name }}</span>
              </button>
            </div>

          </div>
        </div>
      </div>

      <!-- RIGHT PANEL -->
      <div class="flex-1 overflow-y-auto">

        <!-- Welcome state -->
        <div v-if="rightPanelState === 'welcome'" data-panel="welcome" class="h-full flex items-center justify-center">
          <div class="text-center">
            <div class="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-blue-100 to-purple-100 rounded-2xl flex items-center justify-center shadow-lg">
              <span class="text-4xl">📚</span>
            </div>
            <h2 class="text-xl font-bold text-gray-800 mb-2">欢迎使用原始材料库</h2>
            <p class="text-sm text-gray-500">从左侧选择领域开始浏览，或新建摄入</p>
          </div>
        </div>

        <!-- Domain state -->
        <div v-else-if="rightPanelState === 'domain'" data-panel="domain" class="h-full flex flex-col">
          <div class="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-4 flex-shrink-0 shadow-md">
            <div class="flex items-center justify-between">
              <div>
                <h2 class="text-lg font-bold text-white">{{ selectedDomain }}</h2>
                <p class="text-xs text-indigo-100 mt-0.5">{{ filesForDomain(selectedDomain).length }} 个文件</p>
              </div>
              <button
                data-action="new-ingest"
                class="px-4 py-2 bg-gradient-to-r from-green-400 to-emerald-500 hover:from-green-500 hover:to-emerald-600 text-white text-sm font-bold rounded-lg shadow-md hover:shadow-lg transition-all duration-200"
                @click="openForm"
              >+ 新建摄入</button>
            </div>
          </div>

          <div class="flex-1 p-6 overflow-y-auto">
            <div v-if="filesForDomain(selectedDomain).length === 0" class="flex flex-col items-center justify-center h-48 text-gray-400">
              <span class="text-4xl mb-3">📂</span>
              <p class="text-sm">该领域暂无文件</p>
              <p class="text-xs mt-1">点击右上角「+ 新建摄入」添加</p>
            </div>
            <div v-else class="space-y-3">
              <div
                v-for="file in filesForDomain(selectedDomain)"
                :key="file.file_id"
                class="group bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-all duration-200 p-4"
              >
                <!-- Edit mode -->
                <div v-if="editingFileId === file.file_id" class="flex items-center gap-2">
                  <input
                    ref="editInputRef"
                    v-model="editingTitle"
                    class="flex-1 px-3 py-2 rounded-lg border-2 border-indigo-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent"
                    placeholder="输入标题"
                    @keydown.enter="confirmEdit(file)"
                    @keydown.esc="cancelEdit"
                  />
                  <button
                    class="px-3 py-2 bg-gradient-to-r from-indigo-500 to-purple-500 text-white text-xs font-bold rounded-lg hover:shadow-md transition-all"
                    @click="confirmEdit(file)"
                  >保存</button>
                  <button
                    class="px-3 py-2 bg-gray-100 text-gray-600 text-xs font-bold rounded-lg hover:bg-gray-200 transition-all"
                    @click="cancelEdit"
                  >取消</button>
                </div>

                <!-- Normal mode -->
                <div v-else class="flex items-start gap-3">
                  <div
                    class="w-9 h-9 bg-gradient-to-br from-blue-100 to-purple-100 rounded-lg flex items-center justify-center flex-shrink-0 cursor-pointer"
                    @click="onFileClick(file)"
                  >
                    <span class="text-base">{{ file.source_type === 'url' ? '🌐' : file.source_type === 'file' ? '📄' : '📝' }}</span>
                  </div>
                  <div class="flex-1 min-w-0 cursor-pointer" @click="onFileClick(file)">
                    <p class="text-sm font-semibold text-gray-800 leading-snug">{{ file.title || file.orig_name }}</p>
                    <p class="text-xs text-gray-400 mt-0.5 truncate">{{ file.orig_name }}</p>
                  </div>
                  <button
                    class="opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 px-2 py-1 text-xs text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg"
                    @click.stop="startEdit(file)"
                    title="编辑标题"
                  >✏️</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Form state -->
        <div v-else-if="rightPanelState === 'form'" data-panel="form" class="h-full flex flex-col">
          <div class="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-4 flex-shrink-0 shadow-md">
            <div class="flex items-center gap-3">
              <button class="text-indigo-200 hover:text-white transition-colors text-sm" @click="rightPanelState = 'domain'">← 返回</button>
              <span class="text-indigo-300">|</span>
              <span data-domain-badge class="px-3 py-1 text-xs font-semibold rounded-full bg-white/20 text-white">{{ selectedDomain }}</span>
              <h2 class="text-lg font-bold text-white">新建摄入</h2>
            </div>
          </div>

          <div class="flex-1 overflow-y-auto p-6">
            <div class="max-w-lg space-y-5">

              <!-- Title -->
              <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
                <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                  标题 <span class="text-red-400">*</span>
                </label>
                <input
                  data-input="title"
                  type="text"
                  v-model="formTitle"
                  placeholder="为这篇内容起一个标题"
                  class="w-full px-3 py-2.5 rounded-lg border border-gray-200 bg-gray-50 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent transition-all"
                />
              </div>

              <!-- Source type -->
              <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
                <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">摄入方式</label>
                <div class="flex gap-2 mb-4">
                  <button
                    data-source-type="url"
                    :class="[
                      'flex-1 py-2 rounded-lg text-sm font-semibold transition-all duration-200 border-2',
                      sourceType === 'url'
                        ? 'bg-gradient-to-r from-blue-500 to-indigo-500 text-white border-transparent shadow-md'
                        : 'bg-white text-gray-600 border-gray-200 hover:border-indigo-300 hover:text-indigo-600'
                    ]"
                    @click="sourceType = 'url'"
                  >🌐 URL</button>
                  <button
                    data-source-type="text"
                    :class="[
                      'flex-1 py-2 rounded-lg text-sm font-semibold transition-all duration-200 border-2',
                      sourceType === 'text'
                        ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white border-transparent shadow-md'
                        : 'bg-white text-gray-600 border-gray-200 hover:border-purple-300 hover:text-purple-600'
                    ]"
                    @click="sourceType = 'text'"
                  >📝 文本</button>
                  <button
                    data-source-type="file"
                    :class="[
                      'flex-1 py-2 rounded-lg text-sm font-semibold transition-all duration-200 border-2',
                      sourceType === 'file'
                        ? 'bg-gradient-to-r from-green-500 to-emerald-500 text-white border-transparent shadow-md'
                        : 'bg-white text-gray-600 border-gray-200 hover:border-green-300 hover:text-green-600'
                    ]"
                    @click="sourceType = 'file'"
                  >📄 文件</button>
                </div>

                <div v-if="sourceType === 'url'">
                  <input
                    data-input="source_url"
                    type="url"
                    v-model="sourceUrl"
                    placeholder="https://example.com/article"
                    class="w-full px-3 py-2.5 rounded-lg border border-gray-200 bg-gray-50 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent transition-all"
                  />
                </div>

                <div v-if="sourceType === 'text'">
                  <textarea
                    data-input="content"
                    v-model="textContent"
                    placeholder="粘贴文本内容…"
                    class="w-full px-3 py-2.5 rounded-lg border border-gray-200 bg-gray-50 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent transition-all resize-y"
                    style="min-height: 55vh"
                  />
                </div>

                <div v-if="sourceType === 'file'">
                  <label class="flex flex-col items-center justify-center w-full h-28 border-2 border-dashed border-indigo-200 rounded-lg cursor-pointer bg-indigo-50/30 hover:bg-indigo-50 transition-all">
                    <span class="text-2xl mb-1">📁</span>
                    <span class="text-sm text-indigo-600 font-medium">{{ selectedFile ? selectedFile.name : '点击或拖拽文件到此处' }}</span>
                    <span class="text-xs text-gray-400 mt-0.5">支持 PDF、TXT、MD 等格式</span>
                    <input data-input="file" type="file" class="hidden" @change="onFileChange" />
                  </label>
                </div>
              </div>

              <!-- Error -->
              <div v-if="formError" data-ingest-error class="flex items-center gap-2 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-600 shadow-sm">
                <span>⚠️</span> {{ formError }}
              </div>

              <!-- Submit -->
              <button
                data-action="submit-ingest"
                :disabled="isSubmitting"
                :class="[
                  'w-full py-3 rounded-xl text-sm font-bold transition-all duration-200 shadow-md',
                  isSubmitting
                    ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                    : 'bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white hover:shadow-lg'
                ]"
                @click="submitForm"
              >{{ isSubmitting ? '摄入中…' : '🚀 开始摄入' }}</button>
            </div>
          </div>
        </div>

        <!-- Result state -->
        <div v-else-if="rightPanelState === 'result'" data-panel="result" class="h-full flex flex-col">
          <div class="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-4 flex-shrink-0 shadow-md">
            <h2 class="text-lg font-bold text-white">摄入进行中</h2>
            <p class="text-xs text-indigo-100 mt-0.5">内容正在处理，完成后将自动刷新</p>
          </div>
          <div class="flex-1 flex items-center justify-center p-6">
            <div class="bg-white rounded-2xl border border-gray-200 shadow-lg p-8 max-w-md w-full text-center">
              <div class="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-amber-100 to-orange-100 rounded-2xl flex items-center justify-center shadow-md">
                <span class="text-3xl animate-pulse">⏳</span>
              </div>
              <h3 class="text-base font-bold text-gray-800 mb-1">{{ submittedTitle }}</h3>
              <p class="text-sm text-gray-500 mb-6">正在摄入到「{{ selectedDomain }}」领域</p>
              <div class="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
                <div class="h-2 bg-gradient-to-r from-blue-400 to-purple-500 rounded-full animate-pulse" style="width: 60%"></div>
              </div>
              <button class="mt-6 text-xs text-gray-400 hover:text-indigo-600 transition-colors" @click="rightPanelState = 'domain'">
                返回领域列表
              </button>
            </div>
          </div>
        </div>

        <!-- Content viewer state -->
        <div v-else-if="rightPanelState === 'content'" data-panel="content" class="h-full flex flex-col">
          <div class="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-4 flex-shrink-0 shadow-md">
            <div class="flex items-center gap-3">
              <button class="text-indigo-200 hover:text-white transition-colors text-sm" @click="rightPanelState = 'domain'">← 返回</button>
              <span class="text-indigo-300">|</span>
              <h2 class="text-base font-bold text-white truncate">{{ viewingTitle }}</h2>
            </div>
          </div>
          <div class="flex-1 overflow-y-auto p-6">
            <div v-if="!viewingFilename" class="flex flex-col items-center justify-center h-48 gap-3 text-gray-500">
              <span class="text-4xl">📝</span>
              <p class="text-sm">无原始文件可预览</p>
              <p class="text-xs text-gray-400">内容已分块存入知识库，可在问答中使用</p>
            </div>
            <div v-else-if="contentLoading" class="flex items-center justify-center h-48 text-gray-400">
              <span class="animate-spin text-2xl mr-2">⏳</span> 加载中…
            </div>
            <div v-else-if="contentError" class="flex items-center gap-2 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-600">
              ⚠️ 内容加载失败，文件可能已被删除
            </div>
            <div v-else class="bg-white rounded-xl border border-gray-200 shadow-sm p-6 prose max-w-none" v-html="renderedContent" />
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { useIngestStore } from '../stores/ingest.js'
import { useFileContent } from '../composables/useFileContent.js'
import { DOMAINS } from '../constants/domains.js'

const store = useIngestStore()

const rightPanelState = ref('welcome')
const selectedDomain = ref('')
const files = ref([])
const expandedDomains = reactive({})
const viewingFileId = ref(null)
const viewingTitle = ref('')
const viewingSourceType = ref('')
const viewingFilename = ref('')

const formTitle = ref('')
const sourceType = ref('url')
const sourceUrl = ref('')
const textContent = ref('')
const selectedFile = ref(null)
const formError = ref('')
const isSubmitting = ref(false)
const submittedTitle = ref('')

const editingFileId = ref(null)
const editingTitle = ref('')
const editInputRef = ref(null)

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
  if (domain === '其他') {
    return files.value.filter(f => f.domain === '其他' || !DOMAINS.includes(f.domain))
  }
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
  viewingFileId.value = file.file_id
  viewingTitle.value = file.title || file.orig_name
  viewingSourceType.value = file.source_type
  viewingFilename.value = file.filename || ''
  rightPanelState.value = 'content'
  if (file.filename) {
    loadContent(file.file_id, file.orig_name || file.filename)
  }
}

function startEdit(file) {
  editingFileId.value = file.file_id
  editingTitle.value = file.title || ''
  nextTick(() => {
    if (editInputRef.value) {
      const el = Array.isArray(editInputRef.value) ? editInputRef.value[0] : editInputRef.value
      el?.focus()
    }
  })
}

function cancelEdit() {
  editingFileId.value = null
  editingTitle.value = ''
}

async function confirmEdit(file) {
  if (editingFileId.value !== file.file_id) return
  const newTitle = editingTitle.value.trim() || null
  try {
    await store._api.patch('/files/' + file.file_id, { title: newTitle })
    files.value = files.value.map(f =>
      f.file_id === file.file_id ? { ...f, title: newTitle } : f
    )
    if (viewingFileId.value === file.file_id) {
      viewingTitle.value = newTitle || file.orig_name
    }
  } catch {
    // keep existing title on error
  }
  editingFileId.value = null
  editingTitle.value = ''
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
