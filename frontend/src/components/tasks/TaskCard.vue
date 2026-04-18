<template>
    <div class="border rounded mb-3 bg-white dark:bg-gray-800 shadow-sm task-card" @click="onSelectTask">
        <div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center bg-gray-50 dark:bg-gray-700/50">
            <span class="font-bold text-gray-900 dark:text-gray-100">
                <span>{{ t('taskCardIdLabel') }}</span>:
                <code class="px-1 py-0.5 bg-gray-200 dark:bg-gray-600 rounded text-sm text-gray-900 dark:text-gray-100">{{ task.backendId || t('taskCardIdPlaceholder') }}</code>
            </span>
            <button type="button" class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200" @click.stop="onRemoveTask">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>
        </div>
        <div class="p-4 bg-white dark:bg-gray-800">
            <div class="flex flex-col md:flex-row gap-4">
                <div class="w-full md:w-5/12">
                    <input type="file" class="hidden" :id="'fileInput-' + task.uiId" @change="onFileSelect">
                    <div
                        class="file-drop-area"
                        :class="{'drag-over': task.isDragOver, 'file-selected': !!task.file, 'input-error': task.validationError}"
                        @click.stop="triggerFileInput"
                        @dragenter.prevent="task.isDragOver = true"
                        @dragover.prevent="task.isDragOver = true"
                        @dragleave.prevent="task.isDragOver = false"
                        @drop.prevent="onFileDrop">
                        <div v-if="!task.file" class="text-center">
                            <svg class="w-12 h-12 mx-auto text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                            </svg>
                            <p class="m-0 text-gray-500 dark:text-gray-400">{{ t('taskCardFileDrop') }}</p>
                        </div>
                        <div v-else class="text-center">
                            <svg class="w-12 h-12 mx-auto text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <p class="m-0 mt-2 font-bold text-success">{{ t('taskCardFileSelected') }}</p>
                        </div>
                    </div>
                    <div class="mt-2" v-if="task.file || task.fileName">
                        <span class="font-bold text-gray-700 dark:text-gray-300">{{ t('taskCardFilenameLabel') }} </span>
                        <span class="text-success">{{ task.fileName || task.file.name }}</span>
                    </div>
                </div>
                <div class="w-full md:w-7/12">
                    <h6 class="flex items-center gap-2 text-gray-700 dark:text-gray-300 mb-2">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                        <span>{{ t('taskCardLogLabel') }}</span>
                    </h6>
                    <div class="log-area-wrapper">
                        <div class="log-area" v-html="task.logs" :id="'log-' + task.uiId"></div>
                        <button
                            type="button"
                            class="btn btn-sm btn-outline-secondary copy-log-btn"
                            :title="t('copyLogsTooltip')"
                            @click.stop="onCopyLog">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                            </svg>
                        </button>
                    </div>
                    <div class="mt-2 flex items-center">
                        <span class="text-sm" :class="task.statusClass">
                            <template v-if="task.queuePosition && !task.isTranslating && !task.isFinished">
                                {{ t('taskCardQueuePosition', { n: task.queuePosition, total: task.queueTotal }) }}
                            </template>
                            <template v-else>
                                {{ task.statusMessage || t('taskCardStatusWaiting') }}
                            </template>
                        </span>
                        <div v-if="task.isProcessing" class="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin ml-2"></div>
                        <span v-if="task.isProcessing" class="ml-2 text-sm text-gray-500 dark:text-gray-400">{{ task.progressPercent || 0 }}%</span>
                    </div>
                    <!-- Progress Bar -->
                    <div v-if="task.isProcessing" class="w-full h-1 bg-gray-200 dark:bg-gray-700 rounded mt-2 overflow-hidden">
                        <div
                            class="h-full bg-primary transition-all duration-300"
                            :class="{'animate-pulse': task.progressPercent < 100}"
                            :style="{width: (task.progressPercent || 0) + '%'}"></div>
                    </div>
                </div>
            </div>
        </div>
        <div class="px-4 py-3 border-t border-gray-200 dark:border-gray-700 flex justify-between items-center bg-gray-50 dark:bg-gray-700/30">
            <div class="flex gap-2" v-if="task.downloads">
                <button
                    v-if="task.downloads.html"
                    class="px-3 py-1.5 text-sm bg-success text-white rounded hover:bg-green-600 transition-colors flex items-center gap-1"
                    @click.stop="onOpenPreview">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                    <span>{{ t('taskCardPreviewBtn') }}</span>
                </button>
                <Dropdown v-if="Object.keys(task.downloads).length > 0">
                    <template #trigger>
                        <button class="px-3 py-1.5 text-sm bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors flex items-center gap-1">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                            </svg>
                            <span>{{ t('taskCardDownloadBtn') }}</span>
                        </button>
                    </template>
                    <a v-for="(link, key) in task.downloads" :key="key"
                       :href="link"
                       class="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700">
                        {{ key === 'markdown_zip' ? t('downloadMdZip') : (key === 'markdown' ? t('downloadMdEmbedded') : key.toUpperCase()) }}
                    </a>
                    <a v-if="task.downloads.html"
                       href="#"
                       @click.stop.prevent="onPrintPdf"
                       class="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700">
                        PDF
                    </a>
                </Dropdown>
                <Dropdown v-if="task.attachment && Object.keys(task.attachment).length">
                    <template #trigger>
                        <button class="px-3 py-1.5 text-sm bg-info text-white rounded hover:opacity-90 transition-opacity flex items-center gap-1">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                            </svg>
                            <span>{{ t('taskCardAttachmentBtn') }}</span>
                        </button>
                    </template>
                    <a v-for="(link, name) in task.attachment" :key="name"
                       :href="link"
                       class="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700">
                        {{ name }}
                    </a>
                </Dropdown>
            </div>
            <button
                class="px-4 py-1.5 text-sm rounded transition-colors ml-auto"
                :class="[
                    task.isTranslating ? 'bg-danger text-white hover:bg-red-600' : 'bg-primary text-white hover:bg-primary-hover',
                    task.initializing ? 'opacity-50 cursor-not-allowed' : ''
                ]"
                @click.stop="onToggleTaskState"
                :disabled="task.initializing">
                <span v-if="task.initializing" class="flex items-center gap-2">
                    <span class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                    {{ t('btn_initializing') }}
                </span>
                <span v-else-if="task.isTranslating" class="flex items-center gap-1">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                    </svg>
                    {{ t('btn_cancelTranslation') }}
                </span>
                <span v-else-if="task.isFinished" class="flex items-center gap-1">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    {{ t('btn_reTranslate') }}
                </span>
                <span v-else class="flex items-center gap-1">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {{ t('taskCardStartBtn') }}
                </span>
            </button>
        </div>
    </div>
</template>

<script setup>
import { getFileIcon } from '../../utils/helpers';
import Tooltip from '../ui/Tooltip.vue';
import Dropdown from '../ui/Dropdown.vue';

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
