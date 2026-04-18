<template>
  <div class="flex items-start gap-2 p-3 rounded" :class="alertClass">
    <svg v-if="showIcon" class="w-5 h-5 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
      <path v-if="variant === 'success'" fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
      <path v-else-if="variant === 'danger'" fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 10-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
      <path v-else-if="variant === 'warning'" fill-rule="evenodd" d="M8.257 3.099c.765-1.144 2.42-1.114 3.478.49l4.906 6.923c.75 1.059.405 2.547-.842 2.874l-2.147.634a1 1 0 00-.636.906v2.414a1 1 0 01-1 1h-2.414a1 1 0 01-1-1v-2.414a1 1 0 00-.636-.906l-2.147-.634c-1.247-.327-1.592-1.815-.842-2.874l4.906-6.923c1.058-1.604 2.713-1.634 3.478-.49z" clip-rule="evenodd" />
      <path v-else fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2V9a1 1 0 00-1-1H9z" clip-rule="evenodd" />
    </svg>
    <div class="flex-1">
      <slot></slot>
    </div>
    <button v-if="closable" type="button" class="flex-shrink-0 opacity-70 hover:opacity-100" @click="$emit('close')">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  variant: {
    type: String,
    default: 'info' // success, danger, warning, info
  },
  showIcon: {
    type: Boolean,
    default: true
  },
  closable: Boolean
})

defineEmits(['close'])

const alertClass = computed(() => {
  const variants = {
    success: 'bg-green-50 text-green-800 dark:bg-green-900/20 dark:text-green-300',
    danger: 'bg-red-50 text-red-800 dark:bg-red-900/20 dark:text-red-300',
    warning: 'bg-yellow-50 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300',
    info: 'bg-blue-50 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300'
  }
  return variants[props.variant] || variants.info
})
</script>
