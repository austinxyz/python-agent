<template>
  <div class="flex flex-col h-full overflow-hidden">

    <!-- Hero band -->
    <div class="bg-notion-brand-navy text-notion-on-dark px-6 py-4 flex justify-between items-end shrink-0">
      <div>
        <h1 class="text-xl font-semibold">用户管理</h1>
        <p class="text-[12px] text-notion-on-dark-muted mt-0.5">
          {{ adminUsers.users.length }} 个用户 ·
          {{ adminUsers.users.filter(u => u.role === 'admin').length }} admin ·
          {{ adminUsers.users.filter(u => u.status === 'active').length }} active ·
          {{ adminUsers.users.filter(u => u.status === 'invited').length }} invited ·
          {{ adminUsers.users.filter(u => u.status === 'disabled').length }} disabled
        </p>
      </div>
      <button
        class="bg-notion-primary text-white border-none px-3.5 py-2 rounded-md text-[13px] font-medium"
        @click="openInvite"
      >+ 邀请用户</button>
    </div>

    <!-- Desktop table (hidden on mobile) -->
    <div class="hidden md:block flex-1 p-4 overflow-y-auto">
      <div class="bg-white border border-notion-hairline rounded-lg overflow-hidden">
        <!-- Header -->
        <div class="grid text-[10px] font-semibold uppercase tracking-wide text-notion-steel px-3.5 py-2.5 bg-notion-surface border-b border-notion-hairline"
          style="grid-template-columns: 280px 1fr 90px 110px 130px 140px">
          <div>用户</div>
          <div>姓名</div>
          <div>角色</div>
          <div>状态</div>
          <div>最后登录</div>
          <div class="text-right">操作</div>
        </div>
        <!-- Rows -->
        <div
          v-for="user in adminUsers.users"
          :key="user.id"
          :data-user-row="user.id"
          class="grid px-3.5 py-3 border-b border-notion-hairline-soft text-[12px] items-center"
          :class="rowClass(user)"
          style="grid-template-columns: 280px 1fr 90px 110px 130px 140px"
        >
          <!-- Email + avatar -->
          <div class="flex items-center gap-2 min-w-0">
            <div class="w-8 h-8 rounded-full flex items-center justify-center text-[12px] font-semibold text-white shrink-0"
              :style="{ background: avatarColor(user) }">
              {{ (user.name || user.email)?.[0]?.toUpperCase() ?? '?' }}
            </div>
            <div class="min-w-0">
              <div class="text-[12px] font-medium text-notion-ink overflow-hidden text-ellipsis whitespace-nowrap"
                :class="user.status === 'disabled' ? 'line-through' : ''">
                {{ user.email }}
              </div>
              <div v-if="isSelf(user)" class="text-[10px] text-notion-steel">你</div>
            </div>
          </div>
          <!-- Name -->
          <div class="text-notion-charcoal" :class="user.status === 'disabled' ? 'text-notion-slate' : ''">
            {{ user.name ?? (user.status === 'invited' ? '未激活' : '—') }}
          </div>
          <!-- Role badge -->
          <div>
            <span class="px-1.5 py-0.5 rounded text-[11px] font-medium"
              :class="user.role === 'admin' ? 'bg-notion-tint-lavender text-notion-brand-purple-800' : 'bg-notion-tint-gray text-notion-slate'">
              {{ user.role }}
            </span>
          </div>
          <!-- Status -->
          <div>
            <span class="inline-flex items-center gap-1 text-[11px]" :class="statusTextClass(user)">
              <span class="w-1.5 h-1.5 rounded-full" :class="statusDotClass(user)"></span>
              {{ user.status }}
            </span>
          </div>
          <!-- Last login -->
          <div class="text-[11px] text-notion-slate">—</div>
          <!-- Actions -->
          <div class="text-right flex gap-1 justify-end">
            <span v-if="isSelf(user)" class="text-[11px] text-notion-stone italic">不能改自己</span>
            <template v-else>
              <!-- Admin: demote -->
              <button
                v-if="user.role === 'admin'"
                class="px-2 py-0.5 bg-white border border-notion-hairline-strong rounded text-[10px] disabled:opacity-40 disabled:cursor-not-allowed"
                :disabled="adminCount <= 1"
                @click="handleDemote(user)"
              >↓ member</button>
              <!-- Member active: promote -->
              <button
                v-if="user.role === 'member' && user.status === 'active'"
                class="px-2 py-0.5 bg-white border border-notion-hairline-strong rounded text-[10px]"
                @click="adminUsers.updateUser(user.id, { role: 'admin' })"
              >↑ admin</button>
              <!-- Active: disable -->
              <button
                v-if="user.status === 'active'"
                class="px-2 py-0.5 bg-white border border-notion-hairline-strong rounded text-[10px]"
                @click="adminUsers.updateUser(user.id, { status: 'disabled' })"
              >停用</button>
              <!-- Invited: resend + cancel -->
              <button
                v-if="user.status === 'invited'"
                class="px-2 py-0.5 bg-notion-primary text-white border-none rounded text-[10px]"
                @click="adminUsers.resendInvite(user.id)"
              >重发</button>
              <button
                v-if="user.status === 'invited'"
                class="px-2 py-0.5 bg-white border border-notion-hairline-strong rounded text-[10px]"
                @click="adminUsers.updateUser(user.id, { status: 'disabled' })"
              >取消</button>
              <!-- Disabled: enable + delete -->
              <button
                v-if="user.status === 'disabled'"
                class="px-2 py-0.5 bg-white border border-notion-hairline-strong rounded text-[10px]"
                @click="adminUsers.updateUser(user.id, { status: 'active' })"
              >启用</button>
              <button
                v-if="user.status === 'disabled'"
                class="px-2 py-0.5 bg-white border border-notion-tint-rose rounded text-[10px] text-notion-error"
                @click="openDelete(user)"
              >删除</button>
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- Mobile card list (hidden on desktop) -->
    <div class="md:hidden flex-1 p-3 overflow-y-auto flex flex-col gap-2" data-mobile-cards>
      <div
        v-for="user in adminUsers.users"
        :key="user.id"
        class="border border-notion-hairline rounded-lg p-2.5"
        :class="cardClass(user)"
      >
        <div class="flex items-center gap-2 mb-1.5">
          <div class="w-8 h-8 rounded-full flex items-center justify-center text-[13px] font-semibold text-white shrink-0"
            :style="{ background: avatarColor(user) }">
            {{ (user.name || user.email)?.[0]?.toUpperCase() ?? '?' }}
          </div>
          <div class="flex-1 min-w-0">
            <div class="text-[12px] font-medium" :class="user.status === 'disabled' ? 'line-through' : ''">
              {{ user.email }}
            </div>
            <div class="text-[10px] text-notion-steel">{{ user.name ?? '' }} {{ isSelf(user) ? '· 你' : '' }}</div>
          </div>
          <span class="text-[9px] px-1.5 py-0.5 rounded"
            :class="user.role === 'admin' ? 'bg-notion-tint-lavender text-notion-brand-purple-800' : 'bg-notion-tint-gray text-notion-slate'">
            {{ user.role }}
          </span>
        </div>
        <div v-if="isSelf(user)" class="text-[10px] text-notion-stone italic">不能改自己</div>
        <div v-else class="flex gap-1.5">
          <button v-if="user.role === 'admin'" class="flex-1 h-7 bg-white border border-notion-hairline-strong rounded text-[10px]"
            :disabled="adminCount <= 1" @click="handleDemote(user)">改 member</button>
          <button v-if="user.role === 'member' && user.status === 'active'" class="flex-1 h-7 bg-white border border-notion-hairline-strong rounded text-[10px]"
            @click="adminUsers.updateUser(user.id, { role: 'admin' })">改 admin</button>
          <button v-if="user.status === 'active'" class="flex-1 h-7 bg-white border border-notion-hairline-strong rounded text-[10px]"
            @click="adminUsers.updateUser(user.id, { status: 'disabled' })">停用</button>
          <button v-if="user.status === 'invited'" class="flex-1 h-7 bg-notion-primary text-white border-none rounded text-[10px]"
            @click="adminUsers.resendInvite(user.id)">重发</button>
          <button v-if="user.status === 'invited'" class="flex-1 h-7 bg-white border border-notion-hairline-strong rounded text-[10px]"
            @click="adminUsers.updateUser(user.id, { status: 'disabled' })">取消邀请</button>
          <button v-if="user.status === 'disabled'" class="flex-1 h-7 bg-white border border-notion-hairline-strong rounded text-[10px]"
            @click="adminUsers.updateUser(user.id, { status: 'active' })">启用</button>
          <button v-if="user.status === 'disabled'" class="flex-1 h-7 bg-white border border-notion-tint-rose rounded text-[10px] text-notion-error"
            @click="openDelete(user)">删除</button>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <InviteUserModal v-model="showInviteModal" />
    <DeleteUserModal
      v-if="selectedUser"
      v-model="showDeleteModal"
      :user="selectedUser"
    />

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAdminUsersStore } from '../stores/adminUsers.js'
import { useAuthStore } from '../stores/auth.js'
import InviteUserModal from '../components/InviteUserModal.vue'
import DeleteUserModal from '../components/DeleteUserModal.vue'

const adminUsers = useAdminUsersStore()
const auth = useAuthStore()

const showInviteModal = ref(false)
const showDeleteModal = ref(false)
const selectedUser = ref(null)

const adminCount = computed(() => adminUsers.users.filter(u => u.role === 'admin').length)

onMounted(() => adminUsers.fetchUsers())

function isSelf(user) {
  return user.id === auth.currentUser?.id
}

function openInvite() {
  showInviteModal.value = true
}

function openDelete(user) {
  selectedUser.value = user
  showDeleteModal.value = true
}

function handleDemote(user) {
  adminUsers.updateUser(user.id, { role: 'member' })
}

function avatarColor(user) {
  const colors = ['#5645d4', '#dd5b00', '#1aae39', '#0075de', '#e03131']
  const idx = user.email.charCodeAt(0) % colors.length
  return user.status === 'disabled' ? '#a4a097' : colors[idx]
}

function rowClass(user) {
  if (user.status === 'invited') return 'bg-notion-tint-yellow'
  if (user.status === 'disabled') return 'bg-notion-surface-soft opacity-70'
  return ''
}

function cardClass(user) {
  if (user.status === 'invited') return 'bg-notion-tint-yellow border-notion-tint-yellow'
  if (user.status === 'disabled') return 'bg-notion-surface-soft opacity-70'
  return 'bg-white'
}

function statusTextClass(user) {
  if (user.status === 'active') return 'text-notion-success'
  if (user.status === 'invited') return 'text-notion-warning'
  return 'text-notion-steel'
}

function statusDotClass(user) {
  if (user.status === 'active') return 'bg-notion-success'
  if (user.status === 'invited') return 'bg-notion-warning'
  return 'bg-notion-steel'
}
</script>
