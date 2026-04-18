<template>
    <div class="task-area">
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h4 class="mb-0"><i class="bi bi-list-task me-2"></i><span>{{ t('taskListTitle') }}</span></h4>
            <div class="d-flex gap-2">
                <button class="btn btn-outline-danger" @click="handleClearAllTasks" v-if="tasks.length > 0"><i
                        class="bi bi-trash me-2"></i><span>{{ t('clearAllTasksBtn') }}</span></button>
                <input type="file" id="folderInput" ref="folderInput" class="d-none" webkitdirectory directory multiple
                       @change="handleFolderSelectFn">
                <button class="btn btn-outline-primary" @click="$refs.folderInput.click()">
                    <i class="bi bi-folder-fill me-2"></i><span>{{ t('importFolderBtn') }}</span>
                </button>
                <button class="btn btn-success" @click="handleRunAllPendingTasks" v-if="hasPendingTasks">
                    <i class="bi bi-play-fill me-2"></i><span>{{ t('runAllBtn') }}</span>
                </button>
                <button class="btn btn-primary" @click="handleCreateNewTask"><i
                        class="bi bi-plus-circle-fill me-2"></i><span>{{ t('newTaskBtn') }}</span></button>
                <button type="button" class="btn btn-outline-primary icon-btn"
                        :title="t('queueConcurrentLabel')"
                        data-bs-toggle="modal" data-bs-target="#queueSettingsModal">
                    <i class="bi bi-gear-fill"></i>
                </button>
            </div>
        </div>
        <div id="task-container">
            <div v-if="tasks.length === 0" class="text-center text-muted mt-5">
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
    </div>
</template>

<script setup>
import { ref, inject } from 'vue';
import TaskCard from './TaskCard.vue';

defineProps({
    t: Function,
});

const emit = defineEmits([]);

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
</script>
