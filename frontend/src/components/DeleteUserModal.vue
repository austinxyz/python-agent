<template>
  <div v-if="modelValue" class="fixed inset-0 z-50 flex items-center justify-center">
    <div class="absolute inset-0 bg-black/40" @click="close"></div>
    <div class="relative bg-white rounded-lg shadow-xl w-full max-w-[480px] mx-4 p-6">

      <h2 class="text-[15px] font-semibold text-notion-error mb-3.5">⚠ 永久删除用户</h2>
      <p class="text-[13px] text-notion-charcoal mb-2.5">
        <strong>{{ user.email }}</strong> 将被永久删除。
      </p>

      <div class="bg-notion-tint-rose border border-notion-tint-rose rounded p-2.5 text-[12px] text-notion-charcoal mb-3.5 leading-relaxed">
        <strong>会一并删除：</strong><br />
        • 该用户所有 private entries（包括对应 Qdrant vectors）<br />
        • 所有 chat sessions / messages<br />
        • 所有 notes
        <br /><br />
        <strong>不会删除：</strong><br />
        • 该用户向 knowledge 库 ingest 的文件（保留为共享内容，user_id 留作 audit）
      </div>

      <p class="text-[12px] text-notion-charcoal mb-1.5">
        输入 <code class="text-[11px] bg-notion-tint-gray px-1 rounded">{{ localPart }}</code> 确认（防误点）：
      </p>
      <input
        v-model="confirmInput"
        type="text"
        class="w-full h-[34px] px-2.5 border border-notion-hairline-strong rounded text-[13px] mb-3.5 outline-none focus:border-notion-error"
      />

      <div v-if="error" class="text-[12px] text-notion-error mb-2">{{ error }}</div>

      <div class="flex gap-2">
        <button class="flex-1 h-[34px] bg-white border border-notion-hairline-strong rounded text-[13px]" @click="close">取消</button>
        <button
          class="flex-1 h-[34px] bg-notion-error text-white border-none rounded text-[13px] font-medium"
          :disabled="!canDelete"
          @click="handleDelete"
        >永久删除</button>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAdminUsersStore } from '../stores/adminUsers.js'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  user: { type: Object, required: true },
})
const emit = defineEmits(['update:modelValue'])

const adminUsers = useAdminUsersStore()
const confirmInput = ref('')
const error = ref(null)

const localPart = computed(() => props.user?.email?.split('@')[0] ?? '')
const canDelete = computed(() => confirmInput.value === localPart.value)

function close() {
  confirmInput.value = ''
  error.value = null
  emit('update:modelValue', false)
}

async function handleDelete() {
  if (!canDelete.value) return
  try {
    await adminUsers.deleteUser(props.user.id)
    close()
  } catch (err) {
    error.value = err?.message ?? '删除失败'
  }
}
</script>
