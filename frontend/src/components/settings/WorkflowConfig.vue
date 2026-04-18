<template>
    <!-- 1. Workflow Configuration (Merged) -->
    <Collapse v-model="isWorkflowConfigOpen">
        <template #header>
            <strong>
                <span class="step-number">1 </span>
                <svg class="w-5 h-5 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 6h18M3 12h18M3 18h18M7 6v12M17 6v12M11 6v12" />
                </svg>
                <span>{{ t('workflowConfigTitle') }}</span>
            </strong>
        </template>

        <!-- Top: Configure default workflow button -->
        <div class="mb-3">
            <Button variant="outline-primary" @click="openDefaultWorkflowModal">
                <svg class="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 16 16">
                    <path d="M8 4.754a3.246 3.246 0 1 0 0 6.492 3.246 3.246 0 0 0 0-6.492zM5.754 8a2.246 2.246 0 1 1 4.492 0 2.246 2.246 0 0 1-4.492 0z"/>
                    <path d="M9.796 1.343c-.527-1.79-3.065-1.79-3.592 0l-.094.319a.873.873 0 0 1-1.255.52l-.292-.16c-1.64-.892-3.433.902-2.54 2.541l.159.292a.873.873 0 0 1-.52 1.255l-.319.094c-1.79.527-1.79 3.065 0 3.592l.319.094a.873.873 0 0 1 .52 1.255l-.16.292c-.892 1.64.901 3.434 2.541 2.54l.292-.159a.873.873 0 0 1 1.255.52l.094.319c.527 1.79 3.065 1.79 3.592 0l.094-.319a.873.873 0 0 1 1.255-.52l.292.16c1.64.893 3.434-.902 2.54-2.541l-.159-.292a.873.873 0 0 1 .52-1.255l.319-.094c1.79-.527 1.79-3.065 0-3.592l-.319-.094a.873.873 0 0 1-.52-1.255l.16-.292c.893-1.64-.902-3.433-2.541-2.54l-.292.159a.873.873 0 0 1-1.255-.52l-.094-.319zm-2.633.283c.246-.835 1.428-.835 1.674 0l.094.319a1.873 1.873 0 0 0 2.693 1.115l.291-.16c.764-.415 1.6.42 1.184 1.185l-.159.292a1.873 1.873 0 0 0 1.116 2.692l.318.094c.835.246.835 1.428 0 1.674l-.319.094a1.873 1.873 0 0 0-1.115 2.693l.16.291c.415.764-.42 1.6-1.185 1.184l-.291-.159a1.873 1.873 0 0 0-2.693 1.116l-.094.318c-.246.835-1.428.835-1.674 0l-.094-.319a1.873 1.873 0 0 0-2.692-1.115l-.292.16c-.764.415-1.6-.42-1.184-1.185l.159-.291A1.873 1.873 0 0 0 1.945 8.93l-.319-.094c-.835-.246-.835-1.428 0-1.674l.319-.094A1.873 1.873 0 0 0 3.06 4.377l-.16-.292c-.415-.764.42-1.6 1.185-1.184l.292.159a1.873 1.873 0 0 0 2.692-1.115l.094-.319z"/>
                </svg>
                {{ t('openExtWorkflowBtn') }}
            </Button>
        </div>
        <!-- Workflow type selection -->
        <div class="mb-3">
            <select class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
                    v-model="form.workflow_type"
                    @change="saveSetting('translator_last_workflow', form.workflow_type)">
                <option value="markdown_based">{{ t('workflowOptionMarkdown') }}</option>
                <option value="docx">{{ t('workflowOptionDocx') }}</option>
                <option value="xlsx">{{ t('workflowOptionXlsx') }}</option>
                <option value="epub">{{ t('workflowOptionEpub') }}</option>
                <option value="txt">{{ t('workflowOptionTxt') }}</option>
                <option value="pptx">{{ t('workflowOptionPptx') }}</option>
                <option value="srt">{{ t('workflowOptionSrt') }}</option>
                <option value="ass">{{ t('workflowOptionAss') }}</option>
                <option value="json">{{ t('workflowOptionJson') }}</option>
                <option value="html">{{ t('workflowOptionHtml') }}</option>
            </select>
        </div>
        <hr class="border-gray-200 dark:border-gray-700 my-4">
        <!-- Workflow-specific options -->
        <template v-if="currentWorkflowConfig">
            <!-- Common Insert Mode -->
            <div class="mb-3" v-if="currentWorkflowConfig.hasInsertMode">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('insertModeLabel') }}</label>
                <select class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
                        v-model="workflowParams[form.workflow_type].insert_mode"
                        @change="saveWorkflowParam('insert_mode')">
                    <option value="replace">{{ t('insertModeReplace') }}</option>
                    <option value="append">{{ t('insertModeAppend') }}</option>
                    <option value="prepend">{{ t('insertModePrepend') }}</option>
                </select>
                <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    {{ t(currentWorkflowConfig.insertHelpKey || 'insertModeHelpTxt') }}
                </div>
            </div>
            <!-- Common Separator -->
            <div class="mb-3" v-if="currentWorkflowConfig.hasInsertMode"
                 v-show="['append', 'prepend'].includes(workflowParams[form.workflow_type].insert_mode)">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('separatorLabel') }}</label>
                <input type="text"
                       class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
                       v-model="workflowParams[form.workflow_type].separator"
                       @input="saveWorkflowParam('separator')"
                       :placeholder="t(currentWorkflowConfig.separatorPlaceholderKey || 'separatorPlaceholderSimple')">
                <div class="text-sm text-gray-500 dark:text-gray-400 mt-1"
                     v-html="t(currentWorkflowConfig.separatorHelpKey || 'separatorHelp')"></div>
            </div>

            <!-- TXT Specific -->
            <div class="mb-3" v-if="form.workflow_type === 'txt'">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('segmentModeLabel') }}</label>
                <select class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
                        v-model="workflowParams.txt.segment_mode"
                        @change="saveWorkflowParam('segment_mode')">
                    <option value="line">{{ t('segmentModeLine') }}</option>
                    <option value="paragraph">{{ t('segmentModeParagraph') }}</option>
                    <option value="none">{{ t('segmentModeNone') }}</option>
                </select>
                <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">{{ t('segmentModeHelp') }}</div>
            </div>
            <!-- XLSX Specific -->
            <div class="mb-3" v-if="form.workflow_type === 'xlsx'">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('xlsxTranslateRegionsLabel') }}</label>
                <textarea class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
                          v-model="workflowParams.xlsx.translate_regions"
                          @input="saveWorkflowParam('translate_regions')" rows="3"
                          :placeholder="t('xlsxTranslateRegionsPlaceholder')"></textarea>
            </div>
            <!-- JSON Specific -->
            <div class="mb-3" v-if="form.workflow_type === 'json'">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('jsonPathLabel') }}</label>
                <textarea class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
                          :class="{'border-red-500 dark:border-red-400': errors.json_paths}"
                          v-model="workflowParams.json.json_paths"
                          @input="saveWorkflowParam('json_paths'); clearError('json_paths')"
                          rows="4" required
                          :placeholder="t('jsonPathPlaceholder')"></textarea>
                <div class="text-sm text-gray-500 dark:text-gray-400 mt-1" v-html="t('jsonPathHelp')"></div>
            </div>
        </template>
        <!-- Markdown Parsing Settings (only shown for markdown_based workflow) -->
        <div v-if="form.workflow_type === 'markdown_based'">
            <div class="mb-3">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('parsingEngineLabel') }}</label>
                <select class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
                        v-model="form.convert_engine"
                        @change="saveSetting('translator_convert_engin', form.convert_engine)">
                    <option value="identity" v-if="showIdentityOption">
                        {{ t('engineOptionIdentity') || '已经是markdown' }}
                    </option>
                    <option v-for="eng in enginList" :key="eng" :value="eng">
                        {{ t('engineOption' + capitalize(eng)) || eng }}
                    </option>
                </select>
                <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">{{ t('parsingEngineHelp') }}</div>
            </div>

            <!-- Mineru Cloud Config -->
            <div v-if="form.convert_engine === 'mineru'">
                <div class="mb-3">
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Mineru Token
                        <a href="https://mineru.net/apiManage/token" target="_blank" class="ml-1 text-primary hover:underline">
                            <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                            </svg>
                        </a>
                    </label>
                    <div class="flex">
                        <input :type="showMineruToken ? 'text' : 'password'"
                               autocomplete="new-password"
                               class="flex-1 px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-l bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
                               :class="{'border-red-500 dark:border-red-400': errors.mineru_token}"
                               v-model="form.mineru_token"
                               @change="saveSetting('translator_mineru_token', form.mineru_token); clearError('mineru_token')"
                               :placeholder="t('mineruTokenPlaceholder')">
                        <button class="px-3 py-1.5 text-sm border border-l-0 border-gray-300 dark:border-gray-600 rounded-r bg-gray-50 dark:bg-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-500 transition-colors"
                                type="button"
                                @click="emit('update:showMineruToken', !showMineruToken)">
                            <svg v-if="showMineruToken" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                            </svg>
                            <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                            </svg>
                        </button>
                    </div>
                </div>
                <div class="mb-3">
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('modelVersionLabel') }}</label>
                    <select class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
                            v-model="form.model_version"
                            @change="saveSetting('translator_model_version', form.model_version)">
                        <option value="vlm">{{ t('modelVersionVlm') }}</option>
                        <option value="pipeline">{{ t('modelVersionPipline') }}</option>
                    </select>
                    <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">{{ t('modelVersionHelp') }}</div>
                </div>
                <div class="mb-3">
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('mineruLanguageLabel') }}</label>
                    <select class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
                            v-model="form.mineru_language"
                            @change="saveSetting('translator_mineru_language', form.mineru_language)">
                        <option v-for="lang in mineruLangOptions" :key="lang.val" :value="lang.val">
                            {{ lang.label }}
                        </option>
                    </select>
                </div>
            </div>

            <!-- Mineru Local Deploy Config -->
            <div v-if="form.convert_engine === 'mineru_deploy'"
                 class="border border-gray-300 dark:border-gray-600 p-3 rounded mb-3">
                <div class="mb-3">
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('mineruDeployBaseUrlLabel') }}</label>
                    <input type="url"
                           class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
                           :class="{'border-red-500 dark:border-red-400': errors.mineru_deploy_base_url}"
                           v-model="form.mineru_deploy_base_url"
                           @change="saveSetting('mineru_deploy_base_url', form.mineru_deploy_base_url); clearError('mineru_deploy_base_url')"
                           required :placeholder="t('mineruDeployBaseUrlPlaceholder')">
                </div>
                <div class="mb-3">
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('mineruDeployBackendLabel') }}</label>
                    <select class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
                            v-model="form.mineru_deploy_backend"
                            @change="saveSetting('mineru_deploy_backend', form.mineru_deploy_backend)">
                        <option value="pipeline">pipeline</option>
                        <option value="vlm-auto-engine">vlm-auto-engine</option>
                        <option value="vlm-http-client">vlm-http-client</option>
                        <option value="hybrid-auto-engine">hybrid-auto-engine</option>
                        <option value="hybrid-http-client">hybrid-http-client</option>
                    </select>
                </div>

                <div class="mb-3">
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('mineruDeployParseMethodLabel') }}</label>
                    <select class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
                            v-model="form.mineru_deploy_parse_method"
                            @change="saveSetting('mineru_deploy_parse_method', form.mineru_deploy_parse_method)">
                        <option value="auto">auto</option>
                        <option value="txt">txt</option>
                        <option value="ocr">ocr</option>
                    </select>
                </div>

                <!-- Condition: If Backend is Pipeline or Hybrid, show Lang List -->
                <div class="mb-3"
                     v-if="['pipeline', 'hybrid-auto-engine', 'hybrid-http-client'].includes(form.mineru_deploy_backend)">
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('mineruDeployLangListLabel') }}</label>
                    <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
                        <label v-for="lang in mineruLangOptions" :key="lang.val"
                               class="inline-flex items-center gap-2 cursor-pointer">
                            <input type="checkbox"
                                   :value="lang.val"
                                   v-model="form.mineru_deploy_lang_list"
                                   @change="saveSettingArray('mineru_deploy_lang_list', form.mineru_deploy_lang_list)"
                                   class="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary dark:border-gray-600 dark:bg-gray-700">
                            <span class="text-sm text-gray-700 dark:text-gray-300">{{ lang.label }}</span>
                        </label>
                    </div>
                </div>

                <!-- Condition: If Backend is vlm-http-client or hybrid-http-client, show Server URL -->
                <div class="mb-3"
                     v-if="['vlm-http-client', 'hybrid-http-client'].includes(form.mineru_deploy_backend)">
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('mineruDeployServerUrlLabel') }}</label>
                    <input type="url"
                           class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
                           v-model="form.mineru_deploy_server_url"
                           @change="saveSetting('mineru_deploy_server_url', form.mineru_deploy_server_url)"
                           :placeholder="t('mineruDeployServerUrlPlaceholder')">
                </div>

                <div class="grid grid-cols-2 gap-3">
                    <div class="mb-3">
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('mineruDeployStartPageLabel') }}</label>
                        <input type="number"
                               class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
                               v-model="form.mineru_deploy_start_page"
                               @change="saveSetting('mineru_deploy_start_page', form.mineru_deploy_start_page)"
                               min="0">
                    </div>
                    <div class="mb-3">
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('mineruDeployEndPageLabel') }}</label>
                        <input type="number"
                               class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
                               v-model="form.mineru_deploy_end_page"
                               @change="saveSetting('mineru_deploy_end_page', form.mineru_deploy_end_page)"
                               min="0">
                    </div>
                </div>
                <Toggle v-model="form.mineru_deploy_formula_enable"
                        :label="t('mineruDeployFormulaEnableLabel')"
                        @update:modelValue="saveSetting('mineru_deploy_formula_enable', form.mineru_deploy_formula_enable)"
                        class="mb-2" />
                <Toggle v-model="form.mineru_deploy_table_enable"
                        :label="t('mineruDeployTableEnableLabel')"
                        @update:modelValue="saveSetting('mineru_deploy_table_enable', form.mineru_deploy_table_enable)"
                        class="mb-2" />
            </div>


            <div class="mt-3">
                <Toggle v-if="ocrOptions.showFormula"
                        v-model="form.formula_ocr"
                        :label="t('formulaOcrLabel')"
                        @update:modelValue="saveSetting('translator_formula_ocr', form.formula_ocr)"
                        class="mb-2" />
                <Toggle v-if="ocrOptions.showCode"
                        v-model="form.code_ocr"
                        :label="t('codeOcrLabel')"
                        @update:modelValue="saveSetting('translator_code_ocr', form.code_ocr)"
                        class="mb-2" />
            </div>

            <!-- Markdown to Docx Engine Selector -->
            <div class="border-t border-gray-200 dark:border-gray-700 mt-3 pt-3">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('md2docxEngineLabel') || 'Markdown转Docx引擎' }}</label>
                <select class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
                        v-model="form.md2docx_engine"
                        @change="saveSetting('translator_md2docx_engine', form.md2docx_engine)">
                    <option :value="null">{{ t('engineOptionNone') || '不生成docx' }}</option>
                    <option value="auto">{{ t('engineOptionAuto') || '自动选择' }}</option>
                    <option value="python">{{ t('engineOptionPython') || '纯Python' }}</option>
                    <option value="pandoc">{{ t('engineOptionPandoc') || 'Pandoc' }}</option>
                </select>
                <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">{{ t('md2docxEngineHelp') || '选择将Markdown导出为Docx的方式' }}</div>
            </div>
        </div>
    </Collapse>
</template>

<script setup>
import { computed, inject, ref } from 'vue';
import { mineruLangOptions } from '../../constants/mineruLanguages';
import { capitalize } from '../../utils/helpers';
import Collapse from '../ui/Collapse.vue';
import Button from '../ui/Button.vue';
import Toggle from '../ui/Toggle.vue';

const props = defineProps({
    t: Function,
    enginList: Array,
    showMineruToken: Boolean,
    showIdentityOption: Boolean,
});

const emit = defineEmits([
    'update:showMineruToken',
    'openDefaultWorkflowModal',
]);

// Inject from parent
const form = inject('form');
const workflowParams = inject('workflowParams');
const errors = inject('errors');
const saveSetting = inject('saveSetting');
const saveSettingArray = inject('saveSettingArray');
const saveWorkflowParam = inject('saveWorkflowParam');
const clearError = inject('clearError');

// Local state for collapse
const isWorkflowConfigOpen = ref(false);

const openDefaultWorkflowModal = () => {
    emit('openDefaultWorkflowModal');
};

const currentWorkflowConfig = computed(() => {
    const map = {
        'txt': {
            titleKey: 'txtSettingsTitleText',
            icon: 'bi-filetype-txt',
            hasInsertMode: true,
            insertHelpKey: 'insertModeHelpTxt'
        },
        'docx': {
            titleKey: 'docxSettingsTitleText',
            icon: 'bi-file-earmark-word',
            hasInsertMode: true,
            insertHelpKey: 'insertModeHelpDocx'
        },
        'xlsx': {
            titleKey: 'xlsxSettingsTitleText',
            icon: 'bi-file-earmark-spreadsheet',
            hasInsertMode: true,
            insertHelpKey: 'insertModeHelpXlsx'
        },
        'srt': {
            titleKey: 'srtSettingsTitleText',
            icon: 'bi-file-text',
            hasInsertMode: true,
            insertHelpKey: 'insertModeHelpSrt'
        },
        'epub': {
            titleKey: 'epubSettingsTitleText',
            icon: 'bi-book',
            hasInsertMode: true,
            insertHelpKey: 'insertModeHelpEpub'
        },
        'html': {
            titleKey: 'htmlSettingsTitleText',
            icon: 'bi-filetype-html',
            hasInsertMode: true,
            insertHelpKey: 'insertModeHelpHtml'
        },
        'ass': {
            titleKey: 'assSettingsTitleText',
            icon: 'bi-file-easel',
            hasInsertMode: true,
            insertHelpKey: 'insertModeHelpAss',
            separatorHelpKey: 'separatorHelpAss',
            separatorPlaceholderKey: 'separatorPlaceholderAss'
        },
        'pptx': {
            titleKey: 'pptxSettingsTitleText',
            icon: 'bi-file-slides',
            hasInsertMode: true,
            insertHelpKey: 'insertModeHelpPptx'
        },
        'json': {titleKey: 'jsonSettingsTitleText', icon: 'bi-signpost-split', hasInsertMode: false},
    };
    return map[form.workflow_type];
});

const ocrOptions = computed(() => ({
    showFormula: ['mineru', 'docling'].includes(form.convert_engine),
    showCode: form.convert_engine === 'docling'
}));
</script>
