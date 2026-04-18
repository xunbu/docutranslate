<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="modelValue" class="fixed inset-0 z-[1050] flex items-center justify-center p-4">
        <!-- Backdrop -->
        <div
          class="absolute inset-0 bg-black/50"
          @click="closeOnBackdrop && $emit('update:modelValue', false)"
        ></div>

        <!-- Modal Content -->
        <div
          ref="modalRef"
          class="relative bg-white dark:bg-gray-800 rounded shadow-xl w-full max-h-[90vh] overflow-auto"
          :class="sizeClass"
        >
          <!-- Header -->
          <div v-if="$slots.header || title" class="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
            <slot name="header">
              <h5 class="text-lg font-medium">{{ title }}</h5>
            </slot>
            <button
              v-if="closable"
              type="button"
              class="absolute top-3 right-3 text-gray-400 hover:text-gray-600"
              @click="$emit('update:modelValue', false)"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Body -->
          <div class="px-4 py-3">
            <slot></slot>
          </div>

          <!-- Footer -->
          <div v-if="$slots.footer" class="px-4 py-3 border-t border-gray-200 dark:border-gray-700">
            <slot name="footer"></slot>
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
  size: {
    type: String,
    default: 'md'
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

const sizeClass = computed(() => {
  const sizes = {
    sm: 'max-w-sm',      // 384px
    md: 'max-w-lg',      // 512px
    lg: 'max-w-3xl',     // 768px (Bootstrap modal-lg is 800px)
    xl: 'max-w-5xl',     // 1024px (Bootstrap modal-xl is 1140px)
    full: 'max-w-full mx-4'
  }
  return sizes[props.size] || sizes.md
})

// Prevent body scroll when modal is open
watch(() => props.modelValue, (val) => {
  document.body.style.overflow = val ? 'hidden' : ''
})
</script>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .relative,
.modal-leave-active .relative {
  transition: transform 0.2s ease;
}

.modal-enter-from .relative,
.modal-leave-to .relative {
  transform: scale(0.95);
}
</style>
