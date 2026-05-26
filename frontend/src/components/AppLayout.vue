<template>
  <div class="flex h-screen bg-notion-canvas overflow-hidden">
    <!-- Desktop sidebar (md and above) -->
    <aside
      :class="[
        'bg-notion-surface-soft border-r border-notion-hairline hidden md:flex flex-col h-full transition-all duration-300',
        isCollapsed ? 'w-16' : 'w-56'
      ]"
    >
      <!-- User pill at TOP (growing-style) -->
      <div data-user-pill class="border-b border-notion-hairline p-3">
        <!-- Logged-out state -->
        <div v-if="!auth.currentUser" :class="isCollapsed ? 'flex justify-center' : 'flex items-center gap-2 p-2 bg-notion-canvas border border-notion-hairline rounded-md'">
          <div class="w-7 h-7 rounded-full bg-notion-hairline text-notion-stone flex items-center justify-center text-[12px]">?</div>
          <template v-if="!isCollapsed">
            <div class="flex-1 text-[11px] text-notion-slate">未登录</div>
            <router-link
              data-user-pill-login
              to="/login"
              class="bg-notion-primary text-notion-on-primary text-[11px] font-medium px-2.5 py-1 rounded"
            >登录</router-link>
          </template>
        </div>
        <!-- Logged-in state -->
        <div v-else :class="isCollapsed ? 'flex justify-center' : 'flex items-center gap-2 p-2 bg-notion-canvas border border-notion-hairline rounded-md'">
          <div class="w-7 h-7 rounded-full bg-notion-primary text-notion-on-primary flex items-center justify-center text-[12px] font-semibold flex-shrink-0">
            <img v-if="auth.currentUser.picture_url" :src="auth.currentUser.picture_url" class="w-full h-full rounded-full object-cover" :alt="userInitial" />
            <span v-else>{{ userInitial }}</span>
          </div>
          <template v-if="!isCollapsed">
            <div class="flex-1 min-w-0">
              <div class="text-[11px] font-medium text-notion-ink flex items-center gap-1">
                <span class="truncate">{{ displayName }}</span>
                <span v-if="auth.currentUser.role === 'admin'" data-user-pill-admin-badge class="bg-notion-tint-lavender text-notion-brand-purple-800 text-[8px] px-1.5 py-0.5 rounded">admin</span>
              </div>
              <div class="text-[10px] text-notion-steel truncate">{{ auth.currentUser.email }}</div>
            </div>
            <button
              data-user-pill-logout
              title="退出"
              @click="onLogout"
              class="p-1 text-notion-steel hover:text-notion-error transition-colors flex-shrink-0"
            >
              <LogOut class="w-3.5 h-3.5" />
            </button>
          </template>
        </div>
      </div>

      <!-- Logo -->
      <div class="border-b border-notion-hairline p-4 flex items-center" :class="isCollapsed ? 'justify-center' : 'justify-between'">
        <div v-if="!isCollapsed" class="flex items-center space-x-2">
          <div class="w-8 h-8 bg-notion-brand-navy rounded-lg flex items-center justify-center">
            <Brain class="w-5 h-5 text-notion-on-dark" />
          </div>
          <span class="font-semibold text-notion-ink text-sm">知识 Agent</span>
        </div>
        <div v-else class="w-8 h-8 bg-notion-brand-navy rounded-lg flex items-center justify-center">
          <Brain class="w-5 h-5 text-notion-on-dark" />
        </div>
        <button
          v-if="!isCollapsed"
          @click="isCollapsed = true"
          class="p-1.5 rounded-md text-notion-steel hover:text-notion-ink hover:bg-notion-tint-gray transition-colors"
        >
          <ChevronsLeft class="w-4 h-4" />
        </button>
      </div>

      <!-- Expand button when collapsed -->
      <div v-if="isCollapsed" class="p-2 flex justify-center border-b border-notion-hairline">
        <button
          @click="isCollapsed = false"
          class="p-1.5 rounded-md text-notion-steel hover:text-notion-ink hover:bg-notion-tint-gray transition-colors"
        >
          <ChevronsRight class="w-4 h-4" />
        </button>
      </div>

      <!-- Nav -->
      <nav class="flex-1 overflow-y-auto p-2 space-y-1">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          :title="isCollapsed ? item.label : undefined"
          :aria-current="isActiveRoute(item.to) ? 'page' : undefined"
          :class="[
            'flex items-center rounded-md text-sm font-medium transition-colors',
            isCollapsed ? 'justify-center p-2.5' : 'space-x-3 px-3 py-2',
            isActiveRoute(item.to)
              ? 'bg-notion-tint-lavender text-notion-brand-purple-800'
              : 'text-notion-slate hover:bg-notion-tint-gray hover:text-notion-ink'
          ]"
        >
          <component :is="item.icon" class="w-5 h-5 flex-shrink-0" />
          <span v-if="!isCollapsed">{{ item.label }}</span>
        </router-link>
      </nav>

      <!-- Admin section (admin role only) -->
      <div v-if="auth.currentUser?.role === 'admin'" class="border-t border-notion-hairline p-2 space-y-1">
        <router-link
          to="/admin/users"
          :title="isCollapsed ? '用户管理' : undefined"
          :aria-current="isActiveRoute('/admin/users') ? 'page' : undefined"
          :class="[
            'flex items-center rounded-md text-sm font-medium transition-colors',
            isCollapsed ? 'justify-center p-2.5' : 'space-x-3 px-3 py-2',
            isActiveRoute('/admin/users')
              ? 'bg-notion-tint-lavender text-notion-brand-purple-800'
              : 'text-notion-slate hover:bg-notion-tint-gray hover:text-notion-ink'
          ]"
        >
          <Users class="w-5 h-5 flex-shrink-0" />
          <span v-if="!isCollapsed">用户管理</span>
        </router-link>
        <router-link
          to="/admin/cert"
          :title="isCollapsed ? '证书与 Tailscale 状态' : undefined"
          :aria-current="isActiveRoute('/admin/cert') ? 'page' : undefined"
          :class="[
            'flex items-center rounded-md text-sm font-medium transition-colors',
            isCollapsed ? 'justify-center p-2.5' : 'space-x-3 px-3 py-2',
            isActiveRoute('/admin/cert')
              ? 'bg-notion-tint-lavender text-notion-brand-purple-800'
              : 'text-notion-slate hover:bg-notion-tint-gray hover:text-notion-ink'
          ]"
        >
          <Shield class="w-5 h-5 flex-shrink-0" />
          <span v-if="!isCollapsed">证书与 Tailscale 状态</span>
        </router-link>
      </div>

      <!-- Footer -->
      <div v-if="!isCollapsed" class="p-4 border-t border-notion-hairline">
        <p class="text-xs text-notion-stone">v1.0.0</p>
      </div>
    </aside>

    <!-- Main content -->
    <main class="flex-1 overflow-auto pb-[calc(56px+env(safe-area-inset-bottom))] md:pb-0">
      <router-view />
    </main>

    <!-- Mobile bottom tab bar (md-) — 5 tabs (5th is "我") -->
    <nav
      data-bottom-tabs
      class="md:hidden fixed bottom-0 inset-x-0 z-40 flex items-stretch bg-notion-canvas border-t border-notion-hairline pb-[env(safe-area-inset-bottom)]"
      role="navigation"
      aria-label="Primary"
    >
      <router-link
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        :aria-current="isActiveRoute(item.to) ? 'page' : undefined"
        :class="[
          'flex-1 flex flex-col items-center justify-center gap-0.5 py-2 text-[11px] font-medium transition-colors',
          isActiveRoute(item.to)
            ? 'bg-notion-tint-lavender text-notion-brand-purple-800'
            : 'text-notion-steel hover:text-notion-ink'
        ]"
      >
        <component :is="item.icon" class="w-6 h-6" />
        <span>{{ item.label }}</span>
      </router-link>
      <!-- 5th tab: 我 -->
      <router-link
        data-bottom-tab-me
        to="/me"
        :aria-current="isActiveRoute('/me') ? 'page' : undefined"
        :class="[
          'flex-1 flex flex-col items-center justify-center gap-0.5 py-2 text-[11px] font-medium transition-colors',
          isActiveRoute('/me')
            ? 'bg-notion-tint-lavender text-notion-brand-purple-800'
            : 'text-notion-steel hover:text-notion-ink'
        ]"
      >
        <div v-if="auth.currentUser?.picture_url" class="w-6 h-6 rounded-full overflow-hidden">
          <img :src="auth.currentUser.picture_url" class="w-full h-full object-cover" alt="me" />
        </div>
        <div v-else class="w-6 h-6 rounded-full bg-notion-primary text-notion-on-primary flex items-center justify-center text-[10px] font-semibold">
          {{ userInitial }}
        </div>
        <span>我</span>
      </router-link>
    </nav>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Brain, BookOpen, Upload, MessageSquare, Lock, ChevronsLeft, ChevronsRight, LogOut, Shield, Users } from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth.js'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const isCollapsed = ref(false)

const navItems = [
  { to: '/wiki', label: '知识库', icon: BookOpen },
  { to: '/ingest', label: '摄入', icon: Upload },
  { to: '/chat', label: '对话', icon: MessageSquare },
  { to: '/private', label: '私有数据', icon: Lock },
]

const isActiveRoute = (path) => route.path.startsWith(path)

const displayName = computed(() => auth.currentUser?.name || auth.currentUser?.email || '')
const userInitial = computed(() => (displayName.value || '?').charAt(0).toUpperCase())

async function onLogout() {
  await auth.logout()
  router.push('/login')
}
</script>
