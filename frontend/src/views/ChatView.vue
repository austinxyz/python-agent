<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50">
    <div class="bg-white border-b border-border px-8 py-5">
      <div class="max-w-4xl mx-auto flex items-center space-x-3">
        <div class="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-600 rounded-xl flex items-center justify-center">
          <MessageSquare class="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 class="text-xl font-bold text-gray-900">智能对话</h1>
          <p class="text-sm text-muted-foreground">基于知识库的 RAG 问答</p>
        </div>
      </div>
    </div>
    <div class="max-w-4xl mx-auto px-8 py-12 flex flex-col items-center justify-center text-center">
      <div class="w-16 h-16 bg-purple-100 rounded-2xl flex items-center justify-center mb-4">
        <MessageSquare class="w-8 h-8 text-purple-500" />
      </div>
      <h2 class="text-lg font-semibold text-gray-800 mb-2">对话功能即将上线</h2>
      <p class="text-sm text-muted-foreground">先通过「摄入」页面添加知识内容，然后开始问答</p>
    </div>
  </div>
</template>

<script setup>
import { MessageSquare } from 'lucide-vue-next'
</script>
