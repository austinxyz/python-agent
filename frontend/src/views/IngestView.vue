<template>
  <div class="ingest-view">
    <h1>摄入</h1>

    <div class="tabs">
      <button data-tab="ingest" :class="{ active: activeTab === 'ingest' }" @click="activeTab = 'ingest'">新建摄入</button>
      <button data-tab="files" :class="{ active: activeTab === 'files' }" @click="activeTab = 'files'">已上传文件</button>
    </div>

    <div data-panel="ingest" :hidden="activeTab !== 'ingest'" class="panel">
      <div class="destination-toggle">
        <button
          data-destination="knowledge"
          :class="{ active: store.destination === 'knowledge' }"
          @click="store.setDestination('knowledge')"
        >公共知识库</button>
        <button
          data-destination="private"
          :class="{ active: store.destination === 'private' }"
          @click="store.setDestination('private')"
        >私有数据</button>
      </div>

      <div class="source-inputs">
        <input
          data-input="source_url"
          type="url"
          v-model="sourceUrl"
          placeholder="URL 地址"
        />
        <textarea
          data-input="content"
          v-model="textContent"
          placeholder="粘贴文本内容"
        />
        <input
          data-input="file"
          type="file"
          @change="onFileChange"
        />
      </div>

      <div class="meta-inputs">
        <input data-input="domain" v-model="domain" placeholder="领域" />
        <input data-input="topic" v-model="topic" placeholder="主题" />
      </div>

      <p v-if="validationError" class="error">{{ validationError }}</p>

      <button data-action="submit" @click="submit" :disabled="isSubmitting">
        {{ isSubmitting ? '摄入中…' : '开始摄入' }}
      </button>

      <ul class="progress-list">
        <li v-for="job in store.jobs" :key="job.job_id" data-job-row>
          <span>{{ job.label }}</span>
          <span>{{ job.status }}</span>
          <span v-if="job.chunk_count != null">{{ job.chunk_count }} chunks</span>
          <span v-if="job.error" class="error">{{ job.error }}</span>
        </li>
      </ul>
    </div>

    <div data-panel="files" :hidden="activeTab !== 'files'" class="panel">
      <TreeNav :items="fileTreeItems" @select="onTreeSelect" />
      <ul class="file-list">
        <li
          v-for="file in filteredFiles"
          :key="file.file_id"
          data-file-row
        >
          <span>{{ file.orig_name }}</span>
          <span>{{ file.domain }} / {{ file.topic }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useIngestStore } from '../stores/ingest.js'
import TreeNav from '../components/tree-nav/TreeNav.vue'

const props = defineProps({
  initialFiles: {
    type: Array,
    default: () => [],
  },
})

const store = useIngestStore()
const activeTab = ref('ingest')

const sourceUrl = ref('')
const textContent = ref('')
const selectedFile = ref(null)
const domain = ref('general')
const topic = ref('general')
const validationError = ref('')
const selectedNode = ref(null)
const isSubmitting = ref(false)

const fileTreeItems = computed(() => {
  const domains = [...new Set(props.initialFiles.map(f => f.domain))]
  return domains.map(d => ({ label: d }))
})

const filteredFiles = computed(() => {
  if (!selectedNode.value) return props.initialFiles
  return props.initialFiles.filter(f => f.domain === selectedNode.value.label)
})

function onFileChange(event) {
  selectedFile.value = event.target.files[0] || null
}

function onTreeSelect(item) {
  selectedNode.value = item
}

async function submit() {
  if (isSubmitting.value) return
  validationError.value = ''

  const hasUrl = sourceUrl.value.trim().length > 0
  const hasText = textContent.value.trim().length > 0
  const hasFile = selectedFile.value !== null

  if (!hasUrl && !hasText && !hasFile) {
    validationError.value = '请提供摄入内容'
    return
  }

  let sourceType = 'text'
  if (hasUrl) sourceType = 'url'
  else if (hasFile) sourceType = 'file'

  const label = hasFile
    ? selectedFile.value.name
    : hasUrl
      ? sourceUrl.value
      : textContent.value.slice(0, 40)

  let payload
  if (hasFile) {
    payload = new FormData()
    payload.append('source_type', 'file')
    payload.append('destination', store.destination)
    payload.append('domain', domain.value)
    payload.append('topic', topic.value)
    payload.append('file', selectedFile.value)
  } else {
    payload = {
      source_type: sourceType,
      destination: store.destination,
      domain: domain.value,
      topic: topic.value,
    }
    if (hasUrl) payload.source_url = sourceUrl.value
    if (hasText) payload.content = textContent.value
  }

  isSubmitting.value = true
  try {
    const resp = await store._api.post('/ingest', payload)
    const { job_id } = resp.data
    store.addJob(job_id, label)
    sourceUrl.value = ''
    textContent.value = ''
    selectedFile.value = null
  } catch (err) {
    validationError.value = err?.response?.data?.error ?? err.message ?? '摄入失败，请重试'
  } finally {
    isSubmitting.value = false
  }
}
</script>
