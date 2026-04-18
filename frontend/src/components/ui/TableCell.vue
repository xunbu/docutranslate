<template>
  <td class="px-4 py-2 text-sm text-gray-700 dark:text-gray-300" :class="alignClass">
    <slot></slot>
  </td>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  align: {
    type: String,
    default: 'left' // left, center, right
  }
})

const alignClass = computed(() => {
  const aligns = {
    left: 'text-left',
    center: 'text-center',
    right: 'text-right'
  }
  return aligns[props.align] || aligns.left
})
</script>
