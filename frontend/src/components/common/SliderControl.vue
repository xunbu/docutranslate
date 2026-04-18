<template>
  <div class="mb-4">
    <label class="flex justify-between items-center text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
      <span>{{ label }}: <span class="font-normal">{{ modelValue }}</span></span>
      <button
        type="button"
        class="px-2 py-0.5 text-xs border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        :style="{visibility: modelValue != defaultVal ? 'visible': 'hidden'}"
        @click="reset">
        {{ t('resetBtn') }}
      </button>
    </label>
    <input
      type="range"
      class="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary"
      :min="min"
      :max="max"
      :step="step"
      :value="modelValue"
      @input="update">
  </div>
</template>

<script setup>
import { ref } from 'vue';

const props = defineProps(['label', 'modelValue', 'min', 'max', 'step', 'defaultVal', 't', 'saveKey']);
const emit = defineEmits(['update:modelValue']);

const update = (e) => {
    const val = Number(e.target.value);
    emit('update:modelValue', val);
    if (props.saveKey) localStorage.setItem(props.saveKey, val);
};

const reset = () => {
    emit('update:modelValue', props.defaultVal);
    if (props.saveKey) localStorage.setItem(props.saveKey, props.defaultVal);
};
</script>
