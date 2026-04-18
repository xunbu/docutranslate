<template>
  <div class="relative inline-block" ref="triggerRef">
    <div
      @mouseenter="show"
      @mouseleave="hide"
      @focus="show"
      @blur="hide"
    >
      <slot></slot>
    </div>
    <Teleport to="body">
      <Transition name="tooltip">
        <div
          v-if="visible"
          ref="tooltipRef"
          class="fixed z-[1080] px-2 py-1 text-sm bg-gray-900 text-white rounded shadow-lg whitespace-nowrap"
          :style="tooltipStyle"
        >
          {{ content }}
          <div
            class="absolute w-2 h-2 bg-gray-900 transform rotate-45"
            :style="arrowStyle"
          ></div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  content: String,
  placement: {
    type: String,
    default: 'top' // top, bottom, left, right
  }
})

const visible = ref(false)
const triggerRef = ref(null)
const tooltipRef = ref(null)
const position = ref({ x: 0, y: 0 })

const show = () => {
  if (!triggerRef.value) return
  const rect = triggerRef.value.getBoundingClientRect()

  position.value = {
    x: rect.left + rect.width / 2,
    y: rect.top + rect.height / 2
  }
  visible.value = true
}

const hide = () => {
  visible.value = false
}

const tooltipStyle = computed(() => {
  const offset = 10
  switch (props.placement) {
    case 'top':
      return {
        left: `${position.value.x}px`,
        top: `${position.value.y - offset}px`,
        transform: 'translate(-50%, -100%)'
      }
    case 'bottom':
      return {
        left: `${position.value.x}px`,
        top: `${position.value.y + offset}px`,
        transform: 'translate(-50%, 0)'
      }
    case 'left':
      return {
        left: `${position.value.x - offset}px`,
        top: `${position.value.y}px`,
        transform: 'translate(-100%, -50%)'
      }
    case 'right':
      return {
        left: `${position.value.x + offset}px`,
        top: `${position.value.y}px`,
        transform: 'translate(0, -50%)'
      }
    default:
      return {}
  }
})

const arrowStyle = computed(() => {
  switch (props.placement) {
    case 'top':
      return { bottom: '-4px', left: '50%', transform: 'translateX(-50%)' }
    case 'bottom':
      return { top: '-4px', left: '50%', transform: 'translateX(-50%)' }
    case 'left':
      return { right: '-4px', top: '50%', transform: 'translateY(-50%)' }
    case 'right':
      return { left: '-4px', top: '50%', transform: 'translateY(-50%)' }
    default:
      return {}
  }
})
</script>

<style scoped>
.tooltip-enter-active,
.tooltip-leave-active {
  transition: opacity 0.15s ease;
}

.tooltip-enter-from,
.tooltip-leave-to {
  opacity: 0;
}
</style>
