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
                    :form="form"
                    :workflowParams="workflowParams"
                    :errors="errors"
                    :enginList="enginList"
                    :showMineruToken="showMineruToken"
                    :showIdentityOption="showIdentityOption"
                    @update:showMineruToken="val => showMineruToken = val"
                    @saveSetting="saveSetting"
                    @saveSettingArray="saveSettingArray"
                    @saveWorkflowParam="saveWorkflowParam"
                    @clearError="clearError"
                    @openDefaultWorkflowModal="openDefaultWorkflowModal" />

                <AISettings
                    :t="t"
                    :form="form"
                    :errors="errors"
                    :stepNumber="stepMap.ai"
                    @saveSetting="saveSetting"
                    @clearError="clearError" />

                <TranslationSettings
                    :t="t"
                    :form="form"
                    :errors="errors"
                    :defaultParams="defaultParams"
                    :stepNumber="stepMap.trans"
                    @saveSetting="saveSetting"
                    @clearError="clearError" />

                <GlossarySettings
                    :t="t"
                    :form="form"
                    :defaultParams="defaultParams"
                    :glossaryCount="glossaryCount"
                    :stepNumber="stepMap.glossary"
                    @saveSetting="saveSetting"
                    @handleGlossaryFiles="handleGlossaryFiles"
                    @openGlossaryModal="openGlossaryModal"
                    @clearGlossary="clearGlossary"
                    @downloadGlossaryTemplate="downloadGlossaryTemplate" />

            </div>
        </form>

        <!-- Import/Export -->
        <div class="d-flex justify-content-center gap-2 mt-4">
            <button type="button" class="btn btn-outline-primary" @click="configFile.click()"><i
                    class="bi bi-box-arrow-in-down me-1"></i><span>{{ t('importConfigBtn') }}</span>
            </button>
            <button type="button" class="btn btn-outline-secondary" @click="exportConfig"><i
                    class="bi bi-box-arrow-up me-1"></i><span>{{ t('exportConfigBtn') }}</span></button>
        </div>
        <input type="file" ref="configFile" class="d-none" accept=".json" @change="importConfig">

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
import { computed, ref } from 'vue';
import WorkflowConfig from './WorkflowConfig.vue';
import AISettings from './AISettings.vue';
import TranslationSettings from './TranslationSettings.vue';
import GlossarySettings from './GlossarySettings.vue';

const props = defineProps({
    t: Function,
    form: Object,
    workflowParams: Object,
    errors: Object,
    enginList: Array,
    showMineruToken: Boolean,
    showIdentityOption: Boolean,
    glossaryCount: Number,
    version: String,
    stepMap: Object,
    defaultParams: Object,
});

const emit = defineEmits([
    'saveSetting',
    'saveSettingArray',
    'saveWorkflowParam',
    'clearError',
    'openDefaultWorkflowModal',
    'openGlossaryModal',
    'handleGlossaryFiles',
    'clearGlossary',
    'downloadGlossaryTemplate',
    'importConfig',
    'exportConfig',
]);

const configFile = ref(null);
const showMineruToken = ref(props.showMineruToken);
</script>
