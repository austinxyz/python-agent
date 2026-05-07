<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50">
    <div class="bg-white border-b border-border px-8 py-5">
      <div class="max-w-4xl mx-auto flex items-center space-x-3">
        <div class="w-10 h-10 bg-gradient-to-br from-gray-600 to-gray-800 rounded-xl flex items-center justify-center">
          <Lock class="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 class="text-xl font-bold text-gray-900">私有数据</h1>
          <p class="text-sm text-muted-foreground">仅限当前用户访问的私有知识</p>
        </div>
      </div>
    </div>
    <div class="max-w-4xl mx-auto px-8 py-12 flex flex-col items-center justify-center text-center">
      <div class="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mb-4">
        <Lock class="w-8 h-8 text-gray-500" />
      </div>
      <h2 class="text-lg font-semibold text-gray-800 mb-2">私有数据管理即将上线</h2>
      <p class="text-sm text-muted-foreground">在「摄入」页面选择「私有数据」存储个人知识</p>
    </div>
  </div>
</template>

<script setup>
import { Lock } from 'lucide-vue-next'
</script>
