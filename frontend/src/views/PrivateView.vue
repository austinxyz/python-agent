<template>
  <div class="h-screen flex flex-col bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50">

    <!-- Page Header -->
    <div class="bg-gradient-to-r from-blue-600 to-purple-600 shadow-lg px-6 py-4 flex-shrink-0">
      <div class="flex items-center gap-3">
        <Lock class="w-6 h-6 text-white" />
        <div>
          <h1 class="text-2xl font-bold text-white">私有数据</h1>
          <p class="text-xs text-blue-100 mt-1">条目按目录组织，模板条目参与 AI 检索；笔记不参与</p>
        </div>
      </div>
    </div>

    <div v-if="store.error" class="bg-red-50 border-b border-red-200 px-6 py-2 text-sm text-red-600 flex-shrink-0">
      ⚠️ {{ store.error }}
    </div>

    <!-- Two-column layout -->
    <div class="flex-1 flex overflow-hidden">

      <!-- LEFT SIDEBAR -->
      <div data-sidebar class="w-72 flex-shrink-0 bg-white border-r border-gray-200 flex flex-col shadow-lg">
        <div class="px-4 py-3 border-b border-gray-200 bg-gradient-to-r from-indigo-500 to-purple-500 flex items-center justify-between">
          <h2 class="text-sm font-semibold text-white">📁 目录</h2>
          <span class="text-[10px] text-indigo-100">{{ totalCount }} 项</span>
        </div>

        <div class="flex-shrink-0 grid grid-cols-2 gap-2 p-3 border-b border-gray-200 bg-gray-50">
          <button
            data-new-entry-btn
            class="px-3 py-2 bg-gradient-to-r from-green-400 to-emerald-500 hover:from-green-500 hover:to-emerald-600 text-white text-xs font-bold rounded-lg shadow-sm transition-all"
            @click="openNewEntry"
          >+ 新建条目</button>
          <button
            data-new-note-btn
            class="px-3 py-2 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white text-xs font-bold rounded-lg shadow-sm transition-all"
            @click="openNewNote"
          >+ 新建笔记</button>
        </div>

        <div class="flex-1 overflow-y-auto py-2">
          <DirectoryTreeNode
            :tree="store.combinedTree"
            :depth="0"
            :selected-id="selectedItemId"
            :expanded="expandedDirs"
            @toggle="toggleDir"
            @select="selectItem"
          />
        </div>
      </div>

      <!-- RIGHT PANEL -->
      <div class="flex-1 overflow-y-auto">

        <!-- Welcome -->
        <div v-if="rightState === 'welcome'" data-panel="welcome" class="h-full flex items-center justify-center">
          <div class="text-center max-w-md">
            <div class="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-blue-100 to-purple-100 rounded-2xl flex items-center justify-center shadow-lg">
              <Lock class="w-10 h-10 text-indigo-500" />
            </div>
            <h2 class="text-xl font-bold text-gray-800 mb-2">私有数据管理</h2>
            <p class="text-sm text-gray-500 leading-relaxed">从左侧目录选择已有条目查看，或点上方按钮新建模板条目和笔记。<br><span class="text-amber-600 text-xs">提示：模板条目会被 AI 检索，笔记不会。</span></p>
          </div>
        </div>

        <!-- Item view -->
        <div v-else-if="rightState === 'item-view' && selectedItem" data-panel="item-view" class="h-full flex flex-col">
          <div class="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-4 flex-shrink-0 shadow-md">
            <div class="flex items-center justify-between gap-3">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 text-xs text-indigo-100 mb-1">
                  <span class="px-2 py-0.5 rounded-full bg-white/20 font-semibold">{{ selectedItem.kind === 'entry' ? templateLabel(selectedItem.template_type) : '笔记' }}</span>
                  <span>{{ selectedItem.directory || '/' }}</span>
                  <span>·</span>
                  <span>更新 {{ formatDate(selectedItem.updated_at) }}</span>
                </div>
                <h2 class="text-lg font-bold text-white truncate">{{ selectedItem.title }}</h2>
              </div>
              <div class="flex gap-2 flex-shrink-0">
                <button
                  data-edit-item-btn
                  class="px-3 py-1.5 bg-white/20 hover:bg-white/30 text-white text-xs font-semibold rounded-lg transition-all"
                  @click="startEditing"
                >编辑</button>
                <button
                  data-delete-item-btn
                  class="px-3 py-1.5 bg-red-400/30 hover:bg-red-400/50 text-white text-xs font-semibold rounded-lg transition-all"
                  @click="deleteSelected"
                >删除</button>
              </div>
            </div>
          </div>

          <div class="flex-1 overflow-y-auto p-6">
            <div class="max-w-3xl">
              <!-- Entry: render template fields -->
              <div v-if="selectedItem.kind === 'entry'" class="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4">
                <div
                  v-for="field in templateFields(selectedItem.template_type)"
                  :key="field.key"
                  class="flex flex-col gap-1"
                >
                  <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider">{{ field.label }}</span>
                  <span class="text-sm text-gray-800 whitespace-pre-line">{{ fieldValue(selectedItem, field.key) || '—' }}</span>
                </div>
              </div>

              <!-- Note: render markdown content as preformatted text -->
              <div v-else class="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
                <div class="text-sm text-gray-700 whitespace-pre-line leading-relaxed">{{ selectedItem.content || '（空）' }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Item edit -->
        <div v-else-if="rightState === 'item-edit' && selectedItem" data-panel="item-edit" class="h-full flex flex-col">
          <div class="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-4 flex-shrink-0 shadow-md">
            <div class="flex items-center gap-3">
              <button class="text-indigo-200 hover:text-white text-sm" @click="cancelEditing">← 返回</button>
              <span class="text-indigo-300">|</span>
              <h2 class="text-lg font-bold text-white">编辑{{ selectedItem.kind === 'entry' ? '条目' : '笔记' }}</h2>
            </div>
          </div>

          <div class="flex-1 overflow-y-auto p-6">
            <div class="max-w-2xl space-y-4">
              <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-4">
                <div>
                  <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">标题 <span class="text-red-400">*</span></label>
                  <input
                    v-model="editForm.title"
                    type="text"
                    class="w-full px-3 py-2 rounded-lg border border-gray-200 bg-gray-50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent"
                  />
                </div>
                <div>
                  <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">目录</label>
                  <input
                    v-model="editForm.directory"
                    type="text"
                    class="w-full px-3 py-2 rounded-lg border border-gray-200 bg-gray-50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent"
                  />
                </div>

                <!-- Entry fields -->
                <template v-if="selectedItem.kind === 'entry'">
                  <div
                    v-for="field in templateFields(selectedItem.template_type)"
                    :key="field.key"
                  >
                    <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">{{ field.label }}</label>
                    <textarea
                      v-if="field.type === 'textarea'"
                      v-model="editForm.content[field.key]"
                      rows="3"
                      class="w-full px-3 py-2 rounded-lg border border-gray-200 bg-gray-50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent resize-y"
                    />
                    <input
                      v-else
                      v-model="editForm.content[field.key]"
                      :type="field.type === 'number' ? 'number' : 'text'"
                      class="w-full px-3 py-2 rounded-lg border border-gray-200 bg-gray-50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent"
                    />
                  </div>
                </template>

                <!-- Note content -->
                <template v-else>
                  <div>
                    <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">内容</label>
                    <textarea
                      v-model="editForm.noteContent"
                      rows="14"
                      class="w-full px-3 py-2 rounded-lg border border-gray-200 bg-gray-50 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent resize-y"
                    />
                  </div>
                </template>

                <div v-if="formError" class="px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-xs text-red-600">
                  {{ formError }}
                </div>

                <div class="flex gap-2">
                  <button
                    :disabled="submitting"
                    :class="[
                      'flex-1 py-2.5 rounded-lg text-sm font-bold transition-all shadow-md',
                      submitting
                        ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                        : 'bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white hover:shadow-lg',
                    ]"
                    @click="saveEdit"
                  >{{ submitting ? '保存中…' : '💾 保存' }}</button>
                  <button
                    class="px-4 py-2.5 bg-gray-100 text-gray-600 text-sm font-medium rounded-lg hover:bg-gray-200 transition-all"
                    @click="cancelEditing"
                  >取消</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- New entry -->
        <div v-else-if="rightState === 'new-entry'" data-panel="new-entry" class="h-full flex flex-col">
          <div class="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-4 flex-shrink-0 shadow-md">
            <div class="flex items-center gap-3">
              <button class="text-indigo-200 hover:text-white text-sm" @click="goWelcome">← 返回</button>
              <span class="text-indigo-300">|</span>
              <h2 class="text-lg font-bold text-white">新建条目</h2>
            </div>
          </div>

          <div class="flex-1 overflow-y-auto p-6">
            <div class="max-w-2xl space-y-4">
              <!-- Template picker -->
              <div v-if="!entryForm.template" class="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
                <p class="text-sm font-semibold text-gray-700 mb-3">选择模板</p>
                <div class="grid grid-cols-2 gap-2">
                  <button
                    v-for="tpl in store.templates"
                    :key="tpl.type"
                    :data-template-option="tpl.type"
                    class="px-4 py-3 text-sm font-medium rounded-lg border-2 border-gray-200 bg-white hover:border-indigo-400 hover:bg-indigo-50 transition-all text-left"
                    @click="pickTemplate(tpl)"
                  >
                    <span class="text-gray-700">{{ tpl.label }}</span>
                    <span class="block text-[10px] text-gray-400 mt-0.5">默认目录：{{ tpl.default_directory }}</span>
                  </button>
                </div>
              </div>

              <!-- Form -->
              <div v-else class="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-4">
                <div class="flex items-center justify-between">
                  <span class="px-3 py-1 text-xs font-semibold rounded-full bg-gradient-to-r from-blue-500 to-indigo-500 text-white">{{ entryForm.template.label }}</span>
                  <button class="text-xs text-gray-400 hover:text-gray-600" @click="entryForm.template = null">换模板</button>
                </div>
                <div>
                  <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">标题 <span class="text-red-400">*</span></label>
                  <input
                    data-entry-title
                    v-model="entryForm.title"
                    type="text"
                    placeholder="如：2025 税务情况"
                    class="w-full px-3 py-2 rounded-lg border border-gray-200 bg-gray-50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent"
                  />
                </div>
                <div>
                  <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">目录</label>
                  <input
                    data-entry-directory
                    v-model="entryForm.directory"
                    type="text"
                    class="w-full px-3 py-2 rounded-lg border border-gray-200 bg-gray-50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent"
                  />
                </div>
                <div
                  v-for="field in entryForm.template.fields"
                  :key="field.key"
                  data-entry-field
                >
                  <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">{{ field.label }}</label>
                  <textarea
                    v-if="field.type === 'textarea'"
                    v-model="entryForm.content[field.key]"
                    :placeholder="field.placeholder || ''"
                    rows="3"
                    class="w-full px-3 py-2 rounded-lg border border-gray-200 bg-gray-50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent resize-y"
                  />
                  <input
                    v-else
                    v-model="entryForm.content[field.key]"
                    :type="field.type === 'number' ? 'number' : 'text'"
                    :placeholder="field.placeholder || ''"
                    class="w-full px-3 py-2 rounded-lg border border-gray-200 bg-gray-50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent"
                  />
                </div>

                <div v-if="formError" class="px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-xs text-red-600">
                  {{ formError }}
                </div>

                <button
                  data-save-entry-btn
                  :disabled="submitting"
                  :class="[
                    'w-full py-2.5 rounded-lg text-sm font-bold transition-all shadow-md',
                    submitting
                      ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                      : 'bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white hover:shadow-lg',
                  ]"
                  @click="saveNewEntry"
                >{{ submitting ? '保存中…' : '💾 保存条目' }}</button>
              </div>
            </div>
          </div>
        </div>

        <!-- New note -->
        <div v-else-if="rightState === 'new-note'" data-panel="new-note" class="h-full flex flex-col">
          <div class="bg-gradient-to-r from-purple-600 to-pink-600 px-6 py-4 flex-shrink-0 shadow-md">
            <div class="flex items-center gap-3">
              <button class="text-purple-200 hover:text-white text-sm" @click="goWelcome">← 返回</button>
              <span class="text-purple-300">|</span>
              <h2 class="text-lg font-bold text-white">新建笔记</h2>
            </div>
          </div>
          <div class="flex-1 overflow-y-auto p-6">
            <div class="max-w-2xl">
              <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-4">
                <div>
                  <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">标题 <span class="text-red-400">*</span></label>
                  <input
                    data-note-title
                    v-model="noteForm.title"
                    type="text"
                    class="w-full px-3 py-2 rounded-lg border border-gray-200 bg-gray-50 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent"
                  />
                </div>
                <div>
                  <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">目录</label>
                  <input
                    data-note-directory
                    v-model="noteForm.directory"
                    type="text"
                    placeholder="如：退休规划/Roth相关"
                    class="w-full px-3 py-2 rounded-lg border border-gray-200 bg-gray-50 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent"
                  />
                </div>
                <div>
                  <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">内容</label>
                  <textarea
                    data-note-content
                    v-model="noteForm.content"
                    rows="14"
                    class="w-full px-3 py-2 rounded-lg border border-gray-200 bg-gray-50 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent resize-y"
                  />
                </div>

                <div v-if="formError" class="px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-xs text-red-600">
                  {{ formError }}
                </div>

                <button
                  data-save-note-btn
                  :disabled="submitting"
                  :class="[
                    'w-full py-2.5 rounded-lg text-sm font-bold transition-all shadow-md',
                    submitting
                      ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                      : 'bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white hover:shadow-lg',
                  ]"
                  @click="saveNewNote"
                >{{ submitting ? '保存中…' : '💾 保存笔记' }}</button>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, h } from 'vue'
import { Lock } from 'lucide-vue-next'
import { usePrivateStore } from '../stores/private.js'

const store = usePrivateStore()

const rightState = ref('welcome') // welcome | item-view | item-edit | new-entry | new-note
const selectedItemId = ref(null)
const expandedDirs = reactive({})
const formError = ref('')
const submitting = ref(false)

// Forms
const entryForm = reactive({
  template: null,
  title: '',
  directory: '',
  content: {},
})
const noteForm = reactive({
  title: '',
  directory: '',
  content: '',
})
const editForm = reactive({
  title: '',
  directory: '',
  content: {},   // for entries
  noteContent: '', // for notes
})

const allItems = computed(() => {
  const entries = store.entries.map(e => ({
    ...e,
    kind: 'entry',
  }))
  const notes = store.notes.map(n => ({
    ...n,
    kind: 'note',
  }))
  return [...entries, ...notes]
})

const totalCount = computed(() => allItems.value.length)

const selectedItem = computed(() =>
  allItems.value.find(i => i.id === selectedItemId.value) || null
)

onMounted(() => {
  store.fetchTemplates()
  store.fetchEntries()
  store.fetchNotes()
})

function templateLabel(type) {
  const t = store.templates.find(t => t.type === type)
  return t ? t.label : type
}

function templateFields(type) {
  const t = store.templates.find(t => t.type === type)
  return t ? t.fields : []
}

function fieldValue(item, key) {
  return item?.content_json?.[key] ?? ''
}

function formatDate(iso) {
  if (!iso) return ''
  return iso.slice(0, 10)
}

function toggleDir(path) {
  expandedDirs[path] = !expandedDirs[path]
}

function isNewEntryDirty() {
  if (entryForm.template) return true
  if (entryForm.title.trim()) return true
  if (Object.values(entryForm.content || {}).some(v => v !== null && String(v).trim() !== '')) return true
  return false
}

function isNewNoteDirty() {
  return Boolean(
    noteForm.title.trim() || noteForm.directory.trim() || (noteForm.content || '').trim()
  )
}

function selectItem(itemId) {
  if (rightState.value === 'new-entry' && isNewEntryDirty()) {
    if (!window.confirm('放弃当前正在编辑的新条目？')) return
  }
  if (rightState.value === 'new-note' && isNewNoteDirty()) {
    if (!window.confirm('放弃当前正在编辑的新笔记？')) return
  }
  selectedItemId.value = itemId
  rightState.value = 'item-view'
  formError.value = ''
}

function goWelcome() {
  rightState.value = 'welcome'
  selectedItemId.value = null
  formError.value = ''
}

// ===== New entry =====
function confirmDiscardIfDirty() {
  if (rightState.value === 'new-entry' && isNewEntryDirty()) {
    return window.confirm('放弃当前正在编辑的新条目？')
  }
  if (rightState.value === 'new-note' && isNewNoteDirty()) {
    return window.confirm('放弃当前正在编辑的新笔记？')
  }
  return true
}

function openNewEntry() {
  if (!confirmDiscardIfDirty()) return
  entryForm.template = null
  entryForm.title = ''
  entryForm.directory = ''
  entryForm.content = {}
  formError.value = ''
  rightState.value = 'new-entry'
}

function pickTemplate(tpl) {
  entryForm.template = tpl
  entryForm.directory = tpl.default_directory || ''
  entryForm.content = Object.fromEntries(tpl.fields.map(f => [f.key, '']))
}

async function saveNewEntry() {
  formError.value = ''
  if (!entryForm.title.trim()) {
    formError.value = '请输入标题'
    return
  }
  submitting.value = true
  try {
    const created = await store.createEntry({
      template_type: entryForm.template.type,
      title: entryForm.title.trim(),
      directory: entryForm.directory.trim(),
      content_json: { ...entryForm.content },
    })
    if (created?.id) {
      selectedItemId.value = created.id
      rightState.value = 'item-view'
    } else {
      goWelcome()
    }
  } catch {
    formError.value = store.error || '保存失败'
  } finally {
    submitting.value = false
  }
}

// ===== New note =====
function openNewNote() {
  if (!confirmDiscardIfDirty()) return
  noteForm.title = ''
  noteForm.directory = ''
  noteForm.content = ''
  formError.value = ''
  rightState.value = 'new-note'
}

async function saveNewNote() {
  formError.value = ''
  if (!noteForm.title.trim()) {
    formError.value = '请输入标题'
    return
  }
  submitting.value = true
  try {
    const created = await store.createNote({
      title: noteForm.title.trim(),
      directory: noteForm.directory.trim(),
      content: noteForm.content,
    })
    if (created?.id) {
      selectedItemId.value = created.id
      rightState.value = 'item-view'
    } else {
      goWelcome()
    }
  } catch {
    formError.value = store.error || '保存失败'
  } finally {
    submitting.value = false
  }
}

// ===== Edit existing =====
function startEditing() {
  if (!selectedItem.value) return
  editForm.title = selectedItem.value.title
  editForm.directory = selectedItem.value.directory || ''
  if (selectedItem.value.kind === 'entry') {
    editForm.content = { ...(selectedItem.value.content_json || {}) }
  } else {
    editForm.noteContent = selectedItem.value.content || ''
  }
  formError.value = ''
  rightState.value = 'item-edit'
}

function cancelEditing() {
  if (selectedItem.value) {
    rightState.value = 'item-view'
  } else {
    goWelcome()
  }
  formError.value = ''
}

async function saveEdit() {
  if (!selectedItem.value) return
  formError.value = ''
  if (!editForm.title.trim()) {
    formError.value = '请输入标题'
    return
  }
  submitting.value = true
  try {
    if (selectedItem.value.kind === 'entry') {
      await store.updateEntry(selectedItem.value.id, {
        title: editForm.title.trim(),
        directory: editForm.directory.trim(),
        content_json: { ...editForm.content },
      })
    } else {
      await store.updateNote(selectedItem.value.id, {
        title: editForm.title.trim(),
        directory: editForm.directory.trim(),
        content: editForm.noteContent,
      })
    }
    rightState.value = 'item-view'
  } catch {
    formError.value = store.error || '保存失败'
  } finally {
    submitting.value = false
  }
}

async function deleteSelected() {
  if (!selectedItem.value) return
  if (!window.confirm(`确认删除「${selectedItem.value.title}」？`)) return
  try {
    if (selectedItem.value.kind === 'entry') {
      await store.deleteEntry(selectedItem.value.id)
    } else {
      await store.deleteNote(selectedItem.value.id)
    }
    selectedItemId.value = null
    rightState.value = 'welcome'
  } catch {
    // store.error reflected in UI
  }
}

// ===== Recursive directory tree node =====
const DirectoryTreeNode = {
  name: 'DirectoryTreeNode',
  props: {
    tree: { type: Object, required: true },
    depth: { type: Number, default: 0 },
    selectedId: { type: String, default: null },
    expanded: { type: Object, required: true },
    pathPrefix: { type: String, default: '' },
  },
  emits: ['toggle', 'select'],
  setup(props, { emit }) {
    return () => {
      const children = []

      // Direct items (under root or under this directory)
      const directItems = Array.isArray(props.tree._items) ? props.tree._items : []
      for (const item of directItems) {
        const isSelected = props.selectedId === item.id
        const icon = item.kind === 'entry' ? '📋' : '📝'
        children.push(
          h(
            'div',
            {
              'data-item': '',
              class: [
                'cursor-pointer text-sm py-1.5 pr-2 rounded-md transition-all truncate',
                isSelected
                  ? 'bg-gradient-to-r from-blue-50 to-purple-50 text-indigo-700 font-semibold border-l-2 border-l-indigo-500'
                  : 'text-gray-700 hover:bg-gray-50',
              ],
              style: { paddingLeft: `${props.depth * 14 + 12}px` },
              onClick: () => emit('select', item.id),
            },
            [`${icon} `, item.title]
          )
        )
      }

      // Subdirectories
      const subdirs = Object.keys(props.tree)
        .filter(k => k !== '_items')
        .sort((a, b) => a.localeCompare(b, 'zh-Hans-CN'))
      for (const name of subdirs) {
        const path = props.pathPrefix ? `${props.pathPrefix}/${name}` : name
        const isExpanded = props.expanded[path] !== false
        const sub = props.tree[name]
        const itemCount = countItems(sub)
        children.push(
          h(
            'div',
            { class: 'select-none' },
            [
              h(
                'div',
                {
                  class: [
                    'cursor-pointer text-sm font-semibold py-1.5 pr-2 hover:bg-gray-50 rounded-md flex items-center gap-2 transition-all',
                  ],
                  style: { paddingLeft: `${props.depth * 14 + 8}px` },
                  onClick: () => emit('toggle', path),
                },
                [
                  h('span', { class: 'text-gray-600 flex-shrink-0' }, '📁'),
                  h(
                    'span',
                    {
                      'data-directory-name': '',
                      class: 'flex-1 text-gray-700 truncate',
                    },
                    name
                  ),
                  itemCount > 0
                    ? h(
                        'span',
                        { class: 'flex-shrink-0 text-[10px] font-bold text-indigo-500 bg-indigo-50 px-1.5 py-0.5 rounded-full' },
                        String(itemCount)
                      )
                    : null,
                  h(
                    'span',
                    { class: 'flex-shrink-0 text-gray-300 hover:text-indigo-500 transition-colors p-0.5' },
                    [
                      h(
                        'svg',
                        {
                          class: ['w-3.5 h-3.5 transition-transform duration-200', isExpanded ? 'rotate-90' : ''],
                          viewBox: '0 0 24 24',
                          fill: 'none',
                          stroke: 'currentColor',
                          'stroke-width': '2.5',
                        },
                        [h('polyline', { points: '9 18 15 12 9 6' })]
                      ),
                    ]
                  ),
                ]
              ),
              isExpanded
                ? h(DirectoryTreeNode, {
                    tree: sub,
                    depth: props.depth + 1,
                    selectedId: props.selectedId,
                    expanded: props.expanded,
                    pathPrefix: path,
                    onToggle: (p) => emit('toggle', p),
                    onSelect: (id) => emit('select', id),
                  })
                : null,
            ]
          )
        )
      }

      return h('div', children)
    }
  },
}

function countItems(node) {
  if (!node || typeof node !== 'object') return 0
  let total = Array.isArray(node._items) ? node._items.length : 0
  for (const k of Object.keys(node)) {
    if (k === '_items') continue
    total += countItems(node[k])
  }
  return total
}
</script>
