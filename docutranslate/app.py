import asyncio
import io
import logging
import socket
import time
from contextlib import asynccontextmanager, closing
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import quote

import uvicorn
from fastapi import FastAPI, File, Form, UploadFile, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from docutranslate import FileTranslater, __version__
from docutranslate.logger import translater_logger
from docutranslate.utils.resource_utils import resource_path
from docutranslate.global_values import available_packages

# --- 全局配置 ---
log_queue: Optional[asyncio.Queue] = None
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
    "current_task_ref": None,
}
MAX_LOG_HISTORY = 200
log_history: List[str] = []


# --- 日志处理器 ---
class QueueAndHistoryHandler(logging.Handler):
    def __init__(self, queue_ref: asyncio.Queue, history_list_ref: List[str], max_history_items: int):
        super().__init__()
        self.queue = queue_ref
        self.history_list = history_list_ref
        self.max_history = max_history_items

    def emit(self, record: logging.LogRecord):
        log_entry = self.format(record)
        print(log_entry)  # Keep console log for server visibility
        self.history_list.append(log_entry)
        if len(self.history_list) > self.max_history:
            del self.history_list[:len(self.history_list) - self.max_history]

        if self.queue is not None:
            try:
                main_loop = getattr(app.state, "main_event_loop", None)
                if main_loop and main_loop.is_running():
                    main_loop.call_soon_threadsafe(self.queue.put_nowait, log_entry)
                else:
                    self.queue.put_nowait(log_entry)
            except asyncio.QueueFull:
                print(f"Log queue is full. Log dropped: {log_entry}")
            except Exception as e:
                print(f"Error putting log to queue: {e}. Log: {log_entry}")


# --- 应用生命周期事件 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global log_queue
    app.state.main_event_loop = asyncio.get_running_loop()
    log_queue = asyncio.Queue()

    for handler in translater_logger.handlers[:]:
        translater_logger.removeHandler(handler)

    queue_handler = QueueAndHistoryHandler(log_queue, log_history, MAX_LOG_HISTORY)
    queue_handler.setLevel(logging.INFO)
    queue_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    translater_logger.addHandler(queue_handler)
    translater_logger.propagate = False
    translater_logger.setLevel(logging.INFO)

    log_history.clear()
    while not log_queue.empty():
        try:
            log_queue.get_nowait()
        except asyncio.QueueEmpty:
            break

    translater_logger.info("应用启动完成，日志队列/历史处理器已正确配置。")
    yield


app = FastAPI(lifespan=lifespan)

STATIC_DIR = resource_path("static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# --- Background Task Logic ---
async def _perform_translation(params: Dict[str, Any], file_contents: bytes, original_filename: str):
    global current_state

    translater_logger.info(f"后台翻译任务开始: 文件 '{original_filename}'")
    current_state["status_message"] = f"正在处理 '{original_filename}'..."

    try:
        translater_logger.info(f"使用 Base URL: {params['base_url']}, Model: {params['model_id']}")
        translater_logger.info(f"文件大小: {len(file_contents)} 字节。目标语言: {params['to_lang']}")
        translater_logger.info(f"使用转换引擎: {params['convert_engin']}")
        translater_logger.info(
            f"选项 - 公式: {params['formula_ocr']}, 代码: {params['code_ocr']}, 修正: {params['refine_markdown']}")

        ft = FileTranslater(
            base_url=params['base_url'],
            key=params['apikey'],
            model_id=params['model_id'],
            convert_engin=params['convert_engin'],
            mineru_token=params['mineru_token'],
            tips=False  # Assuming tips are not needed for server-side processing
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
    except Exception as e:
        end_time = time.time()
        duration = end_time - current_state["task_start_time"]
        error_message = f"翻译失败: {e}"
        translater_logger.error(error_message, exc_info=True)
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
        current_state["current_task_ref"] = None
        translater_logger.info(f"后台翻译任务 '{original_filename}' 处理结束。")


# --- API Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    index_path = Path("index.html")  # Adjust if index.html is elsewhere
    if not index_path.exists():
        # Fallback to static dir if not in root
        index_path = STATIC_DIR / "index.html"
        if not index_path.exists():
            raise HTTPException(status_code=404, detail="index.html not found")
    no_cache_headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",  # 兼容 HTTP/1.0
        "Expires": "0",  # 兼容旧版代理/缓存
    }
    return FileResponse(index_path, headers=no_cache_headers)


@app.post("/translate")
async def handle_translate(
        request: Request,  # Added request for potential future use, not strictly needed now
        base_url: str = Form(...),
        apikey: str = Form(...),
        model_id: str = Form(...),
        to_lang: str = Form("中文"),
        formula_ocr: bool = Form(False),
        code_ocr: bool = Form(False),
        refine_markdown: bool = Form(False),
        convert_engin: str = Form(...),  # New parameter
        mineru_token: Optional[str] = Form(None),  # New parameter
        file: UploadFile = File(...)
):
    global current_state, log_queue, log_history
    if current_state["is_processing"] and \
            current_state["current_task_ref"] and \
            not current_state["current_task_ref"].done():
        return JSONResponse(
            status_code=429,
            content={"task_started": False, "message": "另一个翻译任务正在进行中，请稍后再试。"}
        )

    if not file or not file.filename:
        return JSONResponse(
            status_code=400,
            content={"task_started": False, "message": "没有选择文件或文件无效。"}
        )

    if convert_engin == "mineru" and (not mineru_token or not mineru_token.strip()):
        return JSONResponse(
            status_code=400,
            content={"task_started": False, "message": "使用 Mineru 引擎时必须提供有效的 Mineru Token。"}
        )

    current_state["is_processing"] = True
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
        "current_task_ref": None,
    })

    log_history.clear()
    if log_queue:
        while not log_queue.empty():
            try:
                log_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    initial_log_msg = f"收到新的翻译请求: {original_filename_for_init}"
    if translater_logger.handlers and isinstance(translater_logger.handlers[0], QueueAndHistoryHandler):
        record = logging.LogRecord(
            name=translater_logger.name, level=logging.INFO, pathname="", lineno=0,
            msg=initial_log_msg, args=(), exc_info=None, func=""
        )
        translater_logger.handlers[0].emit(record)
    else:
        translater_logger.info(initial_log_msg)

    try:
        file_contents = await file.read()
        original_filename = file.filename
        await file.close()

        task_params = {
            "base_url": base_url, "apikey": apikey, "model_id": model_id,
            "to_lang": to_lang, "formula_ocr": formula_ocr,
            "code_ocr": code_ocr, "refine_markdown": refine_markdown,
            "convert_engin": convert_engin,  # Pass to task
            "mineru_token": mineru_token,  # Pass to task
        }

        loop = asyncio.get_running_loop()
        task = loop.create_task(
            _perform_translation(task_params, file_contents, original_filename)
        )
        current_state["current_task_ref"] = task

        return JSONResponse(content={"task_started": True, "message": "翻译任务已成功启动，请稍候..."})
    except Exception as e:
        translater_logger.error(f"启动翻译任务失败: {e}", exc_info=True)
        current_state["is_processing"] = False
        current_state["status_message"] = f"启动任务失败: {e}"
        current_state["error_flag"] = True
        current_state["current_task_ref"] = None
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
        current_state["is_processing"] = False
        current_state["current_task_ref"] = None
        return JSONResponse(
            status_code=400,
            content={"cancelled": False, "message": "任务已完成或已被取消。"}
        )

    translater_logger.info("收到取消翻译任务的请求。")
    task_to_cancel.cancel()
    current_state["status_message"] = "正在取消任务..."

    try:
        await asyncio.wait_for(task_to_cancel, timeout=2.0)
    except asyncio.CancelledError:
        translater_logger.info("任务已成功取消并结束。")
    except asyncio.TimeoutError:
        translater_logger.warning("任务取消请求已发送，但任务未在2秒内结束。可能仍在清理中。")
    except Exception as e:
        translater_logger.error(f"等待任务取消时发生意外错误: {e}")

    return JSONResponse(content={"cancelled": True, "message": "取消请求已发送。请等待状态更新。"})


@app.get("/get-engin-list")
async def get_engin_list():
    engin_list = ["mineru"]
    if available_packages.get("docling"):
        engin_list.append("docling")
    return JSONResponse(content=engin_list)


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
async def get_logs_from_queue():
    global log_queue
    new_logs = []
    if log_queue:
        while not log_queue.empty():
            try:
                log_entry = log_queue.get_nowait()
                new_logs.append(log_entry)
                log_queue.task_done()
            except asyncio.QueueEmpty:
                break
    return JSONResponse(content={"logs": new_logs})


@app.get("/download/markdown/{filename_with_ext}")
async def download_markdown(filename_with_ext: str):
    if not current_state["download_ready"] or not current_state["markdown_content"] or not current_state[
        "original_filename_stem"]:
        raise HTTPException(status_code=404, detail="Markdown 内容尚未准备好或不可用。")

    requested_stem = Path(filename_with_ext).stem.replace("_translated", "")
    if requested_stem != current_state["original_filename_stem"]:
        raise HTTPException(status_code=404, detail="请求的文件名与当前结果不符。")

    actual_filename = f"{current_state['original_filename_stem']}_translated.md"
    return StreamingResponse(
        io.StringIO(current_state["markdown_content"]),
        media_type="text/markdown",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(actual_filename, safe='', encoding='utf-8')}"}
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
        media_type="text/html",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(actual_filename, safe='', encoding='utf-8')}"}
    )


@app.get("/meta")
async def get_app_version():
    return JSONResponse(content={"version": __version__})


def find_free_port(start_port):
    """从指定端口开始查找可用的端口"""
    port = start_port
    while True:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            if sock.connect_ex(('127.0.0.1', port)) != 0:  # 端口可用
                return port
            port += 1  # 端口被占用，尝试下一个端口


def run_app():
    initial_port = 8010
    try:
        # 首先检查初始端口是否可用
        port = find_free_port(initial_port)
        if port != initial_port:
            print(f"端口 {initial_port} 被占用，将使用端口 {port} 代替")
        print("正在启动 DocuTranslate WebUI")
        print(f"请访问 http://127.0.0.1:{port} （ctrl+点击链接即可打开）")
        uvicorn.run(app, host="127.0.0.1", port=port, workers=1)
    except Exception as e:
        print(f"启动失败: {e}")


if __name__ == "__main__":
    run_app()
