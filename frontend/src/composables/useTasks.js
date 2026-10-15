import { ref, reactive, computed, nextTick } from 'vue';
import { emptyToNull, decodeBase64Utf8 } from '../utils/helpers.js';

// 格式化错误信息，处理 FastAPI 422 验证错误等复杂格式
const formatError = (data) => {
    if (!data) return 'Unknown error';

    // 如果 detail 是数组（FastAPI 验证错误格式）
    if (Array.isArray(data.detail)) {
        const errors = data.detail.map(err => {
            const field = err.loc ? err.loc.join('.') : 'unknown';
            const msg = err.msg || 'Validation error';
            return `${field}: ${msg}`;
        });
        return errors.join('; ');
    }

    // 如果 detail 是字符串
    if (typeof data.detail === 'string') {
        return data.detail;
    }

    // 如果有 message
    if (data.message) {
        return data.message;
    }

    // 其他情况尝试转为字符串
    try {
        return JSON.stringify(data);
    } catch {
        return String(data);
    }
};

export function useTasks(settings, glossary, i18n) {
    const { form, workflowParams, default_workflows, queue_concurrent, saveSetting, saveAllSettings, updatePlatformParams, STORAGE, errors, webSkipValidation, textInputLimit } = settings;
    const { glossaryData } = glossary;
    const { t } = i18n;

    const tasks = ref([]);
    const runningCount = ref(0);

    // Pending queue for batch processing
    const pendingQueue = [];
    const batchTasks = new Set();

    // 文本任务没有 task.file，用这个统一判断任务是否可提交（批量运行等场景）
    const isTaskSubmittable = (task) =>
        !!task.file || (task.isTextInput && !!(task.inputText && task.inputText.trim()));

    const hasPendingTasks = computed(() =>
        tasks.value.some(task => isTaskSubmittable(task) && !task.initializing && !task.isTranslating && !task.isFinished && !task.queuePosition)
    );

    const removeFromPendingQueue = (task) => {
        const index = pendingQueue.indexOf(task);
        if (index !== -1) pendingQueue.splice(index, 1);
        task.queuePosition = null;
        task.queueTotal = null;
    };

    const releaseBatchSlot = (task) => {
        if (!batchTasks.delete(task)) return;
        runningCount.value = batchTasks.size;
        startNextPendingTask();
    };

    // ===== Task Creation =====
    const createNewTask = (backendId = null) => {
        const uiId = 'card_' + Math.random().toString(36).substring(2, 9);
        const task = reactive({
            uiId, backendId, file: null, fileName: '', logs: '', statusMessage: '',
            statusClass: 'text-muted', isTranslating: false, isFinished: false, isProcessing: false,
            validationError: false, downloads: null, attachment: null, initializing: false, isDragOver: false,
            progressPercent: 0, detectedWorkflow: null, statistics: null
        });
        tasks.value.unshift(task);
        if (backendId) {
            task.isTranslating = true;
            pollStatus(task);
        }
        return task;
    };

    // ===== Text Task Creation（文本输入任务）=====
    const createNewTextTask = () => {
        const uiId = 'card_' + Math.random().toString(36).substring(2, 9);
        const task = reactive({
            uiId, backendId: null, file: null, fileName: '', logs: '', statusMessage: '',
            statusClass: 'text-muted', isTranslating: false, isFinished: false, isProcessing: false,
            validationError: false, downloads: null, attachment: null, initializing: false, isDragOver: false,
            progressPercent: 0, detectedWorkflow: 'txt', statistics: null,
            isTextInput: true, inputText: '', resultText: null, resultCopied: false
        });
        tasks.value.unshift(task);
        // 让左侧面板同步显示 txt 工作流的专属配置（插入模式/分隔符/分段模式）
        form.workflow_type = 'txt';
        saveSetting('translator_last_workflow', 'txt');
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
        }
        task.removed = true;
        stopPolling(task);
        removeFromPendingQueue(task);
        tasks.value = tasks.value.filter(t => t.uiId !== task.uiId);
        saveActiveTasks();
        try {
            if (task.backendId) await fetch(`/service/release/${task.backendId}`, {method: 'POST'});
        } catch (e) {
            console.error('Failed to release task:', e);
        } finally {
            releaseBatchSlot(task);
        }
    };

    const clearAllTasks = async () => {
        if (!confirm(t('confirmClearAllTasks'))) return;
        const removedTasks = [...tasks.value];
        pendingQueue.length = 0;
        tasks.value = [];
        saveActiveTasks();
        for (const task of removedTasks) {
            task.removed = true;
            stopPolling(task);
            task.queuePosition = null;
            task.queueTotal = null;
            releaseBatchSlot(task);
            if (task.backendId) try {
                await fetch(`/service/release/${task.backendId}`, {method: 'POST'});
            } catch (e) {}
        }
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
        const maxConcurrent = Math.max(1, Number(queue_concurrent.value) || 1);
        while (pendingQueue.length > 0 && runningCount.value < maxConcurrent) {
            const task = pendingQueue.shift();
            task.queuePosition = null;
            task.queueTotal = null;
            if (tasks.value.includes(task) && isTaskSubmittable(task) && !task.removed && !task.initializing && !task.isTranslating && !task.isFinished) {
                batchTasks.add(task);
                runningCount.value = batchTasks.size;
                toggleTaskState(task, errors).finally(() => {
                    if (!task.isTranslating) releaseBatchSlot(task);
                });
            }
        }
    };

    const runAllPendingTasks = () => {
        const pending = tasks.value.filter(t => isTaskSubmittable(t) && !t.initializing && !t.isTranslating && !t.isFinished);
        pendingQueue.length = 0;
        pending.forEach((task, i) => {
            task.queuePosition = i + 1;
            task.queueTotal = pending.length;
            pendingQueue.push(task);
        });
        startNextPendingTask();
    };

    // ===== Translation Logic =====
    const buildPayload = (workflowType = form.workflow_type) => {
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
            glossary_dict: glossaryData.value && Object.keys(glossaryData.value).length ? glossaryData.value : null,
            system_proxy_enable: form.system_proxy_enable,
            force_json: form.force_json,
            glossary_generate_enable: form.glossary_generate_enable,
            workflow_type: workflowType,
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
        if (workflowType === 'markdown_based') {
            basePayload.convert_engine = form.convert_engine;
            basePayload.md2docx_engine = form.md2docx_engine === 'null' ? null : form.md2docx_engine;
            if (form.convert_engine === 'mineru') {
                basePayload.mineru_token = emptyToNull(form.mineru_token);
                basePayload.model_version = form.model_version;
                basePayload.formula_ocr = form.formula_ocr;
                basePayload.mineru_language = form.mineru_language;
            } else if (form.convert_engine === 'mineru_deploy') {
                basePayload.mineru_deploy_base_url = emptyToNull(form.mineru_deploy_base_url);
                basePayload.mineru_deploy_api_key = emptyToNull(form.mineru_deploy_api_key);
                basePayload.mineru_deploy_backend = form.mineru_deploy_backend;
                basePayload.mineru_deploy_effort = form.mineru_deploy_effort;
                basePayload.mineru_deploy_parse_method = form.mineru_deploy_parse_method;
                basePayload.mineru_deploy_formula_enable = form.mineru_deploy_formula_enable;
                basePayload.mineru_deploy_table_enable = form.mineru_deploy_table_enable;
                basePayload.mineru_deploy_image_analysis = form.mineru_deploy_image_analysis;
                basePayload.mineru_deploy_start_page_id = parseInt(form.mineru_deploy_start_page) || 0;
                const endPage = parseInt(form.mineru_deploy_end_page, 10);
                basePayload.mineru_deploy_end_page_id = Number.isNaN(endPage) ? 99999 : endPage;
                if (['pipeline', 'hybrid-engine', 'hybrid-http-client'].includes(form.mineru_deploy_backend)) {
                    basePayload.mineru_deploy_lang_list = form.mineru_deploy_lang_list.length > 0 ? form.mineru_deploy_lang_list : null;
                }
                if (['vlm-http-client', 'hybrid-http-client'].includes(form.mineru_deploy_backend)) {
                    basePayload.mineru_deploy_server_url = emptyToNull(form.mineru_deploy_server_url);
                }
            }
        } else {
            const params = {...workflowParams[workflowType]};
            if (params.separator) {
                params.separator = params.separator.replace(/\\n/g, '\n');
            }
            if (workflowType === 'json') {
                params.json_paths = params.json_paths.split('\n').map(p => p.trim()).filter(p => p);
            } else if (workflowType === 'xlsx') {
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

    const validateForm = (errors, workflowType = form.workflow_type) => {
        let isValid = true;
        if (errors) Object.keys(errors).forEach(k => errors[k] = false);

        // 如果跳过前端空值检查，直接返回 true
        if (webSkipValidation.value) {
            return true;
        }

        if (!form.skip_translate) {
            if (!form.model_id) { if (errors) errors.model_id = true; isValid = false; }
            if (form.platform === 'custom' && !form.base_url) { if (errors) errors.base_url = true; isValid = false; }
            if (form.to_lang === 'custom' && !form.custom_to_lang) { if (errors) errors.custom_to_lang = true; isValid = false; }
        }

        if (workflowType === 'markdown_based') {
            if (form.convert_engine === 'mineru' && !form.mineru_token) { if (errors) errors.mineru_token = true; isValid = false; }
            if (form.convert_engine === 'mineru_deploy' && !form.mineru_deploy_base_url) { if (errors) errors.mineru_deploy_base_url = true; isValid = false; }
        } else if (workflowType === 'json') {
            if (!workflowParams.json.json_paths || !workflowParams.json.json_paths.trim()) {
                if (errors) errors.json_paths = true; isValid = false;
            }
        }

        if (!isValid) {
            nextTick(() => {
                // 查找带有红色边框的错误元素（border-red-500 或 border-red-400）
                const errorEl = document.querySelector('.border-red-500, .border-red-400');
                if (errorEl) {
                    // 找到错误元素所在的 Collapse 并展开
                    const collapseEl = errorEl.closest('.collapse-panel');
                    if (collapseEl) {
                        const headerBtn = collapseEl.querySelector('.collapse-header');
                        const contentEl = collapseEl.querySelector('.overflow-hidden');
                        // 检查是否折叠状态（contentEl 的 v-show 为 false）
                        if (contentEl && contentEl.style.display === 'none') {
                            headerBtn?.click();
                        }
                    }
                    // 等待展开动画完成后再滚动
                    setTimeout(() => {
                        errorEl.scrollIntoView({behavior: 'smooth', block: 'center'});
                        errorEl.focus();
                    }, 250);
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
        if (task.removed || task.initializing) return;
        if (task.isTranslating) {
            task.initializing = true;
            task.isTranslating = false;
            task.statusMessage = t('status_cancelling');
            task.isProcessing = false;
            if (task.backendId) {
                try { await fetch(`/service/cancel/${task.backendId}`, {method: 'POST'}); } catch (e) {}
            }
            task.initializing = false;
            task.isFinished = false;
            task.statusMessage = t('taskCardStatusCancelled');
            task.statusClass = 'text-warning';
            releaseBatchSlot(task);
            return;
        }

        if (task.isFinished) {
            // Re-translation requires a file or text input
            if (!task.file && !task.isTextInput) {
                task.validationError = true;
                setTimeout(() => { task.validationError = false; }, 3000);
                return;
            }
            // Release old task resources before starting new translation
            if (task.backendId) {
                try { await fetch(`/service/release/${task.backendId}`, {method: 'POST'}); } catch (e) {}
                task.backendId = null;
            }
            task.isFinished = false;
            task.logs = '';
            task.downloads = null;
            task.resultText = null;
            await toggleTaskState(task, errors);
            return;
        }

        if (task.isTextInput) {
            const text = task.inputText || '';
            if (!text.trim()) {
                task.validationError = true;
                task.statusMessage = t('textInputEmptyError');
                task.statusClass = 'text-danger';
                setTimeout(() => { task.validationError = false; }, 3000);
                return;
            }
            if (textInputLimit && textInputLimit.value > 0 && text.length > textInputLimit.value) {
                task.validationError = true;
                task.statusMessage = t('textInputTooLong', { n: text.length, limit: textInputLimit.value });
                task.statusClass = 'text-danger';
                setTimeout(() => { task.validationError = false; }, 3000);
                return;
            }
        } else if (!task.file) {
            task.validationError = true;
            // Auto-clear validation error after 3 seconds
            setTimeout(() => { task.validationError = false; }, 3000);
            return;
        }

        removeFromPendingQueue(task);
        const workflowType = task.detectedWorkflow || form.workflow_type;
        if (!validateForm(errors, workflowType)) {
            task.statusMessage = t('status_fillRequired') || "请检查左侧配置项 (Please check settings)";
            task.statusClass = 'text-danger';
            return;
        }

        task.initializing = true;
        try {
            let res;
            if (task.isTextInput) {
                // 文本任务固定走 txt 工作流参数
                res = await fetch('/service/translate/text', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: task.inputText, payload: buildPayload('txt') })
                });
            } else {
                const formData = new FormData();
                formData.append('file', task.file);
                formData.append('payload', JSON.stringify(buildPayload(workflowType)));
                res = await fetch('/service/translate/file', {
                    method: 'POST',
                    body: formData
                });
            }
            const data = await res.json();
            if (res.ok && data.task_started) {
                if (task.removed) {
                    await fetch(`/service/release/${data.task_id}`, {method: 'POST'});
                    return;
                }
                task.backendId = data.task_id;
                task.isTranslating = true;
                task.initializing = false;
                saveActiveTasks();
                pollStatus(task);
                task.statusMessage = data.message;
            } else {
                throw new Error(formatError(data));
            }
        } catch (e) {
            task.statusMessage = e.message;
            task.statusClass = 'text-danger';
            task.isTranslating = false;
            task.initializing = false;
        } finally {
            task.initializing = false;
        }
    };

    const stopPolling = (task) => {
        if (task && task.pollInterval) {
            clearInterval(task.pollInterval);
            task.pollInterval = null;
        }
    };

    const pollStatus = (task) => {
        const polledId = task.backendId;
        let inFlight = false;
        const interval = setInterval(async () => {
            if (!task.isTranslating || task.removed || task.backendId !== polledId) {
                stopPolling(task);
                return;
            }
            if (inFlight) return;
            inFlight = true;
            try {
                // Fetch Logs
                const logRes = await fetch(`/service/logs/${polledId}`);
                const logData = await logRes.json();
                if (!task.isTranslating || task.removed || task.backendId !== polledId) return;
                if (logData.logs && logData.logs.length) {
                    task.logs += logData.logs.map(l => l.replace(/&/g, '&amp;').replace(/</g, "&lt;").replace(/>/g, "&gt;")).join('<br>') + '<br>';
                    nextTick(() => {
                        const logEl = document.getElementById('log-' + task.uiId);
                        if (logEl) logEl.scrollTop = logEl.scrollHeight;
                    });
                }

                // Fetch Status
                const statRes = await fetch(`/service/status/${polledId}`);
                if (!task.isTranslating || task.removed || task.backendId !== polledId) return;

                // Handle 404 (Task not found / Expired)
                if (!statRes.ok) {
                    if (statRes.status === 404) {
                        stopPolling(task);
                        task.isTranslating = false;
                        task.isProcessing = false;
                        task.statusClass = 'text-danger';
                        task.statusMessage = t('status_taskNotFound');
                        task.backendId = null;
                        saveActiveTasks();
                        releaseBatchSlot(task);
                        return;
                    }
                    return;
                }

                const d = await statRes.json();
                if (!task.isTranslating || task.removed || task.backendId !== polledId) return;
                task.statusMessage = d.status_message;
                task.isProcessing = d.is_processing;
                task.progressPercent = d.progress_percent || 0;

                if (d.original_filename && !task.fileName) {
                    task.fileName = d.original_filename;
                }

                // 页面刷新/恢复后，根据后端标记把卡片识别回文本任务
                if (d.input_source === 'text' && !task.isTextInput) {
                    task.isTextInput = true;
                    task.detectedWorkflow = 'txt';
                }

                // Store statistics if available
                if (d.statistics) {
                    task.statistics = d.statistics;
                }

                if (!d.is_processing) {
                    stopPolling(task);
                    task.isTranslating = false;
                    task.isFinished = true;
                    task.isProcessing = false;
                    releaseBatchSlot(task);
                    if (d.download_ready && !d.error_flag) {
                        task.downloads = d.downloads || {};
                        if (task.isTextInput && d.downloads && d.downloads.txt) {
                            fetchTextResult(task);
                        }
                        task.attachment = d.attachment || {};
                        task.statusClass = 'text-success';
                    } else {
                        task.statusClass = 'text-danger';
                        task.statusMessage = d.error_flag ? (d.status_message || 'Failed') : d.status_message;
                    }
                }
            } catch (e) {
                // Continue polling on error
            } finally {
                inFlight = false;
            }
        }, 1500);
        // 记录定时器，删除任务时可以立即停止轮询，而不是再等一个 1.5s 周期。
        task.pollInterval = interval;
    };

    const copyLog = (e, l) => {
        const text = l.replace(/<br>/g, '\n');
        const markCopied = () => {
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
        };

        // navigator.clipboard 在非安全上下文（局域网 http 访问是本项目的默认用法）
        // 是 undefined；以前这里会同步抛 TypeError，既不复制也没有任何反馈。
        const clipboard = navigator.clipboard;
        if (clipboard && typeof clipboard.writeText === 'function') {
            Promise.resolve(clipboard.writeText(text)).then(markCopied).catch(() => fallbackCopy(text));
        } else {
            fallbackCopy(text);
        }
    };

    const fallbackCopy = (text) => {
        try {
            const area = document.createElement('textarea');
            area.value = text;
            area.setAttribute('readonly', '');
            area.style.position = 'fixed';
            area.style.opacity = '0';
            document.body.appendChild(area);
            area.select();
            document.execCommand('copy');
            document.body.removeChild(area);
        } catch (err) {
            console.warn('复制日志失败', err);
        }
    };

    // 拉取文本任务的译文内容（base64 → UTF-8），用于卡片内直接显示
    const fetchTextResult = async (task) => {
        if (task.resultText) return;
        const id = task.backendId;
        try {
            const res = await fetch(`/service/content/${id}/txt`);
            if (!res.ok) return;
            const data = await res.json();
            if (task.backendId !== id) return; // 期间已重新翻译
            task.resultText = decodeBase64Utf8(data.content);
        } catch (e) {
            console.error('获取译文内容失败:', e);
        }
    };

    const copyResultText = (task) => {
        const text = task.resultText || '';
        const markCopied = () => {
            task.resultCopied = true;
            setTimeout(() => { task.resultCopied = false; }, 2000);
        };
        // 与 copyLog 相同的非安全上下文（局域网 http）回退策略
        const clipboard = navigator.clipboard;
        if (clipboard && typeof clipboard.writeText === 'function') {
            Promise.resolve(clipboard.writeText(text)).then(markCopied).catch(() => { fallbackCopy(text); markCopied(); });
        } else {
            fallbackCopy(text);
            markCopied();
        }
    };

    return {
        tasks,
        runningCount,
        queue_concurrent,
        hasPendingTasks,
        pendingQueue,
        createNewTask,
        createNewTextTask,
        fetchTextResult,
        copyResultText,
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
