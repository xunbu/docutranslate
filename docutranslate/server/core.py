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
from pydantic import TypeAdapter

from docutranslate import __version__
from docutranslate.agents.glossary_agent import GlossaryAgentConfig
from docutranslate.core.schemas import TranslatePayload
from docutranslate.exporter.md.types import ConvertEngineType
from docutranslate.global_values.conditional_import import DOCLING_EXIST
from docutranslate.workflow.ass_workflow import AssWorkflow, AssWorkflowConfig
from docutranslate.workflow.base import Workflow
from docutranslate.workflow.docx_workflow import DocxWorkflow, DocxWorkflowConfig
from docutranslate.workflow.epub_workflow import EpubWorkflow, EpubWorkflowConfig
from docutranslate.workflow.html_workflow import HtmlWorkflow, HtmlWorkflowConfig
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
from docutranslate.workflow.json_workflow import JsonWorkflow, JsonWorkflowConfig
from docutranslate.workflow.md_based_workflow import (
    MarkdownBasedWorkflow,
    MarkdownBasedWorkflowConfig,
)
from docutranslate.workflow.pptx_workflow import PPTXWorkflow, PPTXWorkflowConfig
from docutranslate.workflow.srt_workflow import SrtWorkflow, SrtWorkflowConfig
from docutranslate.workflow.txt_workflow import TXTWorkflow, TXTWorkflowConfig
from docutranslate.workflow.xlsx_workflow import XlsxWorkflow, XlsxWorkflowConfig
from docutranslate.logger import global_logger
from docutranslate.progress import ProgressTracker
from docutranslate.translator import default_params

if DOCLING_EXIST:
    from docutranslate.converter.x2md.converter_docling import ConverterDoclingConfig
from docutranslate.converter.x2md.converter_mineru import ConverterMineruConfig
from docutranslate.converter.x2md.converter_mineru_deploy import ConverterMineruDeployConfig
from docutranslate.exporter.md.md2html_exporter import MD2HTMLExporterConfig
from docutranslate.exporter.md.md2docx_exporter import MD2DocxExporterConfig
from docutranslate.exporter.txt.txt2html_exporter import TXT2HTMLExporterConfig
from docutranslate.translator.ai_translator.md_translator import MDTranslatorConfig
from docutranslate.translator.ai_translator.txt_translator import TXTTranslatorConfig
from docutranslate.translator.ai_translator.json_translator import JsonTranslatorConfig
from docutranslate.exporter.js.json2html_exporter import Json2HTMLExporterConfig
from docutranslate.translator.ai_translator.xlsx_translator import XlsxTranslatorConfig
from docutranslate.exporter.xlsx.xlsx2html_exporter import Xlsx2HTMLExporterConfig
from docutranslate.translator.ai_translator.docx_translator import DocxTranslatorConfig
from docutranslate.exporter.docx.docx2html_exporter import Docx2HTMLExporterConfig
from docutranslate.translator.ai_translator.srt_translator import SrtTranslatorConfig
from docutranslate.exporter.srt.srt2html_exporter import Srt2HTMLExporterConfig
from docutranslate.translator.ai_translator.epub_translator import EpubTranslatorConfig
from docutranslate.exporter.epub.epub2html_exporter import Epub2HTMLExporterConfig
from docutranslate.translator.ai_translator.html_translator import HtmlTranslatorConfig
from docutranslate.translator.ai_translator.ass_translator import AssTranslatorConfig
from docutranslate.exporter.ass.ass2html_exporter import Ass2HTMLExporterConfig
from docutranslate.translator.ai_translator.pptx_translator import PPTXTranslatorConfig
from docutranslate.exporter.pptx.pptx2html_exporter import PPTX2HTMLExporterConfig


MAX_LOG_HISTORY = 200


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
    ):
        super().__init__()
        self.queue = queue_ref
        self.history_list = history_list_ref
        self.max_history = max_history_items
        self.task_id = task_id

    def emit(self, record: logging.LogRecord):
        log_entry = self.format(record)
        print(f"[{self.task_id}] {log_entry}")
        self.history_list.append(log_entry)
        if len(self.history_list) > self.max_history:
            del self.history_list[: len(self.history_list) - self.max_history]
        if self.queue is not None:
            try:
                # Try to get the main event loop - this will be set by the application
                self.queue.put_nowait(log_entry)
            except asyncio.QueueFull:
                print(f"[{self.task_id}] Log queue is full. Log dropped: {log_entry}")
            except Exception as e:
                print(
                    f"[{self.task_id}] Error putting log to queue: {e}. Log: {log_entry}"
                )


def get_workflow_type_from_filename(filename: str) -> str:
    """Get workflow type based on file extension."""
    ext = Path(filename).suffix.lower()
    if ext in [".pdf", ".png", ".jpg"]:
        return "markdown_based"
    elif ext in [".md", ".markdown"]:
        return "markdown_based"
    elif ext in [".docx", ".doc"]:
        return "docx"
    elif ext in [".csv", ".xlsx", ".xls"]:
        return "xlsx"
    elif ext in [".pptx", ".ppt"]:
        return "pptx"
    elif ext in [".json"]:
        return "json"
    elif ext in [".srt"]:
        return "srt"
    elif ext in [".ass"]:
        return "ass"
    elif ext in [".epub"]:
        return "epub"
    elif ext in [".html", ".htm"]:
        return "html"
    elif ext in [".txt"]:
        return "txt"
    else:
        return "txt"


def _create_default_task_state() -> Dict[str, Any]:
    """Create a new default task state."""
    return {
        "is_processing": False,
        "status_message": "空闲",
        "error_flag": False,
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
    }


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

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

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
        # Auto workflow routing
        if payload.workflow_type == "auto":
            detected_type = get_workflow_type_from_filename(original_filename)
            print(f"[{task_id}] 自动识别工作流: {original_filename} -> {detected_type}")

            payload_data = payload.model_dump()
            payload_data["workflow_type"] = detected_type

            if detected_type == "json" and not payload_data.get("json_paths"):
                payload_data["json_paths"] = ["$..*"]

            if detected_type == "markdown_based" and not payload_data.get("convert_engine"):
                if Path(original_filename).suffix.lower() == ".pdf":
                    payload_data["convert_engine"] = "mineru" if not DOCLING_EXIST else "docling"
                else:
                    payload_data["convert_engine"] = "identity"

            try:
                payload = TypeAdapter(TranslatePayload).validate_python(payload_data)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"自动转换工作流参数失败: {e}")

        if task_id not in self.tasks_state:
            self.tasks_state[task_id] = _create_default_task_state()
            self.tasks_log_queues[task_id] = asyncio.Queue()
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
                "download_ready": False,
                "workflow_instance": None,
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
        print(f"[{task_id}] {initial_log_msg}")
        await log_queue.put(initial_log_msg)

        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(
                self._perform_translation(task_id, payload, file_contents, original_filename)
            )
            task_state["current_task_ref"] = task
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
            raise HTTPException(status_code=500, detail=f"启动翻译任务时出错: {e}")

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
            log_queue, log_history, MAX_LOG_HISTORY, task_id=task_id
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

        try:
            workflow_class = WORKFLOW_DICT.get(payload.workflow_type)
            if not workflow_class:
                raise ValueError(f"不支持的工作流类型: '{payload.workflow_type}'")

            workflow: Workflow

            def build_glossary_agent_config():
                if payload.glossary_generate_enable and payload.glossary_agent_config:
                    agent_payload = payload.glossary_agent_config
                    return GlossaryAgentConfig(
                        logger=task_logger, **agent_payload.model_dump()
                    )
                return None

            if hasattr(payload, 'md2docx_engine'):
                md2docx_engine = payload.md2docx_engine
            else:
                md2docx_engine = "auto"

            workflow = self._create_workflow(
                payload, task_logger, progress_tracker, build_glossary_agent_config, md2docx_engine
            )

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
            try:
                await self.httpx_client.head(
                    "https://s4.zstatic.net/ajax/libs/KaTeX/0.16.9/contrib/auto-render.min.js",
                    timeout=3,
                )
            except (httpx.TimeoutException, httpx.RequestError):
                is_cdn_available = False
                task_logger.warning("CDN连接失败，将使用本地JS进行渲染。")

            export_map = self._build_export_map(
                workflow, filename_stem, is_cdn_available
            )

            for file_type, (export_func, filename, is_string_output) in export_map.items():
                try:
                    content = await asyncio.to_thread(export_func)
                    content_bytes = content.encode("utf-8") if is_string_output else content
                    file_path = os.path.join(temp_dir, filename)
                    with open(file_path, "wb") as f:
                        f.write(content_bytes)
                    downloadable_files[file_type] = {
                        "path": file_path,
                        "filename": filename,
                    }
                    task_logger.info(f"成功生成 {file_type} 文件")
                except Exception as export_error:
                    task_logger.error(
                        f"生成 {file_type} 文件时出错: {export_error}", exc_info=True
                    )

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
                        with open(attachment_path, "wb") as f:
                            f.write(doc.content)
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
            task_state.update(
                {
                    "status_message": f"翻译成功！用时 {duration:.2f} 秒。",
                    "download_ready": True,
                    "error_flag": False,
                    "progress_percent": 100,
                    "task_end_time": end_time,
                    "downloadable_files": downloadable_files,
                    "attachment_files": attachment_files,
                }
            )
            task_logger.info(f"翻译成功完成，用时 {duration:.2f} 秒。")

        except asyncio.CancelledError:
            end_time = time.time()
            duration = end_time - task_state["task_start_time"]
            task_logger.info(
                f"翻译任务 '{original_filename}' 已被取消 (用时 {duration:.2f} 秒)."
            )
            task_state.update(
                {
                    "status_message": f"翻译任务已取消 (用时 {duration:.2f} 秒).",
                    "error_flag": False,
                    "download_ready": False,
                    "progress_percent": 100,
                    "task_end_time": end_time,
                }
            )
        except Exception as e:
            end_time = time.time()
            duration = end_time - task_state["task_start_time"]
            error_message = f"翻译失败: {e}"
            task_logger.error(error_message, exc_info=True)
            task_state.update(
                {
                    "status_message": f"翻译过程中发生错误 (用时 {duration:.2f} 秒): {e}",
                    "error_flag": True,
                    "download_ready": False,
                    "progress_percent": 100,
                    "task_end_time": end_time,
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
        build_glossary_agent_config,
        md2docx_engine: str,
    ) -> Workflow:
        """Create workflow instance based on payload type."""
        from docutranslate.core.schemas import (
            MarkdownWorkflowParams,
            TextWorkflowParams,
            JsonWorkflowParams,
            XlsxWorkflowParams,
            DocxWorkflowParams,
            SrtWorkflowParams,
            EpubWorkflowParams,
            HtmlWorkflowParams,
            AssWorkflowParams,
            PPTXWorkflowParams,
        )

        if isinstance(payload, MarkdownWorkflowParams):
            task_logger.info("构建 MarkdownBasedWorkflow 配置。")
            translator_args = payload.model_dump(
                include={
                    "skip_translate",
                    "base_url",
                    "api_key",
                    "model_id",
                    "to_lang",
                    "custom_prompt",
                    "temperature",
                    "thinking",
                    "chunk_size",
                    "concurrent",
                    "glossary_dict",
                    "timeout",
                    "retry",
                    "system_proxy_enable",
                    "force_json",
                    "rpm",
                    "tpm",
                    "provider",
                    "extra_body",
                },
                exclude_none=True,
            )
            translator_args["glossary_generate_enable"] = payload.glossary_generate_enable
            translator_args["glossary_agent_config"] = build_glossary_agent_config()
            translator_config = MDTranslatorConfig(**translator_args)
            translator_config.progress_tracker = progress_tracker

            converter_config = None
            if payload.convert_engine == "mineru":
                converter_config = ConverterMineruConfig(
                    logger=task_logger,
                    mineru_token=payload.mineru_token,
                    formula_ocr=payload.formula_ocr,
                    model_version=payload.model_version,
                )
            elif payload.convert_engine == "mineru_deploy":
                converter_config = ConverterMineruDeployConfig(
                    base_url=payload.mineru_deploy_base_url,
                    backend=payload.mineru_deploy_backend,
                    parse_method=payload.mineru_deploy_parse_method,
                    formula_enable=payload.mineru_deploy_formula_enable,
                    table_enable=payload.mineru_deploy_table_enable,
                    start_page_id=payload.mineru_deploy_start_page_id,
                    end_page_id=payload.mineru_deploy_end_page_id,
                    lang_list=payload.mineru_deploy_lang_list,
                    server_url=payload.mineru_deploy_server_url,
                )
            elif payload.convert_engine == "docling" and DOCLING_EXIST:
                converter_config = ConverterDoclingConfig(
                    logger=task_logger,
                    code_ocr=payload.code_ocr,
                    formula_ocr=payload.formula_ocr,
                )
            html_exporter_config = MD2HTMLExporterConfig(cdn=True)
            md2docx_exporter_config = MD2DocxExporterConfig(
                engine=md2docx_engine
            ) if md2docx_engine is not None else None
            workflow_config = MarkdownBasedWorkflowConfig(
                convert_engine=payload.convert_engine,
                converter_config=converter_config,
                translator_config=translator_config,
                html_exporter_config=html_exporter_config,
                md2docx_exporter_config=md2docx_exporter_config,
                logger=task_logger,
                progress_tracker=progress_tracker,
            )
            return MarkdownBasedWorkflow(config=workflow_config)

        elif isinstance(payload, TextWorkflowParams):
            task_logger.info("构建 TXTWorkflow 配置。")
            translator_args = payload.model_dump(
                include={
                    "skip_translate",
                    "base_url",
                    "api_key",
                    "model_id",
                    "to_lang",
                    "custom_prompt",
                    "temperature",
                    "thinking",
                    "chunk_size",
                    "concurrent",
                    "glossary_dict",
                    "insert_mode",
                    "separator",
                    "segment_mode",
                    "timeout",
                    "retry",
                    "system_proxy_enable",
                    "force_json",
                    "rpm",
                    "tpm",
                    "provider",
                    "extra_body",
                },
                exclude_none=True,
            )
            translator_args["glossary_generate_enable"] = payload.glossary_generate_enable
            translator_args["glossary_agent_config"] = build_glossary_agent_config()
            translator_config = TXTTranslatorConfig(**translator_args)
            translator_config.progress_tracker = progress_tracker

            html_exporter_config = TXT2HTMLExporterConfig(cdn=True)
            workflow_config = TXTWorkflowConfig(
                translator_config=translator_config,
                html_exporter_config=html_exporter_config,
                logger=task_logger,
                progress_tracker=progress_tracker,
            )
            return TXTWorkflow(config=workflow_config)

        elif isinstance(payload, JsonWorkflowParams):
            task_logger.info("构建 JsonWorkflow 配置。")
            translator_args = payload.model_dump(
                include={
                    "skip_translate",
                    "base_url",
                    "api_key",
                    "model_id",
                    "to_lang",
                    "custom_prompt",
                    "temperature",
                    "thinking",
                    "chunk_size",
                    "concurrent",
                    "glossary_dict",
                    "json_paths",
                    "timeout",
                    "retry",
                    "system_proxy_enable",
                    "force_json",
                    "rpm",
                    "tpm",
                    "provider",
                    "extra_body",
                },
                exclude_none=True,
            )
            translator_args["glossary_generate_enable"] = payload.glossary_generate_enable
            translator_args["glossary_agent_config"] = build_glossary_agent_config()
            translator_config = JsonTranslatorConfig(**translator_args)
            translator_config.progress_tracker = progress_tracker

            html_exporter_config = Json2HTMLExporterConfig(cdn=True)
            workflow_config = JsonWorkflowConfig(
                translator_config=translator_config,
                html_exporter_config=html_exporter_config,
                logger=task_logger,
                progress_tracker=progress_tracker,
            )
            return JsonWorkflow(config=workflow_config)

        elif isinstance(payload, XlsxWorkflowParams):
            task_logger.info("构建 XlsxWorkflow 配置。")
            translator_args = payload.model_dump(
                include={
                    "skip_translate",
                    "base_url",
                    "api_key",
                    "model_id",
                    "to_lang",
                    "custom_prompt",
                    "temperature",
                    "thinking",
                    "chunk_size",
                    "concurrent",
                    "insert_mode",
                    "separator",
                    "translate_regions",
                    "glossary_dict",
                    "timeout",
                    "retry",
                    "system_proxy_enable",
                    "force_json",
                    "rpm",
                    "tpm",
                    "provider",
                    "extra_body",
                },
                exclude_none=True,
            )
            translator_args["glossary_generate_enable"] = payload.glossary_generate_enable
            translator_args["glossary_agent_config"] = build_glossary_agent_config()
            translator_config = XlsxTranslatorConfig(**translator_args)
            translator_config.progress_tracker = progress_tracker

            html_exporter_config = Xlsx2HTMLExporterConfig(cdn=True)
            workflow_config = XlsxWorkflowConfig(
                translator_config=translator_config,
                html_exporter_config=html_exporter_config,
                logger=task_logger,
                progress_tracker=progress_tracker,
            )
            return XlsxWorkflow(config=workflow_config)

        elif isinstance(payload, DocxWorkflowParams):
            task_logger.info("构建 DocxWorkflow 配置。")
            translator_args = payload.model_dump(
                include={
                    "skip_translate",
                    "base_url",
                    "api_key",
                    "model_id",
                    "to_lang",
                    "custom_prompt",
                    "temperature",
                    "thinking",
                    "chunk_size",
                    "concurrent",
                    "insert_mode",
                    "separator",
                    "glossary_dict",
                    "timeout",
                    "retry",
                    "system_proxy_enable",
                    "force_json",
                    "rpm",
                    "tpm",
                    "provider",
                    "extra_body",
                },
                exclude_none=True,
            )
            translator_args["glossary_generate_enable"] = payload.glossary_generate_enable
            translator_args["glossary_agent_config"] = build_glossary_agent_config()
            translator_config = DocxTranslatorConfig(**translator_args)
            translator_config.progress_tracker = progress_tracker

            html_exporter_config = Docx2HTMLExporterConfig(cdn=True)
            workflow_config = DocxWorkflowConfig(
                translator_config=translator_config,
                html_exporter_config=html_exporter_config,
                logger=task_logger,
                progress_tracker=progress_tracker,
            )
            return DocxWorkflow(config=workflow_config)

        elif isinstance(payload, SrtWorkflowParams):
            task_logger.info("构建 SrtWorkflow 配置。")
            translator_args = payload.model_dump(
                include={
                    "skip_translate",
                    "base_url",
                    "api_key",
                    "model_id",
                    "to_lang",
                    "custom_prompt",
                    "temperature",
                    "thinking",
                    "chunk_size",
                    "concurrent",
                    "insert_mode",
                    "separator",
                    "glossary_dict",
                    "timeout",
                    "retry",
                    "system_proxy_enable",
                    "force_json",
                    "rpm",
                    "tpm",
                    "provider",
                    "extra_body",
                },
                exclude_none=True,
            )
            translator_args["glossary_generate_enable"] = payload.glossary_generate_enable
            translator_args["glossary_agent_config"] = build_glossary_agent_config()
            translator_config = SrtTranslatorConfig(**translator_args)
            translator_config.progress_tracker = progress_tracker

            html_exporter_config = Srt2HTMLExporterConfig(cdn=True)
            workflow_config = SrtWorkflowConfig(
                translator_config=translator_config,
                html_exporter_config=html_exporter_config,
                logger=task_logger,
                progress_tracker=progress_tracker,
            )
            return SrtWorkflow(config=workflow_config)

        elif isinstance(payload, EpubWorkflowParams):
            task_logger.info("构建 EpubWorkflow 配置。")
            translator_args = payload.model_dump(
                include={
                    "skip_translate",
                    "base_url",
                    "api_key",
                    "model_id",
                    "to_lang",
                    "custom_prompt",
                    "temperature",
                    "thinking",
                    "chunk_size",
                    "concurrent",
                    "insert_mode",
                    "separator",
                    "glossary_dict",
                    "timeout",
                    "retry",
                    "system_proxy_enable",
                    "force_json",
                    "rpm",
                    "tpm",
                    "provider",
                    "extra_body",
                },
                exclude_none=True,
            )
            translator_args["glossary_generate_enable"] = payload.glossary_generate_enable
            translator_args["glossary_agent_config"] = build_glossary_agent_config()
            translator_config = EpubTranslatorConfig(**translator_args)
            translator_config.progress_tracker = progress_tracker

            html_exporter_config = Epub2HTMLExporterConfig(cdn=True)
            workflow_config = EpubWorkflowConfig(
                translator_config=translator_config,
                html_exporter_config=html_exporter_config,
                logger=task_logger,
                progress_tracker=progress_tracker,
            )
            return EpubWorkflow(config=workflow_config)

        elif isinstance(payload, HtmlWorkflowParams):
            task_logger.info("构建 HtmlWorkflow 配置。")
            translator_args = payload.model_dump(
                include={
                    "skip_translate",
                    "base_url",
                    "api_key",
                    "model_id",
                    "to_lang",
                    "custom_prompt",
                    "temperature",
                    "thinking",
                    "chunk_size",
                    "concurrent",
                    "insert_mode",
                    "separator",
                    "glossary_dict",
                    "timeout",
                    "retry",
                    "system_proxy_enable",
                    "force_json",
                    "rpm",
                    "tpm",
                    "provider",
                    "extra_body",
                },
                exclude_none=True,
            )
            translator_args["glossary_generate_enable"] = payload.glossary_generate_enable
            translator_args["glossary_agent_config"] = build_glossary_agent_config()
            translator_config = HtmlTranslatorConfig(**translator_args)
            translator_config.progress_tracker = progress_tracker

            workflow_config = HtmlWorkflowConfig(
                translator_config=translator_config, logger=task_logger,
                progress_tracker=progress_tracker,
            )
            return HtmlWorkflow(config=workflow_config)

        elif isinstance(payload, AssWorkflowParams):
            task_logger.info("构建 AssWorkflow 配置。")
            translator_args = payload.model_dump(
                include={
                    "skip_translate",
                    "base_url",
                    "api_key",
                    "model_id",
                    "to_lang",
                    "custom_prompt",
                    "temperature",
                    "thinking",
                    "chunk_size",
                    "concurrent",
                    "insert_mode",
                    "separator",
                    "glossary_dict",
                    "timeout",
                    "retry",
                    "system_proxy_enable",
                    "force_json",
                    "rpm",
                    "tpm",
                    "provider",
                    "extra_body",
                },
                exclude_none=True,
            )
            translator_args["glossary_generate_enable"] = payload.glossary_generate_enable
            translator_args["glossary_agent_config"] = build_glossary_agent_config()
            translator_config = AssTranslatorConfig(**translator_args)
            translator_config.progress_tracker = progress_tracker

            html_exporter_config = Ass2HTMLExporterConfig(cdn=True)
            workflow_config = AssWorkflowConfig(
                translator_config=translator_config,
                html_exporter_config=html_exporter_config,
                logger=task_logger,
                progress_tracker=progress_tracker,
            )
            return AssWorkflow(config=workflow_config)

        elif isinstance(payload, PPTXWorkflowParams):
            task_logger.info("构建 PPTXWorkflow 配置。")
            translator_args = payload.model_dump(
                include={
                    "skip_translate",
                    "base_url",
                    "api_key",
                    "model_id",
                    "to_lang",
                    "custom_prompt",
                    "temperature",
                    "thinking",
                    "chunk_size",
                    "concurrent",
                    "insert_mode",
                    "separator",
                    "glossary_dict",
                    "timeout",
                    "retry",
                    "system_proxy_enable",
                    "force_json",
                    "rpm",
                    "tpm",
                    "provider",
                    "extra_body",
                },
                exclude_none=True,
            )
            translator_args["glossary_generate_enable"] = payload.glossary_generate_enable
            translator_args["glossary_agent_config"] = build_glossary_agent_config()
            translator_config = PPTXTranslatorConfig(**translator_args)
            translator_config.progress_tracker = progress_tracker

            html_exporter_config = PPTX2HTMLExporterConfig(cdn=True)
            workflow_config = PPTXWorkflowConfig(
                translator_config=translator_config,
                html_exporter_config=html_exporter_config,
                logger=task_logger,
                progress_tracker=progress_tracker,
            )
            return PPTXWorkflow(config=workflow_config)

        else:
            raise TypeError(f"工作流类型 '{payload.workflow_type}' 的处理逻辑未实现。")

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
            html_config = None
            if isinstance(workflow, MarkdownBasedWorkflow):
                html_config = MD2HTMLExporterConfig(cdn=is_cdn_available)
            elif isinstance(workflow, TXTWorkflow):
                html_config = TXT2HTMLExporterConfig(cdn=is_cdn_available)
            elif isinstance(workflow, JsonWorkflow):
                html_config = Json2HTMLExporterConfig(cdn=is_cdn_available)
            elif isinstance(workflow, XlsxWorkflow):
                html_config = Xlsx2HTMLExporterConfig(cdn=is_cdn_available)
            elif isinstance(workflow, DocxWorkflow):
                html_config = Docx2HTMLExporterConfig(cdn=is_cdn_available)
            elif isinstance(workflow, SrtWorkflow):
                html_config = Srt2HTMLExporterConfig(cdn=is_cdn_available)
            elif isinstance(workflow, EpubWorkflow):
                html_config = Epub2HTMLExporterConfig(cdn=is_cdn_available)
            elif isinstance(workflow, AssWorkflow):
                html_config = Ass2HTMLExporterConfig(cdn=is_cdn_available)
            elif isinstance(workflow, PPTXWorkflow):
                html_config = PPTX2HTMLExporterConfig(cdn=is_cdn_available)
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

        print(f"[{task_id}] 收到取消翻译任务的请求。")
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
            try:
                print(f"[{task_id}] 任务正在进行中，将在释放前尝试取消。")
                self.cancel_task(task_id)
                message_parts.append("任务已被取消。")
            except HTTPException as e:
                print(f"[{task_id}] 取消任务时出现预期中的情况（可能已完成）: {e.detail}")
                message_parts.append(f"任务取消步骤已跳过（可能已完成或取消）。")

        if task_state:
            temp_dir = task_state.get("temp_dir")
            if temp_dir and os.path.isdir(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    message_parts.append("临时文件已清理。")
                    print(f"[{task_id}] 临时目录 '{temp_dir}' 已被删除。")
                except Exception as e:
                    message_parts.append(f"清理临时文件时出错: {e}。")
                    print(f"[{task_id}] 删除临时目录 '{temp_dir}' 时出错: {e}")

        self.tasks_state.pop(task_id, None)
        self.tasks_log_queues.pop(task_id, None)
        self.tasks_log_histories.pop(task_id, None)
        print(f"[{task_id}] 资源已成功释放。")
        message_parts.append(f"任务 '{task_id}' 的资源已释放。")
        return {"released": True, "message": " ".join(message_parts)}

    async def cleanup_all(self):
        """Cleanup all resources (called during application shutdown)."""
        pending_tasks = []
        for task_id, task_state in self.tasks_state.items():
            task_ref = task_state.get("current_task_ref")
            if task_ref and not task_ref.done():
                print(f"[{task_id}] 检测到未完成任务，正在强制取消...")
                task_ref.cancel()
                pending_tasks.append(task_ref)

        if pending_tasks:
            await asyncio.gather(*pending_tasks, return_exceptions=True)

        for task_id, task_state in self.tasks_state.items():
            temp_dir = task_state.get("temp_dir")
            if temp_dir and os.path.isdir(temp_dir):
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    print(f"[{task_id}] 临时目录已清理: {temp_dir}")
                except Exception as e:
                    print(f"[{task_id}] 清理临时目录 '{temp_dir}' 时出错: {e}")


# Global singleton instance
_translation_service: Optional[TranslationService] = None


def get_translation_service() -> TranslationService:
    """Get the global translation service instance (singleton)."""
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service
