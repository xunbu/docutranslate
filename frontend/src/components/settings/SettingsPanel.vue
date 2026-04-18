<template>
    <div class="settings-panel">
        <div class="d-flex justify-content-between align-items-center mb-3">
            <div class="d-flex align-items-center">
                <h4 class="mb-0 me-3 fw-bold" :title="t('pageTitle')">DocuTranslate</h4>
                <div class="btn-group">
                    <button type="button" class="btn btn-sm btn-outline-info" data-bs-toggle="modal"
                            data-bs-target="#tutorialModal">
                        <i class="bi bi-question-circle-fill me-1"></i><span>{{ t('tutorialBtn') }}</span>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-warning" data-bs-toggle="modal"
                            data-bs-target="#contributorsModal">
                        <i class="bi bi-people-fill me-1"></i><span>{{ t('projectContributeBtn') }}</span>
                    </button>
                </div>
            </div>
        </div>

        <form id="translateForm" @submit.prevent>
            <div class="accordion" id="settingsAccordion">

                <WorkflowConfig
                    :t="t"
                    :enginList="enginList"
                    :showMineruToken="showMineruToken"
                    :showIdentityOption="showIdentityOption"
                    @update:showMineruToken="val => emit('update:showMineruToken', val)" />

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
            <button type="button" class="btn btn-outline-primary" @click="configFile.click()"><i
                    class="bi bi-box-arrow-in-down me-1"></i><span>{{ t('importConfigBtn') }}</span>
            </button>
            <button type="button" class="btn btn-outline-secondary" @click="handleExportConfig"><i
                    class="bi bi-box-arrow-up me-1"></i><span>{{ t('exportConfigBtn') }}</span></button>
        </div>
        <input type="file" ref="configFile" class="d-none" accept=".json" @change="handleImportConfig">

        <!-- Project Info -->
        <div class="mt-4 text-center text-muted small project-info">
            <p class="bi bi-github mb-2"> {{ t('githubHomepage') }}<br/><a
                    href="https://github.com/xunbu/docutranslate" target="_blank">https://github.com/xunbu/docutranslate</a>
            </p>
            <p class="bi bi-tencent-qq mb-2"> {{ t('qqGroup') }}</p>
            <p class="bi mb-0">version:<span>{{ version ? 'v' + version : '' }}</span></p>
        </div>
    </div>
</template>

<script setup>
import { ref, inject } from 'vue';
import WorkflowConfig from './WorkflowConfig.vue';
import AISettings from './AISettings.vue';
import TranslationSettings from './TranslationSettings.vue';
import GlossarySettings from './GlossarySettings.vue';

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

const configFile = ref(null);

const handleExportConfig = () => {
    exportConfig();
};

const handleImportConfig = (e) => {
    importConfig(e, props.t);
};
</script>
