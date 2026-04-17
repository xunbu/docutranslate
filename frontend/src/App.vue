<template>
<div>
    <div class="container-fluid main-container">
        <div class="row gx-4">
            <!-- Left: Settings Panel -->
            <div class="col-lg-4">
                <SettingsPanel
                    :t="t"
                    :form="form"
                    :workflowParams="workflowParams"
                    :errors="errors"
                    :enginList="enginList"
                    :showMineruToken="showMineruToken"
                    :showIdentityOption="showIdentityOption"
                    :glossaryCount="glossaryCount"
                    :version="version"
                    :stepMap="stepMap"
                    :defaultParams="defaultParams"
                    @update:showMineruToken="val => showMineruToken = val"
                    @saveSetting="saveSetting"
                    @saveSettingArray="saveSettingArray"
                    @saveWorkflowParam="saveWorkflowParam"
                    @clearError="clearError"
                    @openDefaultWorkflowModal="openDefaultWorkflowModal"
                    @openGlossaryModal="openGlossaryModal"
                    @handleGlossaryFiles="handleGlossaryFiles"
                    @clearGlossary="clearGlossary"
                    @downloadGlossaryTemplate="downloadGlossaryTemplate"
                    @importConfig="importConfig"
                    @exportConfig="exportConfig" />
            </div>

            <!-- Right: Task Area -->
            <div class="col-lg-8">
                <TaskArea
                    :t="t"
                    :tasks="tasks"
                    :hasPendingTasks="hasPendingTasks"
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
    <GlossaryModal :t="t" :glossaryData="glossaryData" />
    <DefaultWorkflowModal
        :t="t"
        :defaultWorkflows="default_workflows"
        @update:defaultWorkflows="val => Object.assign(default_workflows, val)"
        @save="saveDefaultWorkflows" />
    <TutorialModal :t="t" />
    <ContributorsModal :t="t" />
    <QueueSettingsModal
        :t="t"
        :queueConcurrent="queue_concurrent"
        @update:queueConcurrent="val => queue_concurrent = val"
        @save="val => saveSetting('queue_concurrent', val)" />

    <!-- Preview Offcanvas -->
    <PreviewOffcanvas
        ref="previewOffcanvasComponent"
        :t="t"
        :previewMode="previewMode"
        :syncScrollEnabled="syncScrollEnabled"
        :previewTask="previewTask"
        @setPreviewMode="setPreviewMode"
        @toggleSyncScroll="toggleSyncScroll"
        @printPdf="printPdf" />
    <iframe id="printFrame" ref="printFrame" style="display: none;"></iframe>

    <!-- Bottom Controls -->
    <BottomControls
        :currentLang="currentLang"
        @setLang="setLang"
        @setTheme="setTheme" />
</div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, nextTick } from 'vue';
import SliderControl from './components/common/SliderControl.vue';
import PlatformSelector from './components/common/PlatformSelector.vue';
import TutorialModal from './components/modals/TutorialModal.vue';
import ContributorsModal from './components/modals/ContributorsModal.vue';
import QueueSettingsModal from './components/modals/QueueSettingsModal.vue';
import GlossaryModal from './components/modals/GlossaryModal.vue';
import DefaultWorkflowModal from './components/modals/DefaultWorkflowModal.vue';
import SettingsPanel from './components/settings/SettingsPanel.vue';
import TaskArea from './components/tasks/TaskArea.vue';
import PreviewOffcanvas from './components/preview/PreviewOffcanvas.vue';
import BottomControls from './components/layout/BottomControls.vue';
import { mineruLangOptions } from './constants/mineruLanguages';
import { KNOWN_PLATFORMS } from './constants/platforms';
import { emptyToNull, capitalize, getFileIcon } from './utils/helpers';

// ===== 存储键名常量 =====
const STORAGE = {
    keys: {
        WORKFLOW: 'translator_last_workflow',
        ENGINE: 'translator_convert_engin',
        MD2DOCX: 'translator_md2docx_engine',
        PLATFORM: 'translator_platform_last_platform',
        CHUNK_SIZE: 'chunk_size',
        CONCURRENT: 'concurrent',
        TEMPERATURE: 'temperature',
        TOP_P: 'top_p',
        RETRY: 'retry',
        RPM: 'rpm',
        TPM: 'tpm',
        EXTRA_BODY: 'extra_body',
        CUSTOM_PROMPT: 'custom_prompt',
        QUEUE_CONCURRENT: 'queue_concurrent',
        ACTIVE_TASK_IDS: 'active_task_ids',
        UI_LANGUAGE: 'ui_language',
        UI_SYNC_SCROLL: 'ui_sync_scroll_enabled',
        THEME: 'theme',
        DEFAULT_WORKFLOWS: 'default_workflows',
        CUSTOM_EXTENSIONS: 'custom_extensions',
    },
    prefix: (name, platform, suffix) => `${name}_${platform}_${suffix}`,
};

// ===== 存储工具 =====
const storage = {
    get: (k, def) => { const v = localStorage.getItem(k); return v === null ? def : v; },
    set: (k, v) => { localStorage.setItem(k, v); },
    getBool: (k, def) => { const v = localStorage.getItem(k); return v === null ? def : v === 'true'; },
    getNum: (k, def) => { const v = localStorage.getItem(k); return v ? Number(v) : def; },
    getNumOrNull: (k) => { const v = localStorage.getItem(k); return (v === null || v === '' || v === 'null') ? null : Number(v); },
};

const version = ref("");
const currentLang = ref(localStorage.getItem('ui_language') || 'zh');
const i18nData = ref({});
const glossaryData = ref({});
const tasks = ref([]);
const enginList = ref([]);
const defaultParams = reactive({
    chunk_size: 4000,
    concurrent: 5,
    temperature: 0.7,
    top_p: 0.9,
    retry: 3
});

// Refs for DOM elements
const glossaryInput = ref(null);
const configFile = ref(null);
const folderInput = ref(null);
const previewOffcanvas = ref(null);
const previewOffcanvasComponent = ref(null);

// UI State
const showMineruToken = ref(false);
const previewMode = ref('bilingual');
const syncScrollEnabled = ref(localStorage.getItem('ui_sync_scroll_enabled') === 'true');
const showIdentityOption = ref(true);

// Validation State
const errors = reactive({
    model_id: false,
    api_key: false,
    base_url: false,
    mineru_token: false,
    mineru_deploy_base_url: false,
    custom_to_lang: false,
    json_paths: false
});

const clearError = (field) => {
    if (errors[field]) errors[field] = false;
};

// Form Data
const form = reactive({
    workflow_type: 'markdown_based',
    convert_engine: 'mineru',
    md2docx_engine: 'auto',
    mineru_token: '',
    model_version: 'vlm',
    mineru_language: 'ch',
    mineru_deploy_base_url: 'http://127.0.0.1:8000',
    mineru_deploy_backend: 'hybrid-auto-engine',
    mineru_deploy_parse_method: 'auto',
    mineru_deploy_start_page: 0,
    mineru_deploy_end_page: 99999,
    mineru_deploy_formula_enable: true,
    mineru_deploy_table_enable: true,
    mineru_deploy_lang_list: [],
    mineru_deploy_server_url: '',
    formula_ocr: true,
    code_ocr: true,
    skip_translate: false,
    platform: 'https://api.302.ai/v1',
    base_url: '',
    api_key: '',
    model_id: '',
    provider: 'api.openai.com',
    system_proxy_enable: false,
    force_json: false,
    to_lang: 'Simplified Chinese',
    custom_to_lang: '',
    thinking: 'disable',
    custom_prompt: '',
    chunk_size: 4000,
    concurrent: 30,
    temperature: 0.7,
    top_p: 0.9,
    retry: 2,
    rpm: null,
    tpm: null,
    extra_body: '',
    glossary_generate_enable: false,
    glossary_agent_custom_prompt: '',
    glossary_agent_config_choice: 'same',
    glossary_agent_platform: 'https://api.302.ai/v1',
    glossary_agent_baseurl: '',
    glossary_agent_key: '',
    glossary_agent_model_id: '',
    glossary_agent_provider: 'api.openai.com',
    glossary_agent_to_lang: 'Simplified Chinese',
    glossary_agent_custom_to_lang: '',
    glossary_agent_chunk_size: 4000,
    glossary_agent_concurrent: 30,
    glossary_agent_temperature: 0.7,
    glossary_agent_top_p: 0.9,
    glossary_agent_retry: 2,
    glossary_agent_thinking: 'default',
    glossary_agent_system_proxy_enable: false,
    glossary_agent_force_json: false,
    glossary_agent_rpm: null,
    glossary_agent_tpm: null,
    glossary_agent_extra_body: ''
});

// Default workflows per file extension
const default_workflows = reactive({
    pdf: 'markdown_based', png: 'markdown_based', jpg: 'markdown_based', jpeg: 'markdown_based',
    gif: 'markdown_based', bmp: 'markdown_based', webp: 'markdown_based',
    txt: 'txt', md: 'markdown_based',
    docx: 'docx', doc: 'docx',
    xlsx: 'xlsx', csv: 'xlsx', xls: 'xlsx',
    epub: 'epub',
    pptx: 'pptx', ppt: 'pptx',
    srt: 'srt', ass: 'ass',
    json: 'json', html: 'html', htm: 'html'
});

const workflowLabels = {
    markdown_based: 'Markdown', txt: 'TXT', docx: 'DOCX', xlsx: 'XLSX',
    epub: 'EPUB', pptx: 'PPTX', srt: 'SRT', ass: 'ASS', json: 'JSON', html: 'HTML'
};
const getWorkflowLabel = (wf) => workflowLabels[wf] || wf;

const queue_concurrent = ref(3);
const runningCount = ref(0);

// Nested Params for specific workflows
const workflowParams = reactive({
    txt: {insert_mode: 'replace', separator: '\\n', segment_mode: 'line'},
    xlsx: {insert_mode: 'replace', separator: '\\n', translate_regions: ''},
    docx: {insert_mode: 'replace', separator: ''},
    srt: {insert_mode: 'replace', separator: '\\n'},
    epub: {insert_mode: 'replace', separator: ''},
    html: {insert_mode: 'replace', separator: ''},
    ass: {insert_mode: 'replace', separator: '\\n'},
    json: {json_paths: ''},
    pptx: {insert_mode: 'replace', separator: '\\n'}
});

// ===== 加载配置 - 拆分为子函数 =====
const loadMainConfig = (defaults) => {
    form.workflow_type = storage.get(STORAGE.keys.WORKFLOW, 'markdown_based');
    form.convert_engine = storage.get(STORAGE.keys.ENGINE, 'mineru');
    const md2docxVal = storage.get(STORAGE.keys.MD2DOCX, 'auto');
    form.md2docx_engine = md2docxVal === 'null' ? null : md2docxVal;
    form.mineru_token = storage.get('translator_mineru_token', '');
    form.model_version = storage.get('translator_model_version', 'vlm');
    form.mineru_language = storage.get('translator_mineru_language', 'ch');
    form.mineru_deploy_base_url = storage.get('mineru_deploy_base_url', 'http://127.0.0.1:8000');
    form.mineru_deploy_backend = storage.get('mineru_deploy_backend', 'hybrid-auto-engine');
    form.mineru_deploy_parse_method = storage.get('mineru_deploy_parse_method', 'auto');
    form.mineru_deploy_start_page = storage.getNum('mineru_deploy_start_page', 0);
    form.mineru_deploy_end_page = storage.getNum('mineru_deploy_end_page', 99999);
    form.mineru_deploy_formula_enable = storage.getBool('mineru_deploy_formula_enable', true);
    form.mineru_deploy_table_enable = storage.getBool('mineru_deploy_table_enable', true);
    form.mineru_deploy_server_url = storage.get('mineru_deploy_server_url', '');
    const savedLangList = localStorage.getItem('mineru_deploy_lang_list');
    form.mineru_deploy_lang_list = savedLangList ? JSON.parse(savedLangList) : [];
    form.formula_ocr = storage.getBool('translator_formula_ocr', true);
    form.code_ocr = storage.getBool('translator_code_ocr', true);
    form.skip_translate = storage.getBool('translator_skip_translate', false);
    form.platform = storage.get(STORAGE.keys.PLATFORM, 'https://api.302.ai/v1');
    form.system_proxy_enable = storage.getBool('translator_system_proxy_enable', defaults.system_proxy_enable ?? false);
    form.force_json = storage.getBool('translator_force_json', false);
    form.to_lang = storage.get('translator_to_lang', 'Simplified Chinese');
    form.custom_to_lang = storage.get('translator_custom_to_lang', '');
    form.thinking = storage.get('translator_thinking_mode', defaults.thinking ?? 'disable');
    form.custom_prompt = storage.get(STORAGE.keys.CUSTOM_PROMPT, '');
    form.chunk_size = storage.getNum(STORAGE.keys.CHUNK_SIZE, defaults.chunk_size ?? 4000);
    form.concurrent = storage.getNum(STORAGE.keys.CONCURRENT, defaults.concurrent ?? 30);
    form.temperature = storage.getNum(STORAGE.keys.TEMPERATURE, defaults.temperature ?? 0.7);
    form.top_p = storage.getNum(STORAGE.keys.TOP_P, defaults.top_p ?? 0.9);
    form.retry = storage.getNum(STORAGE.keys.RETRY, defaults.retry ?? 2);
    form.rpm = storage.getNumOrNull(STORAGE.keys.RPM);
    form.tpm = storage.getNumOrNull(STORAGE.keys.TPM);
    form.extra_body = storage.get(STORAGE.keys.EXTRA_BODY, defaults.extra_body ?? '');
};

const loadPlatformConfig = () => {
    const platObj = KNOWN_PLATFORMS.find(p => p.val === form.platform);
    if (form.platform === 'custom') {
        form.provider = storage.get('translator_platform_custom_provider', 'default');
    } else {
        form.provider = platObj ? platObj.provider : '';
    }
};

const loadGlossaryConfig = (defaults) => {
    form.glossary_generate_enable = storage.getBool('glossary_generate_enable', false);
    form.glossary_agent_custom_prompt = storage.get('glossary_agent_custom_prompt', '');
    form.glossary_agent_config_choice = storage.get('glossary_agent_config_choice', 'same');
    form.glossary_agent_platform = storage.get('glossary_agent_platform_last_platform', 'https://api.302.ai/v1');
    form.glossary_agent_to_lang = storage.get('glossary_agent_to_lang', 'Simplified Chinese');
    form.glossary_agent_custom_to_lang = storage.get('glossary_agent_custom_to_lang', '');
    form.glossary_agent_chunk_size = storage.getNum('glossary_agent_chunk_size', defaults.chunk_size ?? 1000);
    form.glossary_agent_concurrent = storage.getNum('glossary_agent_concurrent', defaults.concurrent ?? 5);
    form.glossary_agent_temperature = storage.getNum('glossary_agent_temperature', defaults.temperature ?? 0.7);
    form.glossary_agent_top_p = storage.getNum('glossary_agent_top_p', 0.9);
    form.glossary_agent_retry = storage.getNum('glossary_agent_retry', defaults.retry ?? 3);
    form.glossary_agent_thinking = storage.get('glossary_agent_thinking_mode', defaults.thinking ?? 'default');
    form.glossary_agent_system_proxy_enable = storage.getBool('glossary_agent_system_proxy_enable', defaults.system_proxy_enable ?? false);
    form.glossary_agent_force_json = storage.getBool('glossary_agent_force_json', false);
    form.glossary_agent_rpm = storage.getNumOrNull('glossary_agent_rpm');
    form.glossary_agent_tpm = storage.getNumOrNull('glossary_agent_tpm');
    form.glossary_agent_extra_body = storage.get('glossary_agent_extra_body', defaults.extra_body ?? '');

    const gPlatObj = KNOWN_PLATFORMS.find(p => p.val === form.glossary_agent_platform);
    if (form.glossary_agent_platform === 'custom') {
        form.glossary_agent_provider = storage.get('glossary_agent_platform_custom_provider', 'default');
    } else {
        form.glossary_agent_provider = gPlatObj ? gPlatObj.provider : '';
    }
};

const loadWorkflowParams = () => {
    ['txt', 'xlsx', 'docx', 'srt', 'epub', 'html', 'ass', 'pptx'].forEach(t => {
        workflowParams[t].insert_mode = storage.get(`translator_${t}_insert_mode`, 'replace');
        if (workflowParams[t].separator !== undefined)
            workflowParams[t].separator = storage.get(`translator_${t}_separator`, workflowParams[t].separator);
    });
    workflowParams.txt.segment_mode = storage.get('translator_txt_segment_mode', 'line');
    workflowParams.xlsx.translate_regions = storage.get('translator_xlsx_translate_regions', '');
    workflowParams.json.json_paths = storage.get('translator_json_paths', '');
};

const loadDefaultWorkflows = () => {
    const saved = localStorage.getItem(STORAGE.keys.DEFAULT_WORKFLOWS);
    if (saved) {
        try { Object.assign(default_workflows, JSON.parse(saved)); } catch(e) {}
    }
    const savedCustom = localStorage.getItem(STORAGE.keys.CUSTOM_EXTENSIONS);
    if (savedCustom) {
        try {
            const parsed = JSON.parse(savedCustom);
            if (Array.isArray(parsed)) {
                parsed.forEach(ext => {
                    if (!default_workflows[ext]) default_workflows[ext] = 'markdown_based';
                });
            }
        } catch(e) {}
    }
};

const loadConfig = (defaults = {}) => {
    loadMainConfig(defaults);
    loadPlatformConfig();
    loadGlossaryConfig(defaults);
    loadWorkflowParams();
    loadDefaultWorkflows();

    // Load queue concurrent
    const savedQueueConcurrent = localStorage.getItem(STORAGE.keys.QUEUE_CONCURRENT);
    if (savedQueueConcurrent) queue_concurrent.value = Number(savedQueueConcurrent) || 3;

    // Trigger platform updates to load API keys/models
    updatePlatformParams(form.platform, 'translator_platform', form);
    updatePlatformParams(form.glossary_agent_platform, 'glossary_agent_platform', form, true);
};

// ===== 保存配置 - 拆分为子函数 =====
const saveMainConfig = () => {
    const f = form;
    storage.set(STORAGE.keys.WORKFLOW, f.workflow_type);
    storage.set(STORAGE.keys.ENGINE, f.convert_engine);
    storage.set(STORAGE.keys.MD2DOCX, f.md2docx_engine);
    storage.set('translator_mineru_token', f.mineru_token);
    storage.set('translator_model_version', f.model_version);
    storage.set('translator_mineru_language', f.mineru_language);
    storage.set('mineru_deploy_base_url', f.mineru_deploy_base_url);
    storage.set('mineru_deploy_backend', f.mineru_deploy_backend);
    storage.set('mineru_deploy_parse_method', f.mineru_deploy_parse_method);
    storage.set('mineru_deploy_start_page', f.mineru_deploy_start_page);
    storage.set('mineru_deploy_end_page', f.mineru_deploy_end_page);
    storage.set('mineru_deploy_formula_enable', f.mineru_deploy_formula_enable);
    storage.set('mineru_deploy_table_enable', f.mineru_deploy_table_enable);
    storage.set('mineru_deploy_server_url', f.mineru_deploy_server_url);
    storage.set('mineru_deploy_lang_list', JSON.stringify(f.mineru_deploy_lang_list));
    storage.set('translator_formula_ocr', f.formula_ocr);
    storage.set('translator_code_ocr', f.code_ocr);
    storage.set('translator_skip_translate', f.skip_translate);
    storage.set(STORAGE.keys.PLATFORM, f.platform);
    storage.set('translator_system_proxy_enable', f.system_proxy_enable);
    storage.set('translator_force_json', f.force_json);
    storage.set('translator_to_lang', f.to_lang);
    storage.set('translator_custom_to_lang', f.custom_to_lang);
    storage.set('translator_thinking_mode', f.thinking);
    storage.set(STORAGE.keys.CUSTOM_PROMPT, f.custom_prompt);
    storage.set(STORAGE.keys.CHUNK_SIZE, f.chunk_size);
    storage.set(STORAGE.keys.CONCURRENT, f.concurrent);
    storage.set(STORAGE.keys.TEMPERATURE, f.temperature);
    storage.set(STORAGE.keys.TOP_P, f.top_p);
    storage.set(STORAGE.keys.RETRY, f.retry);
    storage.set(STORAGE.keys.RPM, f.rpm || '');
    storage.set(STORAGE.keys.TPM, f.tpm || '');
    storage.set(STORAGE.keys.EXTRA_BODY, f.extra_body || '');
    // 平台相关
    storage.set(`translator_platform_${f.platform}_apikey`, f.api_key);
    storage.set(`translator_platform_${f.platform}_model_id`, f.model_id);
    storage.set('translator_provider', f.provider);
    if (f.platform === 'custom') storage.set('translator_platform_custom_base_url', f.base_url);
};

const saveGlossaryConfig = () => {
    const f = form;
    storage.set('glossary_generate_enable', f.glossary_generate_enable);
    storage.set('glossary_agent_custom_prompt', f.glossary_agent_custom_prompt);
    storage.set('glossary_agent_config_choice', f.glossary_agent_config_choice);
    storage.set('glossary_agent_platform_last_platform', f.glossary_agent_platform);
    storage.set('glossary_agent_to_lang', f.glossary_agent_to_lang);
    storage.set('glossary_agent_custom_to_lang', f.glossary_agent_custom_to_lang);
    storage.set('glossary_agent_chunk_size', f.glossary_agent_chunk_size);
    storage.set('glossary_agent_concurrent', f.glossary_agent_concurrent);
    storage.set('glossary_agent_temperature', f.glossary_agent_temperature);
    storage.set('glossary_agent_top_p', f.glossary_agent_top_p);
    storage.set('glossary_agent_retry', f.glossary_agent_retry);
    storage.set('glossary_agent_thinking_mode', f.glossary_agent_thinking);
    storage.set('glossary_agent_system_proxy_enable', f.glossary_agent_system_proxy_enable);
    storage.set('glossary_agent_force_json', f.glossary_agent_force_json);
    storage.set('glossary_agent_rpm', f.glossary_agent_rpm || '');
    storage.set('glossary_agent_tpm', f.glossary_agent_tpm || '');
    storage.set('glossary_agent_extra_body', f.glossary_agent_extra_body || '');
    // 术语表平台 Key
    storage.set(`glossary_agent_platform_${f.glossary_agent_platform}_apikey`, f.glossary_agent_key);
    storage.set(`glossary_agent_platform_${f.glossary_agent_platform}_model_id`, f.glossary_agent_model_id);
    storage.set('glossary_agent_provider', f.glossary_agent_provider);
    if (f.glossary_agent_platform === 'custom') storage.set('glossary_agent_platform_custom_base_url', f.glossary_agent_baseurl);
};

const saveWorkflowParamsConfig = () => {
    for (const [wfType, params] of Object.entries(workflowParams)) {
        for (const [key, val] of Object.entries(params)) {
            storage.set(`translator_${wfType}_${key}`, val);
        }
    }
};

const saveAllSettings = () => {
    saveMainConfig();
    saveGlossaryConfig();
    saveWorkflowParamsConfig();
};

const updatePlatformParams = (plat, prefix, target, isGlossary = false) => {
    const get = (k) => localStorage.getItem(k) || '';
    if (isGlossary) {
        target.glossary_agent_key = get(`${prefix}_${plat}_apikey`);
        target.glossary_agent_model_id = get(`${prefix}_${plat}_model_id`);
        if (plat === 'custom')
            target.glossary_agent_baseurl = get(`${prefix}_custom_base_url`);
    } else {
        target.api_key = get(`${prefix}_${plat}_apikey`);
        target.model_id = get(`${prefix}_${plat}_model_id`);
        if (plat === 'custom')
            target.base_url = get(`${prefix}_custom_base_url`);
    }
};

watch(() => form.platform, (newPlat) => {
    updatePlatformParams(newPlat, 'translator_platform', form);
    saveSetting(STORAGE.keys.PLATFORM, newPlat);
    loadPlatformConfig();
});
watch(() => form.glossary_agent_platform, (newPlat) => {
    updatePlatformParams(newPlat, 'glossary_agent_platform', form, true);
    saveSetting('glossary_agent_platform_last_platform', newPlat);
    loadGlossaryConfig(defaultParams);
});

// ===== 工作流配置：动态计算当前工作流的配置 =====
const WORKFLOW_CONFIGS = {
    markdown_based: {hasInsertMode: false},
    txt: {hasInsertMode: true, insertHelpKey: 'insertModeHelpTxtTxt', separatorPlaceholderKey: 'separatorPlaceholderLineBreak'},
    docx: {hasInsertMode: true, insertHelpKey: 'insertModeHelpTxtDocx'},
    xlsx: {hasInsertMode: true, insertHelpKey: 'insertModeHelpTxtXlsx'},
    epub: {hasInsertMode: true, insertHelpKey: 'insertModeHelpTxtEpub'},
    html: {hasInsertMode: true, insertHelpKey: 'insertModeHelpTxtHtml'},
    srt: {hasInsertMode: true, insertHelpKey: 'insertModeHelpTxtSrt', separatorPlaceholderKey: 'separatorPlaceholderLineBreak'},
    ass: {hasInsertMode: true, insertHelpKey: 'insertModeHelpTxtSrt', separatorPlaceholderKey: 'separatorPlaceholderLineBreak'},
    json: {hasInsertMode: false},
    pptx: {hasInsertMode: true, insertHelpKey: 'insertModeHelpTxtPptx', separatorPlaceholderKey: 'separatorPlaceholderLineBreak'}
};
const currentWorkflowConfig = computed(() => WORKFLOW_CONFIGS[form.workflow_type]);

// ===== OCR 选项 =====
const ocrOptions = computed(() => ({
    showFormula: ['mineru', 'mineru_deploy'].includes(form.convert_engine),
    showCode: ['mineru', 'mineru_deploy'].includes(form.convert_engine)
}));

// ===== Step Map: 根据 skip_translate 动态调整步骤编号 =====
const stepMap = computed(() => ({
    ai: form.skip_translate ? 2 : 2,
    trans: form.skip_translate ? -1 : 3,
    glossary: form.skip_translate ? 3 : 4
}));

const glossaryCount = computed(() => Object.keys(glossaryData.value).length);

const saveSetting = (k, v) => localStorage.setItem(k, v);
const saveSettingArray = (k, v) => localStorage.setItem(k, JSON.stringify(v));
const saveWorkflowParam = (keySuffix) => {
    const wfType = form.workflow_type;
    if (workflowParams[wfType] && workflowParams[wfType][keySuffix] !== undefined) {
        localStorage.setItem(`translator_${wfType}_${keySuffix}`, workflowParams[wfType][keySuffix]);
    }
};

// ===== 术语表相关 =====
const handleGlossaryFiles = (e) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;

    files.forEach(file => {
        const reader = new FileReader();
        reader.onload = (ev) => {
            const text = ev.target.result;
            const lines = text.split(/\r?\n/);
            lines.forEach(line => {
                const parts = line.split(',');
                if (parts.length >= 2) {
                    const key = parts[0].trim();
                    const val = parts.slice(1).join(',').trim();
                    if (key && val) glossaryData.value[key] = val;
                }
            });
        };
        reader.readAsText(file);
    });
    e.target.value = '';
};

const clearGlossary = () => { glossaryData.value = {}; };
const openGlossaryModal = () => new bootstrap.Modal(document.getElementById('glossaryModal')).show();
const downloadGlossaryTemplate = () => {
    const content = 'source,target\nHello,你好\nWorld,世界';
    const blob = new Blob([content], {type: 'text/csv'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'glossary_template.csv';
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 100);
};

// ===== 任务管理 =====
let _importingConfig = false;
let _taskIdCounter = 0;

const createNewTask = (backendId = null) => {
    const task = reactive({
        uiId: 'card_' + (++_taskIdCounter),
        backendId: backendId,
        file: null,
        fileName: '',
        logs: '',
        statusMessage: '',
        statusClass: 'text-muted',
        isTranslating: false,
        isFinished: false,
        isProcessing: false,
        validationError: false,
        downloads: null,
        attachment: null,
        initializing: !!backendId,
        isDragOver: false,
        progressPercent: 0,
        detectedWorkflow: null
    });
    tasks.value.unshift(task);
    if (backendId) {
        fetch(`/service/task/${backendId}`).then(r => r.json()).then(d => {
            if (d.file_name) task.fileName = d.file_name;
            task.initializing = false;
        }).catch(() => {
            task.initializing = false;
        });
    }
};

const removeTask = async (task) => {
    if (task.isTranslating) {
        if (!confirm(t('confirmRemoveTranslatingTask'))) return;
        try { await toggleTaskState(task); } catch (e) {}
    }
    const idx = tasks.value.indexOf(task);
    if (idx >= 0) tasks.value.splice(idx, 1);
};

const clearAllTasks = async () => {
    if (!confirm(t('confirmClearAllTasks'))) return;
    for (const task of [...tasks.value]) {
        if (task.isTranslating) {
            try { await toggleTaskState(task); } catch(e) {}
        }
    }
    tasks.value = [];
};

const handleTaskFileSelect = (e, task) => {
    const f = e.target.files[0];
    if (!f) return;
    task.file = f;
    task.fileName = f.name;
    task.logs = '';
    task.statusMessage = '';
    task.statusClass = 'text-muted';
    task.isFinished = false;
    task.isProcessing = false;
    task.downloads = null;
    task.attachment = null;
    task.validationError = false;
    task.progressPercent = 0;

    const ext = f.name.split('.').pop().toLowerCase();
    const newWorkflow = default_workflows[ext] || 'markdown_based';
    form.workflow_type = newWorkflow;
    task.detectedWorkflow = newWorkflow;
    saveSetting('translator_last_workflow', newWorkflow);

    e.target.value = '';
};
const handleTaskFileDrop = (e, task) => handleTaskFileSelect(e, task);

const triggerFileInput = (uiId) => {
    const el = document.getElementById('fileInput-' + uiId);
    if (el) el.click();
};

const selectTaskWorkflow = (task) => {
    if (task.detectedWorkflow) {
        form.workflow_type = task.detectedWorkflow;
        saveSetting('translator_last_workflow', task.detectedWorkflow);
    }
};

watch(tasks, (newTasks) => {
    const ids = newTasks.map(t => t.backendId).filter(Boolean);
    localStorage.setItem(STORAGE.keys.ACTIVE_TASK_IDS, JSON.stringify(ids));
}, {deep: true});

// ===== 翻译逻辑 =====
const buildFormData = (task) => {
    const fd = new FormData();

    fd.append('workflow', form.workflow_type);
    fd.append('convert_engine', form.convert_engine);
    fd.append('md2docx_engine', form.md2docx_engine || '');
    fd.append('skip_translate', form.skip_translate ? 'true' : 'false');

    if (!form.skip_translate) {
        fd.append('platform', form.platform);
        fd.append('base_url', form.base_url || '');
        fd.append('api_key', form.api_key);
        fd.append('model_id', form.model_id);
        fd.append('provider', form.provider || '');
        fd.append('system_proxy_enable', form.system_proxy_enable ? 'true' : 'false');
        fd.append('force_json', form.force_json ? 'true' : 'false');
        fd.append('to_lang', form.to_lang);
        fd.append('custom_to_lang', form.custom_to_lang || '');
        fd.append('thinking', form.thinking);
        fd.append('custom_prompt', form.custom_prompt || '');
        fd.append('chunk_size', String(form.chunk_size));
        fd.append('concurrent', String(form.concurrent));
        fd.append('temperature', String(form.temperature));
        fd.append('top_p', String(form.top_p));
        fd.append('retry', String(form.retry));
        if (form.rpm) fd.append('rpm', String(form.rpm));
        if (form.tpm) fd.append('tpm', String(form.tpm));
        if (form.extra_body) fd.append('extra_body', form.extra_body);

        fd.append('glossary_generate_enable', form.glossary_generate_enable ? 'true' : 'false');
        if (form.glossary_generate_enable) {
            fd.append('glossary_agent_config_choice', form.glossary_agent_config_choice);
            fd.append('glossary_agent_platform', form.glossary_agent_platform);
            fd.append('glossary_agent_baseurl', form.glossary_agent_baseurl || '');
            fd.append('glossary_agent_key', form.glossary_agent_key || '');
            fd.append('glossary_agent_model_id', form.glossary_agent_model_id || '');
            fd.append('glossary_agent_provider', form.glossary_agent_provider || '');
            fd.append('glossary_agent_to_lang', form.glossary_agent_to_lang);
            fd.append('glossary_agent_custom_to_lang', form.glossary_agent_custom_to_lang || '');
            fd.append('glossary_agent_chunk_size', String(form.glossary_agent_chunk_size));
            fd.append('glossary_agent_concurrent', String(form.glossary_agent_concurrent));
            fd.append('glossary_agent_temperature', String(form.glossary_agent_temperature));
            fd.append('glossary_agent_top_p', String(form.glossary_agent_top_p));
            fd.append('glossary_agent_retry', String(form.glossary_agent_retry));
            fd.append('glossary_agent_thinking', form.glossary_agent_thinking);
            fd.append('glossary_agent_system_proxy_enable', form.glossary_agent_system_proxy_enable ? 'true' : 'false');
            fd.append('glossary_agent_force_json', form.glossary_agent_force_json ? 'true' : 'false');
            if (form.glossary_agent_rpm) fd.append('glossary_agent_rpm', String(form.glossary_agent_rpm));
            if (form.glossary_agent_tpm) fd.append('glossary_agent_tpm', String(form.glossary_agent_tpm));
            if (form.glossary_agent_extra_body) fd.append('glossary_agent_extra_body', form.glossary_agent_extra_body);
        }
        if (Object.keys(glossaryData.value).length > 0) {
            fd.append('glossary', JSON.stringify(glossaryData.value));
        }
    }

    // Workflow-specific params
    const wp = workflowParams[form.workflow_type];
    if (wp) {
        if (wp.insert_mode !== undefined) fd.append('insert_mode', wp.insert_mode);
        if (wp.insert_mode !== undefined && ['append', 'prepend'].includes(wp.insert_mode) && wp.separator !== undefined)
            fd.append('separator', wp.separator);
        if (wp.segment_mode !== undefined) fd.append('segment_mode', wp.segment_mode);
        if (wp.translate_regions !== undefined) fd.append('translate_regions', wp.translate_regions);
        if (wp.json_paths !== undefined) fd.append('json_paths', wp.json_paths);
    }

    // Mineru specific
    if (form.convert_engine === 'mineru') {
        fd.append('mineru_token', form.mineru_token);
        fd.append('model_version', form.model_version);
        fd.append('mineru_language', form.mineru_language);
        fd.append('formula_ocr', form.formula_ocr ? 'true' : 'false');
        fd.append('code_ocr', form.code_ocr ? 'true' : 'false');
    } else if (form.convert_engine === 'mineru_deploy') {
        fd.append('mineru_deploy_base_url', form.mineru_deploy_base_url);
        fd.append('mineru_deploy_backend', form.mineru_deploy_backend);
        fd.append('mineru_deploy_parse_method', form.mineru_deploy_parse_method);
        fd.append('mineru_deploy_start_page', String(form.mineru_deploy_start_page));
        fd.append('mineru_deploy_end_page', String(form.mineru_deploy_end_page));
        fd.append('mineru_deploy_formula_enable', form.mineru_deploy_formula_enable ? 'true' : 'false');
        fd.append('mineru_deploy_table_enable', form.mineru_deploy_table_enable ? 'true' : 'false');
        fd.append('mineru_deploy_lang_list', JSON.stringify(form.mineru_deploy_lang_list));
        if (form.mineru_deploy_server_url)
            fd.append('mineru_deploy_server_url', form.mineru_deploy_server_url);
        fd.append('formula_ocr', form.formula_ocr ? 'true' : 'false');
        fd.append('code_ocr', form.code_ocr ? 'true' : 'false');
    }

    if (task.file) fd.append('file', task.file);
    saveAllSettings();
    return fd;
};

const validateTask = (task) => {
    let ok = true;
    if (!form.skip_translate) {
        if (!form.api_key) { errors.api_key = true; ok = false; }
        if (!form.model_id) { errors.model_id = true; ok = false; }
        if (form.platform === 'custom' && !form.base_url) { errors.base_url = true; ok = false; }
        if (form.to_lang === 'custom' && !form.custom_to_lang) { errors.custom_to_lang = true; ok = false; }
        if (form.workflow_type === 'json' && !workflowParams.json.json_paths) { errors.json_paths = true; ok = false; }
    }
    if (form.convert_engine === 'mineru' && !form.mineru_token) { errors.mineru_token = true; ok = false; }
    if (form.convert_engine === 'mineru_deploy' && !form.mineru_deploy_base_url) { errors.mineru_deploy_base_url = true; ok = false; }
    if (!task.file && !task.backendId) { task.validationError = true; ok = false; }
    return ok;
};

const appendLog = (task, msg, isError = false) => {
    const safe = (msg || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    task.logs += (task.logs ? '<br>' : '') + (isError ? `<span class="text-danger">${safe}</span>` : safe);
    nextTick(() => {
        const el = document.getElementById('log-' + task.uiId);
        if (el) el.scrollTop = el.scrollHeight;
    });
};

const toggleTaskState = async (task) => {
    if (task.initializing) return;
    if (task.isTranslating) {
        if (task.backendId) {
            try { await fetch(`/service/task/${task.backendId}/cancel`, {method: 'POST'}); } catch (e) {}
        }
        task.isTranslating = false;
        task.statusMessage = t('taskCardStatusCancelled');
        task.statusClass = 'text-warning';
        return;
    }

    if (!validateTask(task)) {
        appendLog(task, t('taskCardValidationFailed'), true);
        return;
    }

    task.isTranslating = true;
    task.isFinished = false;
    task.isProcessing = true;
    task.progressPercent = 0;
    task.statusMessage = t('taskCardStatusUploading');
    task.statusClass = 'text-primary';
    task.downloads = null;
    task.attachment = null;
    task.logs = '';

    try {
        if (task.backendId) {
            const resp = await fetch(`/service/task/${task.backendId}/restart`, {method: 'POST'});
            const data = await resp.json();
            if (!data.ok) throw new Error(data.error || 'Restart failed');
        } else {
            const fd = buildFormData(task);
            const resp = await fetch('/service/translate', {method: 'POST', body: fd});
            const data = await resp.json();
            if (!data.ok) throw new Error(data.error || 'Upload failed');
            task.backendId = data.task_id;
        }

        appendLog(task, t('taskCardStatusWaiting'));
        const poll = async () => {
            if (!task.isTranslating) return;
            try {
                const resp = await fetch(`/service/task/${task.backendId}`);
                const d = await resp.json();

                if (d.status_message) task.statusMessage = d.status_message;
                if (d.is_processing !== undefined) task.isProcessing = d.is_processing;
                if (d.progress_percent !== undefined) task.progressPercent = d.progress_percent;
                if (d.log) appendLog(task, d.log);
                if (d.original_filename) task.fileName = d.original_filename;

                if (d.is_processing) {
                    task.statusClass = 'text-primary';
                } else if (d.download_ready) {
                    task.downloads = d.downloads || {};
                    task.attachment = d.attachment || {};
                    task.isTranslating = false;
                    task.isFinished = true;
                    task.isProcessing = false;
                    task.statusMessage = t('taskCardStatusFinished');
                    task.statusClass = 'text-success';
                    return;
                } else if (d.error_flag) {
                    task.isTranslating = false;
                    task.isFinished = false;
                    task.isProcessing = false;
                    task.statusMessage = d.status_message || t('taskCardStatusError');
                    task.statusClass = 'text-danger';
                    return;
                }
            } catch (e) {
                appendLog(task, `Poll error: ${e.message}`, true);
            }
            setTimeout(poll, 1000);
        };
        poll();
    } catch (e) {
        task.isTranslating = false;
        task.isProcessing = false;
        task.statusMessage = t('taskCardStatusError');
        task.statusClass = 'text-danger';
        appendLog(task, `Error: ${e.message}`, true);
        throw e;
    }
};

// ===== Preview Logic =====
const splitInstance = ref(null);
const splitContainer = ref(null);
const originalPane = ref(null);
const translatedFrame = ref(null);
const previewTask = ref(null);

const initSplit = () => {
    if (splitInstance.value) {
        try { splitInstance.value.destroy(); } catch (e) {}
    }
    if (!splitContainer.value) return;
    splitInstance.value = new Split(splitContainer.value.children, {
        sizes: [50, 50],
        minSize: 100,
        gutterSize: 8,
        cursor: 'col-resize',
        direction: 'horizontal'
    });
};

let _syncScrollHandler = null;

const openPreview = (task) => {
    previewTask.value = task;
    if (!previewOffcanvas.value) return;
    const off = new bootstrap.Offcanvas(previewOffcanvas.value);
    off.show();
    previewOffcanvas.value.addEventListener('shown.bs.offcanvas', () => {
        initSplit();
        if (!task.downloads || !task.downloads.html) return;
        if (originalPane.value) originalPane.value.innerHTML = '';
        if (translatedFrame.value) {
            translatedFrame.value.src = 'about:blank';
            translatedFrame.value.onload = () => {
                fetch(task.downloads.html).then(r => r.text()).then(html => {
                    const doc = translatedFrame.value.contentWindow.document;
                    doc.open();
                    doc.write(html);
                    doc.close();
                    if (task.downloads.original_html) {
                        fetch(task.downloads.original_html).then(r2 => r2.text()).then(origHtml => {
                            if (originalPane.value) originalPane.value.innerHTML = origHtml;
                            if (syncScrollEnabled.value) {
                                if (_syncScrollHandler) window.removeEventListener('scroll', _syncScrollHandler, true);
                                _syncScrollHandler = (e) => {
                                    if (!syncScrollEnabled.value) return;
                                    const t = e.target;
                                    if (t === originalPane.value) {
                                        if (translatedFrame.value && translatedFrame.value.contentWindow)
                                            translatedFrame.value.contentWindow.scrollTo(0, t.scrollTop);
                                    } else if (t === translatedFrame.value?.contentWindow?.document?.scrollingElement) {
                                        if (originalPane.value)
                                            originalPane.value.scrollTop = translatedFrame.value.contentWindow.scrollY;
                                    }
                                };
                                if (originalPane.value)
                                    originalPane.value.addEventListener('scroll', _syncScrollHandler, true);
                                if (translatedFrame.value && translatedFrame.value.contentWindow)
                                    translatedFrame.value.contentWindow.addEventListener('scroll', _syncScrollHandler, true);
                            }
                        });
                    }
                });
            };
        }
    }, {once: true});
};

const setPreviewMode = (m) => {
    previewMode.value = m;
    nextTick(() => initSplit());
};

const toggleSyncScroll = () => {
    syncScrollEnabled.value = !syncScrollEnabled.value;
    localStorage.setItem('ui_sync_scroll_enabled', String(syncScrollEnabled.value));
};

const printPdf = (url) => {
    const pf = document.getElementById('printFrame');
    if (!pf) return;
    pf.onload = () => {
        pf.contentWindow.print();
    };
    pf.src = url;
};

const copyLog = (e, l) => {
    navigator.clipboard.writeText(l.replace(/<br>/g, '\n')).then(() => {
        const btn = e.currentTarget;
        const icon = btn.querySelector('i');
        btn.classList.replace('btn-outline-secondary', 'btn-success');
        icon.classList.replace('bi-clipboard', 'bi-check-lg');
        setTimeout(() => {
            btn.classList.replace('btn-success', 'btn-outline-secondary');
            icon.classList.replace('bi-check-lg', 'bi-clipboard');
        }, 2000);
    });
};

const exportConfig = () => {
    const config = {form: form, workflowParams: workflowParams};
    const blob = new Blob([JSON.stringify(config, null, 2)], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'config.json';
    a.click();
    setTimeout(() => {
        URL.revokeObjectURL(url);
    }, 100);
};
const importConfig = (e) => {
    const f = e.target.files[0];
    if (f) {
        const r = new FileReader();
        r.onload = (ev) => {
            try {
                const data = JSON.parse(ev.target.result);
                _importingConfig = true;
                if (data.form) Object.assign(form, data.form);
                if (data.workflowParams) Object.assign(workflowParams, data.workflowParams);
                _importingConfig = false;
                saveAllSettings();
                alert(t('configImportSuccess'));
            } catch (err) {
                _importingConfig = false;
                alert(t('configImportError'));
            }
        };
        r.readAsText(f);
    }
    e.target.value = '';
};

const setLang = (l) => {
    currentLang.value = l;
    localStorage.setItem('ui_language', l);
    document.documentElement.lang = l === 'zh' ? 'zh-CN' : 'en';
};
const setTheme = (t) => {
    localStorage.setItem('theme', t);
    if (t === 'auto') document.documentElement.setAttribute('data-bs-theme', window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    else document.documentElement.setAttribute('data-bs-theme', t);
};

// ===== Default workflow constants =====
const DEFAULT_EXTENSIONS = ['pdf','png','jpg','jpeg','gif','bmp','webp','txt','md','docx','doc','xlsx','csv','xls','epub','pptx','ppt','srt','ass','json','html','htm'];

const openDefaultWorkflowModal = () => new bootstrap.Modal(document.getElementById('defaultWorkflowModal')).show();
const saveDefaultWorkflows = () => {
    localStorage.setItem('default_workflows', JSON.stringify(default_workflows));
    // Build ALL_EXTENSIONS from default_workflows keys
    const allExts = new Set([...DEFAULT_EXTENSIONS]);
    Object.keys(default_workflows).forEach(ext => allExts.add(ext));
    const custom = [...allExts].filter(ext => !DEFAULT_EXTENSIONS.includes(ext));
    localStorage.setItem('custom_extensions', JSON.stringify(custom));
};

// Folder upload
const handleFolderSelect = (e) => {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;
    files.forEach(f => {
        const task = reactive({
            uiId: 'card_' + Math.random().toString(36).substring(2, 9),
            backendId: null, file: f, fileName: f.name, logs: '', statusMessage: '',
            statusClass: 'text-muted', isTranslating: false, isFinished: false, isProcessing: false,
            validationError: false, downloads: null, attachment: null, initializing: false, isDragOver: false,
            progressPercent: 0, detectedWorkflow: null
        });
        tasks.value.unshift(task);
        const ext = f.name.split('.').pop().toLowerCase();
        const newWorkflow = default_workflows[ext] || 'markdown_based';
        form.workflow_type = newWorkflow;
        task.detectedWorkflow = newWorkflow;
        saveSetting('translator_last_workflow', newWorkflow);
    });
    e.target.value = '';
};

// Batch run pending tasks - queue management
const pendingQueue = [];
const hasPendingTasks = computed(() => tasks.value.some(t => t.file && !t.isTranslating && !t.isFinished));

const startNextPendingTask = () => {
    const maxConcurrent = Math.max(1, queue_concurrent.value);
    while (pendingQueue.length > 0 && runningCount.value < maxConcurrent) {
        const task = pendingQueue.shift();
        if (task.file && !task.isTranslating && !t.isFinished) {
            runningCount.value++;
            toggleTaskState(task).finally(() => { startNextPendingTask(); });
        }
    }
};

const runAllPendingTasks = () => {
    const pending = tasks.value.filter(t => t.file && !t.isTranslating && !t.isFinished);
    pendingQueue.length = 0;
    pending.forEach((task, i) => {
        task.queuePosition = i + 1;
        task.queueTotal = pending.length;
        pendingQueue.push(task);
    });
    startNextPendingTask();
};

onMounted(async () => {
    // I18n
    try {
        const lang = currentLang.value || 'zh';
        const res = await fetch(`/static/i18n/${lang}.json`);
        i18nData.value = await res.json();

    } catch (e) {
        i18nData.value = {
            pageTitle: "DocuTranslate",
            tutorialBtn: "教程",
            projectContributeBtn: "项目协作",
            workflowTitle: "选择工作流",
            autoWorkflowLabel: "自动选择工作流",
            workflowOptionPptx: "PPTX 演示文稿",
            pptxSettingsTitleText: "PPTX 设置",
            mineruDeployServerUrlLabel: "Server URL",
            mineruDeployLangListLabel: "语言列表 (Pipeline模式)",
            mineruDeployServerUrlPlaceholder: "http://127.0.0.1:30000",
            mineruDeployParseMethodLabel: "解析方法 (Parse Method)",
            mineruDeployTableEnableLabel: "表格识别 (Table Recognition)"
        };
    }

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
    setTheme(localStorage.getItem('theme') || 'auto');

    // Restore tasks
    if (window.location.pathname.includes('/admin')) {
        document.title = "DocuTranslate - Admin Panel";
        try {
            const r = await fetch('/service/task-list');
            const ids = await r.json();
            if (ids) ids.reverse().forEach(id => createNewTask(id));
        } catch (e) {
        }
    } else {
        const savedIds = JSON.parse(localStorage.getItem('active_task_ids') || '[]');
        if (savedIds.length) savedIds.forEach(id => createNewTask(id));
        else createNewTask();
    }

    new bootstrap.Tooltip(document.body, {selector: '[data-bs-toggle="tooltip"]'});

    // Global resize handler for preview
    window.addEventListener('resize', () => {
        if (document.getElementById('previewOffcanvas')?.classList.contains('show')) {
            initSplit();
        }
    });

    // Expose preview refs to PreviewOffcanvas component
    watch(previewOffcanvasComponent, (comp) => {
        if (comp) {
            // Expose the refs to the component
            previewOffcanvas.value = comp.previewOffcanvas;
            splitContainer.value = comp.splitContainer;
            originalPane.value = comp.originalPane;
            translatedFrame.value = comp.translatedFrame;
        }
    }, {flush: 'post'});
});

const t = (k, params) => {
    let v = i18nData.value[k] || k;
    if (params) {
        for (const [key, val] of Object.entries(params)) {
            v = v.replace(new RegExp(`\\{${key}\\}`, 'g'), String(val));
        }
    }
    return v;
};
</script>
