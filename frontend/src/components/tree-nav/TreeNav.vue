<template>
  <ul class="tree-nav">
    <li v-for="item in items" :key="item.label" @click="emit('select', item)">
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
