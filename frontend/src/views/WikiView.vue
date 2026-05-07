<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50">
    <div class="bg-white border-b border-border px-8 py-5">
      <div class="max-w-5xl mx-auto flex items-center space-x-3">
        <div class="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center">
          <BookOpen class="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 class="text-xl font-bold text-gray-900">知识库</h1>
          <p class="text-sm text-muted-foreground">浏览和搜索知识条目</p>
        </div>
      </div>
    </div>
    <div class="max-w-5xl mx-auto px-8 py-12 flex flex-col items-center justify-center text-center">
      <div class="w-16 h-16 bg-blue-100 rounded-2xl flex items-center justify-center mb-4">
        <BookOpen class="w-8 h-8 text-blue-500" />
      </div>
      <h2 class="text-lg font-semibold text-gray-800 mb-2">知识库即将上线</h2>
      <p class="text-sm text-muted-foreground">先通过「摄入」页面添加知识内容</p>
    </div>
  </div>
</template>

<script setup>
import { BookOpen } from 'lucide-vue-next'
</script>
