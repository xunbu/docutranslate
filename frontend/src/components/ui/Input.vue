<template>
  <input
    :type="type"
    :value="modelValue"
    :placeholder="placeholder"
    :disabled="disabled"
    class="w-full px-3 py-1.5 text-sm border rounded transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary"
    :class="inputClass"
    @input="$emit('update:modelValue', $event.target.value)"
  />
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: [String, Number],
  type: {
    type: String,
    default: 'text'
  },
  placeholder: String,
  disabled: Boolean,
  error: Boolean
})

defineEmits(['update:modelValue'])

const inputClass = computed(() => {
  const classes = [
    'border-gray-300 dark:border-gray-600',
    'bg-white dark:bg-gray-700',
    'text-gray-900 dark:text-gray-100'
  ]

  if (props.disabled) {
    classes.push('opacity-50 cursor-not-allowed')
  }

  if (props.error) {
    classes.push('border-danger focus:ring-danger focus:border-danger')
  }

  return classes
})
</script>
