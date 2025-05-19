import asyncio
import io
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import quote

import uvicorn
from fastapi import FastAPI, File, Form, UploadFile, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse,FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from docutranslate import FileTranslater
from docutranslate.logger import translater_logger
from docutranslate.utils.resource_utils import resource_path

app = FastAPI()

STATIC_DIR=resource_path("static")

# print(f"__file__:{Path(__file__).resolve()}")
app.mount("/static",StaticFiles(directory=STATIC_DIR), name="static")

# --- 全局配置 ---
log_queue: Optional[asyncio.Queue] = None  # Will be initialized in startup_event
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
templates = Jinja2Templates(directory=".")
MAX_LOG_HISTORY = 200  # Max items for the persistent log_history list
log_history: List[str] = []  # Keeps a longer history, not directly for "unread"


# --- 日志处理器 ---
class QueueAndHistoryHandler(logging.Handler):
    def __init__(self, queue_ref: asyncio.Queue, history_list_ref: List[str], max_history_items: int):
        super().__init__()
        self.queue = queue_ref
        self.history_list = history_list_ref
        self.max_history = max_history_items

    def emit(self, record: logging.LogRecord):
        log_entry = self.format(record)

        # Add to the persistent history (capped)
        self.history_list.append(log_entry)
        if len(self.history_list) > self.max_history:
            del self.history_list[:len(self.history_list) - self.max_history]

        # Add to the "unread" queue for frontend consumption
        try:
            # Ensure self.queue is not None (it's initialized at startup)
            if self.queue is not None:
                main_loop = getattr(app.state, "main_event_loop", None)
                if main_loop and main_loop.is_running():
                    main_loop.call_soon_threadsafe(self.queue.put_nowait, log_entry)
                else:
                    self.queue.put_nowait(log_entry)  # Fallback
            else:
                print(f"CRITICAL: Log queue not initialized. Log: {log_entry}")
        except asyncio.QueueFull:
            print(f"Log queue is full. Log dropped: {log_entry}")  # Or handle differently
        except Exception as e:
            print(f"Error putting log to queue: {e}. Log: {log_entry}")


# --- 应用生命周期事件 ---
@app.on_event("startup")
async def startup_event():
    global log_queue
    app.state.main_event_loop = asyncio.get_running_loop()
    log_queue = asyncio.Queue()  # Initialize the global log_queue

    for handler in translater_logger.handlers[:]:
        translater_logger.removeHandler(handler)

    queue_handler = QueueAndHistoryHandler(log_queue, log_history, MAX_LOG_HISTORY)
    queue_handler.setLevel(logging.INFO)
    queue_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    translater_logger.addHandler(queue_handler)
    translater_logger.propagate = False
    translater_logger.setLevel(logging.INFO)

    log_history.clear()
    while not log_queue.empty():  # Clear queue just in case
        try:
            log_queue.get_nowait()
        except asyncio.QueueEmpty:
            break

    translater_logger.info("应用启动完成，日志队列/历史处理器已正确配置。")


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
            "error_flag": False,  # Cancellation is not an error in this context
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
    return FileResponse(STATIC_DIR/"index.html")


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

    # Clear logs for the new task
    log_history.clear()
    if log_queue:  # Ensure log_queue is initialized
        while not log_queue.empty():
            try:
                log_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    # Add initial log entry for the new task
    # We create a LogRecord manually to ensure it goes through the formatter and handler
    initial_log_msg = f"收到新的翻译请求: {original_filename_for_init}"
    if translater_logger.handlers and isinstance(translater_logger.handlers[0], QueueAndHistoryHandler):
        # Use the existing handler to format and queue/store the log
        record = logging.LogRecord(
            name=translater_logger.name, level=logging.INFO, pathname="", lineno=0,
            msg=initial_log_msg, args=(), exc_info=None, func=""
        )
        translater_logger.handlers[0].emit(record)  # This will add to both queue and history
    else:  # Fallback if handler setup is unusual
        translater_logger.info(initial_log_msg)

    try:
        file_contents = await file.read()
        original_filename = file.filename
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
async def get_logs_from_queue():  # Renamed for clarity, though path is the same
    global log_queue
    new_logs = []
    if log_queue:  # Ensure log_queue is initialized
        while not log_queue.empty():
            try:
                log_entry = log_queue.get_nowait()  # Consume from queue
                new_logs.append(log_entry)
                log_queue.task_done()  # Important for queue management if using join() elsewhere
            except asyncio.QueueEmpty:
                break
                # No total_count, as the frontend just appends what it receives
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
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(actual_filename, safe='', encoding='utf-8')}"}
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
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(actual_filename, safe='', encoding='utf-8')}"}
    )


def run_app():
    print("正在启动 DocuTranslate")
    print("请访问 http://127.0.0.1:8010")
    uvicorn.run(app, host="127.0.0.1", port=8010, workers=1)


if __name__ == "__main__":
    run_app()
