<template>
  <div class="relative" ref="dropdownRef">
    <div @click="toggle" class="cursor-pointer">
      <slot name="trigger">
        <button
          type="button"
          class="inline-flex items-center justify-center gap-1 px-3 py-1.5 text-sm font-medium border rounded transition-colors"
          :class="buttonClass"
        >
          {{ label }}
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </slot>
    </div>
    <Teleport to="body">
      <Transition name="dropdown">
        <div
          v-if="isOpen"
          class="fixed z-[1060] min-w-[10rem] py-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded shadow-lg"
          :style="menuStyle"
        >
          <slot></slot>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  label: String,
  variant: {
    type: String,
    default: 'secondary'
  }
})

const isOpen = ref(false)
const dropdownRef = ref(null)
const menuStyle = ref({})

const buttonClass = computed(() => {
  const variants = {
    primary: 'border-primary text-primary hover:bg-primary hover:text-white',
    secondary: 'border-gray-300 text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700'
  }
  return variants[props.variant] || variants.secondary
})

const toggle = () => {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    updatePosition()
  }
}

const updatePosition = () => {
  if (!dropdownRef.value) return
  const rect = dropdownRef.value.getBoundingClientRect()
  const menuHeight = 200 // 预估菜单高度

  // 检测是否会超出底部边界
  if (rect.bottom + 4 + menuHeight > window.innerHeight) {
    // 显示在按钮上方
    menuStyle.value = {
      bottom: `${window.innerHeight - rect.top + 4}px`,
      left: `${rect.left}px`
    }
  } else {
    // 显示在按钮下方
    menuStyle.value = {
      top: `${rect.bottom + 4}px`,
      left: `${rect.left}px`
    }
  }
}

const handleClickOutside = (e) => {
  if (dropdownRef.value && !dropdownRef.value.contains(e.target)) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.15s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
}
</style>
