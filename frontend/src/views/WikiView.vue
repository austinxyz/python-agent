<template>
  <div class="h-screen flex flex-col bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50">

    <!-- Page Header -->
    <div class="bg-gradient-to-r from-blue-600 to-purple-600 shadow-lg px-6 py-4 flex-shrink-0">
      <h1 class="text-2xl font-bold text-white">知识库</h1>
      <p class="text-xs text-blue-100 mt-1">浏览和搜索知识条目</p>
    </div>

    <!-- Main: Two-column layout -->
    <div class="flex-1 flex overflow-hidden">

      <!-- LEFT SIDEBAR -->
      <div class="w-60 flex-shrink-0 bg-white border-r border-gray-200 flex flex-col shadow-lg">

        <!-- Sidebar header with search -->
        <div class="px-4 py-3 border-b border-gray-200 bg-gradient-to-r from-indigo-500 to-purple-500">
          <h2 class="text-sm font-semibold text-white mb-2">📚 知识领域</h2>
          <input
            data-search-input
            v-model="store.searchQuery"
            type="text"
            placeholder="搜索知识条目…"
            class="w-full px-2 py-1 rounded-lg text-xs bg-white/90 text-gray-700 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-300"
          />
        </div>

        <!-- Error state -->
        <div v-if="store.error" class="px-4 py-3 text-xs text-red-500 border-b border-red-100 bg-red-50">
          加载失败：{{ store.error }}
        </div>

        <!-- Domain list -->
        <div class="flex-1 overflow-y-auto">
          <div v-for="(entries, domain) in store.filteredTree" :key="domain">

            <!-- Domain row -->
            <div class="flex items-center gap-2 px-3 py-3 border-b border-gray-100 hover:bg-gradient-to-r hover:from-gray-50 hover:to-blue-50 hover:shadow-sm cursor-pointer transition-all duration-200">
              <span class="flex-1 text-sm font-bold text-gray-800 truncate">{{ domain }}</span>

              <!-- File count badge -->
              <span
                v-if="entries.length > 0"
                class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-indigo-100 text-indigo-600 flex-shrink-0"
              >{{ entries.length }} 篇</span>

              <!-- Chevron -->
              <button
                data-domain-chevron
                class="flex-shrink-0 text-gray-300 hover:text-indigo-500 transition-colors p-0.5"
                @click.stop="toggleExpand(domain)"
              >
                <svg
                  class="w-3.5 h-3.5 transition-transform duration-200"
                  :class="expandedDomains[domain] ? 'rotate-90' : ''"
                  viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
                >
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              </button>
            </div>

            <!-- Expanded file list -->
            <div v-if="expandedDomains[domain]" class="bg-gray-50 border-b border-gray-100">
              <div v-if="entries.length === 0" class="px-6 py-2.5 text-xs text-gray-400 italic">
                暂无条目
              </div>
              <button
                v-for="entry in entries"
                :key="entry.file_id"
                data-sidebar-file
                :class="[
                  'w-full text-left px-5 py-2 text-xs transition-all duration-200 block border-b border-gray-100 last:border-0',
                  viewingFileId === entry.file_id
                    ? 'bg-gradient-to-r from-indigo-50 to-purple-50 text-indigo-700 font-semibold border-l-2 border-l-indigo-500 active'
                    : 'text-gray-600 hover:bg-white hover:text-indigo-600'
                ]"
                @click="onEntryClick(entry)"
              >
                <span class="truncate block leading-relaxed">{{ entry.title || entry.orig_name }}</span>
              </button>
            </div>

          </div>
        </div>
      </div>

      <!-- RIGHT PANEL -->
      <div class="flex-1 overflow-hidden flex flex-col">

        <!-- Welcome state -->
        <div v-if="rightPanelState === 'welcome'" data-panel="welcome" class="flex-1 flex items-center justify-center">
          <div class="text-center">
            <div class="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-blue-100 to-purple-100 rounded-2xl flex items-center justify-center shadow-lg">
              <span class="text-4xl">📖</span>
            </div>
            <h2 class="text-xl font-bold text-gray-800 mb-2">欢迎使用知识库</h2>
            <p class="text-sm text-gray-500">从左侧展开领域，点击条目查看内容</p>
          </div>
        </div>

        <!-- Content viewer state -->
        <div v-else-if="rightPanelState === 'content'" data-panel="content" class="flex-1 flex flex-col overflow-hidden">
          <!-- Fixed header -->
          <div class="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-4 flex-shrink-0 shadow-md">
            <div class="flex items-center justify-between gap-3">
              <div class="flex items-center gap-3 min-w-0">
                <button class="text-indigo-200 hover:text-white transition-colors text-sm flex-shrink-0" @click="rightPanelState = 'welcome'">← 返回</button>
                <span class="text-indigo-300 flex-shrink-0">|</span>
                <span data-domain-badge class="px-3 py-1 text-xs font-semibold rounded-full bg-white/20 text-white flex-shrink-0">{{ viewingDomain }}</span>
                <h2 class="text-base font-bold text-white truncate">{{ viewingTitle }}</h2>
              </div>
              <a
                v-if="viewingFileId"
                data-download-btn
                :href="`/api/files/${viewingFileId}/download`"
                class="flex-shrink-0 px-3 py-1.5 bg-white/20 hover:bg-white/30 text-white text-xs font-semibold rounded-lg transition-all"
              >⬇ 下载</a>
            </div>
          </div>

          <!-- Scrollable content -->
          <div class="flex-1 overflow-y-auto p-6">
            <div v-if="!viewingFilename" class="flex flex-col items-center justify-center h-48 gap-3 text-gray-400">
              <span class="text-4xl">📝</span>
              <p class="text-sm">无原始文件可预览</p>
              <p class="text-xs text-gray-400">内容已分块存入知识库，可在问答中使用</p>
            </div>
            <div v-else-if="contentLoading" class="flex items-center justify-center h-48 text-gray-400">
              <span class="animate-spin text-2xl mr-2">⏳</span> 加载中…
            </div>
            <div v-else-if="contentError" class="flex items-center gap-2 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-600">
              ⚠️ 内容加载失败
            </div>
            <div v-else class="bg-white rounded-xl border border-gray-200 shadow-sm p-6 prose max-w-none" v-html="renderedContent" />
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useWikiStore } from '../stores/wiki.js'
import { useFileContent } from '../composables/useFileContent.js'

const store = useWikiStore()

const rightPanelState = ref('welcome')
const expandedDomains = reactive({})
const viewingFileId = ref(null)
const viewingTitle = ref('')
const viewingDomain = ref('')
const viewingFilename = ref('')

const { loading: contentLoading, error: contentError, renderedContent, load: loadContent } = useFileContent()

onMounted(() => store.fetchTree())

function toggleExpand(domain) {
  expandedDomains[domain] = !expandedDomains[domain]
}

function onEntryClick(entry) {
  store.selectFile(entry.file_id)
  viewingFileId.value = entry.file_id
  viewingTitle.value = entry.title || entry.orig_name
  viewingDomain.value = entry.domain
  viewingFilename.value = entry.filename || ''
  rightPanelState.value = 'content'
  if (entry.filename) {
    loadContent(entry.file_id, entry.filename)
  }
}
</script>
