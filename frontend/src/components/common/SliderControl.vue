<template>
  <div class="mb-3">
    <label class="form-label d-flex justify-content-between">
      <span>{{ label }}: <span>{{ modelValue }}</span></span>
      <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-1 slider-reset-btn"
              :style="{visibility: modelValue != defaultVal ? 'visible':'hidden'}" @click="reset">
        {{ t('resetBtn') }}
      </button>
    </label>
    <input type="range" class="form-range" :min="min" :max="max" :step="step" :value="modelValue"
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
