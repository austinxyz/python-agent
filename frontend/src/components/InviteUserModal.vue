<template>
  <div v-if="modelValue" class="fixed inset-0 z-50 flex items-center justify-center">
    <div class="absolute inset-0 bg-black/40" @click="$emit('update:modelValue', false)"></div>
    <div class="relative bg-white rounded-lg shadow-xl w-full max-w-md mx-4 p-5">

      <!-- Form state -->
      <template v-if="state === 'form'">
        <h2 class="text-[14px] font-semibold text-notion-ink mb-3">邀请新用户</h2>
        <form @submit.prevent="handleSubmit">
          <div class="mb-3">
            <label class="block text-[10px] font-semibold uppercase text-notion-steel mb-1">邮箱</label>
            <input
              v-model="email"
              type="email"
              name="email"
              placeholder="user@example.com"
              class="w-full h-8 px-2 border border-notion-hairline-strong rounded text-[12px] outline-none focus:border-notion-primary"
            />
          </div>
          <div class="mb-4">
            <label class="block text-[10px] font-semibold uppercase text-notion-steel mb-1">角色</label>
            <div class="flex gap-1.5">
              <label
                class="flex-1 px-2 py-1.5 border rounded text-[11px] cursor-pointer"
                :class="role === 'member' ? 'border-2 border-notion-primary bg-notion-tint-lavender text-notion-brand-purple-800' : 'border-notion-hairline-strong bg-white'"
              >
                <input type="radio" v-model="role" value="member" class="sr-only" />
                {{ role === 'member' ? '●' : '○' }} member
              </label>
              <label
                class="flex-1 px-2 py-1.5 border rounded text-[11px] cursor-pointer"
                :class="role === 'admin' ? 'border-2 border-notion-primary bg-notion-tint-lavender text-notion-brand-purple-800' : 'border-notion-hairline-strong bg-white'"
              >
                <input type="radio" v-model="role" value="admin" class="sr-only" />
                {{ role === 'admin' ? '●' : '○' }} admin
              </label>
            </div>
          </div>
          <div class="flex gap-1.5 mt-2">
            <button type="button" class="flex-1 h-8 bg-white border border-notion-hairline-strong rounded text-[12px]" @click="$emit('update:modelValue', false)">取消</button>
            <button type="submit" class="flex-1 h-8 bg-notion-primary text-white border-none rounded text-[12px]">生成邀请链接</button>
          </div>
        </form>
      </template>

      <!-- Success state -->
      <template v-else-if="state === 'success'">
        <h2 class="text-[14px] font-semibold text-notion-success mb-3">✓ 邀请已生成</h2>
        <p class="text-[12px] text-notion-charcoal mb-2">把下面链接发给 <strong>{{ email }}</strong>：</p>
        <div class="flex gap-1.5 mb-1.5">
          <code class="flex-1 px-2 py-2 bg-notion-tint-gray border border-notion-hairline rounded text-[10px] text-notion-charcoal overflow-hidden text-ellipsis whitespace-nowrap">{{ inviteUrl }}</code>
          <button
            data-copy-btn
            class="bg-notion-primary text-white border-none px-2.5 rounded text-[11px]"
            @click="copyUrl"
          >复制</button>
        </div>
        <p class="text-[11px] text-notion-steel">7 天后过期。如果对方没及时点，回列表"重发邀请"。</p>
        <button class="mt-3.5 w-full h-[30px] bg-white border border-notion-hairline-strong rounded text-[12px]" @click="$emit('update:modelValue', false)">完成</button>
      </template>

      <!-- Conflict (409) state -->
      <template v-else-if="state === 'conflict'">
        <h2 class="text-[14px] font-semibold text-notion-warning mb-2">⚠ 该用户已存在</h2>
        <p class="text-[12px] text-notion-charcoal mb-2">
          <strong>{{ conflict.email }}</strong> 已经在系统里，状态：
          <span class="font-medium" :class="conflict.status === 'active' ? 'text-notion-success' : ''">{{ conflict.status }}</span>。
        </p>
        <p class="text-[11px] text-notion-steel mb-3">下面操作根据当前状态可选：</p>

        <button
          v-if="conflict.status === 'active'"
          disabled
          class="w-full h-[30px] bg-white border border-notion-hairline-strong rounded text-[12px] text-notion-stone mb-1.5 cursor-not-allowed"
        >已激活，无需邀请</button>
        <button
          v-else-if="conflict.status === 'invited'"
          class="w-full h-[30px] bg-white border border-notion-hairline-strong rounded text-[12px] mb-1.5"
          @click="handleResend"
        >重发邀请</button>
        <button
          v-else-if="conflict.status === 'disabled'"
          class="w-full h-[30px] bg-white border border-notion-hairline-strong rounded text-[12px] mb-1.5"
          @click="handleReEnable"
        >重新启用</button>

        <button class="w-full h-[30px] bg-white border border-notion-hairline-strong rounded text-[12px]" @click="$emit('update:modelValue', false)">关闭</button>
      </template>

    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAdminUsersStore } from '../stores/adminUsers.js'

defineProps({ modelValue: { type: Boolean, default: false } })
defineEmits(['update:modelValue'])

const adminUsers = useAdminUsersStore()

const state = ref('form')
const email = ref('')
const role = ref('member')
const inviteUrl = ref('')
const conflict = ref(null)

async function handleSubmit() {
  const result = await adminUsers.inviteUser(email.value, role.value)
  if (result?.conflict) {
    conflict.value = result.conflict
    state.value = 'conflict'
  } else if (result?.invite_url) {
    inviteUrl.value = result.invite_url
    state.value = 'success'
  }
}

async function handleResend() {
  const result = await adminUsers.resendInvite(conflict.value.id)
  if (result?.invite_url) {
    inviteUrl.value = result.invite_url
    state.value = 'success'
  }
}

async function handleReEnable() {
  try {
    await adminUsers.updateUser(conflict.value.id, { status: 'active' })
    emit('update:modelValue', false)
  } catch {
    // error set on store.error; InviteUserModal surfaces it via adminUsers.error if needed
  }
}

function copyUrl() {
  navigator.clipboard?.writeText(inviteUrl.value)
}
</script>
