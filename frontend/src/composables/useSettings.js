import { reactive, watch, ref } from 'vue';
import { KNOWN_PLATFORMS } from '../constants/platforms';

// ===== 存储键名常量 =====
export const STORAGE = {
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
export const storage = {
    get: (k, def) => { const v = localStorage.getItem(k); return v === null ? def : v; },
    set: (k, v) => { localStorage.setItem(k, v); },
    getBool: (k, def) => { const v = localStorage.getItem(k); return v === null ? def : v === 'true'; },
    getNum: (k, def) => { const v = localStorage.getItem(k); return v ? Number(v) : def; },
    getNumOrNull: (k) => { const v = localStorage.getItem(k); return (v === null || v === '' || v === 'null') ? null : Number(v); },
};

// Import flag for config import
let _importingConfig = false;

export function useSettings() {
    // Default params from backend
    const defaultParams = reactive({
        chunk_size: 4000,
        concurrent: 5,
        temperature: 0.7,
        top_p: 0.9,
        retry: 3
    });

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

    const queue_concurrent = ref(3);

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

    // ===== Clear Error =====
    const clearError = (field) => {
        if (errors[field]) errors[field] = false;
    };

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
            target.glossary_agent_baseurl = plat === 'custom' ? get(`${prefix}_custom_base_url`) : plat;
        } else {
            target.api_key = get(`${prefix}_${plat}_apikey`);
            target.model_id = get(`${prefix}_${plat}_model_id`);
            target.base_url = plat === 'custom' ? get(`${prefix}_custom_base_url`) : plat;
        }
    };

    const saveSetting = (k, v) => localStorage.setItem(k, v);
    const saveSettingArray = (k, v) => localStorage.setItem(k, JSON.stringify(v));
    const saveWorkflowParam = (keySuffix) => {
        const wfType = form.workflow_type;
        if (workflowParams[wfType] && workflowParams[wfType][keySuffix] !== undefined) {
            localStorage.setItem(`translator_${wfType}_${keySuffix}`, workflowParams[wfType][keySuffix]);
        }
    };

    // ===== Platform Watch =====
    const setupPlatformWatchers = () => {
        watch(() => form.platform, (newPlat) => {
            if (_importingConfig) return;
            updatePlatformParams(newPlat, 'translator_platform', form);
            saveSetting(STORAGE.keys.PLATFORM, newPlat);
            loadPlatformConfig();
        });

        watch(() => form.glossary_agent_platform, (newPlat) => {
            if (_importingConfig) return;
            updatePlatformParams(newPlat, 'glossary_agent_platform', form, true);
            saveSetting('glossary_agent_platform_last_platform', newPlat);
            loadGlossaryConfig(defaultParams);
        });
    };

    // ===== Config Import/Export =====
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

    const importConfig = (e, t) => {
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

    // ===== Default Workflow =====
    const DEFAULT_EXTENSIONS = ['pdf','png','jpg','jpeg','gif','bmp','webp','txt','md','docx','doc','xlsx','csv','xls','epub','pptx','ppt','srt','ass','json','html','htm'];

    const saveDefaultWorkflows = () => {
        localStorage.setItem('default_workflows', JSON.stringify(default_workflows));
        // Build ALL_EXTENSIONS from default_workflows keys
        const allExts = new Set([...DEFAULT_EXTENSIONS]);
        Object.keys(default_workflows).forEach(ext => allExts.add(ext));
        const custom = [...allExts].filter(ext => !DEFAULT_EXTENSIONS.includes(ext));
        localStorage.setItem('custom_extensions', JSON.stringify(custom));
    };

    return {
        // State
        form,
        workflowParams,
        errors,
        defaultParams,
        default_workflows,
        queue_concurrent,

        // Methods
        clearError,
        loadConfig,
        loadMainConfig,
        loadPlatformConfig,
        loadGlossaryConfig,
        loadWorkflowParams,
        loadDefaultWorkflows,
        saveSetting,
        saveSettingArray,
        saveWorkflowParam,
        saveAllSettings,
        saveMainConfig,
        saveGlossaryConfig,
        saveWorkflowParamsConfig,
        updatePlatformParams,
        setupPlatformWatchers,
        exportConfig,
        importConfig,
        saveDefaultWorkflows,

        // Constants
        STORAGE,
        storage,
        DEFAULT_EXTENSIONS,
    };
}
