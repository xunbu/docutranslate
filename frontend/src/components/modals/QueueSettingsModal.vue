<template>
    <Modal v-model="visible" title="设置" size="sm">
        <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {{ t('queueConcurrentLabel') }}
            </label>
            <input
                type="number"
                v-model.number="queue_concurrent"
                min="1"
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
                @change="handleChange">
            <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">{{ t('queueConcurrentHelp') || '设置批量运行时同时翻译的任务数量' }}</p>
        </div>
        <div class="p-3 bg-blue-50 dark:bg-blue-900/20 text-blue-800 dark:text-blue-300 rounded text-sm">
            <svg class="w-4 h-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {{ t('queueConcurrentNote') || '手动逐个点击开始翻译不受此限制影响' }}
        </div>
        <template #footer>
            <button type="button" class="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors" @click="visible = false">
                {{ t('closeBtn') }}
            </button>
        </template>
    </Modal>
</template>

<script setup>
import { ref, inject } from 'vue';
import Modal from '../ui/Modal.vue';

const props = defineProps({
    t: Function,
});

const emit = defineEmits(['save']);

const queue_concurrent = inject('queue_concurrent');
const saveSetting = inject('saveSetting');
const visible = ref(false);

const handleChange = () => {
    saveSetting('queue_concurrent', queue_concurrent.value);
    emit('save', queue_concurrent.value);
};

defineExpose({
    show: () => { visible.value = true; },
    hide: () => { visible.value = false; }
});
</script>
