# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
"""
DocuTranslate Shared Server Layer

This module provides the shared TranslationService that encapsulates all core
translation task logic, used by both the Web backend (app.py) and MCP server.
"""

import asyncio
import base64
import json
import logging
import os
import shutil
import tempfile
import time
import uuid
from dataclasses import replace
from pathlib import Path
from typing import (
    List,
    Dict,
    Any,
    Optional,
    Type,
)

import httpx
from fastapi import HTTPException

from docutranslate.config import TASK_MAX_COUNT, TEMP_CLEANUP_AGE_HOURS
from docutranslate.core.schemas import TranslatePayload
from docutranslate.core.file_types import detect_workflow
from docutranslate.core.params import resolve_auto_payload
from docutranslate.core.factory import create_workflow_from_payload
from docutranslate.utils.utils import mask_secrets
from docutranslate.workflow.ass_workflow import AssWorkflow
from docutranslate.workflow.base import Workflow
from docutranslate.workflow.docx_workflow import DocxWorkflow
from docutranslate.workflow.epub_workflow import EpubWorkflow
from docutranslate.workflow.html_workflow import HtmlWorkflow
from docutranslate.workflow.interfaces import (
    DocxExportable,
    EpubExportable,
    HTMLExportable,
    MDFormatsExportable,
    TXTExportable,
    JsonExportable,
    XlsxExportable,
    SrtExportable,
    CsvExportable,
    AssExportable,
    PPTXExportable,
)
from docutranslate.workflow.json_workflow import JsonWorkflow
from docutranslate.workflow.md_based_workflow import MarkdownBasedWorkflow
from docutranslate.workflow.pptx_workflow import PPTXWorkflow
from docutranslate.workflow.srt_workflow import SrtWorkflow
from docutranslate.workflow.txt_workflow import TXTWorkflow
from docutranslate.workflow.xlsx_workflow import XlsxWorkflow
from docutranslate.logger import global_logger
from docutranslate.progress import ProgressTracker

MAX_LOG_HISTORY = 200
MAX_LOG_QUEUE = 500

# --- Workflow dictionary ---
WORKFLOW_DICT: Dict[str, Type[Workflow]] = {
    "markdown_based": MarkdownBasedWorkflow,
    "txt": TXTWorkflow,
    "json": JsonWorkflow,
    "xlsx": XlsxWorkflow,
    "docx": DocxWorkflow,
    "srt": SrtWorkflow,
    "epub": EpubWorkflow,
    "html": HtmlWorkflow,
    "ass": AssWorkflow,
    "pptx": PPTXWorkflow,
}


# --- Media types mapping ---
MEDIA_TYPES = {
    "html": "text/html; charset=utf-8",
    "markdown": "text/markdown; charset=utf-8",
    "markdown_zip": "application/zip",
    "txt": "text/plain; charset=utf-8",
    "json": "application/json; charset=utf-8",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv": "text/csv; charset=utf-8",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "srt": "text/plain; charset=utf-8",
    "epub": "application/epub+zip",
    "ass": "text/plain; charset=utf-8",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


class QueueAndHistoryHandler(logging.Handler):
    """Logging handler that stores logs in both a history list and an asyncio.Queue."""

    def __init__(
        self,
        queue_ref: asyncio.Queue,
        history_list_ref: List[str],
        max_history_items: int,
        task_id: str,
        event_loop: asyncio.AbstractEventLoop | None = None,
    ):
        super().__init__()
        self.queue = queue_ref
        self.history_list = history_list_ref
        self.max_history = max_history_items
        self.task_id = task_id
        self.event_loop = event_loop
        self.dropped_logs = 0

    def _store(self, masked_log_entry: str) -> None:
        self.history_list.append(masked_log_entry)
        if len(self.history_list) > self.max_history:
            del self.history_list[: len(self.history_list) - self.max_history]
        if self.queue is None:
            return
        if self.queue.full():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
                self.dropped_logs += 1
            except asyncio.QueueEmpty:
                pass
        self.queue.put_nowait(masked_log_entry)

    def emit(self, record: logging.LogRecord):
        try:
            log_entry = self.format(record)
            masked_log_entry = mask_secrets(log_entry)
            print(f"[{self.task_id}] {masked_log_entry}")
            try:
                running_loop = asyncio.get_running_loop()
            except RuntimeError:
                running_loop = None
            if (
                self.event_loop is not None
                and self.event_loop.is_running()
                and running_loop is not self.event_loop
            ):
                self.event_loop.call_soon_threadsafe(self._store, masked_log_entry)
            else:
                self._store(masked_log_entry)
        except Exception:
            self.handleError(record)


def get_workflow_type_from_filename(filename: str) -> str:
    """Get workflow type based on file extension."""
    return detect_workflow(filename)


def _create_default_task_state() -> Dict[str, Any]:
    """Create a new default task state."""
    return {
        "is_processing": False,
        "status_message": "空闲",
        "error_flag": False,
        "cancelled": False,
        "download_ready": False,
        "progress_percent": 0,
        "workflow_instance": None,
        "original_filename_stem": None,
        "task_start_time": 0,
        "task_end_time": 0,
        "current_task_ref": None,
        "original_filename": None,
        "temp_dir": None,
        "downloadable_files": {},
        "attachment_files": {},
        "statistics": None,  # 翻译完成后填充
    }


def _write_bytes(path: str, data: bytes) -> None:
    """同步写盘，供 asyncio.to_thread 调用，避免大文件导出阻塞事件循环。"""
    with open(path, "wb") as f:
        f.write(data)


def cleanup_stale_temp_dirs(max_age_hours: float = TEMP_CLEANUP_AGE_HOURS) -> int:
    """清理上一次进程异常退出后残留的 docutranslate_* 临时目录。

    只删除早于 ``max_age_hours`` 的目录，这样同时运行的其他实例（不同端口）
    不会互相删除正在使用的输出。
    """
    if max_age_hours is None or max_age_hours <= 0:
        return 0
    base_dir = tempfile.gettempdir()
    cutoff = time.time() - max_age_hours * 3600
    removed = 0
    try:
        entries = list(os.scandir(base_dir))
    except OSError:
        return 0
    for entry in entries:
        if not entry.name.startswith("docutranslate_"):
            continue
        try:
            if entry.is_dir() and entry.stat().st_mtime < cutoff:
                shutil.rmtree(entry.path, ignore_errors=True)
                removed += 1
        except OSError:
            continue
    if removed:
        global_logger.info("已清理 %d 个残留的临时目录", removed)
    return removed


class TranslationService:
    """
    Shared translation service that provides core task management functionality.

    This class is used by both the Web backend (app.py) and MCP server to ensure
    consistent task management across both interfaces.
    """

    def __init__(self):
        # Task state storage
        self.tasks_state: Dict[str, Dict[str, Any]] = {}
        self.tasks_log_queues: Dict[str, asyncio.Queue] = {}
        self.tasks_log_histories: Dict[str, List[str]] = {}

        # HTTP client for CDN checks
        self.httpx_client: Optional[httpx.AsyncClient] = None

        # 说明：任务状态在所有协程里都是单线程事件循环串行访问的（没有 await 的
        # 临界区不会被抢占），因此不需要额外锁；此前这里声明过一个从未使用的
        # _lock，容易让人误以为状态访问已被保护，已删除。

        # Reference to main event loop (set by application)
        self.main_event_loop: Optional[asyncio.AbstractEventLoop] = None

    def initialize(self, httpx_client: httpx.AsyncClient, main_event_loop: asyncio.AbstractEventLoop):
        """Initialize the service with HTTP client and event loop."""
        self.httpx_client = httpx_client
        self.main_event_loop = main_event_loop

    def clear_all(self):
        """Clear all task states (called during application startup)."""
        self.tasks_state.clear()
        self.tasks_log_queues.clear()
        self.tasks_log_histories.clear()
        # 上一次进程被强杀时不会执行清理，这里按年龄清理残留的临时目录。
        cleanup_stale_temp_dirs()

    def _evict_finished_tasks(self) -> None:
        """把内存中的任务记录限制在上限内（长时间运行/批量调用）。

        只淘汰已经结束的任务，并删除它们的临时目录；正在处理的任务不会被淘汰。
        """
        if TASK_MAX_COUNT <= 0 or len(self.tasks_state) <= TASK_MAX_COUNT:
            return
        candidates = sorted(
            (
                task_id
                for task_id, state in self.tasks_state.items()
                if not state.get("is_processing")
            ),
            key=lambda task_id: self.tasks_state[task_id].get("task_start_time") or 0,
        )
        for task_id in candidates:
            if len(self.tasks_state) <= TASK_MAX_COUNT:
                break
            state = self.tasks_state.get(task_id)
            if state is None or state.get("is_processing"):
                continue
            temp_dir = state.get("temp_dir")
            if temp_dir and os.path.isdir(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            self.tasks_state.pop(task_id, None)
            self.tasks_log_queues.pop(task_id, None)
            self.tasks_log_histories.pop(task_id, None)
            global_logger.info("[%s] 任务记录超出上限，已淘汰并清理临时目录", task_id)

    def list_tasks(self) -> List[str]:
        """List all task IDs."""
        return list(self.tasks_state.keys())

    def get_task_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task state by ID."""
        return self.tasks_state.get(task_id)

    def get_task_logs(self, task_id: str) -> List[str]:
        """Get task log history by ID."""
        return self.tasks_log_histories.get(task_id, [])

    async def get_new_logs(self, task_id: str) -> List[str]:
        """Get new logs from the queue."""
        if task_id not in self.tasks_log_queues:
            raise HTTPException(
                status_code=404, detail=f"找不到任务ID '{task_id}' 的日志队列。"
            )
        log_queue = self.tasks_log_queues[task_id]
        new_logs = []
        while not log_queue.empty():
            try:
                new_logs.append(log_queue.get_nowait())
                log_queue.task_done()
            except asyncio.QueueEmpty:
                break
        return new_logs

    def get_downloadable_file_path(self, task_id: str, file_type: str) -> Optional[Dict[str, str]]:
        """Get downloadable file info."""
        task_state = self.tasks_state.get(task_id)
        if not task_state:
            return None
        return task_state.get("downloadable_files", {}).get(file_type)

    def get_attachment_file_path(self, task_id: str, identifier: str) -> Optional[Dict[str, str]]:
        """Get attachment file info."""
        task_state = self.tasks_state.get(task_id)
        if not task_state:
            return None
        return task_state.get("attachment_files", {}).get(identifier)

    async def start_translation(
        self,
        task_id: str,
        payload: TranslatePayload,
        file_contents: bytes,
        original_filename: str,
    ) -> Dict[str, Any]:
        """
        Start a translation task.

        Args:
            task_id: Unique task identifier
            payload: Translation parameters
            file_contents: File content bytes
            original_filename: Original filename

        Returns:
            Response dict with task_id and status
        """
        try:
            payload = resolve_auto_payload(payload, original_filename)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"参数配置错误: {mask_secrets(str(exc))}") from exc

        if task_id not in self.tasks_state:
            self.tasks_state[task_id] = _create_default_task_state()
            self.tasks_log_queues[task_id] = asyncio.Queue(maxsize=MAX_LOG_QUEUE)
            self.tasks_log_histories[task_id] = []
        task_state = self.tasks_state[task_id]

        if (
            task_state["is_processing"]
            and task_state["current_task_ref"]
            and not task_state["current_task_ref"].done()
        ):
            raise HTTPException(
                status_code=429, detail=f"任务ID '{task_id}' 正在进行中，请稍后再试。"
            )

        if task_state.get("temp_dir") and os.path.isdir(task_state["temp_dir"]):
            shutil.rmtree(task_state["temp_dir"])

        raw_stem = Path(original_filename).stem
        safe_stem = raw_stem[:50] if len(raw_stem) > 50 else raw_stem

        task_state.update(
            {
                "is_processing": True,
                "status_message": "任务初始化中...",
                "error_flag": False,
                "cancelled": False,
                "download_ready": False,
                "workflow_instance": None,
                "statistics": None,
                "original_filename_stem": safe_stem,
                "original_filename": original_filename,
                "task_start_time": time.time(),
                "task_end_time": 0,
                "current_task_ref": None,
                "temp_dir": None,
                "downloadable_files": {},
                "attachment_files": {},
            }
        )

        log_history = self.tasks_log_histories[task_id]
        log_queue = self.tasks_log_queues[task_id]
        log_history.clear()
        while not log_queue.empty():
            try:
                log_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        initial_log_msg = f"收到新的翻译请求: {original_filename}"
        global_logger.info("[%s] %s", task_id, initial_log_msg)
        await log_queue.put(initial_log_msg)

        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(
                self._perform_translation(task_id, payload, file_contents, original_filename)
            )
            task_state["current_task_ref"] = task
            # 批量/长跑场景下限制内存中的任务记录数量（新任务不会被淘汰）。
            self._evict_finished_tasks()
            return {
                "task_started": True,
                "task_id": task_id,
                "message": "翻译任务已成功启动，请稍候...",
            }
        except Exception as e:
            task_state.update(
                {
                    "is_processing": False,
                    "status_message": f"启动任务失败: {e}",
                    "error_flag": True,
                    "current_task_ref": None,
                }
            )
            raise HTTPException(status_code=500, detail=f"启动翻译任务时出错: {mask_secrets(str(e))}")

    async def _perform_translation(
        self,
        task_id: str,
        payload: TranslatePayload,
        file_contents: bytes,
        original_filename: str,
    ):
        """Perform the actual translation work."""
        task_state = self.tasks_state[task_id]
        log_queue = self.tasks_log_queues[task_id]
        log_history = self.tasks_log_histories[task_id]

        task_logger = logging.getLogger(f"task.{task_id}")
        task_logger.setLevel(logging.INFO)
        task_logger.propagate = False
        if task_logger.hasHandlers():
            task_logger.handlers.clear()
        task_handler = QueueAndHistoryHandler(
            log_queue,
            log_history,
            MAX_LOG_HISTORY,
            task_id=task_id,
            event_loop=self.main_event_loop,
        )
        task_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        task_logger.addHandler(task_handler)

        task_logger.info(
            f"后台翻译任务开始: 文件 '{original_filename}', 工作流: '{payload.workflow_type}'"
        )
        task_state["status_message"] = f"正在处理 '{original_filename}'..."

        def update_progress(percent: int, message: str):
            task_state["progress_percent"] = percent
            if message:
                task_state["status_message"] = message

        progress_tracker = ProgressTracker(
            logger=task_logger,
            callback=update_progress
        )

        temp_dir = None
        # 提前绑定：异常/取消分支会读取它，之前只靠 except Exception: pass 兜住未绑定。
        workflow: Workflow | None = None

        try:
            workflow_class = WORKFLOW_DICT.get(payload.workflow_type)
            if not workflow_class:
                raise ValueError(f"不支持的工作流类型: '{payload.workflow_type}'")

            workflow = self._create_workflow(payload, task_logger, progress_tracker)
            # 保存workflow引用以便在polling时获取实时统计
            task_state["workflow_instance"] = workflow

            file_stem = task_state["original_filename_stem"]
            file_suffix = Path(original_filename).suffix
            workflow.read_bytes(content=file_contents, stem=file_stem, suffix=file_suffix)
            await workflow.translate_async()

            task_logger.info("翻译完成，正在生成临时结果文件...")
            temp_dir = tempfile.mkdtemp(prefix=f"docutranslate_{task_id}_")
            task_state["temp_dir"] = temp_dir
            downloadable_files = {}
            filename_stem = task_state["original_filename_stem"]

            is_cdn_available = True
            if self.httpx_client is not None:
                try:
                    await self.httpx_client.head(
                        "https://s4.zstatic.net/ajax/libs/KaTeX/0.16.9/contrib/auto-render.min.js",
                        timeout=3,
                    )
                except (httpx.TimeoutException, httpx.RequestError):
                    is_cdn_available = False
                    task_logger.warning("CDN连接失败，将使用本地JS进行渲染。")
            else:
                is_cdn_available = False
                task_logger.warning("HTTP客户端未初始化，将使用本地JS进行渲染。")

            export_map = self._build_export_map(
                workflow, filename_stem, is_cdn_available
            )

            for file_type, (export_func, filename, is_string_output) in export_map.items():
                try:
                    content = await asyncio.to_thread(export_func)
                    content_bytes = content.encode("utf-8") if is_string_output else content
                    file_path = os.path.join(temp_dir, filename)
                    await asyncio.to_thread(_write_bytes, file_path, content_bytes)
                    downloadable_files[file_type] = {
                        "path": file_path,
                        "filename": filename,
                    }
                    task_logger.info(f"成功生成 {file_type} 文件")
                except Exception as export_error:
                    task_logger.error(
                        f"生成 {file_type} 文件时出错: {export_error}", exc_info=True
                    )

            if not downloadable_files:
                raise RuntimeError("所有导出格式均失败，未生成可下载文件")

            attachment_files = {}
            attachment_object = workflow.get_attachment()
            if attachment_object and attachment_object.attachment_dict:
                task_logger.info(
                    f"发现 {len(attachment_object.attachment_dict)} 个附件，正在处理..."
                )
                for identifier, doc in attachment_object.attachment_dict.items():
                    try:
                        attachment_filename = f"{doc.stem or identifier}{doc.suffix}"
                        attachment_path = os.path.join(temp_dir, attachment_filename)
                        await asyncio.to_thread(_write_bytes, attachment_path, doc.content)
                        attachment_files[identifier] = {
                            "path": attachment_path,
                            "filename": attachment_filename,
                        }
                        task_logger.info(
                            f"成功生成附件 '{identifier}' 文件: {attachment_filename}"
                        )
                    except Exception as attachment_error:
                        task_logger.error(
                            f"生成附件 '{identifier}' 文件时出错: {attachment_error}",
                            exc_info=True,
                        )

            end_time = time.time()
            duration = end_time - task_state["task_start_time"]

            # 收集统计信息
            statistics = workflow.get_statistics()
            task_logger.info(f"收集统计信息: {statistics}")

            task_state.update(
                {
                    "status_message": f"翻译完成！用时 {duration:.2f} 秒。",
                    "download_ready": True,
                    "error_flag": False,
                    "progress_percent": 100,
                    "task_end_time": end_time,
                    "downloadable_files": downloadable_files,
                    "attachment_files": attachment_files,
                    "statistics": statistics,
                }
            )
            task_logger.info(f"翻译完成，用时 {duration:.2f} 秒。")

        except asyncio.CancelledError:
            end_time = time.time()
            duration = end_time - task_state["task_start_time"]
            task_logger.info(
                f"翻译任务 '{original_filename}' 已被取消 (用时 {duration:.2f} 秒)."
            )
            # 尝试获取已有的统计数据
            statistics = {}
            try:
                if workflow:
                    statistics = workflow.get_statistics()
            except Exception:
                pass
            # 取消不是错误，但必须和完成区分开：进度不能停在 100%，
            # 并且要立刻清掉临时目录（否则只有显式 /release 才会删除）。
            if temp_dir and os.path.isdir(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    task_logger.info("任务已取消，临时目录已清理")
                except Exception as cleanup_error:
                    task_logger.warning(f"取消后清理临时目录失败: {cleanup_error}")
                task_state["temp_dir"] = None
                temp_dir = None
            task_state.update(
                {
                    "status_message": f"翻译任务已取消 (用时 {duration:.2f} 秒).",
                    "error_flag": False,
                    "cancelled": True,
                    "download_ready": False,
                    "task_end_time": end_time,
                    "downloadable_files": {},
                    "attachment_files": {},
                    "statistics": statistics,
                }
            )
        except Exception as e:
            end_time = time.time()
            duration = end_time - task_state["task_start_time"]
            error_message = f"翻译失败: {e}"
            task_logger.error(error_message, exc_info=True)
            # 尝试获取已有的统计数据
            statistics = {}
            try:
                if workflow:
                    statistics = workflow.get_statistics()
            except Exception:
                pass
            task_state.update(
                {
                    "status_message": f"翻译过程中发生错误 (用时 {duration:.2f} 秒): {mask_secrets(str(e))}",
                    "error_flag": True,
                    "download_ready": False,
                    "task_end_time": end_time,
                    "statistics": statistics,
                }
            )
        finally:
            task_state["workflow_instance"] = None
            task_state["is_processing"] = False
            task_state["current_task_ref"] = None

            if task_state["error_flag"] and temp_dir and os.path.isdir(temp_dir):
                shutil.rmtree(temp_dir)
                task_logger.info(f"因任务失败，已清理临时目录")
                task_state["temp_dir"] = None

            task_logger.info(f"后台翻译任务 '{original_filename}' 处理结束。")
            task_logger.removeHandler(task_handler)

    def _create_workflow(
        self,
        payload: TranslatePayload,
        task_logger: logging.Logger,
        progress_tracker: ProgressTracker,
        build_glossary_agent_config=None,
        md2docx_engine=None,
    ) -> Workflow:
        """Compatibility wrapper around the shared SDK/server workflow factory."""
        return create_workflow_from_payload(payload, logger=task_logger,
                                            progress_tracker=progress_tracker)

    def _build_export_map(
        self,
        workflow: Workflow,
        filename_stem: str,
        is_cdn_available: bool,
    ) -> Dict[str, Any]:
        """Build export map based on workflow capabilities."""
        export_map = {}

        if isinstance(workflow, MDFormatsExportable):
            export_map["markdown"] = (
                workflow.export_to_markdown,
                f"{filename_stem}_translated.md",
                True,
            )
            export_map["markdown_zip"] = (
                workflow.export_to_markdown_zip,
                f"{filename_stem}_translated.zip",
                False,
            )
        if isinstance(workflow, TXTExportable):
            export_map["txt"] = (
                workflow.export_to_txt,
                f"{filename_stem}_translated.txt",
                True,
            )
        if isinstance(workflow, JsonExportable):
            export_map["json"] = (
                workflow.export_to_json,
                f"{filename_stem}_translated.json",
                True,
            )
        if isinstance(workflow, XlsxExportable):
            export_map["xlsx"] = (
                workflow.export_to_xlsx,
                f"{filename_stem}_translated.xlsx",
                False,
            )
        if isinstance(workflow, CsvExportable):
            export_map["csv"] = (
                workflow.export_to_csv,
                f"{filename_stem}_translated.csv",
                False,
            )
        if isinstance(workflow, DocxExportable):
            # MarkdownBasedWorkflow needs md2docx_exporter_config
            if isinstance(workflow, MarkdownBasedWorkflow):
                if hasattr(workflow.config, 'md2docx_exporter_config') and workflow.config.md2docx_exporter_config is not None:
                    export_map["docx"] = (
                        workflow.export_to_docx,
                        f"{filename_stem}_translated.docx",
                        False,
                    )
            # DocxWorkflow can export docx directly
            elif isinstance(workflow, DocxWorkflow):
                export_map["docx"] = (
                    workflow.export_to_docx,
                    f"{filename_stem}_translated.docx",
                    False,
                )
        if isinstance(workflow, SrtExportable):
            export_map["srt"] = (
                workflow.export_to_srt,
                f"{filename_stem}_translated.srt",
                True,
            )
        if isinstance(workflow, EpubExportable):
            export_map["epub"] = (
                workflow.export_to_epub,
                f"{filename_stem}_translated.epub",
                False,
            )
        if isinstance(workflow, AssExportable):
            export_map["ass"] = (
                workflow.export_to_ass,
                f"{filename_stem}_translated.ass",
                True,
            )
        if isinstance(workflow, PPTXExportable):
            export_map["pptx"] = (
                workflow.export_to_pptx,
                f"{filename_stem}_translated.pptx",
                False,
            )

        if isinstance(workflow, HTMLExportable):
            html_config = getattr(workflow.config, "html_exporter_config", None)
            if html_config is not None and not getattr(workflow, "_html_cdn_explicit", False):
                html_config = replace(html_config, cdn=is_cdn_available)
            export_map["html"] = (
                lambda: workflow.export_to_html(html_config),
                f"{filename_stem}_translated.html",
                True,
            )

        return export_map

    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """Cancel a running task."""
        task_state = self.tasks_state.get(task_id)
        if not task_state:
            raise HTTPException(status_code=404, detail=f"找不到任务ID '{task_id}'。")
        if (
            not task_state
            or not task_state["is_processing"]
            or not task_state["current_task_ref"]
        ):
            raise HTTPException(
                status_code=400, detail=f"任务ID '{task_id}' 没有正在进行的翻译任务可取消。"
            )

        task_to_cancel: Optional[asyncio.Task] = task_state["current_task_ref"]
        if not task_to_cancel or task_to_cancel.done():
            task_state["is_processing"] = False
            task_state["current_task_ref"] = None
            raise HTTPException(status_code=400, detail="任务已完成或已被取消。")

        global_logger.info("[%s] 收到取消翻译任务的请求", task_id)
        task_to_cancel.cancel()
        task_state["status_message"] = "正在取消任务..."
        return {"cancelled": True, "message": "取消请求已发送。请等待状态更新。"}

    async def release_task(self, task_id: str) -> Dict[str, Any]:
        """Release task resources."""
        if task_id not in self.tasks_state:
            return {
                "released": False,
                "message": f"找不到任务ID '{task_id}'。"
            }
        task_state = self.tasks_state.get(task_id)
        message_parts = []
        if (
            task_state
            and task_state.get("is_processing")
            and task_state.get("current_task_ref")
        ):
            task_ref = task_state["current_task_ref"]
            try:
                global_logger.info("[%s] 任务仍在进行，释放前尝试取消", task_id)
                self.cancel_task(task_id)
                message_parts.append("任务已被取消。")
            except HTTPException as e:
                global_logger.info(
                    "[%s] 取消步骤已跳过（任务可能已完成）: %s", task_id, e.detail
                )
                message_parts.append(f"任务取消步骤已跳过（可能已完成或取消）。")
            if task_ref is not asyncio.current_task() and not task_ref.done():
                # Let the worker run its finally block before deleting the
                # task state and its temporary output directory.
                done, pending = await asyncio.wait({task_ref}, timeout=5.0)
                if pending:
                    global_logger.warning("[%s] 取消后任务清理仍未完成", task_id)
                    message_parts.append("任务清理未在 5 秒内完成。")

        if task_state:
            temp_dir = task_state.get("temp_dir")
            if temp_dir and os.path.isdir(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    message_parts.append("临时文件已清理。")
                    global_logger.info("[%s] 临时目录已删除: %s", task_id, temp_dir)
                except Exception as e:
                    message_parts.append(f"清理临时文件时出错: {e}。")
                    global_logger.error(
                        "[%s] 删除临时目录失败: path=%s, error=%s",
                        task_id,
                        temp_dir,
                        e,
                    )

        self.tasks_state.pop(task_id, None)
        self.tasks_log_queues.pop(task_id, None)
        self.tasks_log_histories.pop(task_id, None)
        global_logger.info("[%s] 资源已成功释放", task_id)
        message_parts.append(f"任务 '{task_id}' 的资源已释放。")
        return {"released": True, "message": " ".join(message_parts)}

    async def cleanup_all(self):
        """Cleanup all resources (called during application shutdown)."""
        pending_tasks = []
        for task_id, task_state in self.tasks_state.items():
            task_ref = task_state.get("current_task_ref")
            if task_ref and not task_ref.done():
                global_logger.info("[%s] 检测到未完成任务，正在强制取消", task_id)
                task_ref.cancel()
                pending_tasks.append(task_ref)

        if pending_tasks:
            await asyncio.gather(*pending_tasks, return_exceptions=True)

        for task_id, task_state in self.tasks_state.items():
            temp_dir = task_state.get("temp_dir")
            if temp_dir and os.path.isdir(temp_dir):
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    global_logger.info("[%s] 临时目录已清理: %s", task_id, temp_dir)
                except Exception as e:
                    global_logger.error(
                        "[%s] 清理临时目录失败: path=%s, error=%s",
                        task_id,
                        temp_dir,
                        e,
                    )

        # Cleanup HTTP client
        if self.httpx_client is not None:
            try:
                await self.httpx_client.aclose()
                global_logger.info("[TranslationService] HTTP客户端已关闭")
            except Exception as e:
                global_logger.error(
                    "[TranslationService] 关闭HTTP客户端失败: %s", e
                )
            finally:
                self.httpx_client = None


# Global singleton instance
_translation_service: Optional[TranslationService] = None


def get_translation_service() -> TranslationService:
    """Get the global translation service instance (singleton)."""
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service
