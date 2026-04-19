<template>
  <Teleport to="body">
    <Transition name="offcanvas">
      <div v-if="modelValue" class="fixed inset-0 z-[1040]">
        <!-- Backdrop -->
        <div
          class="absolute inset-0 bg-black/50"
          @click="closeOnBackdrop && $emit('update:modelValue', false)"
        ></div>

        <!-- Offcanvas Panel -->
        <div
          ref="offcanvasRef"
          class="fixed bg-white dark:bg-gray-800 shadow-xl h-full flex flex-col"
          :class="[positionClass, widthClass]"
        >
          <!-- Header -->
          <div v-if="$slots.header || title" class="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between flex-shrink-0">
            <slot name="header">
              <h5 class="text-lg font-medium">{{ title }}</h5>
            </slot>
            <button
              v-if="closable"
              type="button"
              class="text-gray-400 hover:text-gray-600"
              @click="$emit('update:modelValue', false)"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Body -->
          <div class="flex-1 overflow-hidden">
            <slot></slot>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, watch } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  title: String,
  position: {
    type: String,
    default: 'end' // start, end, top, bottom
  },
  width: {
    type: String,
    default: 'md' // sm, md, lg, xl, full
  },
  closable: {
    type: Boolean,
    default: true
  },
  closeOnBackdrop: {
    type: Boolean,
    default: true
  }
})

defineEmits(['update:modelValue'])

const positionClass = computed(() => {
  const positions = {
    start: 'left-0 top-0',
    end: 'right-0 top-0',
    top: 'top-0 left-0 right-0',
    bottom: 'bottom-0 left-0 right-0'
  }
  return positions[props.position] || positions.end
})

const widthClass = computed(() => {
  if (props.position === 'top' || props.position === 'bottom') {
    return 'h-auto max-h-[90vh]'
  }
  const widths = {
    sm: 'w-64',
    md: 'w-80',
    lg: 'w-96',
    xl: 'w-[95vw] max-w-[1600px]',
    full: 'w-full max-w-[95vw]'
  }
  return widths[props.width] || widths.md
})

// Prevent body scroll when offcanvas is open
watch(() => props.modelValue, (val) => {
  document.body.style.overflow = val ? 'hidden' : ''
})
</script>

<style scoped>
.offcanvas-enter-active,
.offcanvas-leave-active {
  transition: opacity 0.3s ease;
}

.offcanvas-enter-from,
.offcanvas-leave-to {
  opacity: 0;
}

.offcanvas-enter-active .fixed,
.offcanvas-leave-active .fixed {
  transition: transform 0.3s ease;
}

.offcanvas-enter-from .fixed,
.offcanvas-leave-to .fixed {
  transform: translateX(100%);
}

/* Left position */
.offcanvas-enter-from .left-0,
.offcanvas-leave-to .left-0 {
  transform: translateX(-100%);
}

/* Right position (default) */
.offcanvas-enter-from .right-0,
.offcanvas-leave-to .right-0 {
  transform: translateX(100%);
}

/* Top position */
.offcanvas-enter-from .top-0,
.offcanvas-leave-to .top-0 {
  transform: translateY(-100%);
}

/* Bottom position */
.offcanvas-enter-from .bottom-0,
.offcanvas-leave-to .bottom-0 {
  transform: translateY(100%);
}
</style>
