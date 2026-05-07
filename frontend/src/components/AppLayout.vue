<template>
  <div class="flex h-screen bg-background overflow-hidden">
    <!-- Sidebar -->
    <aside
      :class="[
        'bg-card border-r border-border flex flex-col h-full transition-all duration-300',
        isCollapsed ? 'w-16' : 'w-56'
      ]"
    >
      <!-- Logo -->
      <div class="border-b border-border p-4 flex items-center" :class="isCollapsed ? 'justify-center' : 'justify-between'">
        <div v-if="!isCollapsed" class="flex items-center space-x-2">
          <div class="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <Brain class="w-5 h-5 text-white" />
          </div>
          <span class="font-bold text-foreground text-sm">知识 Agent</span>
        </div>
        <div v-else class="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
          <Brain class="w-5 h-5 text-white" />
        </div>
        <button
          v-if="!isCollapsed"
          @click="isCollapsed = true"
          class="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
        >
          <ChevronsLeft class="w-4 h-4" />
        </button>
      </div>

      <!-- Expand button when collapsed -->
      <div v-if="isCollapsed" class="p-2 flex justify-center border-b border-border">
        <button
          @click="isCollapsed = false"
          class="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
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
          :class="[
            'flex items-center rounded-md text-sm font-medium transition-colors',
            isCollapsed ? 'justify-center p-2.5' : 'space-x-3 px-3 py-2',
            isActiveRoute(item.to)
              ? 'bg-primary/10 text-primary'
              : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
          ]"
        >
          <component :is="item.icon" class="w-5 h-5 flex-shrink-0" />
          <span v-if="!isCollapsed">{{ item.label }}</span>
        </router-link>
      </nav>

      <!-- Footer -->
      <div v-if="!isCollapsed" class="p-4 border-t border-border">
        <p class="text-xs text-muted-foreground">v1.0.0</p>
      </div>
    </aside>

    <!-- Main content -->
    <main class="flex-1 overflow-auto">
      <router-view />
    </main>
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
