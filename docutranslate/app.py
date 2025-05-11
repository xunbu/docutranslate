import asyncio
import io
import logging
import os
from pathlib import Path
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, File, Form, UploadFile, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# 假设这些导入能够正确找到你的库代码
from docutranslate import FileTranslater  # Your existing FileTranslater
from docutranslate.logger import translater_logger  # Your existing logger

os.environ["FASTAPI_RUNNING"] = "true"
app = FastAPI()

# --- 异步队列和自定义日志处理器设置 ---
log_queue = asyncio.Queue()
SHUTDOWN_SENTINEL = object()  # 使用一个唯一的对象作为哨兵


class AsyncQueueHandler(logging.Handler):
    def __init__(self, queue: asyncio.Queue):
        super().__init__()
        self.queue = queue

    def emit(self, record: logging.LogRecord):
        log_entry = self.format(record)
        # 在 FastAPI 应用上下文中运行时，尝试使用 app.state.main_event_loop
        main_loop = getattr(app.state, "main_event_loop", None)
        if main_loop and main_loop.is_running():
            main_loop.call_soon_threadsafe(self.queue.put_nowait, log_entry)
        else:
            # 如果主循环不可用或未运行（例如，在测试中或非常早期的启动/非常晚的关闭阶段）
            # 这是一个备用方案，但不如 call_soon_threadsafe 安全
            try:
                # 如果在主事件循环上下文之外，或者事件循环已停止，
                # put_nowait 可能仍然有效，因为它不依赖于正在运行的特定循环来放置项目
                # 但理想情况下，日志记录应在主循环活跃时发生。
                self.queue.put_nowait(log_entry)
            except RuntimeError:  # 例如，如果队列本身与已关闭的循环关联
                print(f"Error putting log to queue (loop likely closed): {log_entry[:100]}...")  # 记录部分日志以避免过长输出
                self.handleError(record)  # 调用基类的错误处理
            except Exception as e:
                print(f"Error putting log to queue (no main loop/not running): {e}")
                self.handleError(record)


@app.on_event("startup")
async def startup_event():
    app.state.main_event_loop = asyncio.get_running_loop()
    queue_handler = AsyncQueueHandler(log_queue)
    queue_handler.setLevel(logging.INFO)
    ui_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    queue_handler.setFormatter(ui_formatter)
    # 检查 translater_logger 是否已经有这个类型的 handler，避免重复添加
    if not any(isinstance(h, AsyncQueueHandler) for h in translater_logger.handlers):
        translater_logger.addHandler(queue_handler)
    translater_logger.info("Application startup complete. Log queue handler configured.")


@app.on_event("shutdown")
async def shutdown_event():
    translater_logger.info("Application shutting down. Signaling log streamer to stop.")
    # 向队列发送哨兵值以停止日志流生成器
    await log_queue.put(SHUTDOWN_SENTINEL)
    # (可选) 短暂等待，以允许生成器处理哨兵并退出
    await asyncio.sleep(0.1)
    translater_logger.info("Log streamer signaled.")
    # (可选) 清空队列中剩余的日志，如果不想在关闭时处理它们
    # while not log_queue.empty():
    #     try:
    #         log_queue.get_nowait()
    #         log_queue.task_done()
    #     except asyncio.QueueEmpty:
    #         break
    # translater_logger.info("Log queue cleared during shutdown.")


# --- 全局状态 ---
current_translation_state = {
    "markdown_content": None, "html_content": None, "original_filename_stem": None,
    "error": None, "is_processing": False
}
templates = Jinja2Templates(directory=".")  # 假设模板在当前目录或使用字符串模板

# --- HTML 模板字符串 ---
# --- HTML 模板字符串 (修改后) ---
HTML_TEMPLATE_STR = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DocuTranslate</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@latest/css/pico.min.css">
    <style>
        :root {
            --font-size: 14px; /* 减小基础字体大小 */
            --form-element-spacing-vertical: 0.6rem; /* 减小表单元素垂直间距 */
            --form-element-spacing-horizontal: 0.8rem; /* 调整水平间距 */
        }
        body { 
            padding: 15px; /* 减小 body padding */
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
            font-size: var(--font-size);
            line-height: 1.5;
        }
        .container { 
            max-width: 800px; /* 稍微减小容器宽度 */
            margin: auto; 
        }
        h1, h3 {
            margin-bottom: 0.8rem;
        }
        h1 a {
            text-decoration: none;
            color: var(--pico-h1-color);
        }
        h1 a:hover {
            color: var(--pico-primary-hover);
        }

        /* 表单元素 */
        label, legend {
            font-size: 0.9em; /* 标签字体稍小 */
            margin-bottom: 0.2rem;
            font-weight: 500;
        }
        input[type="text"],
        input[type="password"],
        input[type="file"],
        select {
            font-size: 0.9em; /* 输入框字体稍小 */
            padding: 0.4rem 0.6rem; /* 减小输入框内边距 */
            margin-bottom: 0.6rem;
        }
        input[type="file"] {
            padding: 0.3rem 0.5rem;
        }

        /* Details & Summary */
        details {
            background-color: var(--pico-card-background-color);
            border: 1px solid var(--pico-card-border-color);
            border-radius: var(--pico-border-radius);
            padding: 0.8rem; /* 调整内边距 */
            margin-bottom: 1rem;
        }
        summary {
            font-weight: bold;
            cursor: pointer;
            font-size: 0.95em; /* 摘要字体大小 */
            padding: 0.3rem 0;
        }
        details[open] > summary {
            margin-bottom: 0.6rem;
        }

        /* Fieldset and Checkbox */
        fieldset {
            padding: 0.8rem 1rem;
            margin-top: 0.5rem;
            border-radius: var(--pico-border-radius);
        }
        fieldset legend {
            padding: 0 0.5rem;
        }
        label input[type="checkbox"] { 
            margin-right: 0.4rem; 
            vertical-align: middle; 
            width: 0.9em; height: 0.9em; /* 减小复选框大小 */
        }

        /* 按钮 */
        button, a[role="button"] {
            font-size: 0.85em; /* 减小按钮字体 */
            padding: 0.5rem 0.8rem; /* 减小按钮内边距 */
            margin-right: 0.5rem;
        }

        .grid > div { /* PicoCSS grid 的子元素间距 */
            margin-bottom: 0; /* 移除 grid 内部div的默认下边距，依赖 input 的 margin-bottom */
        }
        .form-group { /* 自定义表单组，用于非 grid 布局 */
             margin-bottom: 0.8rem;
        }

        .log-area {
            background-color: #f4f6f8; /* 更柔和的背景色 */
            border: 1px solid #dfe3e6;
            padding: 10px;
            height: 200px; /* 调整高度 */
            overflow-y: scroll;
            white-space: pre-wrap; 
            word-break: break-all; 
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
            font-size: 0.85em; /* 日志字体稍小 */
            margin-top: 1rem; /* 调整上边距 */
            line-height: 1.4;
            border-radius: var(--pico-border-radius);
        }
        .error-message { color: var(--pico-del-color); font-weight: bold; font-size: 0.9em; }
        .success-message { color: var(--pico-ins-color); font-weight: bold; font-size: 0.9em;}

        #resultArea { margin-top: 1.5rem; }
        #downloadButtons { 
            display: none; 
            margin-top: 0.5rem;
            padding: 0.8rem;
            background-color: var(--pico-card-sectionning-background-color);
            border-radius: var(--pico-border-radius);
        }
        #downloadButtons h3 {
            font-size: 1em;
            margin-top: 0;
            margin-bottom: 0.5rem;
        }
        #customLangInput {
            display: none; /* Initially hidden */
            margin-top: 0.3rem;
        }
    </style>
</head>
<body>
    <main class="container">
        <header style="text-align: center; margin-bottom: 1.5rem;">
             <h1><a href="https://github.com/xunbu/docutranslate" target="_blank">📄 DocuTranslate</a></h1>
        </header>

        <form id="translateForm">
            <details open>
                <summary>⚙️ API 配置</summary>
                <div class="grid">
                    <div>
                        <label for="base_url">API 地址</label>
                        <input type="text" id="base_url" name="base_url" placeholder="例如: https://api.example.com/v1" required>
                    </div>
                    <div>
                        <label for="apikey">API 密钥</label>
                        <input type="password" id="apikey" name="apikey" placeholder="您的 API Key" required>
                    </div>
                </div>
                 <div class="form-group">
                    <label for="model_id">模型 ID</label>
                    <input type="text" id="model_id" name="model_id" placeholder="例如: gpt-3.5-turbo" required>
                </div>
            </details>

            <div class="form-group" style="margin-top: 1rem;">
                <label for="file">选择文档</label>
                <input type="file" id="file" name="file" required>
            </div>

            <fieldset>
                <legend>翻译选项</legend>
                <div class="grid">
                    <div>
                        <label for="to_lang_select">目标语言</label>
                        <select id="to_lang_select" name="to_lang_select">
                            <option value="中文">中文 (简体)</option>
                            <option value="English">English</option>
                            <option value="日本語">日本語</option>
                            <option value="한국어">한국어</option>
                            <option value="Français">Français</option>
                            <option value="Español">Español</option>
                            <option value="Deutsch">Deutsch</option>
                            <option value="Русский">Русский</option>
                            <option value="custom">自定义...</option>
                        </select>
                        <input type="text" id="to_lang_custom" name="to_lang_custom" placeholder="输入自定义目标语言">
                    </div>
                     <div> <!-- Placeholder for alignment if needed --> </div>
                </div>
                <div style="margin-top: 0.5rem;">
                    <label for="formula_ocr"><input type="checkbox" id="formula_ocr" name="formula_ocr" role="switch">公式识别</label>
                    <label for="code_ocr"><input type="checkbox" id="code_ocr" name="code_ocr" role="switch">代码块识别</label>
                    <label for="refine_markdown"><input type="checkbox" id="refine_markdown" name="refine_markdown" role="switch">优化 Markdown</label>
                </div>
            </fieldset>

            <button type="submit" id="submitButton" style="margin-top: 1rem;">开始翻译</button>
        </form>

        <div id="resultArea">
            <p id="statusMessage"></p>
            <div id="downloadButtons">
                <h3>下载翻译结果:</h3>
                <a id="downloadMarkdown" href="#" role="button" class="secondary">下载 Markdown (.md)</a>
                <a id="downloadHtml" href="#" role="button" class="secondary">下载 HTML (.html)</a>
            </div>
        </div>

        <h3 style="margin-top:1.5rem;">实时日志：</h3>
        <div class="log-area" id="logArea"></div>
    </main>

    <script>
        const base_url_input = document.getElementById('base_url');
        const apikey_input = document.getElementById('apikey');
        const model_id_input = document.getElementById('model_id');

        const to_lang_select = document.getElementById('to_lang_select');
        const to_lang_custom_input = document.getElementById('to_lang_custom');

        const formula_ocr_input = document.getElementById('formula_ocr');
        const code_ocr_input = document.getElementById('code_ocr');
        const refine_markdown_input = document.getElementById('refine_markdown');

        // Function to show/hide custom language input
        function toggleCustomLangInput() {
            if (to_lang_select.value === 'custom') {
                to_lang_custom_input.style.display = 'block';
                to_lang_custom_input.required = true; // Make custom input required if selected
            } else {
                to_lang_custom_input.style.display = 'none';
                to_lang_custom_input.required = false;
                to_lang_custom_input.value = ''; // Clear custom input if not selected
            }
        }
        to_lang_select.addEventListener('change', toggleCustomLangInput);


        // Load from localStorage
        if (localStorage.getItem('translator_base_url')) base_url_input.value = localStorage.getItem('translator_base_url');
        if (localStorage.getItem('translator_apikey')) apikey_input.value = localStorage.getItem('translator_apikey');
        if (localStorage.getItem('translator_model_id')) model_id_input.value = localStorage.getItem('translator_model_id');

        const storedToLang = localStorage.getItem('translator_to_lang');
        if (storedToLang) {
            // Check if stored value is one of the predefined options
            let foundInSelect = false;
            for (let i = 0; i < to_lang_select.options.length; i++) {
                if (to_lang_select.options[i].value === storedToLang) {
                    to_lang_select.value = storedToLang;
                    foundInSelect = true;
                    break;
                }
            }
            if (!foundInSelect && storedToLang) { // If not in select, it was a custom lang
                to_lang_select.value = 'custom';
                to_lang_custom_input.value = storedToLang;
            }
        } else {
            to_lang_select.value = '中文'; // Default
        }
        toggleCustomLangInput(); // Initial check for custom lang display

        formula_ocr_input.checked = localStorage.getItem('translator_formula_ocr') === 'true';
        code_ocr_input.checked = localStorage.getItem('translator_code_ocr') === 'true';
        refine_markdown_input.checked = localStorage.getItem('translator_refine_markdown') === 'true';

        // Save to localStorage
        function saveToLocalStorage(key, value) { try { localStorage.setItem(key, value); } catch (e) { console.error("Error saving to localStorage:", e); }}
        base_url_input.addEventListener('input', () => saveToLocalStorage('translator_base_url', base_url_input.value));
        apikey_input.addEventListener('input', () => saveToLocalStorage('translator_apikey', apikey_input.value));
        model_id_input.addEventListener('input', () => saveToLocalStorage('translator_model_id', model_id_input.value));

        function saveLanguagePreference() {
            let langValue = to_lang_select.value;
            if (langValue === 'custom') {
                langValue = to_lang_custom_input.value.trim();
            }
            saveToLocalStorage('translator_to_lang', langValue);
        }
        to_lang_select.addEventListener('change', saveLanguagePreference);
        to_lang_custom_input.addEventListener('input', saveLanguagePreference);

        formula_ocr_input.addEventListener('change', () => saveToLocalStorage('translator_formula_ocr', formula_ocr_input.checked));
        code_ocr_input.addEventListener('change', () => saveToLocalStorage('translator_code_ocr', code_ocr_input.checked));
        refine_markdown_input.addEventListener('change', () => saveToLocalStorage('translator_refine_markdown', refine_markdown_input.checked));

        const form = document.getElementById('translateForm');
        const submitButton = document.getElementById('submitButton');
        const logArea = document.getElementById('logArea');
        const statusMessageElement = document.getElementById('statusMessage');
        const downloadButtonsDiv = document.getElementById('downloadButtons');
        const downloadMarkdownLink = document.getElementById('downloadMarkdown');
        const downloadHtmlLink = document.getElementById('downloadHtml');

        if (form && submitButton) {
            form.addEventListener('submit', async function(event) {
                event.preventDefault();
                submitButton.disabled = true;
                submitButton.setAttribute('aria-busy', 'true');
                submitButton.textContent = '翻译中...'; // Shorter text
                if(logArea) logArea.innerHTML = '';
                statusMessageElement.textContent = '';
                statusMessageElement.className = '';
                downloadButtonsDiv.style.display = 'none';

                const formData = new FormData();
                formData.append('base_url', base_url_input.value);
                formData.append('apikey', apikey_input.value);
                formData.append('model_id', model_id_input.value);
                formData.append('file', document.getElementById('file').files[0]);

                let targetLang = to_lang_select.value;
                if (targetLang === 'custom') {
                    targetLang = to_lang_custom_input.value.trim();
                }
                if (!targetLang) { // Basic validation for custom lang
                    statusMessageElement.textContent = '请选择或输入有效的目标语言。';
                    statusMessageElement.className = 'error-message';
                    submitButton.disabled = false;
                    submitButton.removeAttribute('aria-busy');
                    submitButton.textContent = '开始翻译';
                    return;
                }
                formData.append('to_lang', targetLang);

                formData.append('formula_ocr', formula_ocr_input.checked);
                formData.append('code_ocr', code_ocr_input.checked);
                formData.append('refine_markdown', refine_markdown_input.checked);

                try {
                    const response = await fetch('/translate', { method: 'POST', body: formData });
                    const resultData = await response.json(); // Assuming server sends JSON

                    if (response.ok && resultData && !resultData.error) {
                        statusMessageElement.textContent = resultData.message || '翻译成功！';
                        statusMessageElement.className = 'success-message';
                        if (resultData.download_ready) {
                            downloadMarkdownLink.href = resultData.markdown_url;
                            downloadMarkdownLink.setAttribute('download', resultData.original_filename_stem + '_translated.md');
                            downloadHtmlLink.href = resultData.html_url;
                            downloadHtmlLink.setAttribute('download', resultData.original_filename_stem + '_translated.html');
                            downloadButtonsDiv.style.display = 'block';
                        }
                    } else {
                        statusMessageElement.textContent = '翻译失败: ' + (resultData.message || '未知错误');
                        statusMessageElement.className = 'error-message';
                    }
                } catch (error) {
                    console.error('Fetch error:', error);
                    statusMessageElement.textContent = '请求翻译失败，请检查网络或服务状态。错误: ' + error.message;
                    statusMessageElement.className = 'error-message';
                } finally {
                    submitButton.disabled = false;
                    submitButton.removeAttribute('aria-busy');
                    submitButton.textContent = '开始翻译';
                }
            });
        }

        // EventSource for logs (unchanged, but ensure it works with the new layout)
        if (typeof(EventSource) !== "undefined") {
            let eventSource;
            function connectEventSource() {
                if (eventSource) {
                    eventSource.close();
                }
                eventSource = new EventSource("/stream-logs");
                eventSource.onmessage = function(event) {
                    if (logArea && event.data !== ":heartbeat") {
                        const logEntryDiv = document.createElement('div');
                        logEntryDiv.innerHTML = event.data; // Assuming event.data is already HTML escaped and includes <br>
                        logArea.appendChild(logEntryDiv);
                        logArea.scrollTop = logArea.scrollHeight; 
                    }
                };
                eventSource.onerror = function(err) { 
                    console.error("EventSource failed:", err); 
                    if (logArea) {
                        const errorMsgDiv = document.createElement('div');
                        errorMsgDiv.style.color = 'orange';
                        errorMsgDiv.textContent = '日志流连接暂时中断，尝试重连...';
                        logArea.appendChild(errorMsgDiv);
                        logArea.scrollTop = logArea.scrollHeight;
                    }
                    if (eventSource) eventSource.close();
                    setTimeout(connectEventSource, 5000);
                };
            }
            connectEventSource();
        } else { 
            if(logArea) logArea.innerHTML = "抱歉，您的浏览器不支持实时日志更新。";
        }
    </script>
</body>
</html>
"""


# --- FastAPI Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def main_page_get_endpoint(request: Request):
    # Clear log queue only if not processing, to avoid clearing logs of an ongoing task
    # when page is reloaded. However, SSE should keep logs flowing.
    # This logic might be redundant if SSE handles logs independently of page reloads.
    if not current_translation_state["is_processing"]:
        while not log_queue.empty():
            try:
                log_queue.get_nowait();
                log_queue.task_done()
            except asyncio.QueueEmpty:
                break

    context = {"request": request, "config": {}, "message": None, "error": False, "download_ready": False}
    # If you are using Jinja2Templates with a file:
    # return templates.TemplateResponse("your_template_name.html", context)
    # If using the string template:
    jinja_env = templates.env  # Or initialize a Jinja2 Environment if not using FastAPI's templates
    template_obj = jinja_env.from_string(HTML_TEMPLATE_STR)
    return HTMLResponse(content=template_obj.render(context))


async def log_stream_generator() -> AsyncGenerator[str, None]:
    last_heartbeat_time = asyncio.get_event_loop().time()
    heartbeat_interval = 15  # Send heartbeat every 15 seconds
    is_shutting_down = False

    try:
        while not is_shutting_down:  # Loop until sentinel or cancellation
            log_message = None
            try:
                # Wait for a log message with a timeout, so we can send heartbeats
                # and check for shutdown sentinel periodically.
                log_message = await asyncio.wait_for(log_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                # No log message in this interval, proceed to check heartbeat
                pass
            except asyncio.CancelledError:  # Handle cancellation if client disconnects
                translater_logger.info("Log stream generator cancelled by client disconnect.")
                raise  # Re-raise to ensure task cleanup

            if log_message is SHUTDOWN_SENTINEL:
                translater_logger.info("Log stream generator received shutdown sentinel. Exiting.")
                log_queue.task_done()  # Mark sentinel as processed
                is_shutting_down = True
                break  # Exit the loop

            if log_message:  # Process actual log message
                # Basic HTML escaping for log messages to prevent XSS if logs contain HTML/JS
                escaped_message = log_message.replace('&', '&').replace('<', '<').replace('>', '>')
                yield f"data: {escaped_message}<br>\n\n"
                log_queue.task_done()
                last_heartbeat_time = asyncio.get_event_loop().time()  # Reset heartbeat timer on actual data

            current_time = asyncio.get_event_loop().time()
            if current_time - last_heartbeat_time >= heartbeat_interval:
                yield "data: :heartbeat\n\n"
                last_heartbeat_time = current_time

    except asyncio.CancelledError:  # Catch again if cancellation happens outside the get()
        translater_logger.info("Log stream generator task was cancelled externally.")
        # Ensure any pending item in queue due to this generator is marked done IF it was fetched
        # However, at this point, it's safer to just re-raise.
        raise
    finally:
        translater_logger.info("Log stream generator finished.")
        # Ensure the queue is not blocked if join() is ever used elsewhere for this queue.
        # If a log_message was retrieved but not task_done'd before cancellation/sentinel,
        # this could be an issue. The current logic should cover it.


@app.get("/stream-logs")
async def stream_logs_endpoint(request: Request):
    return StreamingResponse(log_stream_generator(), media_type="text/event-stream")


@app.post("/translate", response_class=JSONResponse)
async def handle_translate_endpoint(
        request: Request,  # Keep request if needed for other things, like client IP
        base_url: str = Form(...), apikey: str = Form(...), model_id: str = Form(...),
        to_lang: str = Form("中文"), formula_ocr: bool = Form(False),
        code_ocr: bool = Form(False), refine_markdown: bool = Form(False),
        file: UploadFile = File(...)
):
    if current_translation_state["is_processing"]:
        return JSONResponse(status_code=429, content={"error": True, "message": "另一个翻译任务正在进行中，请稍后再试。"})

    current_translation_state["is_processing"] = True
    # It's good practice to clear the log queue for a new task if appropriate,
    # or ensure old logs don't interfere. The AsyncQueueHandler means logs are
    # continuously added, so clearing here makes sense for a "fresh" log view per task.
    # However, the main page GET also clears it, so be mindful of desired behavior.
    # For now, let's assume logs for a new task should start fresh.
    while not log_queue.empty():
        try:
            item = log_queue.get_nowait()
            if item is SHUTDOWN_SENTINEL:  # Put sentinel back if accidentally removed
                log_queue.put_nowait(SHUTDOWN_SENTINEL)
            log_queue.task_done()
        except asyncio.QueueEmpty:
            break

    translater_logger.info("收到翻译请求。")
    response_data = {"error": False, "message": "", "download_ready": False, "markdown_url": None, "html_url": None,
                     "original_filename_stem": None}

    file_contents = None  # Initialize to ensure it's defined for finally block
    try:
        file_contents = await file.read()  # Read file contents
        original_filename = file.filename if file.filename else "uploaded_file"
        current_translation_state["original_filename_stem"] = Path(original_filename).stem
        response_data["original_filename_stem"] = current_translation_state["original_filename_stem"]

        translater_logger.info(f"文件 '{original_filename}' 已上传, 大小: {len(file_contents)} 字节。")

        ft = FileTranslater(base_url=base_url, key=apikey, model_id=model_id, tips=False)

        # Run the blocking translation task in a separate thread
        await asyncio.to_thread(
            ft.translate_bytes, name=original_filename, file=file_contents, to_lang=to_lang,
            formula=formula_ocr, code=code_ocr, refine=refine_markdown, save=False
            # save=False if handling content in memory
        )

        # Assuming FileTranslater populates its internal state with translated content
        current_translation_state["markdown_content"] = ft.export_to_markdown()
        current_translation_state["html_content"] = ft.export_to_html(
            title=current_translation_state["original_filename_stem"])  # Pass title if your method supports it

        response_data["message"] = "翻译成功！下载链接已生成。"
        response_data["download_ready"] = True
        response_data["markdown_url"] = f"/download/markdown/{response_data['original_filename_stem']}_translated.md"
        response_data["html_url"] = f"/download/html/{response_data['original_filename_stem']}_translated.html"
        translater_logger.info("翻译流程处理完毕。")

    except Exception as e:
        translater_logger.error(f"翻译失败: {e}", exc_info=True)  # exc_info=True for traceback
        response_data["error"] = True
        response_data["message"] = f"翻译过程中发生错误: {str(e)}"
    finally:
        current_translation_state["is_processing"] = False
        if file:  # Ensure file object exists
            await file.close()  # Close the UploadFile object
        # Do not clear file_contents here as it's used by translate_bytes
        # The content is in memory; if it were a temp file, you'd delete it here.

    return JSONResponse(content=response_data)


# --- 下载接口 ---
@app.get("/download/markdown/{filename_with_ext}")
async def download_markdown_endpoint(filename_with_ext: str):  # filename_with_ext from URL
    # Use original_filename_stem from state to construct the expected filename for security/consistency
    if current_translation_state["markdown_content"] and current_translation_state["original_filename_stem"]:
        # Compare requested filename stem with stored stem if necessary, or just use stored stem
        actual_filename = f"{current_translation_state['original_filename_stem']}_translated.md"
        # if Path(filename_with_ext).stem != Path(actual_filename).stem:
        #     raise HTTPException(status_code=404, detail="文件名不匹配或内容不可用。")

        return StreamingResponse(io.StringIO(current_translation_state["markdown_content"]), media_type="text/markdown",
                                 headers={"Content-Disposition": f"attachment; filename=\"{actual_filename}\""})
    raise HTTPException(status_code=404, detail="无 Markdown 翻译内容可用。")


@app.get("/download/html/{filename_with_ext}")
async def download_html_endpoint(filename_with_ext: str):
    if current_translation_state["html_content"] and current_translation_state["original_filename_stem"]:
        actual_filename = f"{current_translation_state['original_filename_stem']}_translated.html"
        # if Path(filename_with_ext).stem != Path(actual_filename).stem:
        #     raise HTTPException(status_code=404, detail="文件名不匹配或内容不可用。")

        return HTMLResponse(content=current_translation_state["html_content"], media_type="text/html",
                            headers={"Content-Disposition": f"attachment; filename=\"{actual_filename}\""})
    raise HTTPException(status_code=404, detail="无 HTML 翻译内容可用。")


# --- Uvicorn 启动 ---
if __name__ == "__main__":
    print("正在启动 FastAPI 文档翻译服务 (使用 asyncio.Queue 和 SSE)...")  # Updated message
    print("请访问 http://127.0.0.1:8010")
    # Consider adding reload_dirs if you have other modules like docutranslate in development
    uvicorn.run(app, host="127.0.0.1", port=8010)  # Removed reload=True for this specific test
    # Add it back if you are actively developing