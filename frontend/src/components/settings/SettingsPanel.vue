<template>
    <div class="settings-panel">
        <div class="d-flex justify-content-between align-items-center mb-3">
            <div class="d-flex align-items-center">
                <h4 class="mb-0 me-3 fw-bold" :title="t('pageTitle')">DocuTranslate</h4>
                <div class="btn-group">
                    <button type="button" class="btn btn-sm btn-outline-info" @click="showTutorial = true">
                        <svg class="w-4 h-4 me-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9a3 3 0 011.924-2.786c.903-.42 1.96-.42 2.863 0a3 3 0 011.924 2.786c0 1.452-1.168 2.625-2.606 2.786a3 3 0 00-2.606 2.786v.001M12 18.75a.75.75 0 11-1.5 0 .75.75 0 011.5 0z" />
                        </svg>
                        <span>{{ t('tutorialBtn') }}</span>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-warning" @click="showContributors = true">
                        <svg class="w-4 h-4 me-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-2.24-2.9l-1.76-.44V17a3 3 0 01-3 3h-2a3 3 0 01-3-3v-1.34l-1.76.44A3 3 0 006 18v2h5" />
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 11a3 3 0 11-6 0 3 3 0 016 0zm8 0a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                        <span>{{ t('projectContributeBtn') }}</span>
                    </button>
                </div>
            </div>
        </div>

        <form id="translateForm" @submit.prevent>
            <div class="border rounded" style="border-color: var(--bs-border-color);">

                <WorkflowConfig
                    :t="t"
                    :enginList="enginList"
                    :showMineruToken="showMineruToken"
                    :showIdentityOption="showIdentityOption"
                    @update:showMineruToken="val => emit('update:showMineruToken', val)"
                    @openDefaultWorkflowModal="openDefaultWorkflowModal" />

                <AISettings
                    :t="t"
                    :stepNumber="stepMap.ai" />

                <TranslationSettings
                    :t="t"
                    :stepNumber="stepMap.trans" />

                <GlossarySettings
                    :t="t"
                    :stepNumber="stepMap.glossary" />

            </div>
        </form>

        <!-- Import/Export -->
        <div class="d-flex justify-content-center gap-2 mt-4">
            <button type="button" class="btn btn-outline-primary" @click="configFile.click()">
                <svg class="w-4 h-4 me-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
                <span>{{ t('importConfigBtn') }}</span>
            </button>
            <button type="button" class="btn btn-outline-secondary" @click="handleExportConfig">
                <svg class="w-4 h-4 me-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                <span>{{ t('exportConfigBtn') }}</span>
            </button>
        </div>
        <input type="file" ref="configFile" class="d-none" accept=".json" @change="handleImportConfig">

        <!-- Project Info -->
        <div class="mt-4 text-center text-muted small">
            <p class="mb-2">
                <svg class="w-4 h-4 me-1" style="display: inline; vertical-align: middle;" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.107-3.162 0 0 1.008-.322 3.301 1.23.957-.266 1.976-.399 3-.404 1.024.005 2.043.138 3 .404 2.293-1.552 3.301-1.23 3.301-1.23.643 1.638.232 2.859.107 3.162.768.84 1.236 1.91 1.236 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.214.694.825.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                </svg>
                {{ t('githubHomepage') }}<br/>
                <a href="https://github.com/xunbu/docutranslate" target="_blank" style="color: var(--bs-primary);">https://github.com/xunbu/docutranslate</a>
            </p>
            <p class="mb-2">{{ t('qqGroup') }}</p>
            <p class="mb-0">version:<span>{{ version ? 'v' + version : '' }}</span></p>
        </div>
    </div>

    <!-- Tutorial Modal -->
    <Modal v-model="showTutorial" :title="t('tutorialModalTitle')" size="xl">
        <TutorialContent :t="t" @close="showTutorial = false" />
    </Modal>

    <!-- Contributors Modal -->
    <Modal v-model="showContributors" :title="t('contributorsModalTitle')" size="lg">
        <ContributorsContent :t="t" @close="showContributors = false" />
    </Modal>

    <!-- Default Workflow Modal -->
    <DefaultWorkflowModal
        ref="defaultWorkflowModal"
        :t="t"
        @save="saveDefaultWorkflows" />
</template>

<script setup>
import { ref, inject } from 'vue';
import WorkflowConfig from './WorkflowConfig.vue';
import AISettings from './AISettings.vue';
import TranslationSettings from './TranslationSettings.vue';
import GlossarySettings from './GlossarySettings.vue';
import Modal from '../ui/Modal.vue';
import TutorialContent from '../modals/TutorialContent.vue';
import ContributorsContent from '../modals/ContributorsContent.vue';
import DefaultWorkflowModal from '../modals/DefaultWorkflowModal.vue';

const props = defineProps({
    t: Function,
    enginList: Array,
    showMineruToken: Boolean,
    showIdentityOption: Boolean,
    version: String,
    stepMap: Object,
});

const emit = defineEmits([
    'update:showMineruToken',
]);

// Inject from parent
const form = inject('form');
const workflowParams = inject('workflowParams');
const errors = inject('errors');
const defaultParams = inject('defaultParams');
const glossaryCount = inject('glossaryCount');
const saveSetting = inject('saveSetting');
const saveSettingArray = inject('saveSettingArray');
const saveWorkflowParam = inject('saveWorkflowParam');
const clearError = inject('clearError');
const handleGlossaryFiles = inject('handleGlossaryFiles');
const clearGlossary = inject('clearGlossary');
const openGlossaryModal = inject('openGlossaryModal');
const downloadGlossaryTemplate = inject('downloadGlossaryTemplate');
const exportConfig = inject('exportConfig');
const importConfig = inject('importConfig');
const saveDefaultWorkflows = inject('saveDefaultWorkflows');

const configFile = ref(null);
const showTutorial = ref(false);
const showContributors = ref(false);
const defaultWorkflowModal = ref(null);

const handleExportConfig = () => {
    exportConfig();
};

const handleImportConfig = (e) => {
    importConfig(e, props.t);
};

const openDefaultWorkflowModal = () => {
    defaultWorkflowModal.value?.show();
};
</script>
