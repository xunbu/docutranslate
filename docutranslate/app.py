import asyncio
import io
import logging
import time
from pathlib import Path
from typing import AsyncGenerator, List, Dict, Any
import traceback

import uvicorn
from fastapi import FastAPI, File, Form, UploadFile, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from docutranslate import FileTranslater
from docutranslate.logger import translater_logger

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
        self.history.append(log_entry)
        if len(self.history) > self.max_history:
            del self.history[:len(self.history) - self.max_history]
        try:
            main_loop = getattr(app.state, "main_event_loop", None)
            if main_loop and main_loop.is_running():
                main_loop.call_soon_threadsafe(self.queue.put_nowait, log_entry)
            else:
                self.queue.put_nowait(log_entry)
        except Exception as e:
            print(f"Error putting log to queue: {e}")


# --- 应用生命周期事件 ---
@app.on_event("startup")
async def startup_event():
    app.state.main_event_loop = asyncio.get_running_loop()
    queue_handler = QueueAndHistoryHandler(log_queue, log_history, MAX_LOG_HISTORY)
    queue_handler.setLevel(logging.INFO)
    queue_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    if not any(isinstance(h, QueueAndHistoryHandler) for h in translater_logger.handlers):
        translater_logger.addHandler(queue_handler)
        translater_logger.propagate = False
        translater_logger.setLevel(logging.INFO)
    translater_logger.info("应用启动完成，日志队列/历史处理器已配置。")


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
        :root { --primary-color: #1e88e5; --border-radius: 0.25rem; }
        body { padding: 20px; background-color: #f9f9f9; }
        .container { max-width: 800px; margin: auto; background-color: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05); }
        h1 { font-size: 1.8rem; margin-bottom: 1.5rem; color: var(--primary-color); display: flex; align-items: center; gap: 0.5rem; }
        .log-area { background-color: #f5f5f5; border: 1px solid #e0e0e0; border-radius: var(--border-radius); padding: 10px; height: 200px; overflow-y: scroll; white-space: pre-wrap; word-break: break-all; font-family: monospace; font-size: 0.85em; line-height: 1.4; margin-top: 1rem; }
        .error-message { color: #d32f2f; font-weight: 500; }
        .success-message { color: #2e7d32; font-weight: 500; }
        .form-group { margin-bottom: 1rem; }
        .form-group label { margin-bottom: 0.2rem; font-weight: 500; font-size: 0.9rem; }
        .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
        .button-group { margin-top: 1rem; display: flex; gap: 0.5rem; flex-wrap: wrap; }
        details { background: transparent; border: none; box-shadow: none; padding: 0; border-bottom: 1px solid #eee; margin-bottom: 1rem; }
        summary { font-weight: 500; padding: 0.5rem 0; }
        details[open] > summary { border-bottom: none; margin-bottom: 0; }
        .checkbox-label { display: flex; align-items: center; margin-right: 1rem; margin-bottom: 0.5rem; }
        .checkbox-group { display: flex; flex-wrap: wrap; margin-bottom: 1rem; }
        #resultArea { margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #eee; }
        #downloadButtons { display: none; margin-top: 1rem; }
        .section-header { display: flex; align-items: center; margin-bottom: 0.5rem; font-size: 1.1rem; font-weight: 500; }
        select, input[type="text"], input[type="password"], input[type="file"] { padding: 0.5rem; border: 1px solid #ddd; border-radius: var(--border-radius); background-color: white; }
        button, a[role="button"] { padding: 0.5rem 1rem; }
        .options-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem; }
        @media print { .no-print { display: none !important; } body { padding: 0; background-color: white; } .container { box-shadow: none; max-width: 100%; padding: 0; } }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0, 0, 0, 0.6); z-index: 1000; overflow: auto; }
        .modal-content { position: relative; background-color: #fff; margin: 2% auto; padding: 20px; width: 90%; max-width: 900px; max-height: 90vh; border-radius: 8px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2); overflow: auto; }
        .close-modal { position: absolute; top: 10px; right: 10px; font-size: 24px; font-weight: bold; color: #666; cursor: pointer; }
        .modal-actions { display: flex; justify-content: flex-end; margin-top: 20px; gap: 10px; }
        #previewFrame { width: 100%; min-height: 500px; border: 1px solid #ddd; border-radius: var(--border-radius); }
        #printFrame { display: none; }
        .hidden { display: none !important; }
        @media (max-width: 768px) { .form-grid, .options-grid { grid-template-columns: 1fr; } .container { padding: 1rem; } }
    </style>
</head>
<body>
<main class="container no-print">
    <h1>
        <a href="https://github.com/xunbu/docutranslate" target="_blank">DocuTranslate</a>
    </h1>
    <form id="translateForm">
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
                        <option value="https://dashscope.aliyuncs.com/compatible-mode/v1">阿里云百炼</option>
                        <option value="https://www.dmxapi.cn/v1">DMXAPI</option>
                        <option value="https://openrouter.ai/api/v1">OpenRouter</option>
                        <option value="https://ark.cn-beijing.volces.com/api/v3">火山引擎</option>
                        <option value="https://api.siliconflow.cn/v1">硅基流动</option>
                    </select>
                </div>
                <div class="form-group hidden" id="baseUrlGroup">
                    <label for="base_url">API 地址 (Base URL)</label>
                    <input type="text" id="base_url" name="base_url" placeholder="https://api.openai.com/v1">
                </div>
            </div>
            <div class="form-group">
                <label for="apikey">API 密钥</label>
                <input type="password" id="apikey" name="apikey" placeholder="平台对应的API Key" required>
            </div>
            <div class="form-group">
                <label for="model_id">模型 ID</label>
                <input type="text" id="model_id" name="model_id" placeholder="模型id" required>
            </div>
        </details>
        <div class="form-group">
            <label for="file">文档选择</label>
            <input type="file" id="file" name="file" required>
        </div>
        <div class="options-grid">
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
                </select>
            </div>
            <div class="form-group">
                <label>高级选项</label>
                <div class="checkbox-group">
                    <label class="checkbox-label" for="formula_ocr"><input type="checkbox" id="formula_ocr" name="formula_ocr">公式识别</label>
                    <label class="checkbox-label" for="code_ocr"><input type="checkbox" id="code_ocr" name="code_ocr">代码识别</label>
                    <label class="checkbox-label" for="refine_markdown"><input type="checkbox" id="refine_markdown" name="refine_markdown">修正文本（耗时）</label>
                </div>
            </div>
        </div>
        <button type="submit" id="submitButton" class="primary">开始翻译</button>
    </form>
    <div id="resultArea">
        <p id="statusMessage"></p>
        <div id="downloadButtons" class="button-group">
            <div class="section-header">翻译结果</div>
            <a id="downloadMarkdown" href="#" role="button" class="outline">下载 Markdown</a>
            <a id="downloadHtml" href="#" role="button" class="outline">下载 HTML</a>
            <button id="downloadPdf" class="outline">下载 PDF</button>
            <button id="previewHtml" class="outline">预览</button>
        </div>
    </div>
    <div class="section-header" style="margin-top: 1.5rem;">运行日志</div>
    <div class="log-area" id="logArea"></div>
</main>
<div id="previewModal" class="modal">
    <div class="modal-content">
        <span class="close-modal" id="closeModalBtn">×</span>
        <h3>HTML 预览</h3>
        <iframe id="previewFrame"></iframe>
        <div class="modal-actions">
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

    let logPollIntervalId = null;
    let statusPollIntervalId = null;
    let lastLogCount = 0;

    function saveToStorage(key, value) { try { localStorage.setItem(key, value); } catch (e) { console.warn("保存到本地存储失败:", e); } }
    function getFromStorage(key, defaultValue = '') { try { return localStorage.getItem(key) || defaultValue; } catch (e) { console.warn("从本地存储读取失败:", e); return defaultValue; } }

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
    function loadSettings() {
        const lastPlatform = getFromStorage('translator_last_platform', 'custom');
        platformSelect.value = lastPlatform;
        updatePlatformUI();
        toLangSelect.value = getFromStorage('translator_to_lang', '中文');
        formulaCheckbox.checked = getFromStorage('translator_formula_ocr') === 'true';
        codeCheckbox.checked = getFromStorage('translator_code_ocr') === 'true';
        refineCheckbox.checked = getFromStorage('translator_refine_markdown') === 'true';
    }
    loadSettings();

    platformSelect.addEventListener('change', updatePlatformUI);
    apikeyInput.addEventListener('input', (e) => saveToStorage(`translator_platform_${platformSelect.value}_apikey`, e.target.value));
    modelInput.addEventListener('input', (e) => saveToStorage(`translator_platform_${platformSelect.value}_model_id`, e.target.value));
    baseUrlInput.addEventListener('input', (e) => { if (platformSelect.value === 'custom') saveToStorage('translator_platform_custom_base_url', e.target.value); });
    toLangSelect.addEventListener('change', e => saveToStorage('translator_to_lang', e.target.value));
    formulaCheckbox.addEventListener('change', e => saveToStorage('translator_formula_ocr', e.target.checked));
    codeCheckbox.addEventListener('change', e => saveToStorage('translator_code_ocr', e.target.checked));
    refineCheckbox.addEventListener('change', e => saveToStorage('translator_refine_markdown', e.target.checked));

    [closeModalButton, closePreviewBtn].forEach(elem => elem.addEventListener('click', () => modal.style.display = 'none'));
    window.addEventListener('click', (event) => { if (event.target === modal) modal.style.display = 'none'; });
    printFromPreview.addEventListener('click', () => {
        try {
            previewFrame.contentWindow.focus();
            previewFrame.contentWindow.print();
        } catch (err) {
            console.error('打印预览内容失败:', err);
            alert('打印失败，请尝试使用浏览器的打印功能 (Ctrl+P 或 ⌘+P)。');
        }
    });

    async function pollLogs() {
        try {
            const response = await fetch(`/get-logs?since=${lastLogCount}`);
            if (!response.ok) {
                console.warn(`Log polling failed: ${response.status}`); return;
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

                if (status.download_ready && !status.error_flag) {
                    markdownLink.href = status.markdown_url;
                    markdownLink.setAttribute('download', status.original_filename_stem + '_translated.md');
                    htmlLink.href = status.html_url;
                    htmlLink.setAttribute('download', status.original_filename_stem + '_translated.html');

                    let htmlUrl = status.html_url; // Stays in scope for click handlers
                    let fileName = status.original_filename_stem; // Stays in scope

                    previewHtmlBtn.onclick = function () {
                        const currentHtmlUrl = htmlUrl;
                        const currentFileName = fileName;
                        fetch(currentHtmlUrl)
                            .then(resp => { if (!resp.ok) throw new Error(`HTTP error ${resp.status}`); return resp.text();})
                            .then(html => {
                                const blob = new Blob([html], {type: 'text/html'});
                                const blobUrl = URL.createObjectURL(blob);
                                previewFrame.src = blobUrl;
                                previewFrame.onload = function () { try { previewFrame.contentWindow.document.title = currentFileName + '_translated'; URL.revokeObjectURL(blobUrl); } catch (e) { console.warn('无法设置iframe标题或释放Blob URL', e); } };
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
                                    iframe.onload = null; // Critical: prevent re-trigger
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
                                        setTimeout(() => { // Re-enable button after a delay
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
            } else {
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
        pollLogs();
        pollStatus();
        logPollIntervalId = setInterval(pollLogs, 2000);
        statusPollIntervalId = setInterval(pollStatus, 1500);
    }

    function stopPolling() {
        if (logPollIntervalId) clearInterval(logPollIntervalId);
        if (statusPollIntervalId) clearInterval(statusPollIntervalId);
        logPollIntervalId = null;
        statusPollIntervalId = null;
        setTimeout(pollLogs, 100); // Final log poll
    }

    form.addEventListener('submit', async function (event) {
        event.preventDefault();
        stopPolling();
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
            const response = await fetch('/translate', { method: 'POST', body: formData });
            const result = await response.json();
            if (response.ok && result.task_started) {
                statusMsg.textContent = result.message || '任务已开始，正在处理...';
                statusMsg.className = '';
                submitButton.textContent = '翻译中...';
                startPolling();
            } else {
                statusMsg.textContent = result.message || `请求失败 (${response.status})`;
                statusMsg.className = 'error-message';
                submitButton.disabled = false;
                submitButton.removeAttribute('aria-busy');
                submitButton.textContent = '开始翻译';
            }
        } catch (error) {
            console.error('请求失败:', error);
            statusMsg.textContent = '请求翻译失败，请检查网络或服务状态。';
            statusMsg.className = 'error-message';
            submitButton.disabled = false;
            submitButton.removeAttribute('aria-busy');
            submitButton.textContent = '开始翻译';
        }
    });
</script>
</body>
</html>
"""


# --- Background Task Logic ---
async def _perform_translation(params: Dict[str, Any], file_contents: bytes, original_filename: str):
    start_time = time.time()
    global current_state
    global log_history

    file_stem = Path(original_filename).stem
    translater_logger.info(f"后台任务开始: 文件 '{original_filename}'")

    current_state.update({
        "status_message": f"正在处理 '{original_filename}'...",
        "error_flag": False,
        "download_ready": False,
        "markdown_content": None,
        "html_content": None,
        "original_filename_stem": file_stem,
        "task_start_time": start_time,
        "task_end_time": 0,
    })
    log_history.clear()
    log_history.append(translater_logger.handlers[0].format(logging.LogRecord(
        name=translater_logger.name, level=logging.INFO, pathname="", lineno=0,
        msg=f"开始处理文件: {original_filename}", args=[], exc_info=None, func=""
    )))

    try:
        translater_logger.info(f"使用 Base URL: {params['base_url']}, Model: {params['model_id']}")
        translater_logger.info(f"文件大小: {len(file_contents)} 字节。目标语言: {params['to_lang']}")
        translater_logger.info(f"选项 - 公式: {params['formula_ocr']}, 代码: {params['code_ocr']}, 修正: {params['refine_markdown']}")

        ft = FileTranslater(
            base_url=params['base_url'],
            key=params['apikey'],
            model_id=params['model_id'],
            tips=False
        )
        await asyncio.to_thread(
            ft.translate_bytes,
            name=original_filename,
            file=file_contents,
            to_lang=params['to_lang'],
            formula=params['formula_ocr'],
            code=params['code_ocr'],
            refine=params['refine_markdown'],
            save=False
        )
        md_content = ft.export_to_markdown()
        html_content = ft.export_to_html(title=file_stem)
        end_time = time.time()
        duration = end_time - start_time

        current_state.update({
            "markdown_content": md_content,
            "html_content": html_content,
            "status_message": f"翻译成功！用时 {duration:.2f} 秒。",
            "download_ready": True,
            "error_flag": False,
            "task_end_time": end_time,
        })
        translater_logger.info(f"翻译成功完成，用时 {duration:.2f} 秒。")
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        error_message = f"翻译失败: {e}"
        translater_logger.error(error_message, exc_info=True)
        tb_str = traceback.format_exc()
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
        translater_logger.info("后台翻译任务结束。")


# --- API Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    return HTMLResponse(content=HTML_TEMPLATE)


@app.post("/translate")
async def handle_translate(
        background_tasks: BackgroundTasks,
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
    if current_state["is_processing"]:
        return JSONResponse(
            status_code=429,
            content={"task_started": False, "message": "另一个翻译任务正在进行中，请稍后再试。"}
        )

    current_state["is_processing"] = True
    current_state.update({
        "status_message": "任务初始化中...",
        "error_flag": False,
        "download_ready": False,
        "markdown_content": None,
        "html_content": None,
        "original_filename_stem": None,
        "task_start_time": 0,
        "task_end_time": 0,
    })
    log_history.clear()
    log_history.append(translater_logger.handlers[0].format(logging.LogRecord(
        name=translater_logger.name, level=logging.INFO, pathname="", lineno=0,
        msg="收到新的翻译请求...", args=[], exc_info=None, func=""
    )))

    try:
        file_contents = await file.read()
        original_filename = file.filename or "uploaded_file"
        await file.close()

        task_params = {
            "base_url": base_url, "apikey": apikey, "model_id": model_id,
            "to_lang": to_lang, "formula_ocr": formula_ocr,
            "code_ocr": code_ocr, "refine_markdown": refine_markdown,
        }
        background_tasks.add_task(_perform_translation, task_params, file_contents, original_filename)
        return JSONResponse(content={"task_started": True, "message": "翻译任务已成功启动，请稍候..."})
    except Exception as e:
        translater_logger.error(f"启动翻译任务失败: {e}", exc_info=True)
        current_state["is_processing"] = False
        current_state["status_message"] = f"启动任务失败: {e}"
        current_state["error_flag"] = True
        return JSONResponse(status_code=500, content={"task_started": False, "message": f"启动翻译任务时出错: {e}"})


@app.get("/get-status")
async def get_status():
    global current_state
    status_data = {
        "is_processing": current_state["is_processing"],
        "status_message": current_state["status_message"],
        "error_flag": current_state["error_flag"],
        "download_ready": current_state["download_ready"],
        "original_filename_stem": current_state["original_filename_stem"],
        "markdown_url": f"/download/markdown/{current_state['original_filename_stem']}_translated.md" if current_state["download_ready"] else None,
        "html_url": f"/download/html/{current_state['original_filename_stem']}_translated.html" if current_state["download_ready"] else None,
        "task_start_time": current_state["task_start_time"],
        "task_end_time": current_state["task_end_time"],
    }
    return JSONResponse(content=status_data)


@app.get("/get-logs")
async def get_logs(since: int = 0):
    global log_history
    since = max(0, min(since, len(log_history)))
    new_logs = log_history[since:]
    return JSONResponse(content={"logs": new_logs, "total_count": len(log_history)})


@app.get("/download/markdown/{filename_with_ext}")
async def download_markdown(filename_with_ext: str):
    if not current_state["download_ready"] or not current_state["markdown_content"] or not current_state["original_filename_stem"]:
        raise HTTPException(status_code=404, detail="Markdown 内容尚未准备好或不可用。")
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
    if not current_state["download_ready"] or not current_state["html_content"] or not current_state["original_filename_stem"]:
        raise HTTPException(status_code=404, detail="HTML 内容尚未准备好或不可用。")
    requested_stem = Path(filename_with_ext).stem.replace("_translated", "")
    if requested_stem != current_state["original_filename_stem"]:
         raise HTTPException(status_code=404, detail="请求的文件名与当前结果不符。")
    actual_filename = f"{current_state['original_filename_stem']}_translated.html"
    return HTMLResponse(
        content=current_state["html_content"],
        media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename=\"{actual_filename}\""}
    )

def run_app():
    print("正在启动 DocuTranslate")
    print("请访问 http://127.0.0.1:8010")
    uvicorn.run(app, host="127.0.0.1", port=8010, workers=1)

if __name__ == "__main__":
    run_app()