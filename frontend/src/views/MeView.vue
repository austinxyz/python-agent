<template>
  <!-- MeView — multi-user-auth-core. Mobile-only profile/menu page. -->
  <div class="h-full flex flex-col bg-notion-surface-soft text-notion-ink">
    <div class="bg-notion-brand-navy text-notion-on-dark px-6 py-5 flex-shrink-0">
      <h1 class="text-xl font-semibold tracking-tight leading-tight">我</h1>
    </div>

    <div class="flex-1 px-4 py-5 flex flex-col gap-3">
      <!-- Profile card -->
      <div class="bg-notion-canvas border border-notion-hairline rounded-lg p-3 flex items-center gap-3">
        <div class="w-[42px] h-[42px] rounded-full bg-notion-primary text-notion-on-primary flex items-center justify-center font-semibold text-[16px]">
          {{ initial }}
        </div>
        <div class="flex-1 min-w-0">
          <div class="text-[14px] font-semibold text-notion-ink flex items-center gap-1.5">
            {{ displayName }}
            <span v-if="isAdmin" class="bg-notion-tint-lavender text-notion-brand-purple-800 text-[9px] px-1.5 py-0.5 rounded">admin</span>
          </div>
          <div class="text-[11px] text-notion-steel truncate">{{ email }}</div>
        </div>
      </div>

      <button
        v-if="hasPassword"
        data-me-change-password
        class="text-left bg-notion-canvas border border-notion-hairline rounded-md px-3 py-3 text-[13px] text-notion-charcoal"
        @click="$router.push('/change-password')"
      >🔑 修改密码</button>

      <button
        data-me-logout
        class="text-left bg-notion-canvas border border-notion-tint-rose rounded-md px-3 py-3 text-[13px] text-notion-error"
        @click="onLogout"
      >→ 退出登录</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const router = useRouter()
const auth = useAuthStore()

const email = computed(() => auth.currentUser?.email ?? '')
const displayName = computed(() => auth.currentUser?.name || email.value || '')
const isAdmin = computed(() => auth.currentUser?.role === 'admin')
const initial = computed(() => (displayName.value || '?').charAt(0).toUpperCase())

// `hasPassword` is approximated: we don't expose password_hash from /me.
// Always show the "修改密码" link for V1 — Google-only users will get a 401
// from the backend, which the form catches as an error.
const hasPassword = computed(() => true)

async function onLogout() {
  await auth.logout()
  router.push('/login')
}
</script>
