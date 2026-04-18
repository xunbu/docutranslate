<template>
  <ul class="space-y-1">
    <slot></slot>
  </ul>
</template>

<script setup>
defineProps({
  activeKey: [String, Number]
})

defineEmits(['update:activeKey'])
</script>
