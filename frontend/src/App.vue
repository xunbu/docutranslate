<template>
<div>
    <div class="main-container">
        <div class="main-row">
            <!-- Left: Settings Panel -->
            <div class="settings-col">
                <SettingsPanel
                    :t="t"
                    :enginList="enginList"
                    :showMineruToken="showMineruToken"
                    :showIdentityOption="showIdentityOption"
                    :version="version"
                    :stepMap="stepMap"
                    @update:showMineruToken="val => showMineruToken = val" />
            </div>

            <!-- Right: Task Area -->
            <div class="task-col">
                <TaskArea
                    :t="t"
                    @clearAllTasks="clearAllTasks"
                    @handleFolderSelect="handleFolderSelect"
                    @runAllPendingTasks="runAllPendingTasks"
                    @createNewTask="createNewTask"
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
    </div>

    <!-- Modals -->
    <GlossaryModal ref="glossaryModalRefLocal" :t="t" />
    <DefaultWorkflowModal
        :t="t"
        @save="saveDefaultWorkflows" />
    <TutorialModal :t="t" />
    <ContributorsModal :t="t" />
    <QueueSettingsModal
        ref="queueSettingsModalRef"
        :t="t"
        @save="val => saveSetting('queue_concurrent', val)" />

    <!-- Preview Offcanvas -->
    <PreviewOffcanvas
        ref="previewOffcanvasRef"
        :t="t"
        @printPdf="printPdf" />
    <iframe id="printFrame" ref="printFrame" style="display: none;"></iframe>

    <!-- Bottom Controls -->
    <BottomControls
        :currentLang="currentLang"
        @setLang="setLanguage"
        @setTheme="setTheme" />
</div>
</template>

<script setup>
import { ref, computed, onMounted, provide, watch } from 'vue';
import TutorialModal from './components/modals/TutorialModal.vue';
import ContributorsModal from './components/modals/ContributorsModal.vue';
import QueueSettingsModal from './components/modals/QueueSettingsModal.vue';
import GlossaryModal from './components/modals/GlossaryModal.vue';
import DefaultWorkflowModal from './components/modals/DefaultWorkflowModal.vue';
import SettingsPanel from './components/settings/SettingsPanel.vue';
import TaskArea from './components/tasks/TaskArea.vue';
import PreviewOffcanvas from './components/preview/PreviewOffcanvas.vue';
import BottomControls from './components/layout/BottomControls.vue';

// Import composables
import { useSettings } from './composables/useSettings.js';
import { useI18n } from './composables/useI18n.js';
import { useGlossary } from './composables/useGlossary.js';
import { useTasks } from './composables/useTasks.js';
import { usePreview } from './composables/usePreview.js';

// ===== Initialize Composables =====
const settings = useSettings();
const i18n = useI18n();
const glossary = useGlossary();
const tasksComposable = useTasks(settings, glossary, i18n);
const preview = usePreview(i18n);

// Destructure from composables
const { form, workflowParams, errors, defaultParams, default_workflows, queue_concurrent,
        clearError, loadConfig, saveSetting, saveSettingArray, saveWorkflowParam,
        saveAllSettings, setupPlatformWatchers, exportConfig, importConfig,
        saveDefaultWorkflows } = settings;

const { currentLang, t, setLanguage, loadI18n } = i18n;

const { glossaryData, glossaryCount, glossaryModalRef, handleGlossaryFiles, clearGlossary,
        openGlossaryModal, downloadGlossaryTemplate } = glossary;

const { tasks, hasPendingTasks, createNewTask, removeTask, clearAllTasks,
        handleTaskFileSelect, handleTaskFileDrop, triggerFileInput, selectTaskWorkflow,
        handleFolderSelect, runAllPendingTasks, toggleTaskState, copyLog } = tasksComposable;

const { previewMode, syncScrollEnabled, previewTask, isOpen, previewOffcanvasComponent,
        openPreview, closePreview, setPreviewMode, toggleSyncScroll, printPdf, initSplit } = preview;

// Local ref for template binding, sync to composable
const previewOffcanvasRef = ref(null);
watch(previewOffcanvasRef, (val) => {
    previewOffcanvasComponent.value = val;
}, { immediate: true });

// Sync glossaryModalRef to composable
const glossaryModalRefLocal = ref(null);
watch(glossaryModalRefLocal, (val) => {
    glossaryModalRef.value = val;
}, { immediate: true });

// Queue settings modal ref
const queueSettingsModalRef = ref(null);
const openQueueSettings = () => {
    if (queueSettingsModalRef.value) {
        queueSettingsModalRef.value.show();
    }
};
provide('openQueueSettings', openQueueSettings);

// ===== Provide to child components =====
provide('form', form);
provide('workflowParams', workflowParams);
provide('errors', errors);
provide('defaultParams', defaultParams);
provide('default_workflows', default_workflows);
provide('queue_concurrent', queue_concurrent);
provide('glossaryData', glossaryData);
provide('glossaryCount', glossaryCount);
provide('tasks', tasks);
provide('hasPendingTasks', hasPendingTasks);
provide('previewMode', previewMode);
provide('syncScrollEnabled', syncScrollEnabled);
provide('previewTask', previewTask);
provide('previewIsOpen', isOpen);

// Provide methods
provide('clearError', clearError);
provide('saveSetting', saveSetting);
provide('saveSettingArray', saveSettingArray);
provide('saveWorkflowParam', saveWorkflowParam);
provide('saveAllSettings', saveAllSettings);
provide('handleGlossaryFiles', handleGlossaryFiles);
provide('clearGlossary', clearGlossary);
provide('openGlossaryModal', openGlossaryModal);
provide('downloadGlossaryTemplate', downloadGlossaryTemplate);
provide('exportConfig', exportConfig);
provide('importConfig', importConfig);
provide('setPreviewMode', setPreviewMode);
provide('toggleSyncScroll', toggleSyncScroll);
provide('printPdf', printPdf);
provide('createNewTask', createNewTask);
provide('removeTask', removeTask);
provide('clearAllTasks', clearAllTasks);
provide('handleTaskFileSelect', handleTaskFileSelect);
provide('handleTaskFileDrop', handleTaskFileDrop);
provide('triggerFileInput', triggerFileInput);
provide('selectTaskWorkflow', selectTaskWorkflow);
provide('handleFolderSelect', handleFolderSelect);
provide('runAllPendingTasks', runAllPendingTasks);
provide('toggleTaskState', toggleTaskState);
provide('copyLog', copyLog);
provide('openPreview', openPreview);
provide('closePreview', closePreview);
provide('saveDefaultWorkflows', saveDefaultWorkflows);

// ===== Local State =====
const version = ref("");
const enginList = ref([]);
const showMineruToken = ref(false);
const showIdentityOption = ref(true);
const printFrame = ref(null);

// ===== Computed =====
// Dynamic Step Numbering (matches index.html.bak)
const stepMap = computed(() => {
    let step = 2; // 1=Workflow Configuration (merged, includes parsing), from 2 onwards are dynamic
    const map = {ai: 0, trans: 0, glossary: 0};
    map.ai = step++;
    if (!form.skip_translate) map.trans = step++;
    map.glossary = step++;
    return map;
});

// ===== Theme =====
const setTheme = (theme) => {
    localStorage.setItem('theme', theme);
    if (theme === 'auto') document.documentElement.setAttribute('data-theme', window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    else document.documentElement.setAttribute('data-theme', theme);
};

// ===== Lifecycle =====
onMounted(async () => {
    // Load i18n
    await loadI18n();

    // Backend Metadata
    try {
        const [metaRes, enginRes, paramsRes] = await Promise.all([
            fetch("/service/meta"), fetch('/service/engin-list'), fetch("/service/default-params")
        ]);
        const meta = await metaRes.json();
        version.value = meta.version;
        enginList.value = await enginRes.json();
        Object.assign(defaultParams, await paramsRes.json());
    } catch (e) {
        console.error("Backend init failed", e);
    }

    loadConfig(defaultParams);
    setupPlatformWatchers();
    setTheme(localStorage.getItem('theme') || 'auto');

    // Restore tasks
    if (window.location.pathname.includes('/admin')) {
        document.title = "DocuTranslate - Admin Panel";
        try {
            const r = await fetch('/service/task-list');
            const ids = await r.json();
            if (ids) ids.reverse().forEach(id => createNewTask(id));
        } catch (e) {}
    } else {
        const savedIds = JSON.parse(localStorage.getItem('active_task_ids') || '[]');
        if (savedIds.length) savedIds.forEach(id => createNewTask(id));
        else createNewTask();
    }

    // Global resize handler for preview
    window.addEventListener('resize', () => {
        if (isOpen.value) {
            initSplit();
        }
    });
});
</script>
