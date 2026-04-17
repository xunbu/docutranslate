<template>
    <div class="modal fade" id="queueSettingsModal" tabindex="-1">
        <div class="modal-dialog modal-dialog-centered modal-sm">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title"><i class="bi bi-gear-fill me-2"></i>{{ t('queueConcurrentLabel') }}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="mb-3">
                        <label class="form-label">{{ t('queueConcurrentLabel') }}</label>
                        <input type="number" class="form-control"
                               v-model.number="queueConcurrent" min="1" max="10"
                               @change="handleChange">
                        <div class="form-text">{{ t('queueConcurrentHelp') || '设置批量运行时同时翻译的任务数量（1-10）' }}</div>
                    </div>
                    <div class="alert alert-info py-2 small mb-0">
                        <i class="bi bi-info-circle me-1"></i>
                        {{ t('queueConcurrentNote') || '手动逐个点击开始翻译不受此限制影响' }}
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">{{ t('closeBtn') }}</button>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
    t: Function,
    queueConcurrent: Number,
});

const emit = defineEmits(['update:queueConcurrent', 'save']);

const queueConcurrent = computed({
    get: () => props.queueConcurrent,
    set: (val) => emit('update:queueConcurrent', val)
});

const handleChange = () => {
    emit('save', queueConcurrent.value);
};
</script>
