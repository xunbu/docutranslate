<template>
    <div class="task-area">
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h4 class="mb-0"><i class="bi bi-list-task me-2"></i><span>{{ t('taskListTitle') }}</span></h4>
            <div class="d-flex gap-2">
                <button class="btn btn-outline-danger" @click="clearAllTasks" v-if="tasks.length > 0"><i
                        class="bi bi-trash me-2"></i><span>{{ t('clearAllTasksBtn') }}</span></button>
                <input type="file" id="folderInput" ref="folderInput" class="d-none" webkitdirectory directory multiple
                       @change="handleFolderSelect">
                <button class="btn btn-outline-primary" @click="$refs.folderInput.click()">
                    <i class="bi bi-folder-fill me-2"></i><span>{{ t('importFolderBtn') }}</span>
                </button>
                <button class="btn btn-success" @click="runAllPendingTasks" v-if="hasPendingTasks">
                    <i class="bi bi-play-fill me-2"></i><span>{{ t('runAllBtn') }}</span>
                </button>
                <button class="btn btn-primary" @click="createNewTask"><i
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
                @selectTask="selectTaskWorkflow"
                @removeTask="removeTask"
                @fileSelect="handleTaskFileSelect"
                @fileDrop="handleTaskFileDrop"
                @triggerFileInput="triggerFileInput"
                @copyLog="copyLog"
                @openPreview="openPreview"
                @printPdf="printPdf"
                @toggleTaskState="toggleTaskState" />
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import TaskCard from './TaskCard.vue';

defineProps({
    t: Function,
    tasks: Array,
    hasPendingTasks: Boolean,
});

const emit = defineEmits([
    'clearAllTasks',
    'handleFolderSelect',
    'runAllPendingTasks',
    'createNewTask',
    'selectTaskWorkflow',
    'removeTask',
    'handleTaskFileSelect',
    'handleTaskFileDrop',
    'triggerFileInput',
    'copyLog',
    'openPreview',
    'printPdf',
    'toggleTaskState',
]);

const folderInput = ref(null);
</script>
