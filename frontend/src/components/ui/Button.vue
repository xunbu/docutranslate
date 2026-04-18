<template>
  <button
    :type="type"
    :disabled="disabled"
    class="inline-flex items-center justify-center font-medium rounded transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2"
    :class="buttonClass"
  >
    <slot></slot>
  </button>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  type: {
    type: String,
    default: 'button'
  },
  variant: {
    type: String,
    default: 'primary' // primary, secondary, success, danger, warning, outline-primary, outline-secondary, link
  },
  size: {
    type: String,
    default: 'md' // sm, md, lg
  },
  disabled: Boolean
})

const buttonClass = computed(() => {
  const sizeClasses = {
    sm: 'px-2 py-1 text-sm',
    md: 'px-3 py-1.5 text-sm',
    lg: 'px-4 py-2 text-base'
  }

  const variantClasses = {
    primary: 'bg-primary text-white hover:bg-primary-hover focus:ring-primary',
    secondary: 'bg-gray-200 text-gray-800 hover:bg-gray-300 focus:ring-gray-400 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600',
    success: 'bg-success text-white hover:bg-green-600 focus:ring-success',
    danger: 'bg-danger text-white hover:bg-red-600 focus:ring-danger',
    warning: 'bg-warning text-gray-800 hover:bg-yellow-500 focus:ring-warning',
    'outline-primary': 'border border-primary text-primary hover:bg-primary hover:text-white focus:ring-primary',
    'outline-secondary': 'border border-gray-300 text-gray-700 hover:bg-gray-100 focus:ring-gray-400 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700',
    'outline-danger': 'border border-danger text-danger hover:bg-danger hover:text-white focus:ring-danger',
    link: 'text-primary hover:underline focus:ring-0'
  }

  const classes = [sizeClasses[props.size] || sizeClasses.md]

  if (props.disabled) {
    classes.push('opacity-50 cursor-not-allowed')
  } else {
    classes.push(variantClasses[props.variant] || variantClasses.primary)
  }

  return classes
})
</script>
