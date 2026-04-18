<template>
    <!-- 1. Workflow Configuration (Merged) -->
    <div class="accordion-item">
        <h2 class="accordion-header">
            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse"
                    data-bs-target="#collapseWorkflowConfig">
                <strong><span class="step-number">1</span><i
                        class="bi bi-diagram-3 me-2"></i><span>{{ t('workflowConfigTitle')
                    }}</span></strong>
            </button>
        </h2>
        <div id="collapseWorkflowConfig" class="accordion-collapse collapse">
            <div class="accordion-body">
                <!-- Top: Configure default workflow button -->
                <div class="mb-3">
                    <button type="button" class="btn btn-outline-primary" @click="openDefaultWorkflowModal">
                        <i class="bi bi-gear-fill me-2"></i>{{ t('openExtWorkflowBtn') }}
                    </button>
                </div>
                <!-- Workflow type selection -->
                <div class="mb-3">
                    <select class="form-select" v-model="form.workflow_type"
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
                <hr>
                <!-- Workflow-specific options -->
                <template v-if="currentWorkflowConfig">
                    <!-- Common Insert Mode -->
                    <div class="mb-3" v-if="currentWorkflowConfig.hasInsertMode">
                        <label class="form-label">{{ t('insertModeLabel') }}</label>
                        <select class="form-select"
                                v-model="workflowParams[form.workflow_type].insert_mode"
                                @change="saveWorkflowParam('insert_mode')">
                            <option value="replace">{{ t('insertModeReplace') }}</option>
                            <option value="append">{{ t('insertModeAppend') }}</option>
                            <option value="prepend">{{ t('insertModePrepend') }}</option>
                        </select>
                        <div class="form-text">
                            {{ t(currentWorkflowConfig.insertHelpKey || 'insertModeHelpTxt') }}
                        </div>
                    </div>
                    <!-- Common Separator -->
                    <div class="mb-3" v-if="currentWorkflowConfig.hasInsertMode"
                         v-show="['append', 'prepend'].includes(workflowParams[form.workflow_type].insert_mode)">
                                        <label class="form-label">{{ t('separatorLabel') }}</label>
                                        <input type="text" class="form-control"
                                               v-model="workflowParams[form.workflow_type].separator"
                                               @input="saveWorkflowParam('separator')"
                                               :placeholder="t(currentWorkflowConfig.separatorPlaceholderKey || 'separatorPlaceholderSimple')">
                                        <div class="form-text"
                                             v-html="t(currentWorkflowConfig.separatorHelpKey || 'separatorHelp')"></div>
                    </div>

                    <!-- TXT Specific -->
                    <div class="mb-3" v-if="form.workflow_type === 'txt'">
                        <label class="form-label">{{ t('segmentModeLabel') }}</label>
                        <select class="form-select" v-model="workflowParams.txt.segment_mode"
                                @change="saveWorkflowParam('segment_mode')">
                            <option value="line">{{ t('segmentModeLine') }}</option>
                            <option value="paragraph">{{ t('segmentModeParagraph') }}</option>
                            <option value="none">{{ t('segmentModeNone') }}</option>
                        </select>
                        <div class="form-text">{{ t('segmentModeHelp') }}</div>
                    </div>
                    <!-- XLSX Specific -->
                    <div class="mb-3" v-if="form.workflow_type === 'xlsx'">
                        <label class="form-label">{{ t('xlsxTranslateRegionsLabel') }}</label>
                        <textarea class="form-control"
                                  v-model="workflowParams.xlsx.translate_regions"
                                  @input="saveWorkflowParam('translate_regions')" rows="3"
                                  :placeholder="t('xlsxTranslateRegionsPlaceholder')"></textarea>
                    </div>
                    <!-- JSON Specific -->
                    <div class="mb-3" v-if="form.workflow_type === 'json'">
                        <label class="form-label">{{ t('jsonPathLabel') }}</label>
                        <textarea class="form-control" :class="{'is-invalid': errors.json_paths}"
                                  v-model="workflowParams.json.json_paths"
                                  @input="saveWorkflowParam('json_paths'); clearError('json_paths')"
                                  rows="4" required
                                  :placeholder="t('jsonPathPlaceholder')"></textarea>
                        <div class="form-text" v-html="t('jsonPathHelp')"></div>
                    </div>
                </template>
                <!-- Markdown Parsing Settings (only shown for markdown_based workflow) -->
                <div v-if="form.workflow_type === 'markdown_based'">
                    <div class="mb-3">
                        <label class="form-label">{{ t('parsingEngineLabel') }}</label>
                        <select class="form-select" v-model="form.convert_engine"
                                @change="saveSetting('translator_convert_engin', form.convert_engine)">
                            <option value="identity" v-if="showIdentityOption">
                                {{ t('engineOptionIdentity') || '已经是markdown' }}
                            </option>
                            <option v-for="eng in enginList" :key="eng" :value="eng">
                                {{ t('engineOption' + capitalize(eng)) || eng }}
                            </option>
                        </select>
                        <div class="form-text">{{ t('parsingEngineHelp') }}</div>
                    </div>

                    <!-- Mineru Cloud Config -->
                    <div v-if="form.convert_engine === 'mineru'">
                        <div class="mb-3">
                            <label class="form-label">Mineru Token <a
                                    href="https://mineru.net/apiManage/token" target="_blank"
                                    class="ms-1"><i
                                    class="bi bi-box-arrow-up-right"></i></a></label>
                            <div class="input-group">
                                <input :type="showMineruToken ? 'text' : 'password'"
                                       autocomplete="new-password" class="form-control"
                                       :class="{'is-invalid': errors.mineru_token}"
                                       v-model="form.mineru_token"
                                       @change="saveSetting('translator_mineru_token', form.mineru_token); clearError('mineru_token')"
                                       :placeholder="t('mineruTokenPlaceholder')">
                                <button class="btn btn-outline-secondary" type="button"
                                        @click="emit('update:showMineruToken', !showMineruToken)"><i class="bi"
                                                                                       :class="showMineruToken ? 'bi-eye' : 'bi-eye-slash'"></i>
                                </button>
                            </div>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">{{ t('modelVersionLabel') }}</label>
                            <select class="form-select" v-model="form.model_version"
                                    @change="saveSetting('translator_model_version', form.model_version)">
                                <option value="vlm">{{ t('modelVersionVlm') }}</option>
                                <option value="pipeline">{{ t('modelVersionPipline') }}</option>
                            </select>
                            <div class="form-text">{{ t('modelVersionHelp') }}</div>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">{{ t('mineruLanguageLabel') }}</label>
                            <select class="form-select" v-model="form.mineru_language"
                                    @change="saveSetting('translator_mineru_language', form.mineru_language)">
                                <option v-for="lang in mineruLangOptions" :key="lang.val" :value="lang.val">
                                    {{ lang.label }}
                                </option>
                            </select>
                        </div>
                    </div>

                    <!-- Mineru Local Deploy Config -->
                    <div v-if="form.convert_engine === 'mineru_deploy'"
                         class="border p-3 rounded mb-3">
                        <div class="mb-3">
                            <label class="form-label">{{ t('mineruDeployBaseUrlLabel') }}</label>
                            <input type="url" class="form-control"
                                   :class="{'is-invalid': errors.mineru_deploy_base_url}"
                                   v-model="form.mineru_deploy_base_url"
                                   @change="saveSetting('mineru_deploy_base_url', form.mineru_deploy_base_url); clearError('mineru_deploy_base_url')"
                                   required :placeholder="t('mineruDeployBaseUrlPlaceholder')">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">{{ t('mineruDeployBackendLabel') }}</label>
                            <select class="form-select" v-model="form.mineru_deploy_backend"
                                    @change="saveSetting('mineru_deploy_backend', form.mineru_deploy_backend)">
                                <option value="pipeline">pipeline</option>
                                <option value="vlm-auto-engine">vlm-auto-engine</option>
                                <option value="vlm-http-client">vlm-http-client</option>
                                <option value="hybrid-auto-engine">hybrid-auto-engine</option>
                                <option value="hybrid-http-client">hybrid-http-client</option>
                            </select>
                        </div>

                        <div class="mb-3">
                            <label class="form-label">{{ t('mineruDeployParseMethodLabel')
                                }}</label>
                            <select class="form-select" v-model="form.mineru_deploy_parse_method"
                                    @change="saveSetting('mineru_deploy_parse_method', form.mineru_deploy_parse_method)">
                                <option value="auto">auto</option>
                                <option value="txt">txt</option>
                                <option value="ocr">ocr</option>
                            </select>
                        </div>

                        <!-- Condition: If Backend is Pipeline or Hybrid, show Lang List -->
                        <div class="mb-3"
                             v-if="['pipeline', 'hybrid-auto-engine', 'hybrid-http-client'].includes(form.mineru_deploy_backend)">
                            <label class="form-label">{{ t('mineruDeployLangListLabel') }}</label>
                            <div class="lang-list-container">
                                <div class="form-check" v-for="lang in mineruLangOptions"
                                     :key="lang.val">
                                    <input class="form-check-input" type="checkbox"
                                           :value="lang.val"
                                           :id="'langCheck-'+lang.val"
                                           v-model="form.mineru_deploy_lang_list"
                                           @change="saveSettingArray('mineru_deploy_lang_list', form.mineru_deploy_lang_list)">
                                    <label class="form-check-label" :for="'langCheck-'+lang.val">
                                        {{ lang.label }}
                                    </label>
                                </div>
                            </div>
                        </div>

                        <!-- Condition: If Backend is vlm-http-client or hybrid-http-client, show Server URL -->
                        <div class="mb-3"
                             v-if="['vlm-http-client', 'hybrid-http-client'].includes(form.mineru_deploy_backend)">
                            <label class="form-label">{{ t('mineruDeployServerUrlLabel') }}</label>
                            <input type="url" class="form-control"
                                   v-model="form.mineru_deploy_server_url"
                                   @change="saveSetting('mineru_deploy_server_url', form.mineru_deploy_server_url)"
                                   :placeholder="t('mineruDeployServerUrlPlaceholder')">
                        </div>

                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">{{ t('mineruDeployStartPageLabel')
                                    }}</label>
                                <input type="number" class="form-control"
                                       v-model="form.mineru_deploy_start_page"
                                       @change="saveSetting('mineru_deploy_start_page', form.mineru_deploy_start_page)"
                                       min="0">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">{{ t('mineruDeployEndPageLabel')
                                    }}</label>
                                <input type="number" class="form-control"
                                       v-model="form.mineru_deploy_end_page"
                                       @change="saveSetting('mineru_deploy_end_page', form.mineru_deploy_end_page)"
                                       min="0">
                            </div>
                        </div>
                        <div class="form-check form-switch mb-2">
                            <input class="form-check-input" type="checkbox" role="switch"
                                   v-model="form.mineru_deploy_formula_enable"
                                   @change="saveSetting('mineru_deploy_formula_enable', form.mineru_deploy_formula_enable)">
                            <label class="form-check-label">{{ t('mineruDeployFormulaEnableLabel')
                                }}</label>
                        </div>
                        <div class="form-check form-switch mb-2">
                            <input class="form-check-input" type="checkbox" role="switch"
                                   v-model="form.mineru_deploy_table_enable"
                                   @change="saveSetting('mineru_deploy_table_enable', form.mineru_deploy_table_enable)">
                            <label class="form-check-label">{{ t('mineruDeployTableEnableLabel')
                                }}</label>
                        </div>
                    </div>


                    <div class="mt-3">
                        <div class="form-check form-switch mb-2" v-if="ocrOptions.showFormula">
                            <input class="form-check-input" type="checkbox" role="switch"
                                   v-model="form.formula_ocr"
                                   @change="saveSetting('translator_formula_ocr', form.formula_ocr)">
                            <label class="form-check-label">{{ t('formulaOcrLabel') }}</label>
                        </div>
                        <div class="form-check form-switch mb-2" v-if="ocrOptions.showCode">
                            <input class="form-check-input" type="checkbox" role="switch"
                                   v-model="form.code_ocr"
                                   @change="saveSetting('translator_code_ocr', form.code_ocr)">
                            <label class="form-check-label">{{ t('codeOcrLabel') }}</label>
                        </div>
                    </div>

                    <!-- Markdown to Docx Engine Selector -->
                    <div class="border-top mt-3  pt-3">
                        <label class="form-label">{{ t('md2docxEngineLabel') || 'Markdown转Docx引擎'
                            }}</label>
                        <select class="form-select" v-model="form.md2docx_engine"
                                @change="saveSetting('translator_md2docx_engine', form.md2docx_engine)">
                            <option :value="null">{{ t('engineOptionNone') || '不生成docx' }}
                            </option>
                            <option value="auto">{{ t('engineOptionAuto') || '自动选择' }}</option>
                            <option value="python">{{ t('engineOptionPython') || '纯Python' }}
                            </option>
                            <option value="pandoc">{{ t('engineOptionPandoc') || 'Pandoc' }}
                            </option>
                        </select>
                        <div class="form-text">{{ t('md2docxEngineHelp') || '选择将Markdown导出为Docx的方式'
                            }}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { computed, inject } from 'vue';
import { mineruLangOptions } from '../../constants/mineruLanguages';
import { capitalize } from '../../utils/helpers';

const props = defineProps({
    t: Function,
    enginList: Array,
    showMineruToken: Boolean,
    showIdentityOption: Boolean,
});

const emit = defineEmits([
    'update:showMineruToken',
]);

// Inject from parent
const form = inject('form');
const workflowParams = inject('workflowParams');
const errors = inject('errors');
const saveSetting = inject('saveSetting');
const saveSettingArray = inject('saveSettingArray');
const saveWorkflowParam = inject('saveWorkflowParam');
const clearError = inject('clearError');

const openDefaultWorkflowModal = () => {
    new bootstrap.Modal(document.getElementById('defaultWorkflowModal')).show();
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
