<template>
  <!--
    IngestView — redesigned 2026-05-08 against docs/design/notion.md.
    Same data-* selectors as before; only the visual layer changed.
  -->
  <div class="h-screen flex flex-col bg-notion-surface-soft text-notion-ink">

    <!-- Page Header — brand-navy hero band -->
    <div class="bg-notion-brand-navy text-notion-on-dark px-6 py-5 flex-shrink-0">
      <h1 class="text-xl font-semibold tracking-tight leading-tight">原始材料库</h1>
      <p class="text-[13px] text-notion-on-dark-muted mt-0.5">摄入文件、网页或文本，按领域分类管理</p>
    </div>

    <!-- Two-column layout -->
    <div class="flex-1 flex overflow-hidden">

      <!-- LEFT SIDEBAR -->
      <div class="w-60 flex-shrink-0 bg-notion-canvas border-r border-notion-hairline flex flex-col">
        <div class="px-4 py-3 border-b border-notion-hairline-soft flex items-center justify-between">
          <h2 class="text-[11px] font-semibold uppercase tracking-[0.08em] text-notion-steel">领域分类</h2>
          <span class="text-[11px] text-notion-stone">{{ files.length }} 个文件</span>
        </div>

        <div class="flex-1 overflow-y-auto py-1">
          <div v-for="d in DOMAINS" :key="d">
            <div
              :class="[
                'flex items-center gap-2 px-3 py-2 cursor-pointer transition-colors',
                selectedDomain === d && rightPanelState !== 'welcome'
                  ? 'bg-notion-surface border-l-2 border-l-notion-primary'
                  : 'hover:bg-notion-surface'
              ]"
            >
              <span
                data-domain-name
                class="flex-1 text-[13px] font-medium text-notion-charcoal truncate"
                @click="onDomainNameClick(d)"
              >{{ d }}</span>

              <span
                v-if="filesForDomain(d).length > 0"
                class="px-1.5 py-0.5 text-[11px] font-semibold rounded-full bg-notion-surface border border-notion-hairline text-notion-steel flex-shrink-0"
              >{{ filesForDomain(d).length }}</span>

              <button
                data-domain-chevron
                class="flex-shrink-0 text-notion-stone hover:text-notion-steel transition-colors p-0.5"
                @click.stop="toggleExpand(d)"
              >
                <svg
                  class="w-3 h-3 transition-transform duration-200"
                  :class="expandedDomains[d] ? 'rotate-90' : ''"
                  viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
                >
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              </button>
            </div>

            <div v-if="expandedDomains[d]" class="bg-notion-surface-soft">
              <div v-if="filesForDomain(d).length === 0" class="px-6 py-2 text-[12px] text-notion-stone italic">
                暂无文件
              </div>
              <button
                v-for="file in filesForDomain(d)"
                :key="file.file_id"
                data-sidebar-file
                :class="[
                  'w-full text-left px-6 py-1.5 text-[13px] block transition-colors',
                  viewingFileId === file.file_id
                    ? 'bg-notion-canvas text-notion-ink font-medium border-l-2 border-l-notion-primary'
                    : 'text-notion-slate hover:bg-notion-canvas hover:text-notion-ink'
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
      <div class="flex-1 overflow-y-auto bg-notion-surface-soft">

        <!-- Welcome -->
        <div v-if="rightPanelState === 'welcome'" data-panel="welcome" class="h-full flex items-center justify-center px-8">
          <div class="text-center max-w-md">
            <div class="w-14 h-14 mx-auto mb-5 rounded-md bg-notion-tint-lavender flex items-center justify-center">
              <svg class="w-7 h-7 text-notion-brand-purple-800" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 19v-7m0 0L8 16m4-4l4 4M20 7H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z"/></svg>
            </div>
            <h2 class="text-lg font-semibold text-notion-ink mb-2">欢迎使用原始材料库</h2>
            <p class="text-[14px] text-notion-slate leading-relaxed">从左侧选择领域开始浏览，或新建摄入。</p>
          </div>
        </div>

        <!-- Domain state -->
        <div v-else-if="rightPanelState === 'domain'" data-panel="domain" class="h-full flex flex-col">
          <div class="bg-notion-canvas border-b border-notion-hairline px-8 py-5 flex-shrink-0">
            <div class="flex items-center justify-between">
              <div>
                <h2 class="text-[22px] font-semibold tracking-tight text-notion-ink">{{ selectedDomain }}</h2>
                <p class="text-[12px] text-notion-steel mt-0.5">{{ filesForDomain(selectedDomain).length }} 个文件</p>
              </div>
              <button
                data-action="new-ingest"
                class="h-9 px-4 bg-notion-primary hover:bg-notion-primary-pressed text-notion-on-primary text-[13px] font-medium rounded-md transition-colors"
                @click="openForm"
              >+ 新建摄入</button>
            </div>
          </div>

          <div class="flex-1 px-8 py-6 overflow-y-auto">
            <div v-if="filesForDomain(selectedDomain).length === 0" class="flex flex-col items-center justify-center h-48 text-notion-stone">
              <p class="text-[14px]">该领域暂无文件</p>
              <p class="text-[12px] mt-1 text-notion-muted-text">点击右上角「+ 新建摄入」添加</p>
            </div>
            <div v-else class="space-y-2 max-w-3xl">
              <div
                v-for="file in filesForDomain(selectedDomain)"
                :key="file.file_id"
                class="group bg-notion-canvas rounded-lg border border-notion-hairline hover:border-notion-hairline-strong transition-colors p-4"
              >
                <!-- Edit mode -->
                <div v-if="editingFileId === file.file_id" class="flex items-center gap-2">
                  <input
                    ref="editInputRef"
                    v-model="editingTitle"
                    class="flex-1 h-10 px-3 rounded-md border border-notion-primary text-[14px] text-notion-ink focus:outline-none focus:ring-1 focus:ring-notion-primary"
                    placeholder="输入标题"
                    @keydown.enter="confirmEdit(file)"
                    @keydown.esc="cancelEdit"
                  />
                  <button
                    class="h-10 px-3 bg-notion-primary hover:bg-notion-primary-pressed text-notion-on-primary text-[13px] font-medium rounded-md transition-colors"
                    @click="confirmEdit(file)"
                  >保存</button>
                  <button
                    class="h-10 px-3 bg-transparent hover:bg-notion-surface text-notion-ink text-[13px] font-medium rounded-md border border-notion-hairline-strong transition-colors"
                    @click="cancelEdit"
                  >取消</button>
                </div>

                <!-- Normal mode -->
                <div v-else class="flex items-start gap-3">
                  <div
                    :class="[
                      'w-9 h-9 rounded-md flex items-center justify-center flex-shrink-0 cursor-pointer text-[14px] font-semibold',
                      file.source_type === 'url'
                        ? 'bg-notion-tint-sky text-notion-link-blue'
                        : file.source_type === 'file'
                          ? 'bg-notion-tint-mint text-notion-brand-green'
                          : 'bg-notion-tint-lavender text-notion-brand-purple-800',
                    ]"
                    @click="onFileClick(file)"
                  >
                    <span>{{ file.source_type === 'url' ? 'URL' : file.source_type === 'file' ? 'F' : 'T' }}</span>
                  </div>
                  <div class="flex-1 min-w-0 cursor-pointer" @click="onFileClick(file)">
                    <p class="text-[14px] font-medium text-notion-ink leading-snug">{{ file.title || file.orig_name }}</p>
                    <p class="text-[12px] text-notion-stone mt-0.5 truncate">{{ file.orig_name }}</p>
                  </div>
                  <button
                    class="opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 h-7 px-2 text-[12px] text-notion-steel hover:text-notion-ink hover:bg-notion-surface rounded-md"
                    @click.stop="startEdit(file)"
                    title="编辑标题"
                  >编辑</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Form state -->
        <div v-else-if="rightPanelState === 'form'" data-panel="form" class="h-full flex flex-col">
          <div class="bg-notion-canvas border-b border-notion-hairline px-8 py-5 flex-shrink-0">
            <div class="flex items-center gap-3">
              <button class="text-[13px] text-notion-steel hover:text-notion-ink transition-colors" @click="rightPanelState = 'domain'">← 返回</button>
              <span class="text-notion-hairline-strong">|</span>
              <span data-domain-badge class="px-2.5 py-1 text-[12px] font-semibold rounded-md bg-notion-tint-lavender text-notion-brand-purple-800">{{ selectedDomain }}</span>
              <h2 class="text-[18px] font-semibold text-notion-ink">新建摄入</h2>
            </div>
          </div>

          <div class="flex-1 overflow-y-auto px-8 py-6">
            <div class="max-w-2xl space-y-4">

              <!-- Title -->
              <div class="bg-notion-canvas rounded-lg border border-notion-hairline p-5">
                <label class="block text-[11px] font-semibold uppercase tracking-[0.08em] text-notion-steel mb-1.5">
                  标题 <span class="text-notion-error">*</span>
                </label>
                <input
                  data-input="title"
                  type="text"
                  v-model="formTitle"
                  placeholder="为这篇内容起一个标题"
                  class="w-full h-11 px-3 bg-notion-canvas border border-notion-hairline-strong text-notion-ink text-[14px] rounded-md placeholder:text-notion-stone focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary"
                />
              </div>

              <!-- Source type -->
              <div class="bg-notion-canvas rounded-lg border border-notion-hairline p-5 space-y-4">
                <label class="block text-[11px] font-semibold uppercase tracking-[0.08em] text-notion-steel">摄入方式</label>
                <div class="flex gap-2">
                  <button
                    data-source-type="url"
                    :class="[
                      'flex-1 h-9 rounded-md text-[13px] font-medium transition-colors',
                      sourceType === 'url'
                        ? 'bg-notion-ink-deep text-notion-on-dark'
                        : 'bg-transparent text-notion-charcoal border border-notion-hairline-strong hover:bg-notion-surface'
                    ]"
                    @click="sourceType = 'url'"
                  >URL</button>
                  <button
                    data-source-type="text"
                    :class="[
                      'flex-1 h-9 rounded-md text-[13px] font-medium transition-colors',
                      sourceType === 'text'
                        ? 'bg-notion-ink-deep text-notion-on-dark'
                        : 'bg-transparent text-notion-charcoal border border-notion-hairline-strong hover:bg-notion-surface'
                    ]"
                    @click="sourceType = 'text'"
                  >文本</button>
                  <button
                    data-source-type="file"
                    :class="[
                      'flex-1 h-9 rounded-md text-[13px] font-medium transition-colors',
                      sourceType === 'file'
                        ? 'bg-notion-ink-deep text-notion-on-dark'
                        : 'bg-transparent text-notion-charcoal border border-notion-hairline-strong hover:bg-notion-surface'
                    ]"
                    @click="sourceType = 'file'"
                  >文件</button>
                </div>

                <div v-if="sourceType === 'url'">
                  <input
                    data-input="source_url"
                    type="url"
                    v-model="sourceUrl"
                    placeholder="https://example.com/article"
                    class="w-full h-11 px-3 bg-notion-canvas border border-notion-hairline-strong text-notion-ink text-[14px] rounded-md placeholder:text-notion-stone focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary"
                  />
                </div>

                <div v-if="sourceType === 'text'">
                  <textarea
                    data-input="content"
                    v-model="textContent"
                    placeholder="粘贴文本内容…"
                    class="w-full px-3 py-2 bg-notion-canvas border border-notion-hairline-strong text-notion-ink text-[14px] rounded-md placeholder:text-notion-stone focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary resize-y"
                    style="min-height: 55vh"
                  />
                </div>

                <div v-if="sourceType === 'file'">
                  <label class="flex flex-col items-center justify-center w-full h-28 border border-dashed border-notion-hairline-strong rounded-md cursor-pointer bg-notion-surface-soft hover:bg-notion-surface transition-colors">
                    <span class="text-[14px] text-notion-charcoal font-medium">{{ selectedFile ? selectedFile.name : '点击或拖拽文件到此处' }}</span>
                    <span class="text-[12px] text-notion-stone mt-1">支持 PDF、TXT、MD 等格式</span>
                    <input data-input="file" type="file" class="hidden" @change="onFileChange" />
                  </label>
                </div>
              </div>

              <!-- Error -->
              <div v-if="formError" data-ingest-error class="px-4 py-3 bg-notion-tint-rose border border-notion-hairline rounded-md text-[13px] text-notion-error">
                {{ formError }}
              </div>

              <!-- Submit -->
              <button
                data-action="submit-ingest"
                :disabled="isSubmitting"
                :class="[
                  'w-full h-11 rounded-md text-[14px] font-medium transition-colors',
                  isSubmitting
                    ? 'bg-notion-hairline text-notion-muted-text cursor-not-allowed'
                    : 'bg-notion-primary hover:bg-notion-primary-pressed text-notion-on-primary'
                ]"
                @click="submitForm"
              >{{ isSubmitting ? '摄入中…' : '开始摄入' }}</button>
            </div>
          </div>
        </div>

        <!-- Result state -->
        <div v-else-if="rightPanelState === 'result'" data-panel="result" class="h-full flex flex-col">
          <div class="bg-notion-canvas border-b border-notion-hairline px-8 py-5 flex-shrink-0">
            <h2 class="text-[18px] font-semibold text-notion-ink">摄入进行中</h2>
            <p class="text-[12px] text-notion-steel mt-0.5">内容正在处理，完成后将自动刷新</p>
          </div>
          <div class="flex-1 flex items-center justify-center px-8 py-6">
            <div class="bg-notion-canvas rounded-lg border border-notion-hairline p-8 max-w-md w-full text-center">
              <div class="w-12 h-12 mx-auto mb-4 rounded-md bg-notion-tint-yellow flex items-center justify-center">
                <span class="text-lg text-notion-brand-orange-deep animate-pulse">⏳</span>
              </div>
              <h3 class="text-[15px] font-semibold text-notion-ink mb-1">{{ submittedTitle }}</h3>
              <p class="text-[13px] text-notion-steel mb-5">正在摄入到「{{ selectedDomain }}」领域</p>
              <div class="w-full bg-notion-surface rounded-full h-1.5 overflow-hidden">
                <div class="h-1.5 bg-notion-primary rounded-full animate-pulse" style="width: 60%"></div>
              </div>
              <button class="mt-5 text-[12px] text-notion-steel hover:text-notion-ink transition-colors" @click="rightPanelState = 'domain'">
                返回领域列表
              </button>
            </div>
          </div>
        </div>

        <!-- Content viewer state -->
        <div v-else-if="rightPanelState === 'content'" data-panel="content" class="h-full flex flex-col">
          <div class="bg-notion-canvas border-b border-notion-hairline px-8 py-5 flex-shrink-0">
            <div class="flex items-center gap-3">
              <button class="text-[13px] text-notion-steel hover:text-notion-ink transition-colors" @click="rightPanelState = 'domain'">← 返回</button>
              <span class="text-notion-hairline-strong">|</span>
              <h2 class="text-[16px] font-semibold text-notion-ink truncate">{{ viewingTitle }}</h2>
            </div>
          </div>
          <div class="flex-1 overflow-y-auto px-8 py-6">
            <div v-if="!viewingFilename" class="flex flex-col items-center justify-center h-48 text-notion-stone">
              <p class="text-[14px]">无原始文件可预览</p>
              <p class="text-[12px] text-notion-muted-text mt-1">内容已分块存入知识库，可在问答中使用</p>
            </div>
            <div v-else-if="contentLoading" class="flex items-center justify-center h-48 text-notion-stone text-[14px]">
              加载中…
            </div>
            <div v-else-if="contentError" class="px-4 py-3 bg-notion-tint-rose border border-notion-hairline rounded-md text-[13px] text-notion-error">
              内容加载失败，文件可能已被删除
            </div>
            <div v-else class="bg-notion-canvas rounded-lg border border-notion-hairline p-6 prose max-w-none" v-html="renderedContent" />
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
