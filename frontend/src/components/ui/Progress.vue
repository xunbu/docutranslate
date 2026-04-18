<template>
  <div class="relative">
    <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden" :class="sizeClass">
      <div
        class="h-full transition-all duration-300 rounded-full"
        :class="progressClass"
        :style="{ width: `${clampedProgress}%` }"
      ></div>
    </div>
    <span v-if="showLabel" class="ml-2 text-sm text-gray-600 dark:text-gray-400">
      {{ Math.round(clampedProgress) }}%
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  progress: {
    type: Number,
    default: 0
  },
  variant: {
    type: String,
    default: 'primary' // primary, success, danger, warning
  },
  size: {
    type: String,
    default: 'md' // sm, md, lg
  },
  showLabel: Boolean
})

const clampedProgress = computed(() => Math.min(100, Math.max(0, props.progress)))

const sizeClass = computed(() => {
  const sizes = {
    sm: 'h-1.5',
    md: 'h-2',
    lg: 'h-3'
  }
  return sizes[props.size] || sizes.md
})

const progressClass = computed(() => {
  const variants = {
    primary: 'bg-primary',
    success: 'bg-success',
    danger: 'bg-danger',
    warning: 'bg-warning'
  }
  return variants[props.variant] || variants.primary
})
</script>
