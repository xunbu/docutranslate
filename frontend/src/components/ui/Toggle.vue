<template>
  <label class="inline-flex items-center gap-2 cursor-pointer">
    <input
      type="checkbox"
      :checked="modelValue"
      :disabled="disabled"
      class="sr-only"
      @change="$emit('update:modelValue', $event.target.checked)"
    />
    <span
      class="relative inline-flex w-10 h-5 rounded-full transition-colors"
      :class="toggleClass"
    >
      <span
        class="absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform"
        :class="{ 'translate-x-5': modelValue }"
      ></span>
    </span>
    <span v-if="label" class="text-sm text-gray-700 dark:text-gray-300">{{ label }}</span>
  </label>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  label: String,
  disabled: Boolean
})

defineEmits(['update:modelValue'])

const toggleClass = computed(() => {
  if (props.disabled) {
    return 'bg-gray-300 dark:bg-gray-600 opacity-50'
  }
  return props.modelValue
    ? 'bg-primary'
    : 'bg-gray-300 dark:bg-gray-600'
})
</script>
