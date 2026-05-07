<template>
  <ul class="space-y-1">
    <li
      v-for="item in items"
      :key="item.label"
      @click="emit('select', item)"
      class="px-3 py-2 rounded-lg text-sm cursor-pointer transition-colors hover:bg-accent hover:text-accent-foreground text-muted-foreground"
    >
      {{ item.label }}
    </li>
  </ul>
</template>

<script setup>
defineProps({
  items: { type: Array, required: true },
})
const emit = defineEmits(['select'])
</script>
