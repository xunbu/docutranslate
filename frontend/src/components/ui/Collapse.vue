<template>
  <div class="collapse-panel">
    <button
      type="button"
      class="collapse-header"
      :class="{ 'open': isOpen }"
      @click="toggle"
    >
      <span class="font-medium">
        <slot name="header">{{ title }}</slot>
      </span>
      <svg
        class="w-5 h-5 collapse-icon"
        :class="{ 'open': isOpen }"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>
    <Transition
      name="collapse"
      @enter="onEnter"
      @after-enter="onAfterEnter"
      @leave="onLeave"
      @after-leave="onAfterLeave"
    >
      <div v-show="isOpen" class="overflow-hidden">
        <div class="collapse-body">
          <slot></slot>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  title: String
})

const emit = defineEmits(['update:modelValue'])

const isOpen = ref(props.modelValue)

watch(() => props.modelValue, (val) => {
  isOpen.value = val
})

const toggle = () => {
  isOpen.value = !isOpen.value
  emit('update:modelValue', isOpen.value)
}

// Animation helpers
const onEnter = (el) => {
  el.style.height = '0'
}

const onAfterEnter = (el) => {
  el.style.height = 'auto'
}

const onLeave = (el) => {
  el.style.height = el.scrollHeight + 'px'
  // Force reflow
  el.offsetHeight
  el.style.height = '0'
}

const onAfterLeave = (el) => {
  el.style.height = ''
}
</script>

<style scoped>
.collapse-enter-active,
.collapse-leave-active {
  transition: height 0.2s ease;
  overflow: hidden;
}
</style>
