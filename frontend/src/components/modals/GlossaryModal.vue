<template>
    <Modal v-model="visible" :title="t('glossaryModalTitle')" size="xl">
        <table class="w-full text-sm">
            <thead>
                <tr class="border-b border-gray-200 dark:border-gray-700">
                    <th class="px-4 py-2 text-left text-gray-700 dark:text-gray-300">{{ t('glossaryTableSource') }}</th>
                    <th class="px-4 py-2 text-left text-gray-700 dark:text-gray-300">{{ t('glossaryTableDestination') }}</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="(dst, src) in glossaryData" :key="src" class="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                    <td class="px-4 py-2 text-gray-700 dark:text-gray-300">{{ src }}</td>
                    <td class="px-4 py-2 text-gray-700 dark:text-gray-300">{{ dst }}</td>
                </tr>
                <tr v-if="Object.keys(glossaryData).length === 0">
                    <td colspan="2" class="px-4 py-4 text-center text-gray-500">{{ t('glossaryEmpty') }}</td>
                </tr>
            </tbody>
        </table>
        <template #footer>
            <button type="button" class="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors" @click="visible = false">
                {{ t('closeBtn') }}
            </button>
        </template>
    </Modal>
</template>

<script setup>
import { ref, inject, watch } from 'vue';
import Modal from '../ui/Modal.vue';

defineProps(['t']);

const glossaryData = inject('glossaryData');
const visible = ref(false);

// Expose for parent to control
defineExpose({
    show: () => { visible.value = true; },
    hide: () => { visible.value = false; }
});
</script>
