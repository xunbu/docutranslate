import asyncio
import io
import logging
from pathlib import Path
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, File, Form, UploadFile, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# 导入文档翻译相关模块
from docutranslate import FileTranslater
from docutranslate.logger import translater_logger
# 设置FastAPI运行标识
app = FastAPI()

# --- 全局配置 ---
SHUTDOWN_SENTINEL = object()  # 哨兵对象，用于标识关闭
log_queue = asyncio.Queue()  # 日志队列
current_state = {
    "markdown_content": None,
    "html_content": None,
    "original_filename_stem": None,
    "is_processing": False
}
templates = Jinja2Templates(directory=".")


# --- 日志处理器 ---
class AsyncQueueHandler(logging.Handler):
    def __init__(self, queue: asyncio.Queue):
        super().__init__()
        self.queue = queue

    def emit(self, record: logging.LogRecord):
        log_entry = self.format(record)
        try:
            # 尝试使用主事件循环安全地添加日志到队列
            main_loop = getattr(app.state, "main_event_loop", None)
            if main_loop and main_loop.is_running():
                main_loop.call_soon_threadsafe(self.queue.put_nowait, log_entry)
            else:
                # 备用方案
                self.queue.put_nowait(log_entry)
        except Exception as e:
            print(f"Error putting log to queue: {e}")
            self.handleError(record)


# --- 应用生命周期事件 ---
@app.on_event("startup")
async def startup_event():
    app.state.main_event_loop = asyncio.get_running_loop()
    # 配置日志处理器
    queue_handler = AsyncQueueHandler(log_queue)
    queue_handler.setLevel(logging.INFO)
    queue_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    # 避免重复添加handler
    if not any(isinstance(h, AsyncQueueHandler) for h in translater_logger.handlers):
        translater_logger.addHandler(queue_handler)
    translater_logger.info("应用启动完成，日志队列处理器已配置。")


@app.on_event("shutdown")
async def shutdown_event():
    translater_logger.info("应用正在关闭，通知日志流停止。")
    await log_queue.put(SHUTDOWN_SENTINEL)
    await asyncio.sleep(0.1)  # 给处理器留出时间处理哨兵


# --- HTML模板 ---
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
        body { padding: 20px; font-family: system-ui, -apple-system, sans-serif; background-color: #f9f9f9; }
        .container { max-width: 800px; margin: auto; background-color: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        h1 { font-size: 1.8rem; margin-bottom: 1.5rem; color: var(--primary-color); display: flex; align-items: center; gap: 0.5rem; }
        h1 a { text-decoration: none; }
        h1 a:hover { text-decoration: underline; }
        .log-area { background-color: #f5f5f5; border: 1px solid #e0e0e0; border-radius: var(--border-radius); padding: 10px; height: 200px; overflow-y: scroll; white-space: pre-wrap; word-break: break-all; font-family: monospace; font-size: 0.85em; line-height: 1.4; margin-top: 1rem; }
        .error-message { color: #d32f2f; font-weight: 500; }
        .success-message { color: #2e7d32; font-weight: 500; }
        .form-group { margin-bottom: 1rem; }
        .form-group label { margin-bottom: 0.2rem; display: block; font-weight: 500; font-size: 0.9rem; }
        .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
        .button-group { margin-top: 1rem; display: flex; gap: 0.5rem; flex-wrap: wrap; }
        summary { font-weight: 500; cursor: pointer; padding: 0.5rem 0; }
        details { border-bottom: 1px solid #eee; margin-bottom: 1rem; }
        .checkbox-label { display: flex; align-items: center; margin-right: 1rem; margin-bottom: 0.5rem; }
        .checkbox-label input[type="checkbox"] { margin-right: 0.5rem; }
        .checkbox-group { display: flex; flex-wrap: wrap; margin-bottom: 1rem; }
        #resultArea { margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #eee; }
        #downloadButtons { display: none; margin-top: 1rem; }
        .section-header { display: flex; align-items: center; margin-bottom: 0.5rem; font-size: 1.1rem; font-weight: 500; }
        select, input[type="text"], input[type="password"], input[type="file"] { padding: 0.5rem; border: 1px solid #ddd; border-radius: var(--border-radius); background-color: white; }
        button, a[role="button"] { border-radius: var(--border-radius); padding: 0.5rem 1rem; }
        .options-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem; }
        /* 打印样式 */
        @media print {
            .no-print { display: none !important; }
            body { padding: 0; background-color: white; }
            .container { box-shadow: none; max-width: 100%; padding: 0; }
        }
        /* 预览模态窗口样式 */
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
            position: relative;
            background-color: #fff;
            margin: 2% auto;
            padding: 20px;
            width: 90%;
            max-width: 900px;
            max-height: 90vh;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            overflow: auto;
        }
        .close-modal {
            position: absolute;
            top: 10px;
            right: 10px;
            font-size: 24px;
            font-weight: bold;
            color: #666;
            cursor: pointer;
        }
        .modal-actions {
            display: flex;
            justify-content: flex-end;
            margin-top: 20px;
            gap: 10px;
        }
        #previewFrame {
            width: 100%;
            min-height: 500px;
            border: 1px solid #ddd;
            border-radius: var(--border-radius);
        }
        /* 嵌入式iframe样式 */
        #printFrame { display: none; }
        @media (max-width: 768px) { .form-grid, .options-grid { grid-template-columns: 1fr; } .container { padding: 1rem; } }
    </style>
</head>
<body>
    <main class="container no-print">
        <h1>
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M5 8l6 6"></path><path d="M4 14l6-6 2-3"></path><path d="M2 5l7 7v6"></path>
                <path d="M15 10l6 6"></path><path d="M19 6l-7 7-6 2"></path><path d="M22 5l-7 7v6"></path>
            </svg>
            <a href="https://github.com/xunbu/docutranslate" target="_blank">DocuTranslate</a>
        </h1>

        <form id="translateForm">
            <details>
                <summary>API 配置</summary>
                <div class="form-grid">
                    <div class="form-group">
                        <label for="base_url">API 地址</label>
                        <input type="text" id="base_url" name="base_url" placeholder="如: https://api.openai.com/v1" required>
                    </div>
                    <div class="form-group">
                        <label for="apikey">API 密钥</label>
                        <input type="password" id="apikey" name="apikey" placeholder="sk-..." required>
                    </div>
                </div>
                <div class="form-group">
                    <label for="model_id">模型 ID</label>
                    <input type="text" id="model_id" name="model_id" placeholder="如: gpt-4-turbo-preview" required>
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

    <!-- 预览模态窗口 -->
    <div id="previewModal" class="modal">
        <div class="modal-content">
            <span class="close-modal" id="closeModal">&times;</span>
            <h3>HTML 预览</h3>
            <iframe id="previewFrame"></iframe>
            <div class="modal-actions">
                <button id="printFromPreview" class="primary">打印/保存为PDF</button>
                <button id="closePreviewBtn" class="outline">关闭</button>
            </div>
        </div>
    </div>

    <!-- 用于生成PDF的隐藏iframe -->
    <iframe id="printFrame" style="display:none;"></iframe>

    <script>
        // 加载和保存本地存储的函数
        function loadFromStorage() {
            const inputs = {
                'base_url': 'translator_base_url',
                'apikey': 'translator_apikey',
                'model_id': 'translator_model_id'
            };

            // 加载文本输入
            Object.entries(inputs).forEach(([id, storageKey]) => {
                const value = localStorage.getItem(storageKey);
                if (value) document.getElementById(id).value = value;
            });

            // 加载下拉菜单
            const savedLang = localStorage.getItem('translator_to_lang');
            if (savedLang) {
                const langSelect = document.getElementById('to_lang');
                for (const option of langSelect.options) {
                    if (option.value === savedLang) {
                        option.selected = true;
                        break;
                    }
                }
            }

            // 加载复选框
            ['formula_ocr', 'code_ocr', 'refine_markdown'].forEach(id => {
                const storageKey = 'translator_' + id;
                document.getElementById(id).checked = localStorage.getItem(storageKey) === 'true';
            });
        }

        function saveToStorage(key, value) {
            try { localStorage.setItem(key, value); } 
            catch (e) { console.error("保存到本地存储失败:", e); }
        }

        // 加载保存的值
        loadFromStorage();

        // 设置事件监听器
        ['base_url', 'apikey', 'model_id'].forEach(id => {
            document.getElementById(id).addEventListener('input', e => 
                saveToStorage('translator_' + id, e.target.value));
        });

        document.getElementById('to_lang').addEventListener('change', e => 
            saveToStorage('translator_to_lang', e.target.value));

        ['formula_ocr', 'code_ocr', 'refine_markdown'].forEach(id => {
            document.getElementById(id).addEventListener('change', e => 
                saveToStorage('translator_' + id, e.target.checked));
        });

        // 模态窗口控制
        const modal = document.getElementById('previewModal');
        const previewFrame = document.getElementById('previewFrame');
        const closeModal = document.getElementById('closeModal');
        const closePreviewBtn = document.getElementById('closePreviewBtn');
        const printFromPreview = document.getElementById('printFromPreview');

        // 关闭模态窗口的事件
        [closeModal, closePreviewBtn].forEach(elem => {
            elem.addEventListener('click', () => {
                modal.style.display = 'none';
            });
        });

        // 点击模态窗口外部关闭
        window.addEventListener('click', (event) => {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });

        // 从预览打印PDF
        printFromPreview.addEventListener('click', () => {
            try {
                previewFrame.contentWindow.focus();
                previewFrame.contentWindow.print();
            } catch (err) {
                console.error('打印预览内容失败:', err);
                alert('打印失败，请尝试使用浏览器的打印功能(Ctrl+P或⌘+P)。');
            }
        });

        // 表单提交处理
        const form = document.getElementById('translateForm');
        const submitButton = document.getElementById('submitButton');
        const logArea = document.getElementById('logArea');
        const statusMsg = document.getElementById('statusMessage');
        const downloadBtns = document.getElementById('downloadButtons');
        const markdownLink = document.getElementById('downloadMarkdown');
        const htmlLink = document.getElementById('downloadHtml');
        const previewHtmlBtn = document.getElementById('previewHtml');
        const downloadPdfBtn = document.getElementById('downloadPdf');
        const printFrame = document.getElementById('printFrame');

        form.addEventListener('submit', async function(event) {
            event.preventDefault();

            // 提交前UI状态
            submitButton.disabled = true;
            submitButton.setAttribute('aria-busy', 'true');
            submitButton.textContent = '翻译中...';
            logArea.innerHTML = '';
            statusMsg.textContent = '';
            statusMsg.className = '';
            downloadBtns.style.display = 'none';

            try {
                const response = await fetch('/translate', { 
                    method: 'POST', 
                    body: new FormData(form) 
                });
                const result = await response.json();

                // 处理结果
                statusMsg.textContent = result.message;
                statusMsg.className = result.error ? 'error-message' : 'success-message';

                if (result.download_ready) {
                    // 设置下载链接
                    markdownLink.href = result.markdown_url;
                    markdownLink.setAttribute('download', result.original_filename_stem + '_translated.md');

                    htmlLink.href = result.html_url;
                    htmlLink.setAttribute('download', result.original_filename_stem + '_translated.html');

                    // 预览HTML按钮（使用模态窗口）
                    let htmlUrl = result.html_url;
                    let fileName = result.original_filename_stem;
                    
                    previewHtmlBtn.onclick = function() {
                        // 获取HTML内容并直接加载到iframe中，而不是使用URL
                        fetch(htmlUrl)
                            .then(response => response.text())
                            .then(html => {
                                // 创建一个blob并生成内存URL以避免下载提示
                                const blob = new Blob([html], { type: 'text/html' });
                                const blobUrl = URL.createObjectURL(blob);
                                
                                // 加载blob URL到预览框架
                                previewFrame.src = blobUrl;
                                
                                previewFrame.onload = function() {
                                    // 设置标题
                                    try {
                                        previewFrame.contentWindow.document.title = fileName + '_translated';
                                        // 释放blob URL
                                        URL.revokeObjectURL(blobUrl);
                                    } catch(e) {
                                        console.warn('无法设置iframe标题', e);
                                    }
                                };
                                
                                // 显示模态窗口
                                modal.style.display = 'block';
                            })
                            .catch(err => {
                                console.error('获取HTML内容失败:', err);
                                alert('获取HTML内容失败，无法预览。');
                            });
                    };

                    // PDF下载按钮
                    downloadPdfBtn.onclick = function() {
                        try {
                            // 使用打印API直接生成PDF
                            fetch(htmlUrl)
                                .then(response => response.text())
                                .then(html => {
                                    const iframe = printFrame;
                                    iframe.srcdoc = html;
                                    
                                    iframe.onload = function() {
                                        try {
                                            const iframeWindow = iframe.contentWindow;
                                            iframeWindow.document.title = fileName + '_translated.pdf';
                                            
                                            // 设置一个短暂延迟确保内容完全加载
                                            setTimeout(() => {
                                                iframeWindow.focus();
                                                iframeWindow.print();
                                            }, 500);
                                        } catch (err) {
                                            console.error('打印PDF出错:', err);
                                            alert('无法直接生成PDF，请使用"预览HTML"后，通过浏览器的打印功能保存为PDF。');
                                        }
                                    };
                                })
                                .catch(err => {
                                    console.error('获取HTML内容失败:', err);
                                    alert('获取HTML内容失败，请尝试使用"预览HTML"功能。');
                                });
                        } catch (err) {
                            console.error('PDF生成过程出错:', err);
                            alert('PDF生成失败，请尝试使用"预览HTML"功能后，通过浏览器的打印功能保存为PDF。');
                        }
                    };

                    downloadBtns.style.display = 'block';
                }
            } catch (error) {
                console.error('请求失败:', error);
                statusMsg.textContent = '请求翻译失败，请检查网络或服务状态。';
                statusMsg.className = 'error-message';
            } finally {
                // 恢复按钮状态
                submitButton.disabled = false;
                submitButton.removeAttribute('aria-busy');
                submitButton.textContent = '开始翻译';
            }
        });

        // 日志流事件源
        if (typeof(EventSource) !== "undefined") {
            let eventSource;

            function connectEventSource() {
                if (eventSource) eventSource.close();

                eventSource = new EventSource("/stream-logs");

                eventSource.onmessage = function(event) {
                    if (event.data !== ":heartbeat") { 
                        logArea.innerHTML += event.data;
                        logArea.scrollTop = logArea.scrollHeight;
                    }
                };

                eventSource.onerror = function(err) {
                    console.error("事件源连接失败:", err);
                    const errorMsg = document.createElement('div');
                    errorMsg.style.color = 'orange';
                    errorMsg.textContent = '日志流连接暂时中断，尝试重连...';
                    logArea.appendChild(errorMsg);
                    logArea.scrollTop = logArea.scrollHeight;

                    eventSource.close();
                    setTimeout(connectEventSource, 5000);
                };
            }

            connectEventSource();
        } else {
            logArea.innerHTML = "抱歉，您的浏览器不支持实时日志更新。";
        }
    </script>
</body>
</html>
"""


# --- 日志流处理 ---
async def log_stream_generator() -> AsyncGenerator[str, None]:
    last_heartbeat = asyncio.get_event_loop().time()
    heartbeat_interval = 15  # 15秒发送一次心跳

    try:
        while True:
            try:
                # 等待日志消息，带超时
                log_message = await asyncio.wait_for(log_queue.get(), timeout=1.0)

                # 检查关闭哨兵
                if log_message is SHUTDOWN_SENTINEL:
                    translater_logger.info("日志流收到关闭信号，正在退出。")
                    log_queue.task_done()
                    break

                # 正常处理日志
                escaped_message = log_message.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                yield f"data: {escaped_message}<br>\n\n"
                log_queue.task_done()
                last_heartbeat = asyncio.get_event_loop().time()

            except asyncio.TimeoutError:
                # 超时，检查是否需要发送心跳
                current_time = asyncio.get_event_loop().time()
                if current_time - last_heartbeat >= heartbeat_interval:
                    yield "data: :heartbeat\n\n"
                    last_heartbeat = current_time

            except asyncio.CancelledError:
                translater_logger.info("日志流被取消。")
                raise

    except asyncio.CancelledError:
        translater_logger.info("日志流任务被外部取消。")
        raise
    finally:
        translater_logger.info("日志流生成器结束。")


# --- API端点 ---
@app.get("/", response_class=HTMLResponse)
async def main_page():
    # 如果没有处理中的任务，清空日志队列
    if not current_state["is_processing"]:
        while not log_queue.empty():
            try:
                item = log_queue.get_nowait()
                if item is SHUTDOWN_SENTINEL:
                    await log_queue.put(SHUTDOWN_SENTINEL)
                log_queue.task_done()
            except asyncio.QueueEmpty:
                break

    # 返回HTML模板
    return HTMLResponse(content=HTML_TEMPLATE)


@app.get("/stream-logs")
async def stream_logs():
    return StreamingResponse(log_stream_generator(), media_type="text/event-stream")


@app.post("/translate")
async def handle_translate(
        base_url: str = Form(...),
        apikey: str = Form(...),
        model_id: str = Form(...),
        to_lang: str = Form("中文"),
        formula_ocr: bool = Form(False),
        code_ocr: bool = Form(False),
        refine_markdown: bool = Form(False),
        file: UploadFile = File(...)
):
    # 检查是否有正在进行的任务
    if current_state["is_processing"]:
        return JSONResponse(
            status_code=429,
            content={"error": True, "message": "另一个翻译任务正在进行中，请稍后再试。"}
        )

    # 设置处理状态
    current_state["is_processing"] = True

    # 清空日志队列
    while not log_queue.empty():
        try:
            item = log_queue.get_nowait()
            if item is SHUTDOWN_SENTINEL:
                await log_queue.put(SHUTDOWN_SENTINEL)
            log_queue.task_done()
        except asyncio.QueueEmpty:
            break

    translater_logger.info("收到翻译请求。")
    response_data = {
        "error": False,
        "message": "",
        "download_ready": False,
        "markdown_url": None,
        "html_url": None,
        "original_filename_stem": None
    }

    try:
        # 读取文件内容
        file_contents = await file.read()
        original_filename = file.filename or "uploaded_file"
        file_stem = Path(original_filename).stem

        current_state["original_filename_stem"] = file_stem
        response_data["original_filename_stem"] = file_stem

        translater_logger.info(f"文件 '{original_filename}' 已上传, 大小: {len(file_contents)} 字节。")

        # 创建翻译器并翻译
        ft = FileTranslater(base_url=base_url, key=apikey, model_id=model_id, tips=False)

        # 在单独的线程中运行翻译任务
        await asyncio.to_thread(
            ft.translate_bytes,
            name=original_filename,
            file=file_contents,
            to_lang=to_lang,
            formula=formula_ocr,
            code=code_ocr,
            refine=refine_markdown,
            save=False
        )

        # 保存翻译结果
        current_state["markdown_content"] = ft.export_to_markdown()
        current_state["html_content"] = ft.export_to_html(title=file_stem)

        # 设置响应数据
        response_data["message"] = "翻译成功！下载链接已生成。"
        response_data["download_ready"] = True
        response_data["markdown_url"] = f"/download/markdown/{file_stem}_translated.md"
        response_data["html_url"] = f"/download/html/{file_stem}_translated.html"

        translater_logger.info("翻译流程处理完毕。")

    except Exception as e:
        translater_logger.error(f"翻译失败: {e}", exc_info=True)
        response_data["error"] = True
        response_data["message"] = f"翻译过程中发生错误: {str(e)}"
    finally:
        current_state["is_processing"] = False
        await file.close()

    return JSONResponse(content=response_data)


# --- 下载接口 ---
@app.get("/download/markdown/{filename_with_ext}")
async def download_markdown(filename_with_ext: str):
    if not current_state["markdown_content"] or not current_state["original_filename_stem"]:
        raise HTTPException(status_code=404, detail="无 Markdown 翻译内容可用。")

    actual_filename = f"{current_state['original_filename_stem']}_translated.md"
    return StreamingResponse(
        io.StringIO(current_state["markdown_content"]),
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=\"{actual_filename}\""}
    )


@app.get("/download/html/{filename_with_ext}")
async def download_html(filename_with_ext: str):
    if not current_state["html_content"] or not current_state["original_filename_stem"]:
        raise HTTPException(status_code=404, detail="无 HTML 翻译内容可用。")

    actual_filename = f"{current_state['original_filename_stem']}_translated.html"
    return HTMLResponse(
        content=current_state["html_content"],
        media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename=\"{actual_filename}\""}
    )


# --- 启动服务 ---
if __name__ == "__main__":
    print("正在启动 FastAPI 文档翻译服务...")
    print("请访问 http://127.0.0.1:8010")
    uvicorn.run(app, host="127.0.0.1", port=8010)