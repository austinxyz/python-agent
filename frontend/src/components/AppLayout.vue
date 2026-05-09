<template>
  <div class="flex h-screen bg-notion-canvas overflow-hidden">
    <!-- Desktop sidebar (md and above) -->
    <aside
      :class="[
        'bg-notion-surface-soft border-r border-notion-hairline hidden md:flex flex-col h-full transition-all duration-300',
        isCollapsed ? 'w-16' : 'w-56'
      ]"
    >
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

      <!-- Footer -->
      <div v-if="!isCollapsed" class="p-4 border-t border-notion-hairline">
        <p class="text-xs text-notion-stone">v1.0.0</p>
      </div>
    </aside>

    <!-- Main content -->
    <main class="flex-1 overflow-auto pb-[calc(56px+env(safe-area-inset-bottom))] md:pb-0">
      <router-view />
    </main>

    <!-- Mobile bottom tab bar (md-) -->
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
    </nav>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { Brain, BookOpen, Upload, MessageSquare, Lock, ChevronsLeft, ChevronsRight } from 'lucide-vue-next'

const route = useRoute()
const isCollapsed = ref(false)

const navItems = [
  { to: '/wiki', label: '知识库', icon: BookOpen },
  { to: '/ingest', label: '摄入', icon: Upload },
  { to: '/chat', label: '对话', icon: MessageSquare },
  { to: '/private', label: '私有数据', icon: Lock },
]

const isActiveRoute = (path) => route.path.startsWith(path)
</script>
