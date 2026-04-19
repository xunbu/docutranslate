import { ref, reactive, computed, nextTick } from 'vue';
import { emptyToNull } from '../utils/helpers.js';

export function useTasks(settings, glossary, i18n) {
    const { form, workflowParams, default_workflows, saveSetting, saveAllSettings, updatePlatformParams, STORAGE } = settings;
    const { glossaryData } = glossary;
    const { t } = i18n;

    const tasks = ref([]);
    const runningCount = ref(0);
    const queue_concurrent = ref(3);

    // Pending queue for batch processing
    const pendingQueue = [];

    const hasPendingTasks = computed(() =>
        tasks.value.some(task => task.file && !task.isTranslating && !task.isFinished)
    );

    // ===== Task Creation =====
    const createNewTask = (backendId = null) => {
        const uiId = 'card_' + Math.random().toString(36).substring(2, 9);
        const task = reactive({
            uiId, backendId, file: null, fileName: '', logs: '', statusMessage: '',
            statusClass: 'text-muted', isTranslating: false, isFinished: false, isProcessing: false,
            validationError: false, downloads: null, attachment: null, initializing: false, isDragOver: false,
            progressPercent: 0, detectedWorkflow: null
        });
        tasks.value.unshift(task);
        if (backendId) {
            task.isTranslating = true;
            pollStatus(task);
        }
        return task;
    };

    const saveActiveTasks = () => {
        if (window.location.pathname.includes('/admin')) return;
        const ids = tasks.value.map(t => t.backendId).filter(id => id);
        localStorage.setItem('active_task_ids', JSON.stringify(ids));
    };

    const removeTask = async (task) => {
        if (task.isTranslating) {
            if (!confirm(t('confirmRemoveTranslatingTask'))) return;
            try { await toggleTaskState(task); } catch (e) {}
        }
        if (task.backendId) try {
            await fetch(`/service/release/${task.backendId}`, {method: 'POST'});
        } catch (e) {}
        tasks.value = tasks.value.filter(t => t.uiId !== task.uiId);
        saveActiveTasks();
    };

    const clearAllTasks = async () => {
        if (!confirm(t('confirmClearAllTasks'))) return;
        for (const task of [...tasks.value]) {
            if (task.backendId) try {
                await fetch(`/service/release/${task.backendId}`, {method: 'POST'});
            } catch (e) {}
        }
        tasks.value = [];
        saveActiveTasks();
    };

    // ===== File Handling =====
    const handleTaskFileSelect = (e, task) => {
        const f = e.target.files ? e.target.files[0] : e.dataTransfer.files[0];
        if (!f) return;
        task.file = f;
        task.fileName = f.name;
        task.validationError = false;
        task.isDragOver = false;

        const ext = f.name.split('.').pop().toLowerCase();
        const newWorkflow = default_workflows[ext] || 'markdown_based';
        form.workflow_type = newWorkflow;
        task.detectedWorkflow = newWorkflow;
        saveSetting('translator_last_workflow', newWorkflow);

        if (e.target) e.target.value = '';
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

    // ===== Folder Upload =====
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

    // ===== Batch Run =====
    const startNextPendingTask = () => {
        const maxConcurrent = Math.max(1, queue_concurrent.value);
        while (pendingQueue.length > 0 && runningCount.value < maxConcurrent) {
            const task = pendingQueue.shift();
            if (task.file && !task.isTranslating && !task.isFinished) {
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

    // ===== Translation Logic =====
    const buildPayload = () => {
        const basePayload = {
            skip_translate: form.skip_translate,
            base_url: emptyToNull(form.base_url),
            api_key: form.api_key || "",
            model_id: emptyToNull(form.model_id),
            provider: emptyToNull(form.provider),
            to_lang: form.to_lang === 'custom' ? form.custom_to_lang : form.to_lang,
            thinking: form.thinking,
            chunk_size: Number(form.chunk_size),
            concurrent: Number(form.concurrent),
            temperature: Number(form.temperature),
            top_p: Number(form.top_p),
            retry: Number(form.retry),
            custom_prompt: emptyToNull(form.custom_prompt),
            glossary_dict: Object.keys(glossaryData.value).length ? glossaryData.value : null,
            system_proxy_enable: form.system_proxy_enable,
            force_json: form.force_json,
            glossary_generate_enable: form.glossary_generate_enable,
            workflow_type: form.workflow_type,
            rpm: emptyToNull(form.rpm),
            tpm: emptyToNull(form.tpm),
            extra_body: emptyToNull(form.extra_body)
        };

        if (basePayload.glossary_generate_enable) {
            const isCustom = form.glossary_agent_config_choice === 'custom';
            basePayload.glossary_agent_config = {
                base_url: isCustom ? emptyToNull(form.glossary_agent_baseurl) : basePayload.base_url,
                api_key: isCustom ? (form.glossary_agent_key || "") : basePayload.api_key,
                model_id: isCustom ? emptyToNull(form.glossary_agent_model_id) : basePayload.model_id,
                provider: isCustom ? emptyToNull(form.glossary_agent_provider) : basePayload.provider,
                to_lang: isCustom ? (form.glossary_agent_to_lang === 'custom' ? form.glossary_agent_custom_to_lang : form.glossary_agent_to_lang) : basePayload.to_lang,
                custom_prompt: emptyToNull(form.glossary_agent_custom_prompt),
                temperature: isCustom ? Number(form.glossary_agent_temperature) : basePayload.temperature,
                top_p: isCustom ? Number(form.glossary_agent_top_p) : basePayload.top_p,
                concurrent: isCustom ? Number(form.glossary_agent_concurrent) : basePayload.concurrent,
                retry: isCustom ? Number(form.glossary_agent_retry) : basePayload.retry,
                thinking: isCustom ? form.glossary_agent_thinking : basePayload.thinking,
                system_proxy_enable: isCustom ? form.glossary_agent_system_proxy_enable : basePayload.system_proxy_enable,
                chunk_size: isCustom ? Number(form.glossary_agent_chunk_size) : basePayload.chunk_size,
                force_json: isCustom ? form.glossary_agent_force_json : basePayload.force_json,
                rpm: isCustom ? emptyToNull(form.glossary_agent_rpm) : basePayload.rpm,
                tpm: isCustom ? emptyToNull(form.glossary_agent_tpm) : basePayload.tpm,
                extra_body: isCustom ? emptyToNull(form.glossary_agent_extra_body) : basePayload.extra_body
            };
        }

        // Workflow-specific params
        if (form.workflow_type === 'markdown_based') {
            basePayload.convert_engine = form.convert_engine;
            basePayload.md2docx_engine = form.md2docx_engine === 'null' ? null : form.md2docx_engine;
            if (form.convert_engine === 'mineru') {
                basePayload.mineru_token = emptyToNull(form.mineru_token);
                basePayload.model_version = form.model_version;
                basePayload.formula_ocr = form.formula_ocr;
                basePayload.mineru_language = form.mineru_language;
            } else if (form.convert_engine === 'mineru_deploy') {
                basePayload.mineru_deploy_base_url = emptyToNull(form.mineru_deploy_base_url);
                basePayload.mineru_deploy_backend = form.mineru_deploy_backend;
                basePayload.mineru_deploy_parse_method = form.mineru_deploy_parse_method;
                basePayload.mineru_deploy_formula_enable = form.mineru_deploy_formula_enable;
                basePayload.mineru_deploy_table_enable = form.mineru_deploy_table_enable;
                basePayload.mineru_deploy_start_page_id = parseInt(form.mineru_deploy_start_page) || 0;
                basePayload.mineru_deploy_end_page_id = parseInt(form.mineru_deploy_end_page) || 99999;
                if (['pipeline', 'hybrid-auto-engine', 'hybrid-http-client'].includes(form.mineru_deploy_backend)) {
                    basePayload.mineru_deploy_lang_list = form.mineru_deploy_lang_list.length > 0 ? form.mineru_deploy_lang_list : null;
                }
                if (['vlm-http-client', 'hybrid-http-client'].includes(form.mineru_deploy_backend)) {
                    basePayload.mineru_deploy_server_url = emptyToNull(form.mineru_deploy_server_url);
                }
            } else if (form.convert_engine === 'docling') {
                basePayload.code_ocr = form.code_ocr;
                basePayload.formula_ocr = form.formula_ocr;
            }
        } else {
            const params = {...workflowParams[form.workflow_type]};
            if (params.separator) {
                params.separator = params.separator.replace(/\\n/g, '\n');
            }
            if (form.workflow_type === 'json') {
                params.json_paths = params.json_paths.split('\n').map(p => p.trim()).filter(p => p);
            } else if (form.workflow_type === 'xlsx') {
                if (params.translate_regions && typeof params.translate_regions === 'string' && params.translate_regions.trim()) {
                    params.translate_regions = params.translate_regions.split('\n').map(p => p.trim()).filter(p => p);
                    if (params.translate_regions.length === 0) delete params.translate_regions;
                } else {
                    delete params.translate_regions;
                }
            }
            Object.assign(basePayload, params);
        }

        return basePayload;
    };

    const validateForm = (errors) => {
        let isValid = true;
        Object.keys(errors).forEach(k => errors[k] = false);

        if (!form.skip_translate) {
            if (!form.model_id) { errors.model_id = true; isValid = false; }
            if (form.platform === 'custom' && !form.base_url) { errors.base_url = true; isValid = false; }
            if (form.to_lang === 'custom' && !form.custom_to_lang) { errors.custom_to_lang = true; isValid = false; }
        }

        if (form.workflow_type === 'markdown_based') {
            if (form.convert_engine === 'mineru' && !form.mineru_token) { errors.mineru_token = true; isValid = false; }
            if (form.convert_engine === 'mineru_deploy' && !form.mineru_deploy_base_url) { errors.mineru_deploy_base_url = true; isValid = false; }
        } else if (form.workflow_type === 'json') {
            if (!workflowParams.json.json_paths || !workflowParams.json.json_paths.trim()) {
                errors.json_paths = true; isValid = false;
            }
        }

        if (!isValid) {
            nextTick(() => {
                const errorEl = document.querySelector('.is-invalid');
                if (errorEl) {
                    errorEl.scrollIntoView({behavior: 'smooth', block: 'center'});
                    errorEl.focus();
                }
            });
        }
        return isValid;
    };

    const appendLog = (task, msg, isError = false) => {
        const safe = (msg || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        task.logs += (task.logs ? '<br>' : '') + (isError ? `<span class="text-danger">${safe}</span>` : safe);
        nextTick(() => {
            const el = document.getElementById('log-' + task.uiId);
            if (el) el.scrollTop = el.scrollHeight;
        });
    };

    const toggleTaskState = async (task, errors) => {
        if (task.initializing) return;
        if (task.isTranslating) {
            task.statusMessage = t('status_cancelling');
            task.isProcessing = false;
            if (task.backendId) {
                try { await fetch(`/service/cancel/${task.backendId}`, {method: 'POST'}); } catch (e) {}
            }
            runningCount.value = Math.max(0, runningCount.value - 1);
            task.isTranslating = false;
            task.isFinished = false;
            task.statusMessage = t('taskCardStatusCancelled');
            task.statusClass = 'text-warning';
            return;
        }

        if (task.isFinished) {
            // Re-translation requires a file
            if (!task.file) {
                task.validationError = true;
                setTimeout(() => { task.validationError = false; }, 3000);
                return;
            }
            task.isFinished = false;
            task.logs = '';
            task.downloads = null;
            toggleTaskState(task, errors);
            return;
        }

        if (!task.file) {
            task.validationError = true;
            // Auto-clear validation error after 3 seconds
            setTimeout(() => { task.validationError = false; }, 3000);
            return;
        }

        if (!validateForm(errors)) {
            task.statusMessage = t('status_fillRequired') || "请检查左侧配置项 (Please check settings)";
            task.statusClass = 'text-danger';
            return;
        }

        task.initializing = true;
        try {
            const savedWorkflow = form.workflow_type;
            if (task.detectedWorkflow) {
                form.workflow_type = task.detectedWorkflow;
            }
            const formData = new FormData();
            formData.append('file', task.file);
            formData.append('payload', JSON.stringify(buildPayload()));
            form.workflow_type = savedWorkflow;
            const res = await fetch('/service/translate/file', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (res.ok && data.task_started) {
                task.backendId = data.task_id;
                task.isTranslating = true;
                task.initializing = false;
                saveActiveTasks();
                pollStatus(task);
                task.statusMessage = data.message;
            } else {
                throw new Error(data.message || data.detail || 'Error');
            }
        } catch (e) {
            task.statusMessage = e.message;
            task.statusClass = 'text-danger';
            task.isTranslating = false;
            task.initializing = false;
            runningCount.value = Math.max(0, runningCount.value - 1);
        }
    };

    const pollStatus = (task) => {
        const interval = setInterval(async () => {
            if (!task.isTranslating) {
                clearInterval(interval);
                return;
            }
            try {
                // Fetch Logs
                const logRes = await fetch(`/service/logs/${task.backendId}`);
                const logData = await logRes.json();
                if (logData.logs && logData.logs.length) {
                    task.logs += logData.logs.map(l => l.replace(/</g, "&lt;").replace(/>/g, "&gt;")).join('<br>') + '<br>';
                    nextTick(() => {
                        const logEl = document.getElementById('log-' + task.uiId);
                        if (logEl) logEl.scrollTop = logEl.scrollHeight;
                    });
                }

                // Fetch Status
                const statRes = await fetch(`/service/status/${task.backendId}`);

                // Handle 404 (Task not found / Expired)
                if (!statRes.ok) {
                    if (statRes.status === 404) {
                        clearInterval(interval);
                        task.isTranslating = false;
                        task.isProcessing = false;
                        task.statusClass = 'text-danger';
                        task.statusMessage = t('status_taskNotFound');
                        const savedIds = JSON.parse(localStorage.getItem('active_task_ids') || '[]');
                        const newIds = savedIds.filter(id => id !== task.backendId);
                        localStorage.setItem('active_task_ids', JSON.stringify(newIds));
                        return;
                    }
                    return;
                }

                const d = await statRes.json();
                task.statusMessage = d.status_message;
                task.isProcessing = d.is_processing;
                task.progressPercent = d.progress_percent || 0;

                if (d.original_filename && !task.fileName) {
                    task.fileName = d.original_filename;
                }

                if (!d.is_processing) {
                    clearInterval(interval);
                    task.isTranslating = false;
                    task.isFinished = true;
                    task.isProcessing = false;
                    runningCount.value = Math.max(0, runningCount.value - 1);
                    if (d.download_ready && !d.error_flag) {
                        task.downloads = d.downloads || {};
                        task.attachment = d.attachment || {};
                        task.statusClass = 'text-success';
                    } else {
                        task.statusClass = 'text-danger';
                        task.statusMessage = d.error_flag ? (d.status_message || 'Failed') : d.status_message;
                    }
                }
            } catch (e) {
                // Continue polling on error
            }
        }, 1500);
    };

    const copyLog = (e, l) => {
        navigator.clipboard.writeText(l.replace(/<br>/g, '\n')).then(() => {
            const btn = e.currentTarget;
            const svg = btn.querySelector('svg');
            btn.classList.add('text-success');
            btn.classList.remove('text-gray-600', 'dark:text-gray-400');
            if (svg) {
                svg.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />';
            }
            setTimeout(() => {
                btn.classList.remove('text-success');
                btn.classList.add('text-gray-600', 'dark:text-gray-400');
                if (svg) {
                    svg.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />';
                }
            }, 2000);
        });
    };

    return {
        tasks,
        runningCount,
        queue_concurrent,
        hasPendingTasks,
        pendingQueue,
        createNewTask,
        saveActiveTasks,
        removeTask,
        clearAllTasks,
        handleTaskFileSelect,
        handleTaskFileDrop,
        triggerFileInput,
        selectTaskWorkflow,
        handleFolderSelect,
        startNextPendingTask,
        runAllPendingTasks,
        buildPayload,
        validateForm,
        appendLog,
        toggleTaskState,
        pollStatus,
        copyLog
    };
}
