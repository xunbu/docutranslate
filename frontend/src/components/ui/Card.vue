<template>
  <div class="border rounded" :class="cardClass">
    <div v-if="$slots.header || title" class="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
      <slot name="header">
        <h3 class="text-lg font-medium text-gray-900 dark:text-gray-100">{{ title }}</h3>
      </slot>
    </div>
    <div class="p-4">
      <slot></slot>
    </div>
    <div v-if="$slots.footer" class="px-4 py-3 border-t border-gray-200 dark:border-gray-700">
      <slot name="footer"></slot>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: String,
  variant: {
    type: String,
    default: 'default' // default, bordered
  }
})

const cardClass = computed(() => {
  const variants = {
    default: 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800',
    bordered: 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800'
  }
  return variants[props.variant] || variants.default
})
</script>
