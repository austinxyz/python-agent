<template>
  <!--
    Slide-in drawer for mobile (md-). Used by Wiki/Private/Ingest views to
    host their tree navigation when the inline sidebar is hidden. Desktop
    layout never mounts this; the host view conditionally renders us only
    when `open` is true at md-.
  -->
  <div
    v-if="open"
    class="md:hidden fixed inset-0 z-50 flex"
    @keydown.esc="$emit('close')"
  >
    <!-- Backdrop -->
    <div class="absolute inset-0 bg-black/40" @click="$emit('close')"></div>

    <!-- Panel -->
    <div class="relative w-[85%] max-w-sm h-full bg-notion-canvas shadow-xl flex flex-col animate-slide-in-left">
      <div v-if="title || $slots.header" class="flex items-center justify-between px-4 py-3 border-b border-notion-hairline">
        <slot name="header">
          <h2 class="text-[13px] font-semibold text-notion-ink">{{ title }}</h2>
        </slot>
        <button
          class="p-1.5 rounded-md hover:bg-notion-tint-gray text-notion-steel"
          aria-label="关闭"
          @click="$emit('close')"
        >
          <X class="w-4 h-4" />
        </button>
      </div>
      <div class="flex-1 overflow-y-auto">
        <slot />
      </div>
    </div>
  </div>
</template>

<script setup>
import { X } from 'lucide-vue-next'

defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: '' },
})
defineEmits(['close'])
</script>

<style>
@keyframes slide-in-left {
  from { transform: translateX(-100%); }
  to { transform: translateX(0); }
}
.animate-slide-in-left {
  animation: slide-in-left 0.18s ease-out;
}
</style>
