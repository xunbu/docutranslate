<template>
    <div class="task-area">
        <div class="flex justify-between items-center mb-3">
            <h4 class="m-0 flex items-center gap-2 text-gray-900 dark:text-gray-100">
                <Heroicon name="ClipboardDocumentListIcon" class="w-5 h-5" />
                <span>{{ t('taskListTitle') }}</span>
            </h4>
            <div class="flex gap-2">
                <button
                    v-if="tasks.length > 0"
                    class="px-3 py-1.5 text-sm border border-danger text-danger rounded hover:bg-danger hover:text-white transition-colors flex items-center gap-2"
                    @click="handleClearAllTasks">
                    <Heroicon name="TrashIcon" class="w-4 h-4" />
                    <span>{{ t('clearAllTasksBtn') }}</span>
                </button>
                <input type="file" id="folderInput" ref="folderInput" class="hidden" webkitdirectory directory multiple
                       @change="handleFolderSelectFn">
                <button
                    class="px-3 py-1.5 text-sm border border-primary text-primary rounded hover:bg-primary hover:text-white transition-colors flex items-center gap-2"
                    @click="$refs.folderInput.click()">
                    <Heroicon name="FolderOpenIcon" class="w-4 h-4" />
                    <span>{{ t('importFolderBtn') }}</span>
                </button>
                <button
                    v-if="hasPendingTasks"
                    class="px-3 py-1.5 text-sm bg-success text-white rounded hover:bg-green-600 transition-colors flex items-center gap-2"
                    @click="handleRunAllPendingTasks">
                    <Heroicon name="PlayIcon" class="w-4 h-4" />
                    <span>{{ t('runAllBtn') }}</span>
                </button>
                <button
                    class="px-3 py-1.5 text-sm bg-primary text-white rounded hover:bg-primary-hover transition-colors flex items-center gap-2"
                    @click="handleCreateNewTask">
                    <Heroicon name="PlusIcon" class="w-4 h-4" />
                    <span>{{ t('newTaskBtn') }}</span>
                </button>
                <Tooltip content="设置" placement="top">
                    <button
                        type="button"
                        class="p-2 text-sm border border-primary text-primary rounded hover:bg-primary hover:text-white transition-colors"
                        @click="handleShowQueueSettings">
                        <Heroicon name="Cog6ToothIcon" class="w-4 h-4" />
                    </button>
                </Tooltip>
            </div>
        </div>
        <div id="task-container">
            <div v-if="tasks.length === 0" class="flex flex-col items-center justify-center text-gray-500 dark:text-gray-400 mt-5">
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
import Heroicon from '../ui/Heroicon.vue';

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
