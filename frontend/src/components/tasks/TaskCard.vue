<template>
    <div class="border rounded mb-2 bg-white dark:bg-gray-800 shadow-sm task-card" @click="onSelectTask">
        <div class="px-3 py-2 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center bg-gray-50 dark:bg-gray-700/50">
            <span class="font-bold text-gray-900 dark:text-gray-100 text-sm">
                <span>{{ t('taskCardIdLabel') }}</span>:
                <code class="px-1 py-0.5 bg-gray-200 dark:bg-gray-600 rounded text-xs text-gray-900 dark:text-gray-100">{{ task.backendId || t('taskCardIdPlaceholder') }}</code>
            </span>
            <button type="button" class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200" @click.stop="onRemoveTask">
                <Heroicon name="XMarkIcon" class="w-4 h-4" />
            </button>
        </div>
        <div class="p-3 bg-white dark:bg-gray-800">
            <div class="flex flex-col md:flex-row gap-3">
                <div class="w-full md:w-5/12">
                    <input type="file" class="hidden" :id="'fileInput-' + task.uiId" @change="onFileSelect">
                    <div
                        class="file-drop-area border-2 border-dashed rounded transition-colors"
                        :class="{
                            'border-gray-300 dark:border-gray-600': !task.isDragOver && !task.file && !task.validationError,
                            'border-primary bg-blue-50 dark:bg-blue-900/20': task.isDragOver,
                            'border-solid border-success bg-green-50 dark:bg-green-900/20': !!task.file,
                            'border-red-400 dark:border-red-500': task.validationError && !task.file
                        }"
                        @click.stop="triggerFileInput"
                        @dragenter.prevent="task.isDragOver = true"
                        @dragover.prevent="task.isDragOver = true"
                        @dragleave.prevent="task.isDragOver = false"
                        @drop.prevent="onFileDrop">
                        <div v-if="!task.file" class="text-center py-2">
                            <Heroicon name="CloudArrowUpIcon" class="w-8 h-8 mx-auto text-gray-400" />
                            <p class="m-0 text-sm text-gray-500 dark:text-gray-400">{{ t('taskCardFileDrop') }}</p>
                        </div>
                        <div v-else class="text-center py-2">
                            <Heroicon name="CheckCircleIcon" class="w-8 h-8 mx-auto text-success" solid />
                            <p class="m-0 mt-1 text-sm font-bold text-success">{{ t('taskCardFileSelected') }}</p>
                        </div>
                    </div>
                    <div class="mt-1 text-sm" v-if="task.file || task.fileName">
                        <span class="font-bold text-gray-700 dark:text-gray-300">{{ t('taskCardFilenameLabel') }} </span>
                        <span class="text-success">{{ task.fileName || task.file.name }}</span>
                    </div>
                </div>
                <div class="w-full md:w-7/12">
                    <div class="log-area-wrapper">
                        <div class="log-area text-xs" v-html="task.logs" :id="'log-' + task.uiId"></div>
                        <button
                            type="button"
                            class="btn btn-sm btn-outline-secondary copy-log-btn"
                            :title="t('copyLogsTooltip')"
                            @click.stop="onCopyLog">
                            <Heroicon name="ClipboardDocumentIcon" class="w-3 h-3" />
                        </button>
                    </div>
                    <div class="mt-1 flex items-center gap-2">
                        <span class="text-xs flex-1 truncate" :class="task.statusClass">
                            <template v-if="task.queuePosition && !task.isTranslating && !task.isFinished">
                                {{ t('taskCardQueuePosition', { n: task.queuePosition, total: task.queueTotal }) }}
                            </template>
                            <template v-else>
                                {{ task.statusMessage || t('taskCardStatusWaiting') }}
                            </template>
                        </span>
                        <div v-if="task.isProcessing" class="w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin flex-shrink-0"></div>
                        <span v-if="task.isProcessing" class="text-xs text-gray-500 dark:text-gray-400 flex-shrink-0">{{ task.progressPercent || 0 }}%</span>
                    </div>
                </div>
            </div>
        </div>
        <div class="px-3 py-2 border-t border-gray-200 dark:border-gray-700 flex justify-between items-center bg-gray-50 dark:bg-gray-700/30">
            <div class="flex gap-1.5" v-if="task.downloads">
                <button
                    v-if="task.downloads.html"
                    class="px-2.5 py-1 text-sm bg-success text-white rounded hover:bg-green-600 transition-colors flex items-center gap-1"
                    @click.stop="onOpenPreview">
                    <Heroicon name="EyeIcon" class="w-4 h-4" />
                    <span>{{ t('taskCardPreviewBtn') }}</span>
                </button>
                <Dropdown v-if="Object.keys(task.downloads).length > 0">
                    <template #trigger>
                        <button class="px-2.5 py-1 text-sm bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors flex items-center gap-1">
                            <Heroicon name="ArrowDownTrayIcon" class="w-4 h-4" />
                            <span>{{ t('taskCardDownloadBtn') }}</span>
                        </button>
                    </template>
                    <a v-for="(link, key) in task.downloads" :key="key"
                       :href="link"
                       class="block px-3 py-1.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2">
                        <Heroicon :name="getDownloadIcon(key).name" class="w-4 h-4" />
                        {{ key === 'markdown_zip' ? t('downloadMdZip') : (key === 'markdown' ? t('downloadMdEmbedded') : key.toUpperCase()) }}
                    </a>
                    <a v-if="task.downloads.html"
                       href="#"
                       @click.stop.prevent="onPrintPdf"
                       class="block px-3 py-1.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2">
                        <Heroicon name="DocumentTextIcon" class="w-4 h-4" />
                        PDF
                    </a>
                </Dropdown>
                <Dropdown v-if="task.attachment && Object.keys(task.attachment).length">
                    <template #trigger>
                        <button class="px-2.5 py-1 text-sm bg-info text-white rounded hover:opacity-90 transition-opacity flex items-center gap-1">
                            <Heroicon name="PaperClipIcon" class="w-4 h-4" />
                            <span>{{ t('taskCardAttachmentBtn') }}</span>
                        </button>
                    </template>
                    <a v-for="(link, name) in task.attachment" :key="name"
                       :href="link"
                       class="block px-3 py-1.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2">
                        <Heroicon name="DocumentArrowDownIcon" class="w-4 h-4" />
                        {{ name }}
                    </a>
                </Dropdown>
            </div>
            <button
                class="px-3 py-1 text-sm rounded transition-colors ml-auto"
                :class="[
                    task.isTranslating ? 'bg-danger text-white hover:bg-red-600' : 'bg-primary text-white hover:bg-primary-hover',
                    task.initializing ? 'opacity-50 cursor-not-allowed' : ''
                ]"
                @click.stop="onToggleTaskState"
                :disabled="task.initializing">
                <span v-if="task.initializing" class="flex items-center gap-1">
                    <span class="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                    {{ t('btn_initializing') }}
                </span>
                <span v-else-if="task.isTranslating" class="flex items-center gap-1">
                    <Heroicon name="StopIcon" class="w-4 h-4" />
                    {{ t('btn_cancelTranslation') }}
                </span>
                <span v-else-if="task.isFinished" class="flex items-center gap-1">
                    <Heroicon name="ArrowPathIcon" class="w-4 h-4" />
                    {{ t('btn_reTranslate') }}
                </span>
                <span v-else class="flex items-center gap-1">
                    <Heroicon name="PlayIcon" class="w-4 h-4" />
                    {{ t('taskCardStartBtn') }}
                </span>
            </button>
        </div>
    </div>
</template>

<script setup>
import { getFileIcon, getDownloadIcon } from '../../utils/helpers';
import Tooltip from '../ui/Tooltip.vue';
import Dropdown from '../ui/Dropdown.vue';
import Heroicon from '../ui/Heroicon.vue';

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
