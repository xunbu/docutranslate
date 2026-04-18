<template>
    <div class="task-area">
        <div class="flex justify-between items-center mb-3">
            <h4 class="m-0 flex items-center gap-2 text-gray-900 dark:text-gray-100">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                </svg>
                <span>{{ t('taskListTitle') }}</span>
            </h4>
            <div class="flex gap-2">
                <button
                    v-if="tasks.length > 0"
                    class="px-3 py-1.5 text-sm border border-danger text-danger rounded hover:bg-danger hover:text-white transition-colors flex items-center gap-2"
                    @click="handleClearAllTasks">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                    <span>{{ t('clearAllTasksBtn') }}</span>
                </button>
                <input type="file" id="folderInput" ref="folderInput" class="hidden" webkitdirectory directory multiple
                       @change="handleFolderSelectFn">
                <button
                    class="px-3 py-1.5 text-sm border border-primary text-primary rounded hover:bg-primary hover:text-white transition-colors flex items-center gap-2"
                    @click="$refs.folderInput.click()">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                    </svg>
                    <span>{{ t('importFolderBtn') }}</span>
                </button>
                <button
                    v-if="hasPendingTasks"
                    class="px-3 py-1.5 text-sm bg-success text-white rounded hover:bg-green-600 transition-colors flex items-center gap-2"
                    @click="handleRunAllPendingTasks">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>{{ t('runAllBtn') }}</span>
                </button>
                <button
                    class="px-3 py-1.5 text-sm bg-primary text-white rounded hover:bg-primary-hover transition-colors flex items-center gap-2"
                    @click="handleCreateNewTask">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>{{ t('newTaskBtn') }}</span>
                </button>
                <Tooltip :content="t('queueConcurrentLabel')" placement="top">
                    <button
                        type="button"
                        class="p-2 text-sm border border-primary text-primary rounded hover:bg-primary hover:text-white transition-colors"
                        @click="handleShowQueueSettings">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                    </button>
                </Tooltip>
            </div>
        </div>
        <div id="task-container">
            <div v-if="tasks.length === 0" class="flex flex-col items-center justify-center text-gray-500 mt-5">
                <img src="/static/favicon.ico" alt="LOGO" style="width:10%;min-width: 55px; height: auto;">
                <p class="mt-3">{{ t('noTaskPlaceholder') }}</p>
            </div>
            <TaskCard
                v-for="task in tasks"
                :key="task.uiId"
                :t="t"
                :task="task"
                @selectTask="handleSelectTask"
                @removeTask="handleRemoveTask"
                @fileSelect="handleFileSelect"
                @fileDrop="handleFileDrop"
                @triggerFileInput="handleTriggerFileInput"
                @copyLog="handleCopyLog"
                @openPreview="handleOpenPreview"
                @printPdf="handlePrintPdf"
                @toggleTaskState="handleToggleTaskState" />
        </div>

        <!-- Queue Settings Modal -->
        <QueueSettingsModal ref="queueSettingsModal" :t="t" @save="val => {}" />
    </div>
</template>

<script setup>
import { ref, inject } from 'vue';
import TaskCard from './TaskCard.vue';
import Tooltip from '../ui/Tooltip.vue';
import QueueSettingsModal from '../modals/QueueSettingsModal.vue';

defineProps({
    t: Function,
});

// Inject from parent
const tasks = inject('tasks');
const hasPendingTasks = inject('hasPendingTasks');
const errors = inject('errors');
const createNewTask = inject('createNewTask');
const removeTask = inject('removeTask');
const clearAllTasks = inject('clearAllTasks');
const handleTaskFileSelect = inject('handleTaskFileSelect');
const handleTaskFileDrop = inject('handleTaskFileDrop');
const triggerFileInput = inject('triggerFileInput');
const selectTaskWorkflow = inject('selectTaskWorkflow');
const handleFolderSelectFn = inject('handleFolderSelect');
const runAllPendingTasks = inject('runAllPendingTasks');
const toggleTaskState = inject('toggleTaskState');
const copyLog = inject('copyLog');
const openPreview = inject('openPreview');
const printPdf = inject('printPdf');

const folderInput = ref(null);
const queueSettingsModal = ref(null);
const showQueueSettings = ref(false);

// Inject openQueueSettings from parent
const openQueueSettings = inject('openQueueSettings');

// Event handlers
const handleClearAllTasks = () => clearAllTasks();
const handleCreateNewTask = () => createNewTask();
const handleRunAllPendingTasks = () => runAllPendingTasks();
const handleSelectTask = (task) => selectTaskWorkflow(task);
const handleRemoveTask = (task) => removeTask(task);
const handleFileSelect = (e, task) => handleTaskFileSelect(e, task);
const handleFileDrop = (e, task) => handleTaskFileDrop(e, task);
const handleTriggerFileInput = (uiId) => triggerFileInput(uiId);
const handleCopyLog = (e, logs) => copyLog(e, logs);
const handleOpenPreview = (task) => openPreview(task);
const handlePrintPdf = (url) => printPdf(url);
const handleToggleTaskState = (task) => toggleTaskState(task, errors);

const handleShowQueueSettings = () => {
    if (openQueueSettings) {
        openQueueSettings();
    }
};
</script>
