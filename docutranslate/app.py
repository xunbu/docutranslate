import asyncio
import io
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

import uvicorn
from fastapi import FastAPI, File, Form, UploadFile, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from docutranslate import FileTranslater
from docutranslate.logger import translater_logger

# --- HTML模板 (JS part needs modification) ---
# language=HTML
HTML_TEMPLATE = """
                <!DOCTYPE html>
                <html lang="zh-CN">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>DocuTranslate</title>
                    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@latest/css/pico.min.css">
                    <style>
                        body {
                            padding: 20px;
                        }

                        .container {
                            max-width: 800px;
                            margin: auto;
                            padding: 1rem;
                        }

                        .log-area {
                            background-color: #f5f5f5;
                            border: 1px solid #e0e0e0;
                            padding: 10px;
                            height: 200px;
                            overflow-y: scroll;
                            white-space: pre-wrap;
                            font-family: monospace;
                            margin-top: 1rem;
                        }

                        .error-message {
                            color: #d32f2f;
                        }

                        .success-message {
                            color: #2e7d32;
                        }

                        .form-group {
                            margin-bottom: 1rem;
                        }

                        .form-grid {
                            display: grid;
                            grid-template-columns: 1fr 1fr;
                            gap: 1rem;
                        }

                        .button-group {
                            margin-top: 1rem;
                            display: flex;
                            gap: 0.5rem;
                            flex-wrap: wrap;
                        }

                        details {
                            margin-bottom: 1rem;
                        }

                        .checkbox-group {
                            display: flex;
                            flex-wrap: wrap;
                            margin-bottom: 1rem;
                        }

                        #resultArea {
                            margin-top: 1.5rem;
                            padding-top: 1rem;
                            border-top: 1px solid #eee;
                        }

                        #downloadButtons {
                            display: none;
                            margin-top: 1rem;
                        }

                        .hidden {
                            display: none !important;
                        }

                        .modal {
                            display: none;
                            position: fixed;
                            top: 0;
                            left: 0;
                            width: 100%;
                            height: 100%;
                            background-color: rgba(0, 0, 0, 0.6);
                            z-index: 1000;
                            overflow: auto;
                        }

                        .modal-content {
                            background-color: #fff;
                            margin: 2% auto;
                            padding: 20px;
                            width: 90%;
                            max-width: 900px;
                            max-height: 90vh;
                            border-radius: 8px;
                            overflow: auto;
                        }

                        #previewFrame {
                            width: 100%;
                            min-height: 500px;
                            border: 1px solid #ddd;
                        }

                        #printFrame {
                            display: none;
                        }

                        /* Styles for drag and drop area */
                        #fileDropArea {
                            border: 2px dashed #ccc;
                            padding: 20px;
                            text-align: center;
                            cursor: pointer;
                            transition: background-color 0.2s ease-in-out, border-color 0.2s ease-in-out;
                        }

                        #fileDropArea.drag-over {
                            border-color: #007bff; /* Pico primary color */
                            background-color: rgba(0, 123, 255, 0.05);
                        }

                        #fileDropArea p {
                            margin: 0.5rem 0;
                            color: #555;
                        } \
 \
                        #fileNameDisplay {
                            margin-top: 0.5rem;
                            font-style: italic;
                            color: #333;
                        }


                        @media (max-width: 768px) {
                            .form-grid {
                                grid-template-columns: 1fr;
                            }
                        }
                    </style>
                </head>
                <body>
                <main class="container">
                    <h1>
                        <a href="https://github.com/xunbu/docutranslate" target="_blank">DocuTranslate</a>
                    </h1>
                    <form id="translateForm">

                        <!-- Modified File Input Area -->
                        <div class="form-group">
                            <label for="file">文档选择</label>
                            <div id="fileDropArea">
                                <input type="file" id="file" name="file" required style="display: none;">
                                <p>点击此处选择文件，或将文件拖拽到这里</p>
                                <div id="fileNameDisplay">未选择文件</div>
                            </div>
                        </div>

                        <div class="form-grid">
                            <div class="form-group">
                                <label for="to_lang">目标语言</label>
                                <select id="to_lang" name="to_lang">
                                    <option value="中文">中文 (Chinese)</option>
                                    <option value="English">英文 (English)</option>
                                    <option value="日本語">日语 (Japanese)</option>
                                    <option value="한국어">韩语 (Korean)</option>
                                    <option value="Français">法语 (French)</option>
                                    <option value="Deutsch">德语 (German)</option>
                                    <option value="Español">西班牙语 (Spanish)</option>
                                    <option value="Italiano">意大利语 (Italian)</option>
                                    <option value="Português">葡萄牙语 (Portuguese)</option>
                                    <option value="Русский">俄语 (Russian)</option>
                                    <option value="العربية">阿拉伯语 (Arabic)</option>
                                    <option value="हिन्दी">印地语 (Hindi)</option>
                                    <option value="Nederlands">荷兰语 (Dutch)</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label>高级选项</label>
                                <div class="checkbox-group">
                                    <label for="formula_ocr"><input type="checkbox" id="formula_ocr" name="formula_ocr">公式识别</label>
                                    <label for="code_ocr"><input type="checkbox" id="code_ocr" name="code_ocr">代码识别</label>
                                    <label for="refine_markdown"><input type="checkbox" id="refine_markdown"
                                                                        name="refine_markdown">修正文本（耗时）</label>
                                </div>
                            </div>
                        </div>
                        <details open>
                            <summary>API 配置</summary>
                            <div class="form-grid">
                                <div class="form-group">
                                    <label for="platform_select">AI 平台</label>
                                    <select id="platform_select" name="platform_select_ui">
                                        <option value="custom">自定义接口</option>
                                        <option value="https://api.openai.com/v1">OpenAI</option>
                                        <option value="https://open.bigmodel.cn/api/paas/v4">智谱AI</option>
                                        <option value="https://api.deepseek.com/v1">DeepSeek</option>
                                        <option value="https://dashscope.aliyuncs.com/compatible-mode/v1">阿里云百炼
                                        </option>
                                        <option value="https://www.dmxapi.cn/v1">DMXAPI</option>
                                        <option value="https://openrouter.ai/api/v1">OpenRouter</option>
                                        <option value="https://ark.cn-beijing.volces.com/api/v3">火山引擎</option>
                                        <option value="https://api.siliconflow.cn/v1">硅基流动</option>
                                    </select>
                                </div>
                                <div class="form-group hidden" id="baseUrlGroup">
                                    <label for="base_url">API 地址 (Base URL)</label>
                                    <input type="text" id="base_url" name="base_url"
                                           placeholder="https://api.openai.com/v1">
                                </div>
                            </div>
                            <div class="form-group">
                                <label for="apikey">API 密钥</label>
                                <input type="password" id="apikey" name="apikey" placeholder="平台对应的API Key"
                                       required>
                            </div>
                            <div class="form-group">
                                <label for="model_id">模型 ID</label>
                                <input type="text" id="model_id" name="model_id" placeholder="模型id" required>
                            </div>
                        </details>
                        <button type="submit" id="submitButton" class="primary">开始翻译</button>
                    </form>
                    <div id="resultArea">
                        <p id="statusMessage"></p>
                        <div id="downloadButtons" class="button-group">
                            <h4>翻译结果</h4>
                            <a id="downloadMarkdown" href="#" role="button" class="outline">下载 Markdown</a>
                            <a id="downloadHtml" href="#" role="button" class="outline">下载 HTML</a>
                            <button id="downloadPdf" class="outline">下载 PDF</button>
                            <button id="previewHtml" class="outline">预览</button>
                        </div>
                    </div>
                    <h4 style="margin-top: 1.5rem;">运行日志</h4>
                    <div class="log-area" id="logArea"></div>
                </main>
                <div id="previewModal" class="modal">
                    <div class="modal-content">
                        <span id="closeModalBtn" style="cursor:pointer; float:right;">×</span>
                        <h3>HTML 预览</h3>
                        <iframe id="previewFrame"></iframe>
                        <div class="button-group">
                            <button id="printFromPreview" class="primary">打印/保存为PDF</button>
                            <button id="closePreviewBtn" class="outline">关闭</button>
                        </div>
                    </div>
                </div>
                <iframe id="printFrame" style="display:none;"></iframe>

                <script>
                    const platformSelect = document.getElementById('platform_select');
                    const baseUrlGroup = document.getElementById('baseUrlGroup');
                    const baseUrlInput = document.getElementById('base_url');
                    const apikeyInput = document.getElementById('apikey');
                    const modelInput = document.getElementById('model_id');
                    const toLangSelect = document.getElementById('to_lang');
                    const formulaCheckbox = document.getElementById('formula_ocr');
                    const codeCheckbox = document.getElementById('code_ocr');
                    const refineCheckbox = document.getElementById('refine_markdown');
                    const form = document.getElementById('translateForm');
                    const submitButton = document.getElementById('submitButton');
                    const logArea = document.getElementById('logArea');
                    const statusMsg = document.getElementById('statusMessage');
                    const downloadBtns = document.getElementById('downloadButtons');
                    const markdownLink = document.getElementById('downloadMarkdown');
                    const htmlLink = document.getElementById('downloadHtml');
                    const previewHtmlBtn = document.getElementById('previewHtml');
                    const downloadPdfBtn = document.getElementById('downloadPdf');
                    const printFrameEl = document.getElementById('printFrame');
                    const modal = document.getElementById('previewModal');
                    const previewFrame = document.getElementById('previewFrame');
                    const closeModalButton = document.getElementById('closeModalBtn');
                    const closePreviewBtn = document.getElementById('closePreviewBtn');
                    const printFromPreview = document.getElementById('printFromPreview');

                    // File input and drag-drop elements
                    const fileInput = document.getElementById('file');
                    const fileDropArea = document.getElementById('fileDropArea');
                    const fileNameDisplay = document.getElementById('fileNameDisplay');


                    let logPollIntervalId = null;
                    let statusPollIntervalId = null;
                    let lastLogCount = 0;
                    let isTranslating = false; // Flag to track translation state for cancel button

                    function saveToStorage(key, value) {
                        try {
                            localStorage.setItem(key, value);
                        } catch (e) {
                            console.warn("保存到本地存储失败:", e);
                        }
                    }

                    function getFromStorage(key, defaultValue = '') {
                        try {
                            return localStorage.getItem(key) || defaultValue;
                        } catch (e) {
                            console.warn("从本地存储读取失败:", e);
                            return defaultValue;
                        }
                    }

                    function updatePlatformUI() {
                        const selectedPlatformValue = platformSelect.value;
                        apikeyInput.value = getFromStorage(`translator_platform_${selectedPlatformValue}_apikey`);
                        modelInput.value = getFromStorage(`translator_platform_${selectedPlatformValue}_model_id`);
                        if (selectedPlatformValue === 'custom') {
                            baseUrlGroup.classList.remove('hidden');
                            baseUrlInput.required = true;
                            baseUrlInput.value = getFromStorage('translator_platform_custom_base_url');
                        } else {
                            baseUrlGroup.classList.add('hidden');
                            baseUrlInput.required = false;
                            baseUrlInput.value = selectedPlatformValue;
                        }
                        saveToStorage('translator_last_platform', selectedPlatformValue);
                    }

                    loadSettings();

                    platformSelect.addEventListener('change', updatePlatformUI);
                    apikeyInput.addEventListener('input', (e) => saveToStorage(`translator_platform_${platformSelect.value}_apikey`, e.target.value));
                    modelInput.addEventListener('input', (e) => saveToStorage(`translator_platform_${platformSelect.value}_model_id`, e.target.value));
                    baseUrlInput.addEventListener('input', (e) => {
                        if (platformSelect.value === 'custom') saveToStorage('translator_platform_custom_base_url', e.target.value);
                    });
                    toLangSelect.addEventListener('change', e => saveToStorage('translator_to_lang', e.target.value));
                    formulaCheckbox.addEventListener('change', e => saveToStorage('translator_formula_ocr', e.target.checked));
                    codeCheckbox.addEventListener('change', e => saveToStorage('translator_code_ocr', e.target.checked));
                    refineCheckbox.addEventListener('change', e => saveToStorage('translator_refine_markdown', e.target.checked));

                    [closeModalButton, closePreviewBtn].forEach(elem => elem.addEventListener('click', () => modal.style.display = 'none'));
                    window.addEventListener('click', (event) => {
                        if (event.target === modal) modal.style.display = 'none';
                    });
                    printFromPreview.addEventListener('click', () => {
                        try {
                            previewFrame.contentWindow.focus();
                            previewFrame.contentWindow.print();
                        } catch (err) {
                            console.error('打印预览内容失败:', err);
                            alert('打印失败，请尝试使用浏览器的打印功能 (Ctrl+P 或 ⌘+P)。');
                        }
                    });

                    // --- Drag and Drop File Handling ---
                    fileDropArea.addEventListener('click', () => {
                        fileInput.click(); // Trigger click on hidden file input
                    });

                    fileInput.addEventListener('change', () => {
                        if (fileInput.files.length > 0) {
                            fileNameDisplay.textContent = `已选择: ${fileInput.files[0].name}`;
                        } else {
                            fileNameDisplay.textContent = '未选择文件';
                        }
                    });

                    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                        fileDropArea.addEventListener(eventName, preventDefaults, false);
                    });

                    function preventDefaults(e) {
                        e.preventDefault();
                        e.stopPropagation();
                    }

                    ['dragenter', 'dragover'].forEach(eventName => {
                        fileDropArea.addEventListener(eventName, () => {
                            fileDropArea.classList.add('drag-over');
                        }, false);
                    });

                    ['dragleave', 'drop'].forEach(eventName => {
                        fileDropArea.addEventListener(eventName, () => {
                            fileDropArea.classList.remove('drag-over');
                        }, false);
                    });

                    fileDropArea.addEventListener('drop', (e) => {
                        const dt = e.dataTransfer;
                        const files = dt.files;

                        if (files.length > 0) {
                            fileInput.files = files; // Assign dropped files to the input
                            fileNameDisplay.textContent = `已选择: ${files[0].name}`;
                            // Manually trigger change event for any listeners on fileInput
                            const event = new Event('change', {bubbles: true});
                            fileInput.dispatchEvent(event);
                        }
                    }, false); \
 \
                    // --- End Drag and Drop ---


                    async function pollLogs() {
                        try {
                            const response = await fetch(`/get-logs?since=${lastLogCount}`);
                            if (!response.ok) {
                                console.warn(`Log polling failed: ${response.status}`);
                                return;
                            }
                            const data = await response.json();
                            if (data.logs && data.logs.length > 0) {
                                data.logs.forEach(log => {
                                    const escapedLog = log.replace(/&/g, "&").replace(/</g, "<").replace(/>/g, ">");
                                    logArea.innerHTML += escapedLog + "<br>";
                                });
                                logArea.scrollTop = logArea.scrollHeight;
                            }
                            lastLogCount = data.total_count;
                        } catch (error) {
                            console.warn("Error polling logs:", error);
                        }
                    }

                    async function pollStatus() {
                        try {
                            const response = await fetch('/get-status');
                            if (!response.ok) {
                                console.warn(`Status polling failed: ${response.status}`);
                                statusMsg.textContent = `状态更新失败 (${response.status})`;
                                statusMsg.className = 'error-message';
                                return;
                            }
                            const status = await response.json();
                            statusMsg.textContent = status.status_message || '正在获取状态...';
                            statusMsg.className = status.error_flag ? 'error-message' : 'success-message';

                            if (!status.is_processing) {
                                stopPolling();
                                submitButton.disabled = false;
                                submitButton.removeAttribute('aria-busy');
                                submitButton.textContent = '开始翻译';
                                submitButton.classList.remove('secondary', 'contrast'); // PicoCSS: remove secondary/contrast
                                submitButton.classList.add('primary');    // PicoCSS: add primary
                                isTranslating = false;

                                if (status.download_ready && !status.error_flag) {
                                    markdownLink.href = status.markdown_url;
                                    markdownLink.setAttribute('download', status.original_filename_stem + '_translated.md');
                                    htmlLink.href = status.html_url;
                                    htmlLink.setAttribute('download', status.original_filename_stem + '_translated.html');

                                    let htmlUrl = status.html_url;
                                    let fileName = status.original_filename_stem;

                                    previewHtmlBtn.onclick = function () {
                                        const currentHtmlUrl = htmlUrl;
                                        const currentFileName = fileName;
                                        fetch(currentHtmlUrl)
                                                .then(resp => {
                                                    if (!resp.ok) throw new Error(`HTTP error ${resp.status}`);
                                                    return resp.text();
                                                })
                                                .then(html => {
                                                    const blob = new Blob([html], {type: 'text/html'});
                                                    const blobUrl = URL.createObjectURL(blob);
                                                    previewFrame.src = blobUrl;
                                                    previewFrame.onload = function () {
                                                        try {
                                                            previewFrame.contentWindow.document.title = currentFileName + '_translated';
                                                            URL.revokeObjectURL(blobUrl);
                                                        } catch (e) {
                                                            console.warn('无法设置iframe标题或释放Blob URL', e);
                                                        }
                                                    };
                                                    modal.style.display = 'block';
                                                })
                                                .catch(err => {
                                                    console.error('预览: 获取HTML内容失败:', err);
                                                    statusMsg.textContent = '获取HTML内容失败，无法预览。';
                                                    statusMsg.className = 'error-message';
                                                });
                                    };

                                    downloadPdfBtn.onclick = function () {
                                        downloadPdfBtn.disabled = true;
                                        downloadPdfBtn.textContent = '准备PDF...';
                                        const currentHtmlUrl = htmlUrl;
                                        const currentFileName = fileName;
                                        const iframe = printFrameEl;

                                        fetch(currentHtmlUrl)
                                                .then(resp => {
                                                    if (!resp.ok) throw new Error(`HTTP error ${resp.status} for PDF HTML`);
                                                    return resp.text();
                                                })
                                                .then(htmlContent => {
                                                    iframe.onload = () => {
                                                        iframe.onload = null;
                                                        try {
                                                            const iframeWindow = iframe.contentWindow;
                                                            if (!iframeWindow) throw new Error("无法访问打印框架。");
                                                            iframeWindow.document.title = currentFileName + '_translated.pdf';
                                                            iframeWindow.focus();
                                                            iframeWindow.print();
                                                        } catch (err) {
                                                            console.error('打印PDF出错:', err);
                                                            statusMsg.textContent = '无法直接生成PDF。请预览HTML后，使用浏览器的打印功能 (Ctrl+P) 保存。';
                                                            statusMsg.className = 'error-message';
                                                        } finally {
                                                            setTimeout(() => {
                                                                downloadPdfBtn.disabled = false;
                                                                downloadPdfBtn.textContent = '下载 PDF';
                                                            }, 2000);
                                                        }
                                                    };
                                                    iframe.srcdoc = htmlContent;
                                                })
                                                .catch(err => {
                                                    console.error('PDF生成: 获取HTML内容失败:', err);
                                                    statusMsg.textContent = '获取HTML内容失败，无法生成PDF。请尝试预览。';
                                                    statusMsg.className = 'error-message';
                                                    downloadPdfBtn.disabled = false;
                                                    downloadPdfBtn.textContent = '下载 PDF';
                                                });
                                    };
                                    downloadBtns.style.display = 'flex';
                                } else {
                                    downloadBtns.style.display = 'none';
                                }
                            } else { // Task is still processing
                                submitButton.textContent = '取消翻译';
                                submitButton.classList.remove('primary');
                                submitButton.classList.add('secondary'); // PicoCSS: use secondary for cancel
                                isTranslating = true;
                                submitButton.disabled = false; // Enable button to allow cancellation
                                submitButton.removeAttribute('aria-busy');
                                downloadBtns.style.display = 'none';
                            }
                        } catch (error) {
                            console.error("Error polling status:", error);
                            statusMsg.textContent = '状态更新出错。';
                            statusMsg.className = 'error-message';
                        }
                    }

                    function startPolling() {
                        stopPolling();
                        lastLogCount = 0;
                        logArea.innerHTML = '';
                        pollLogs(); // Initial poll
                        pollStatus(); // Initial poll
                        logPollIntervalId = setInterval(pollLogs, 2000);
                        statusPollIntervalId = setInterval(pollStatus, 1500);
                    }

                    function stopPolling() {
                        if (logPollIntervalId) clearInterval(logPollIntervalId);
                        if (statusPollIntervalId) clearInterval(statusPollIntervalId);
                        logPollIntervalId = null;
                        statusPollIntervalId = null;
                        setTimeout(pollLogs, 100);
                    }

                    function loadSettings() {
                        platformSelect.value = getFromStorage('translator_last_platform', 'custom');
                        updatePlatformUI(); // This will also load API key and model for the platform
                        toLangSelect.value = getFromStorage('translator_to_lang', '中文');
                        formulaCheckbox.checked = getFromStorage('translator_formula_ocr') === 'true';
                        codeCheckbox.checked = getFromStorage('translator_code_ocr') === 'true';
                        refineCheckbox.checked = getFromStorage('translator_refine_markdown') === 'true';
                    }


                    async function cancelTranslation() {
                        submitButton.disabled = true;
                        submitButton.textContent = '正在取消...';
                        submitButton.setAttribute('aria-busy', 'true');

                        try {
                            const response = await fetch('/cancel-translate', {method: 'POST'});
                            const result = await response.json();

                            if (response.ok && result.cancelled) {
                                statusMsg.textContent = result.message || '取消请求已发送。';
                                statusMsg.className = ''; // Neutral message
                            } else {
                                statusMsg.textContent = result.message || '取消失败。';
                                statusMsg.className = 'error-message';
                                // Re-enable button as "Cancel Translation" if cancellation failed but task might still be running
                                submitButton.disabled = false;
                                submitButton.textContent = '取消翻译';
                                submitButton.removeAttribute('aria-busy');
                            }
                        } catch (error) {
                            console.error('取消请求失败:', error);
                            statusMsg.textContent = '取消请求发送失败。';
                            statusMsg.className = 'error-message';
                            submitButton.disabled = false;
                            submitButton.textContent = '取消翻译'; // Or '开始翻译' if we assume it stopped
                            submitButton.removeAttribute('aria-busy');
                        }
                        // Polling will handle the final state update for the button and status.
                    }

                    form.addEventListener('submit', async function (event) {
                        event.preventDefault();

                        if (isTranslating) {
                            await cancelTranslation();
                            return;
                        }

                        // Validate file input
                        if (fileInput.files.length === 0) {
                            statusMsg.textContent = '请选择一个文件进行翻译。';
                            statusMsg.className = 'error-message';
                            fileNameDisplay.textContent = '请选择文件！';
                            fileDropArea.classList.add('error-message'); // Optional: add error style to drop area
                            setTimeout(() => fileDropArea.classList.remove('error-message'), 2000);
                            return;
                        }


                        stopPolling(); // Stop any existing polling
                        submitButton.disabled = true;
                        submitButton.setAttribute('aria-busy', 'true');
                        submitButton.textContent = '初始化...';
                        logArea.innerHTML = '';
                        statusMsg.textContent = '正在提交任务...';
                        statusMsg.className = '';
                        downloadBtns.style.display = 'none';
                        lastLogCount = 0;

                        const formData = new FormData(form);
                        try {
                            const response = await fetch('/translate', {method: 'POST', body: formData});
                            const result = await response.json();
                            if (response.ok && result.task_started) {
                                statusMsg.textContent = result.message || '任务已开始，正在处理...';
                                statusMsg.className = '';
                                submitButton.textContent = '取消翻译'; // Change button text
                                submitButton.classList.remove('primary');
                                submitButton.classList.add('secondary'); // Change button style
                                isTranslating = true; // Set translation flag
                                submitButton.removeAttribute('aria-busy'); // No longer busy submitting, now in "cancellable" state
                                startPolling(); // Start polling for status and logs
                            } else {
                                statusMsg.textContent = result.message || `请求失败 (${response.status})`;
                                statusMsg.className = 'error-message';
                                submitButton.disabled = false;
                                submitButton.removeAttribute('aria-busy');
                                submitButton.textContent = '开始翻译';
                                isTranslating = false;
                            }
                        } catch (error) {
                            console.error('请求失败:', error);
                            statusMsg.textContent = '请求翻译失败，请检查网络或服务状态。';
                            statusMsg.className = 'error-message';
                            submitButton.disabled = false;
                            submitButton.removeAttribute('aria-busy');
                            submitButton.textContent = '开始翻译';
                            isTranslating = false;
                        }
                    });
                </script>
                </body>
                </html> \
                """

app = FastAPI()

# --- 全局配置 ---
log_queue = asyncio.Queue()
current_state: Dict[str, Any] = {
    "is_processing": False,
    "status_message": "空闲",
    "error_flag": False,
    "download_ready": False,
    "markdown_content": None,
    "html_content": None,
    "original_filename_stem": None,
    "task_start_time": 0,
    "task_end_time": 0,
    "current_task_ref": None,  # Stores the asyncio.Task object
}
templates = Jinja2Templates(directory=".")
MAX_LOG_HISTORY = 200
log_history: List[str] = []


# --- 日志处理器 ---
class QueueAndHistoryHandler(logging.Handler):
    def __init__(self, queue: asyncio.Queue, history: List[str], max_history: int):
        super().__init__()
        self.queue = queue
        self.history = history
        self.max_history = max_history

    def emit(self, record: logging.LogRecord):
        log_entry = self.format(record)
        print(log_entry)
        self.history.append(log_entry)
        if len(self.history) > self.max_history:
            del self.history[:len(self.history) - self.max_history]
        try:
            main_loop = getattr(app.state, "main_event_loop", None)
            if main_loop and main_loop.is_running():
                main_loop.call_soon_threadsafe(self.queue.put_nowait, log_entry)
            else:
                # Fallback if loop isn't available or running (e.g. during shutdown)
                self.queue.put_nowait(log_entry)
        except Exception as e:
            # Avoid crashing the logger if queue operations fail
            print(f"Error putting log to queue: {e}")


# --- 应用生命周期事件 ---
@app.on_event("startup")
async def startup_event():
    app.state.main_event_loop = asyncio.get_running_loop()
    if translater_logger.hasHandlers():
        translater_logger.handlers.clear()
    queue_handler = QueueAndHistoryHandler(log_queue, log_history, MAX_LOG_HISTORY)
    queue_handler.setLevel(logging.INFO)
    queue_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    translater_logger.addHandler(queue_handler)
    translater_logger.propagate = False  # 非常重要，阻止日志向上传播到root logger
    translater_logger.setLevel(logging.INFO)  # 确保 translater_logger 本身的级别是 INFO

    translater_logger.info("应用启动完成，日志队列/历史处理器已清除并重新配置。")

# --- Background Task Logic ---
async def _perform_translation(params: Dict[str, Any], file_contents: bytes, original_filename: str):
    global current_state

    translater_logger.info(f"后台翻译任务开始: 文件 '{original_filename}'")
    current_state["status_message"] = f"正在处理 '{original_filename}'..."

    try:
        translater_logger.info(f"使用 Base URL: {params['base_url']}, Model: {params['model_id']}")
        translater_logger.info(f"文件大小: {len(file_contents)} 字节。目标语言: {params['to_lang']}")
        translater_logger.info(
            f"选项 - 公式: {params['formula_ocr']}, 代码: {params['code_ocr']}, 修正: {params['refine_markdown']}")

        ft = FileTranslater(
            base_url=params['base_url'],
            key=params['apikey'],
            model_id=params['model_id'],
            tips=False
        )
        await ft.translate_bytes_async(
            name=original_filename,
            file=file_contents,
            to_lang=params['to_lang'],
            formula=params['formula_ocr'],
            code=params['code_ocr'],
            refine=params['refine_markdown'],
            save=False
        )

        md_content = ft.export_to_markdown()
        html_content = ft.export_to_html(title=current_state["original_filename_stem"])
        end_time = time.time()
        duration = end_time - current_state["task_start_time"]

        current_state.update({
            "markdown_content": md_content,
            "html_content": html_content,
            "status_message": f"翻译成功！用时 {duration:.2f} 秒。",
            "download_ready": True,
            "error_flag": False,
            "task_end_time": end_time,
        })
        translater_logger.info(f"翻译成功完成，用时 {duration:.2f} 秒。")

    except asyncio.CancelledError:
        end_time = time.time()
        duration = end_time - current_state["task_start_time"]
        translater_logger.info(f"翻译任务 '{original_filename}' 已被取消 (用时 {duration:.2f} 秒).")
        current_state.update({
            "status_message": f"翻译任务已取消（若有转换任务仍会后台进行） (用时 {duration:.2f} 秒).",
            "error_flag": False,
            "download_ready": False,
            "markdown_content": None,
            "html_content": None,
            "task_end_time": end_time,
        })
        # Do not re-raise CancelledError, it's handled.
    except Exception as e:
        end_time = time.time()
        duration = end_time - current_state["task_start_time"]
        error_message = f"翻译失败: {e}"
        translater_logger.error(error_message, exc_info=True)
        # tb_str = traceback.format_exc() # Not used directly, exc_info=True logs it
        current_state.update({
            "status_message": f"翻译过程中发生错误 (用时 {duration:.2f} 秒): {e}",
            "error_flag": True,
            "download_ready": False,
            "markdown_content": None,
            "html_content": None,
            "task_end_time": end_time,
        })
    finally:
        current_state["is_processing"] = False
        current_state["current_task_ref"] = None  # Clear the task reference
        translater_logger.info(f"后台翻译任务 '{original_filename}' 处理结束。")


# --- API Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    return HTMLResponse(content=HTML_TEMPLATE)


@app.post("/translate")
async def handle_translate(
        # No BackgroundTasks needed here for the main task
        base_url: str = Form(...),
        apikey: str = Form(...),
        model_id: str = Form(...),
        to_lang: str = Form("中文"),
        formula_ocr: bool = Form(False),
        code_ocr: bool = Form(False),
        refine_markdown: bool = Form(False),
        file: UploadFile = File(...)
):
    global current_state
    if current_state["is_processing"] and \
            current_state["current_task_ref"] and \
            not current_state["current_task_ref"].done():
        return JSONResponse(
            status_code=429,
            content={"task_started": False, "message": "另一个翻译任务正在进行中，请稍后再试。"}
        )

    if not file or not file.filename:  # Check if a file was actually uploaded
        return JSONResponse(
            status_code=400,
            content={"task_started": False, "message": "没有选择文件或文件无效。"}
        )

    current_state["is_processing"] = True  # Set this immediately
    original_filename_for_init = file.filename or "uploaded_file"

    current_state.update({
        "status_message": "任务初始化中...",
        "error_flag": False,
        "download_ready": False,
        "markdown_content": None,
        "html_content": None,
        "original_filename_stem": Path(original_filename_for_init).stem,
        "task_start_time": time.time(),
        "task_end_time": 0,
        "current_task_ref": None,  # Will be set after task creation
    })
    log_history.clear()  # Clear logs for the new task
    log_history.append(translater_logger.handlers[0].format(logging.LogRecord(
        name=translater_logger.name, level=logging.INFO, pathname="", lineno=0,
        msg=f"收到新的翻译请求: {original_filename_for_init}", args=[], exc_info=None, func=""
    )))

    try:
        file_contents = await file.read()
        original_filename = file.filename  # Use the actual filename (already checked it's not None)
        await file.close()

        task_params = {
            "base_url": base_url, "apikey": apikey, "model_id": model_id,
            "to_lang": to_lang, "formula_ocr": formula_ocr,
            "code_ocr": code_ocr, "refine_markdown": refine_markdown,
        }

        loop = asyncio.get_running_loop()
        task = loop.create_task(
            _perform_translation(task_params, file_contents, original_filename)
        )
        current_state["current_task_ref"] = task

        return JSONResponse(content={"task_started": True, "message": "翻译任务已成功启动，请稍候..."})
    except Exception as e:
        translater_logger.error(f"启动翻译任务失败: {e}", exc_info=True)
        current_state["is_processing"] = False  # Reset processing flag
        current_state["status_message"] = f"启动任务失败: {e}"
        current_state["error_flag"] = True
        current_state["current_task_ref"] = None  # Ensure task ref is cleared
        return JSONResponse(status_code=500, content={"task_started": False, "message": f"启动翻译任务时出错: {e}"})


@app.post("/cancel-translate")
async def cancel_translate_task():
    global current_state
    if not current_state["is_processing"] or not current_state["current_task_ref"]:
        return JSONResponse(
            status_code=400,
            content={"cancelled": False, "message": "没有正在进行的翻译任务可取消。"}
        )

    task_to_cancel: Optional[asyncio.Task] = current_state["current_task_ref"]

    if not task_to_cancel or task_to_cancel.done():
        # Task might have finished or been cancelled just before this request arrived
        current_state["is_processing"] = False  # Ensure state consistency
        current_state["current_task_ref"] = None
        return JSONResponse(
            status_code=400,
            content={"cancelled": False, "message": "任务已完成或已被取消。"}
        )

    translater_logger.info("收到取消翻译任务的请求。")
    task_to_cancel.cancel()
    current_state["status_message"] = "正在取消任务..."  # Optimistic update

    try:
        # Give the task a moment to process cancellation
        await asyncio.wait_for(task_to_cancel, timeout=2.0)
    except asyncio.CancelledError:
        translater_logger.info("任务已成功取消并结束。")
        # State update (is_processing=False, status_message="已取消") is handled by _perform_translation's finally/except block
    except asyncio.TimeoutError:
        translater_logger.warning("任务取消请求已发送，但任务未在2秒内结束。可能仍在清理中。")
        # The task is cancelled, but it might take longer. Frontend polling will get the final state.
    except Exception as e:
        # This might happen if the task errored out while we were waiting for it after cancellation.
        translater_logger.error(f"等待任务取消时发生意外错误: {e}")
        # The task's own error handling should manage state.

    # The final state (is_processing=False, specific status message) will be set by _perform_translation.
    # This endpoint just initiates the cancellation.
    return JSONResponse(content={"cancelled": True, "message": "取消请求已发送。请等待状态更新。"})


@app.get("/get-status")
async def get_status():
    global current_state
    status_data = {
        "is_processing": current_state["is_processing"],
        "status_message": current_state["status_message"],
        "error_flag": current_state["error_flag"],
        "download_ready": current_state["download_ready"],
        "original_filename_stem": current_state["original_filename_stem"],
        "markdown_url": f"/download/markdown/{current_state['original_filename_stem']}_translated.md" if current_state[
                                                                                                             "download_ready"] and
                                                                                                         current_state[
                                                                                                             "original_filename_stem"] else None,
        "html_url": f"/download/html/{current_state['original_filename_stem']}_translated.html" if current_state[
                                                                                                       "download_ready"] and
                                                                                                   current_state[
                                                                                                       "original_filename_stem"] else None,
        "task_start_time": current_state["task_start_time"],
        "task_end_time": current_state["task_end_time"],
    }
    return JSONResponse(content=status_data)


@app.get("/get-logs")
async def get_logs(since: int = 0):
    global log_history
    # Ensure 'since' is within bounds
    since = max(0, min(since, len(log_history)))
    new_logs = log_history[since:]
    return JSONResponse(content={"logs": new_logs, "total_count": len(log_history)})


@app.get("/download/markdown/{filename_with_ext}")
async def download_markdown(filename_with_ext: str):
    if not current_state["download_ready"] or not current_state["markdown_content"] or not current_state[
        "original_filename_stem"]:
        raise HTTPException(status_code=404, detail="Markdown 内容尚未准备好或不可用。")

    # Basic check to prevent arbitrary filename access, though content is from current_state
    requested_stem = Path(filename_with_ext).stem.replace("_translated", "")
    if requested_stem != current_state["original_filename_stem"]:
        raise HTTPException(status_code=404, detail="请求的文件名与当前结果不符。")

    actual_filename = f"{current_state['original_filename_stem']}_translated.md"
    return StreamingResponse(
        io.StringIO(current_state["markdown_content"]),
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=\"{actual_filename}\""}
    )


@app.get("/download/html/{filename_with_ext}")
async def download_html(filename_with_ext: str):
    if not current_state["download_ready"] or not current_state["html_content"] or not current_state[
        "original_filename_stem"]:
        raise HTTPException(status_code=404, detail="HTML 内容尚未准备好或不可用。")

    requested_stem = Path(filename_with_ext).stem.replace("_translated", "")
    if requested_stem != current_state["original_filename_stem"]:
        raise HTTPException(status_code=404, detail="请求的文件名与当前结果不符。")

    actual_filename = f"{current_state['original_filename_stem']}_translated.html"
    return HTMLResponse(
        content=current_state["html_content"],
        media_type="text/html",  # For direct viewing, browser decides on download based on Content-Disposition
        headers={"Content-Disposition": f"attachment; filename=\"{actual_filename}\""}  # Prompts download
    )


def run_app():
    print("正在启动 DocuTranslate")
    print("请访问 http://127.0.0.1:8010")
    uvicorn.run(app, host="127.0.0.1", port=8010, workers=1)


if __name__ == "__main__":
    run_app()
