<template>
    <div class="card mb-3 task-card" @click="onSelectTask">
        <div class="card-header d-flex justify-content-between align-items-center">
            <span class="fw-bold"><span>{{ t('taskCardIdLabel')
                }}</span>: <code>{{ task.backendId || t('taskCardIdPlaceholder') }}</code></span>
            <button type="button" class="btn-close" @click.stop="onRemoveTask"></button>
        </div>
        <div class="card-body">
            <div class="row">
                <div class="col-md-5">
                    <input type="file" class="d-none" :id="'fileInput-' + task.uiId"
                           @change="onFileSelect">
                    <div class="file-drop-area"
                         :class="{'drag-over': task.isDragOver, 'file-selected': !!task.file, 'input-error': task.validationError}"
                         @click.stop="triggerFileInput"
                         @dragenter.prevent="task.isDragOver = true"
                         @dragover.prevent="task.isDragOver = true"
                         @dragleave.prevent="task.isDragOver = false"
                         @drop.prevent="onFileDrop">
                                        <div v-if="!task.file" class="file-drop-default">
                                            <i class="bi bi-cloud-arrow-up fs-1"></i>
                                            <p class="mb-0">{{ t('taskCardFileDrop') }}</p>
                                        </div>
                                        <div v-else class="file-drop-selected">
                                            <i class="bi bi-check-circle-fill fs-1 text-success"></i>
                                            <p class="mb-0 mt-2 fw-bold text-success">{{ t('taskCardFileSelected')
                                                }}</p>
                                        </div>
                    </div>
                    <div class="mt-2" v-if="task.file || task.fileName">
                        <span class="fw-bold">{{ t('taskCardFilenameLabel') }} </span><span
                            class="text-success">{{ task.fileName || task.file.name }}</span>
                    </div>
                </div>
                <div class="col-md-7">
                    <h6><i class="bi bi-terminal me-2"></i><span>{{ t('taskCardLogLabel') }}</span>
                    </h6>
                    <div class="log-area-wrapper">
                        <div class="log-area" v-html="task.logs" :id="'log-' + task.uiId"></div>
                        <button type="button" class="btn btn-sm btn-outline-secondary copy-log-btn"
                                @click.stop="onCopyLog" data-bs-toggle="tooltip"
                                :data-bs-title="t('copyLogsTooltip')">
                            <i class="bi bi-clipboard"></i>
                        </button>
                    </div>
                    <div class="mt-2 d-flex align-items-center">
                        <span class="small"
                              :class="task.statusClass">
                            <template v-if="task.queuePosition && !task.isTranslating && !task.isFinished">
                                {{ t('taskCardQueuePosition', { n: task.queuePosition, total: task.queueTotal }) }}
                            </template>
                            <template v-else>
                                {{ task.statusMessage || t('taskCardStatusWaiting') }}
                            </template>
                        </span>
                        <div v-if="task.isProcessing" class="spinner-border spinner-border-sm ms-2"
                             role="status"></div>
                        <span v-if="task.isProcessing"
                              class="ms-2 small text-muted">{{ task.progressPercent || 0 }}%</span>
                    </div>
                    <!-- Progress Bar -->
                    <div v-if="task.isProcessing" class="progress"
                         style="height: 4px; min-height: 4px; margin-top: 4px;">
                        <div class="progress-bar bg-primary"
                             :class="{'progress-bar-striped progress-bar-animated': task.progressPercent < 100}"
                             :style="{width: (task.progressPercent || 0) + '%'}"></div>
                    </div>
                </div>
            </div>
        </div>
        <div class="card-footer d-flex justify-content-between align-items-center">
            <div class="download-buttons" v-if="task.downloads">
                <button class="btn btn-sm btn-success me-1" v-if="task.downloads.html"
                        @click.stop="onOpenPreview"><i
                        class="bi bi-eye-fill me-1"></i><span>{{ t('taskCardPreviewBtn') }}</span>
                </button>
                <div class="btn-group me-1">
                    <button type="button" class="btn btn-sm btn-secondary dropdown-toggle"
                            data-bs-toggle="dropdown"><i
                            class="bi bi-download me-1"></i><span>{{ t('taskCardDownloadBtn')
                        }}</span></button>
                    <ul class="dropdown-menu">
                        <li v-for="(link, key) in task.downloads" :key="key">
                            <a class="dropdown-item" :href="link"><i class="bi me-2"
                                                                     :class="getWorkflowIcon(key)"></i>{{ key === 'markdown_zip' ? t('downloadMdZip') : (key === 'markdown' ? t('downloadMdEmbedded') : key.toUpperCase())
                                }}</a>
                        </li>
                        <li v-if="task.downloads.html">
                            <a class="dropdown-item" href="#"
                               @click.stop.prevent="onPrintPdf"><i
                                    class="bi bi-file-earmark-pdf me-2"></i>PDF</a>
                        </li>
                    </ul>
                </div>
                <div class="btn-group"
                     v-if="task.attachment && Object.keys(task.attachment).length">
                    <button type="button" class="btn btn-sm btn-info dropdown-toggle"
                            data-bs-toggle="dropdown"><i
                            class="bi bi-paperclip me-1"></i><span>{{ t('taskCardAttachmentBtn')
                        }}</span></button>
                    <ul class="dropdown-menu">
                        <li v-for="(link, name) in task.attachment" :key="name"><a
                                class="dropdown-item" :href="link"><i
                                class="bi bi-file-earmark-arrow-down me-2"></i>{{ name }}</a></li>
                    </ul>
                </div>
            </div>
            <button class="btn ms-auto" :class="task.isTranslating ? 'btn-danger' : 'btn-primary'"
                    @click.stop="onToggleTaskState" :disabled="task.initializing">
                <span v-if="task.initializing"><span
                        class="spinner-border spinner-border-sm"></span> {{ t('btn_initializing') }}</span>
                <span v-else-if="task.isTranslating"><i
                        class="bi bi-stop-circle-fill me-1"></i>{{ t('btn_cancelTranslation')
                    }}</span>
                <span v-else-if="task.isFinished"><i
                        class="bi bi-arrow-clockwise me-1"></i>{{ t('btn_reTranslate') }}</span>
                <span v-else><i class="bi bi-play-fill me-1"></i>{{ t('taskCardStartBtn') }}</span>
            </button>
        </div>
    </div>
</template>

<script setup>
import { getFileIcon } from '../../utils/helpers';

const props = defineProps({
    t: Function,
    task: Object,
});

const emit = defineEmits([
    'selectTask',
    'removeTask',
    'fileSelect',
    'fileDrop',
    'triggerFileInput',
    'copyLog',
    'openPreview',
    'printPdf',
    'toggleTaskState',
]);

const onSelectTask = () => emit('selectTask', props.task);
const onRemoveTask = () => emit('removeTask', props.task);
const onFileSelect = (e) => emit('fileSelect', e, props.task);
const onFileDrop = (e) => emit('fileDrop', e, props.task);
const triggerFileInput = () => emit('triggerFileInput', props.task.uiId);
const onCopyLog = (e) => emit('copyLog', e, props.task.logs);
const onOpenPreview = () => emit('openPreview', props.task);
const onPrintPdf = () => emit('printPdf', props.task.downloads.html);
const onToggleTaskState = () => emit('toggleTaskState', props.task);

const getWorkflowIcon = (key) => getFileIcon(key);
</script>
