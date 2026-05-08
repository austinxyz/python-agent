<template>
  <!--
    PrivateView — redesigned 2026-05-08 against docs/design/notion.md.
    Tokens: notion-* in tailwind.config.cjs. Light canvas, brand-navy hero band,
    single primary purple CTA, pastel tints for template differentiation.
  -->
  <div class="h-screen flex flex-col bg-notion-surface-soft text-notion-ink">

    <!-- Page Header — brand-navy hero band, replaces V1 blue→purple gradient -->
    <div class="bg-notion-brand-navy text-notion-on-dark px-6 py-5 flex-shrink-0">
      <div class="flex items-center gap-3">
        <div class="w-9 h-9 rounded-md bg-white/10 flex items-center justify-center">
          <Lock class="w-5 h-5" />
        </div>
        <div>
          <h1 class="text-xl font-semibold tracking-tight leading-tight">私有数据</h1>
          <p class="text-[13px] text-notion-on-dark-muted mt-0.5">条目按目录组织，模板条目参与 AI 检索；笔记不参与</p>
        </div>
      </div>
    </div>

    <div v-if="store.error" class="bg-notion-tint-rose border-b border-notion-hairline px-6 py-2 text-[13px] text-notion-error flex-shrink-0">
      {{ store.error }}
    </div>

    <!-- Two-column layout -->
    <div class="flex-1 flex overflow-hidden">

      <!-- LEFT SIDEBAR -->
      <div data-sidebar class="w-72 flex-shrink-0 bg-notion-canvas border-r border-notion-hairline flex flex-col">
        <!-- Section header -->
        <div class="px-4 py-3 border-b border-notion-hairline-soft flex items-center justify-between">
          <h2 class="text-[11px] font-semibold uppercase tracking-[0.08em] text-notion-steel">目录</h2>
          <span class="text-[11px] text-notion-stone">{{ totalCount }} 项</span>
        </div>

        <!-- New buttons — primary purple + secondary dark -->
        <div class="flex-shrink-0 grid grid-cols-2 gap-2 p-3 border-b border-notion-hairline-soft">
          <button
            data-new-entry-btn
            class="px-3 h-9 bg-notion-primary hover:bg-notion-primary-pressed text-notion-on-primary text-[13px] font-medium rounded-md transition-colors"
            @click="openNewEntry"
          >+ 新建条目</button>
          <button
            data-new-note-btn
            class="px-3 h-9 bg-notion-ink-deep hover:bg-notion-charcoal text-notion-on-dark text-[13px] font-medium rounded-md transition-colors"
            @click="openNewNote"
          >+ 新建笔记</button>
        </div>

        <!-- Directory tree -->
        <div class="flex-1 overflow-y-auto py-2 px-1">
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
      <div class="flex-1 overflow-y-auto bg-notion-surface-soft">

        <!-- Welcome -->
        <div v-if="rightState === 'welcome'" data-panel="welcome" class="h-full flex items-center justify-center px-8">
          <div class="text-center max-w-md">
            <div class="w-14 h-14 mx-auto mb-5 rounded-md bg-notion-tint-lavender flex items-center justify-center">
              <Lock class="w-7 h-7 text-notion-brand-purple-800" />
            </div>
            <h2 class="text-lg font-semibold text-notion-ink mb-2">私有数据管理</h2>
            <p class="text-[14px] text-notion-slate leading-relaxed">从左侧目录选择已有条目查看，或点上方按钮新建模板条目和笔记。<br><span class="text-[13px] text-notion-steel">提示：模板条目会被 AI 检索，笔记不会。</span></p>
          </div>
        </div>

        <!-- Item view -->
        <div v-else-if="rightState === 'item-view' && selectedItem" data-panel="item-view" class="h-full flex flex-col">
          <div class="bg-notion-canvas border-b border-notion-hairline px-8 py-5 flex-shrink-0">
            <div class="flex items-start justify-between gap-4">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 text-[12px] text-notion-steel mb-1.5">
                  <span :class="kindBadgeClass(selectedItem)">{{ selectedItem.kind === 'entry' ? templateLabel(selectedItem.template_type) : '笔记' }}</span>
                  <span class="text-notion-stone">·</span>
                  <span>{{ selectedItem.directory || '/' }}</span>
                  <span class="text-notion-stone">·</span>
                  <span>更新 {{ formatDate(selectedItem.updated_at) }}</span>
                </div>
                <h2 class="text-[22px] font-semibold tracking-tight text-notion-ink truncate">{{ selectedItem.title }}</h2>
              </div>
              <div class="flex gap-2 flex-shrink-0">
                <button
                  data-edit-item-btn
                  class="h-8 px-3 bg-transparent hover:bg-notion-surface text-notion-ink text-[13px] font-medium rounded-md border border-notion-hairline-strong transition-colors"
                  @click="startEditing"
                >编辑</button>
                <button
                  data-delete-item-btn
                  class="h-8 px-3 bg-transparent hover:bg-notion-tint-rose text-notion-error text-[13px] font-medium rounded-md border border-notion-hairline-strong transition-colors"
                  @click="deleteSelected"
                >删除</button>
              </div>
            </div>
          </div>

          <div class="flex-1 overflow-y-auto px-8 py-6">
            <div class="max-w-3xl">
              <!-- Entry: render template fields -->
              <div v-if="selectedItem.kind === 'entry'" class="bg-notion-canvas rounded-lg border border-notion-hairline p-6 space-y-5">
                <div
                  v-for="field in templateFields(selectedItem.template_type)"
                  :key="field.key"
                  class="flex flex-col gap-1.5 pb-4 last:pb-0 last:border-0 border-b border-notion-hairline-soft"
                >
                  <span class="text-[11px] font-semibold uppercase tracking-[0.08em] text-notion-steel">{{ field.label }}</span>
                  <span class="text-[14px] text-notion-ink whitespace-pre-line leading-relaxed">{{ fieldValue(selectedItem, field.key) || '—' }}</span>
                </div>
              </div>

              <!-- Note: render markdown content -->
              <div v-else class="bg-notion-canvas rounded-lg border border-notion-hairline p-6">
                <div class="text-[14px] text-notion-charcoal whitespace-pre-line leading-relaxed">{{ selectedItem.content || '（空）' }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Item edit -->
        <div v-else-if="rightState === 'item-edit' && selectedItem" data-panel="item-edit" class="h-full flex flex-col">
          <div class="bg-notion-canvas border-b border-notion-hairline px-8 py-5 flex-shrink-0">
            <div class="flex items-center gap-3">
              <button class="text-[13px] text-notion-steel hover:text-notion-ink transition-colors" @click="cancelEditing">← 返回</button>
              <span class="text-notion-hairline-strong">|</span>
              <h2 class="text-[18px] font-semibold text-notion-ink">编辑{{ selectedItem.kind === 'entry' ? '条目' : '笔记' }}</h2>
            </div>
          </div>

          <div class="flex-1 overflow-y-auto px-8 py-6">
            <div class="max-w-2xl space-y-4">
              <div class="bg-notion-canvas rounded-lg border border-notion-hairline p-6 space-y-4">
                <div>
                  <label class="block text-[11px] font-semibold uppercase tracking-[0.08em] text-notion-steel mb-1.5">标题 <span class="text-notion-error">*</span></label>
                  <input
                    v-model="editForm.title"
                    type="text"
                    class="w-full h-11 px-3 bg-notion-canvas border border-notion-hairline-strong text-notion-ink text-[14px] rounded-md focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary"
                  />
                </div>
                <div>
                  <label class="block text-[11px] font-semibold uppercase tracking-[0.08em] text-notion-steel mb-1.5">目录</label>
                  <input
                    v-model="editForm.directory"
                    type="text"
                    class="w-full h-11 px-3 bg-notion-canvas border border-notion-hairline-strong text-notion-ink text-[14px] rounded-md focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary"
                  />
                </div>

                <!-- Entry fields -->
                <template v-if="selectedItem.kind === 'entry'">
                  <div
                    v-for="field in templateFields(selectedItem.template_type)"
                    :key="field.key"
                  >
                    <label class="block text-[11px] font-semibold uppercase tracking-[0.08em] text-notion-steel mb-1.5">{{ field.label }}</label>
                    <textarea
                      v-if="field.type === 'textarea'"
                      v-model="editForm.content[field.key]"
                      rows="3"
                      class="w-full px-3 py-2 bg-notion-canvas border border-notion-hairline-strong text-notion-ink text-[14px] rounded-md focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary resize-y"
                    />
                    <input
                      v-else
                      v-model="editForm.content[field.key]"
                      :type="field.type === 'number' ? 'number' : 'text'"
                      class="w-full h-11 px-3 bg-notion-canvas border border-notion-hairline-strong text-notion-ink text-[14px] rounded-md focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary"
                    />
                  </div>
                </template>

                <!-- Note content -->
                <template v-else>
                  <div>
                    <label class="block text-[11px] font-semibold uppercase tracking-[0.08em] text-notion-steel mb-1.5">内容</label>
                    <textarea
                      v-model="editForm.noteContent"
                      rows="14"
                      class="w-full px-3 py-2 bg-notion-canvas border border-notion-hairline-strong text-notion-ink text-[14px] rounded-md focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary resize-y"
                    />
                  </div>
                </template>

                <div v-if="formError" class="px-3 py-2 bg-notion-tint-rose border border-notion-hairline rounded-md text-[13px] text-notion-error">
                  {{ formError }}
                </div>

                <div class="flex gap-2">
                  <button
                    :disabled="submitting"
                    :class="[
                      'h-10 px-5 rounded-md text-[14px] font-medium transition-colors',
                      submitting
                        ? 'bg-notion-hairline text-notion-muted-text cursor-not-allowed'
                        : 'bg-notion-primary hover:bg-notion-primary-pressed text-notion-on-primary',
                    ]"
                    @click="saveEdit"
                  >{{ submitting ? '保存中…' : '保存' }}</button>
                  <button
                    class="h-10 px-5 bg-transparent hover:bg-notion-surface text-notion-ink text-[14px] font-medium rounded-md border border-notion-hairline-strong transition-colors"
                    @click="cancelEditing"
                  >取消</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- New entry -->
        <div v-else-if="rightState === 'new-entry'" data-panel="new-entry" class="h-full flex flex-col">
          <div class="bg-notion-canvas border-b border-notion-hairline px-8 py-5 flex-shrink-0">
            <div class="flex items-center gap-3">
              <button class="text-[13px] text-notion-steel hover:text-notion-ink transition-colors" @click="goWelcome">← 返回</button>
              <span class="text-notion-hairline-strong">|</span>
              <h2 class="text-[18px] font-semibold text-notion-ink">新建条目</h2>
            </div>
          </div>

          <div class="flex-1 overflow-y-auto px-8 py-6">
            <div class="max-w-2xl space-y-4">
              <!-- Template picker — pastel tinted cards -->
              <div v-if="!entryForm.template" class="bg-notion-canvas rounded-lg border border-notion-hairline p-6">
                <p class="text-[14px] font-medium text-notion-ink mb-4">选择模板</p>
                <div class="grid grid-cols-2 gap-3">
                  <button
                    v-for="(tpl, idx) in store.templates"
                    :key="tpl.type"
                    :data-template-option="tpl.type"
                    :class="[
                      'px-4 py-4 text-left rounded-lg transition-colors',
                      templateTintClass(idx),
                      'hover:ring-2 hover:ring-notion-primary',
                    ]"
                    @click="pickTemplate(tpl)"
                  >
                    <span class="block text-[14px] font-semibold text-notion-charcoal">{{ tpl.label }}</span>
                    <span class="block text-[12px] text-notion-slate mt-1">默认目录：{{ tpl.default_directory }}</span>
                  </button>
                </div>
              </div>

              <!-- Form -->
              <div v-else class="bg-notion-canvas rounded-lg border border-notion-hairline p-6 space-y-4">
                <div class="flex items-center justify-between">
                  <span class="px-2.5 py-1 text-[12px] font-semibold rounded-md bg-notion-tint-lavender text-notion-brand-purple-800">{{ entryForm.template.label }}</span>
                  <button class="text-[13px] text-notion-steel hover:text-notion-ink transition-colors" @click="entryForm.template = null">换模板</button>
                </div>
                <div>
                  <label class="block text-[11px] font-semibold uppercase tracking-[0.08em] text-notion-steel mb-1.5">标题 <span class="text-notion-error">*</span></label>
                  <input
                    data-entry-title
                    v-model="entryForm.title"
                    type="text"
                    placeholder="如：2025 税务情况"
                    class="w-full h-11 px-3 bg-notion-canvas border border-notion-hairline-strong text-notion-ink text-[14px] rounded-md placeholder:text-notion-stone focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary"
                  />
                </div>
                <div>
                  <label class="block text-[11px] font-semibold uppercase tracking-[0.08em] text-notion-steel mb-1.5">目录</label>
                  <input
                    data-entry-directory
                    v-model="entryForm.directory"
                    type="text"
                    class="w-full h-11 px-3 bg-notion-canvas border border-notion-hairline-strong text-notion-ink text-[14px] rounded-md focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary"
                  />
                </div>
                <div
                  v-for="field in entryForm.template.fields"
                  :key="field.key"
                  data-entry-field
                >
                  <label class="block text-[11px] font-semibold uppercase tracking-[0.08em] text-notion-steel mb-1.5">{{ field.label }}</label>
                  <textarea
                    v-if="field.type === 'textarea'"
                    v-model="entryForm.content[field.key]"
                    :placeholder="field.placeholder || ''"
                    rows="3"
                    class="w-full px-3 py-2 bg-notion-canvas border border-notion-hairline-strong text-notion-ink text-[14px] rounded-md placeholder:text-notion-stone focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary resize-y"
                  />
                  <input
                    v-else
                    v-model="entryForm.content[field.key]"
                    :type="field.type === 'number' ? 'number' : 'text'"
                    :placeholder="field.placeholder || ''"
                    class="w-full h-11 px-3 bg-notion-canvas border border-notion-hairline-strong text-notion-ink text-[14px] rounded-md placeholder:text-notion-stone focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary"
                  />
                </div>

                <div v-if="formError" class="px-3 py-2 bg-notion-tint-rose border border-notion-hairline rounded-md text-[13px] text-notion-error">
                  {{ formError }}
                </div>

                <button
                  data-save-entry-btn
                  :disabled="submitting"
                  :class="[
                    'w-full h-11 rounded-md text-[14px] font-medium transition-colors',
                    submitting
                      ? 'bg-notion-hairline text-notion-muted-text cursor-not-allowed'
                      : 'bg-notion-primary hover:bg-notion-primary-pressed text-notion-on-primary',
                  ]"
                  @click="saveNewEntry"
                >{{ submitting ? '保存中…' : '保存条目' }}</button>
              </div>
            </div>
          </div>
        </div>

        <!-- New note -->
        <div v-else-if="rightState === 'new-note'" data-panel="new-note" class="h-full flex flex-col">
          <div class="bg-notion-canvas border-b border-notion-hairline px-8 py-5 flex-shrink-0">
            <div class="flex items-center gap-3">
              <button class="text-[13px] text-notion-steel hover:text-notion-ink transition-colors" @click="goWelcome">← 返回</button>
              <span class="text-notion-hairline-strong">|</span>
              <h2 class="text-[18px] font-semibold text-notion-ink">新建笔记</h2>
            </div>
          </div>
          <div class="flex-1 overflow-y-auto px-8 py-6">
            <div class="max-w-2xl">
              <div class="bg-notion-canvas rounded-lg border border-notion-hairline p-6 space-y-4">
                <div>
                  <label class="block text-[11px] font-semibold uppercase tracking-[0.08em] text-notion-steel mb-1.5">标题 <span class="text-notion-error">*</span></label>
                  <input
                    data-note-title
                    v-model="noteForm.title"
                    type="text"
                    class="w-full h-11 px-3 bg-notion-canvas border border-notion-hairline-strong text-notion-ink text-[14px] rounded-md focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary"
                  />
                </div>
                <div>
                  <label class="block text-[11px] font-semibold uppercase tracking-[0.08em] text-notion-steel mb-1.5">目录</label>
                  <input
                    data-note-directory
                    v-model="noteForm.directory"
                    type="text"
                    placeholder="如：退休规划/Roth相关"
                    class="w-full h-11 px-3 bg-notion-canvas border border-notion-hairline-strong text-notion-ink text-[14px] rounded-md placeholder:text-notion-stone focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary"
                  />
                </div>
                <div>
                  <label class="block text-[11px] font-semibold uppercase tracking-[0.08em] text-notion-steel mb-1.5">内容</label>
                  <textarea
                    data-note-content
                    v-model="noteForm.content"
                    rows="14"
                    class="w-full px-3 py-2 bg-notion-canvas border border-notion-hairline-strong text-notion-ink text-[14px] rounded-md focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary resize-y"
                  />
                </div>

                <div v-if="formError" class="px-3 py-2 bg-notion-tint-rose border border-notion-hairline rounded-md text-[13px] text-notion-error">
                  {{ formError }}
                </div>

                <button
                  data-save-note-btn
                  :disabled="submitting"
                  :class="[
                    'w-full h-11 rounded-md text-[14px] font-medium transition-colors',
                    submitting
                      ? 'bg-notion-hairline text-notion-muted-text cursor-not-allowed'
                      : 'bg-notion-primary hover:bg-notion-primary-pressed text-notion-on-primary',
                  ]"
                  @click="saveNewNote"
                >{{ submitting ? '保存中…' : '保存笔记' }}</button>
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

// Cycle Notion's pastel tints across the 6 templates so each gets a distinct
// but coordinated tile color in the picker.
const TEMPLATE_TINTS = [
  'bg-notion-tint-lavender',
  'bg-notion-tint-mint',
  'bg-notion-tint-sky',
  'bg-notion-tint-peach',
  'bg-notion-tint-cream',
  'bg-notion-tint-yellow',
]
function templateTintClass(idx) {
  return TEMPLATE_TINTS[idx % TEMPLATE_TINTS.length]
}

function kindBadgeClass(item) {
  return item.kind === 'entry'
    ? 'px-2 py-0.5 rounded-md bg-notion-tint-lavender text-notion-brand-purple-800 font-semibold text-[11px]'
    : 'px-2 py-0.5 rounded-md bg-notion-tint-mint text-notion-brand-green font-semibold text-[11px]'
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

// ===== Recursive directory tree node — Notion-restyled =====
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
                'cursor-pointer text-[13px] py-1.5 pr-2 rounded-md transition-colors truncate flex items-center gap-1.5',
                isSelected
                  ? 'bg-notion-surface text-notion-ink font-medium border-l-2 border-l-notion-primary'
                  : 'text-notion-charcoal hover:bg-notion-surface',
              ],
              style: { paddingLeft: `${props.depth * 14 + 12}px` },
              onClick: () => emit('select', item.id),
            },
            [
              h('span', { class: 'opacity-70 text-[12px]' }, icon),
              h('span', { class: 'truncate' }, item.title),
            ]
          )
        )
      }

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
                    'cursor-pointer text-[13px] font-medium py-1.5 pr-2 rounded-md flex items-center gap-1.5 transition-colors hover:bg-notion-surface',
                  ],
                  style: { paddingLeft: `${props.depth * 14 + 8}px` },
                  onClick: () => emit('toggle', path),
                },
                [
                  h(
                    'span',
                    { class: 'flex-shrink-0 text-notion-stone hover:text-notion-steel p-0.5' },
                    [
                      h(
                        'svg',
                        {
                          class: ['w-3 h-3 transition-transform duration-200', isExpanded ? 'rotate-90' : ''],
                          viewBox: '0 0 24 24',
                          fill: 'none',
                          stroke: 'currentColor',
                          'stroke-width': '2.5',
                        },
                        [h('polyline', { points: '9 18 15 12 9 6' })]
                      ),
                    ]
                  ),
                  h('span', { class: 'text-notion-stone' }, '📁'),
                  h(
                    'span',
                    {
                      'data-directory-name': '',
                      class: 'flex-1 text-notion-charcoal truncate',
                    },
                    name
                  ),
                  itemCount > 0
                    ? h(
                        'span',
                        { class: 'flex-shrink-0 text-[11px] font-semibold text-notion-steel bg-notion-surface border border-notion-hairline rounded-full px-1.5 py-0.5' },
                        String(itemCount)
                      )
                    : null,
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
