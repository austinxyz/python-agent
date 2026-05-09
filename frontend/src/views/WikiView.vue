<template>
  <!--
    WikiView — redesigned 2026-05-08 against docs/design/notion.md.
    The literal `active` class on the selected sidebar file is preserved
    because tests/views/WikiView.test.js asserts on it explicitly.
  -->
  <div class="h-screen flex flex-col bg-notion-surface-soft text-notion-ink">

    <!-- Page Header -->
    <div class="bg-notion-brand-navy text-notion-on-dark px-6 py-5 flex-shrink-0">
      <div class="flex items-center gap-3">
        <button
          data-tree-toggle
          class="md:hidden p-2 -ml-2 rounded-md hover:bg-white/10 text-notion-on-dark"
          aria-label="知识领域"
          @click="drawerOpen = true"
        >
          <Menu class="w-5 h-5" />
        </button>
        <div class="flex-1">
          <h1 class="text-xl font-semibold tracking-tight leading-tight">知识库</h1>
          <p class="text-[13px] text-notion-on-dark-muted mt-0.5 hidden sm:block">浏览和搜索知识条目</p>
        </div>
      </div>
    </div>

    <!-- Two-column layout -->
    <div class="flex-1 flex overflow-hidden">

      <!-- LEFT SIDEBAR (md+) -->
      <div data-tree-inline class="w-60 flex-shrink-0 bg-notion-canvas border-r border-notion-hairline hidden md:flex flex-col">

        <!-- Sidebar header with search -->
        <div class="px-4 py-3 border-b border-notion-hairline-soft space-y-2">
          <h2 class="text-[11px] font-semibold uppercase tracking-[0.08em] text-notion-steel">知识领域</h2>
          <input
            data-search-input
            v-model="store.searchQuery"
            type="text"
            placeholder="搜索知识条目…"
            class="w-full h-8 px-2.5 text-[13px] bg-notion-surface text-notion-ink rounded-md border border-notion-hairline placeholder:text-notion-stone focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary"
          />
        </div>

        <!-- Error state -->
        <div v-if="store.error" class="px-4 py-2 text-[12px] text-notion-error border-b border-notion-hairline bg-notion-tint-rose">
          加载失败：{{ store.error }}
        </div>

        <!-- Domain list -->
        <div class="flex-1 overflow-y-auto py-1">
          <div v-for="(entries, domain) in store.filteredTree" :key="domain">

            <div class="flex items-center gap-2 px-3 py-2 hover:bg-notion-surface cursor-pointer transition-colors">
              <span class="flex-1 text-[13px] font-medium text-notion-charcoal truncate">{{ domain }}</span>

              <span
                v-if="entries.length > 0"
                class="px-1.5 py-0.5 text-[11px] font-semibold rounded-full bg-notion-surface border border-notion-hairline text-notion-steel flex-shrink-0"
              >{{ entries.length }}</span>

              <button
                data-domain-chevron
                class="flex-shrink-0 text-notion-stone hover:text-notion-steel transition-colors p-0.5"
                @click.stop="toggleExpand(domain)"
              >
                <svg
                  class="w-3 h-3 transition-transform duration-200"
                  :class="expandedDomains[domain] ? 'rotate-90' : ''"
                  viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
                >
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              </button>
            </div>

            <div v-if="expandedDomains[domain]" class="bg-notion-surface-soft">
              <div v-if="entries.length === 0" class="px-6 py-2 text-[12px] text-notion-stone italic">
                暂无条目
              </div>
              <button
                v-for="entry in entries"
                :key="entry.file_id"
                data-sidebar-file
                :class="[
                  'w-full text-left px-6 py-1.5 text-[13px] block transition-colors',
                  viewingFileId === entry.file_id
                    ? 'bg-notion-canvas text-notion-ink font-medium border-l-2 border-l-notion-primary active'
                    : 'text-notion-slate hover:bg-notion-canvas hover:text-notion-ink'
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
      <div class="flex-1 overflow-hidden flex flex-col bg-notion-surface-soft">

        <!-- Welcome -->
        <div v-if="rightPanelState === 'welcome'" data-panel="welcome" class="flex-1 flex items-center justify-center px-8">
          <div class="text-center max-w-md">
            <div class="w-14 h-14 mx-auto mb-5 rounded-md bg-notion-tint-mint flex items-center justify-center">
              <svg class="w-7 h-7 text-notion-brand-green" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2zM22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>
            </div>
            <h2 class="text-lg font-semibold text-notion-ink mb-2">欢迎使用知识库</h2>
            <p class="text-[14px] text-notion-slate leading-relaxed">从左侧展开领域，点击条目查看内容。</p>
          </div>
        </div>

        <!-- Content viewer -->
        <div v-else-if="rightPanelState === 'content'" data-panel="content" class="flex-1 flex flex-col overflow-hidden">
          <div class="bg-notion-canvas border-b border-notion-hairline px-8 py-5 flex-shrink-0">
            <div class="flex items-center justify-between gap-3">
              <div class="flex items-center gap-3 min-w-0">
                <button class="text-[13px] text-notion-steel hover:text-notion-ink transition-colors flex-shrink-0" @click="rightPanelState = 'welcome'">← 返回</button>
                <span class="text-notion-hairline-strong flex-shrink-0">|</span>
                <span data-domain-badge class="px-2.5 py-1 text-[12px] font-semibold rounded-md bg-notion-tint-lavender text-notion-brand-purple-800 flex-shrink-0">{{ viewingDomain }}</span>
                <h2 class="text-[16px] font-semibold text-notion-ink truncate">{{ viewingTitle }}</h2>
              </div>
              <a
                v-if="viewingFileId"
                data-download-btn
                :href="`/api/files/${viewingFileId}/download`"
                class="flex-shrink-0 h-8 px-3 inline-flex items-center bg-transparent hover:bg-notion-surface text-notion-ink text-[13px] font-medium rounded-md border border-notion-hairline-strong transition-colors"
              >下载</a>
            </div>
          </div>

          <div class="flex-1 overflow-y-auto px-8 py-6">
            <div v-if="!viewingFilename" class="flex flex-col items-center justify-center h-48 gap-2 text-notion-stone">
              <p class="text-[14px]">无原始文件可预览</p>
              <p class="text-[12px] text-notion-muted-text">内容已分块存入知识库，可在问答中使用</p>
            </div>
            <div v-else-if="contentLoading" class="flex items-center justify-center h-48 text-notion-stone text-[14px]">
              加载中…
            </div>
            <div v-else-if="contentError" class="px-4 py-3 bg-notion-tint-rose border border-notion-hairline rounded-md text-[13px] text-notion-error">
              内容加载失败
            </div>
            <div v-else class="bg-notion-canvas rounded-lg border border-notion-hairline p-6 prose max-w-none" v-html="renderedContent" />
          </div>
        </div>

      </div>
    </div>

    <!-- MOBILE TREE DRAWER (md-) -->
    <MobileDrawer :open="drawerOpen" title="知识领域" @close="drawerOpen = false">
      <div data-tree-drawer class="py-1">
        <div class="px-4 py-2 border-b border-notion-hairline-soft">
          <input
            v-model="store.searchQuery"
            type="text"
            placeholder="搜索知识条目…"
            class="w-full h-9 px-2.5 text-[13px] bg-notion-surface text-notion-ink rounded-md border border-notion-hairline placeholder:text-notion-stone focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary"
          />
        </div>
        <div v-for="(entries, domain) in store.filteredTree" :key="domain" data-drawer-domain>
          <div class="flex items-center gap-2 px-3 py-2.5 hover:bg-notion-surface cursor-pointer transition-colors">
            <span class="flex-1 text-[14px] font-medium text-notion-charcoal truncate">{{ domain }}</span>
            <span
              v-if="entries.length > 0"
              class="px-1.5 py-0.5 text-[11px] font-semibold rounded-full bg-notion-surface border border-notion-hairline text-notion-steel flex-shrink-0"
            >{{ entries.length }}</span>
            <button
              data-drawer-chevron
              class="flex-shrink-0 text-notion-stone hover:text-notion-steel transition-colors p-1"
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
          <div v-if="expandedDomains[domain]" class="bg-notion-surface-soft">
            <button
              v-for="entry in entries"
              :key="entry.file_id"
              data-drawer-file
              class="w-full text-left px-6 py-2 text-[13px] block transition-colors text-notion-slate hover:bg-notion-canvas hover:text-notion-ink"
              @click="onDrawerEntryClick(entry)"
            >
              <span class="truncate block leading-relaxed">{{ entry.title || entry.orig_name }}</span>
            </button>
          </div>
        </div>
      </div>
    </MobileDrawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Menu } from 'lucide-vue-next'
import { useWikiStore } from '../stores/wiki.js'
import { useFileContent } from '../composables/useFileContent.js'
import MobileDrawer from '../components/MobileDrawer.vue'

const store = useWikiStore()
const route = useRoute()

const rightPanelState = ref('welcome')
const drawerOpen = ref(false)
const expandedDomains = reactive({})
const viewingFileId = ref(null)
const viewingTitle = ref('')
const viewingDomain = ref('')
const viewingFilename = ref('')

const { loading: contentLoading, error: contentError, renderedContent, load: loadContent } = useFileContent()

onMounted(async () => {
  await store.fetchTree()
  // Deep-link support: /wiki?file=<id> opens the entry directly. Used by
  // ChatView's source chips so the user can jump from an answer to the
  // cited document without manually drilling through the sidebar tree.
  if (route.query.file) {
    openByFileId(String(route.query.file))
  }
})

// React to query changes when the user clicks a different chip while still
// on /wiki — Vue Router reuses the component, so we watch instead of remount.
watch(() => route.query.file, (fileId) => {
  if (fileId) openByFileId(String(fileId))
})

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

function onDrawerEntryClick(entry) {
  drawerOpen.value = false
  onEntryClick(entry)
}

function openByFileId(fileId) {
  // The wiki tree is keyed by domain → list of entries. Walk it to find
  // the matching file_id, expand its domain group, and show the content.
  for (const [domain, entries] of Object.entries(store.tree || {})) {
    if (!Array.isArray(entries)) continue
    const entry = entries.find(e => e.file_id === fileId)
    if (entry) {
      expandedDomains[domain] = true
      onEntryClick(entry)
      return
    }
  }
}
</script>
