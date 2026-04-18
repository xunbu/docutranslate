<template>
  <li>
    <button
      type="button"
      class="w-full px-3 py-2 text-sm text-left rounded transition-colors"
      :class="itemClass"
      @click="$parent.$emit('update:activeKey', itemKey)"
    >
      <slot></slot>
    </button>
  </li>
</template>

<script setup>
import { computed, inject } from 'vue'

const props = defineProps({
  itemKey: [String, Number],
  disabled: Boolean
})

const activeKey = inject('activeKey', null)

const itemClass = computed(() => {
  const isActive = activeKey?.value === props.itemKey
  if (props.disabled) {
    return 'opacity-50 cursor-not-allowed text-gray-400'
  }
  if (isActive) {
    return 'bg-primary text-white'
  }
  return 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
})
</script>
