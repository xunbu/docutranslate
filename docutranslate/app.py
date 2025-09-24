# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
import base64
import binascii
import logging
import os
import shutil
import socket
import tempfile
import time
import uuid
from contextlib import asynccontextmanager, closing
from pathlib import Path
from typing import (
    List,
    Dict,
    Any,
    Optional,
    Literal,
    Union,
    Annotated,
    TYPE_CHECKING,
    Type,
)

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, APIRouter, Body, Path as FastApiPath
from fastapi.openapi.docs import (
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
    get_redoc_html,
)
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator, AliasChoices

from docutranslate import __version__
from docutranslate.agents.agent import ThinkingMode
from docutranslate.agents.glossary_agent import GlossaryAgentConfig
from docutranslate.exporter.md.types import ConvertEngineType
from docutranslate.global_values import USE_PROXY

# --- 核心代码 Imports ---
from docutranslate.global_values.conditional_import import DOCLING_EXIST
from docutranslate.workflow.ass_workflow import AssWorkflow, AssWorkflowConfig
from docutranslate.workflow.base import Workflow
from docutranslate.workflow.docx_workflow import DocxWorkflow, DocxWorkflowConfig
from docutranslate.workflow.epub_workflow import EpubWorkflow, EpubWorkflowConfig
from docutranslate.workflow.html_workflow import HtmlWorkflow, HtmlWorkflowConfig
from docutranslate.workflow.interfaces import DocxExportable, EpubExportable
from docutranslate.workflow.interfaces import (
    HTMLExportable,
    MDFormatsExportable,
    TXTExportable,
    JsonExportable,
    XlsxExportable,
    SrtExportable,
    CsvExportable,
    AssExportable,
)
from docutranslate.workflow.json_workflow import JsonWorkflow, JsonWorkflowConfig
from docutranslate.workflow.md_based_workflow import (
    MarkdownBasedWorkflow,
    MarkdownBasedWorkflowConfig,
)
from docutranslate.workflow.srt_workflow import SrtWorkflow, SrtWorkflowConfig
from docutranslate.workflow.txt_workflow import TXTWorkflow, TXTWorkflowConfig
from docutranslate.workflow.xlsx_workflow import XlsxWorkflow, XlsxWorkflowConfig

if DOCLING_EXIST or TYPE_CHECKING:
    from docutranslate.converter.x2md.converter_docling import ConverterDoclingConfig
from docutranslate.converter.x2md.converter_mineru import ConverterMineruConfig
from docutranslate.exporter.md.md2html_exporter import MD2HTMLExporterConfig
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

# ------------------------------------

from docutranslate.logger import global_logger
from docutranslate.translator import default_params
from docutranslate.utils.resource_utils import resource_path

# --- 全局配置 ---
tasks_state: Dict[str, Dict[str, Any]] = {}
tasks_log_queues: Dict[str, asyncio.Queue] = {}
tasks_log_histories: Dict[str, List[str]] = {}
MAX_LOG_HISTORY = 200
httpx_client: httpx.AsyncClient

# --- Workflow字典 ---
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
}

# --- 媒体类型映射 ---
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
}


# --- 辅助函数 ---
def _create_default_task_state() -> Dict[str, Any]:
    """创建新的默认任务状态，存储 workflow 实例而不是具体内容"""
    return {
        "is_processing": False,
        "status_message": "空闲",
        "error_flag": False,
        "download_ready": False,
        "workflow_instance": None,  # 仅在处理期间使用
        "original_filename_stem": None,
        "task_start_time": 0,
        "task_end_time": 0,
        "current_task_ref": None,
        "original_filename": None,
        "temp_dir": None,  # 用于存储临时文件的目录
        "downloadable_files": {},  # 存储可下载文件的路径和名称
        "attachment_files": {},  # 存储附件文件的路径和标识符
    }


# --- 日志处理器 ---
class QueueAndHistoryHandler(logging.Handler):
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
                main_loop = getattr(app.state, "main_event_loop", None)
                if main_loop and main_loop.is_running():
                    main_loop.call_soon_threadsafe(self.queue.put_nowait, log_entry)
                else:
                    self.queue.put_nowait(log_entry)
            except asyncio.QueueFull:
                print(f"[{self.task_id}] Log queue is full. Log dropped: {log_entry}")
            except Exception as e:
                print(
                    f"[{self.task_id}] Error putting log to queue: {e}. Log: {log_entry}"
                )


# --- 应用生命周期事件 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global httpx_client
    app.state.main_event_loop = asyncio.get_running_loop()
    httpx_client = httpx.AsyncClient()
    tasks_state.clear()
    tasks_log_queues.clear()
    tasks_log_histories.clear()
    global_logger.propagate = False
    global_logger.setLevel(logging.INFO)
    print("应用启动完成，多任务状态已初始化。")
    print(f"服务接口文档: http://127.0.0.1:{app.state.port_to_use}/docs")
    print(f"请用浏览器访问 http://127.0.0.1:{app.state.port_to_use}\n")
    yield
    # 清理任何可能残留的临时目录
    for task_id, task_state in tasks_state.items():
        temp_dir = task_state.get("temp_dir")
        if temp_dir and os.path.isdir(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                print(f"应用关闭，清理任务 '{task_id}' 的临时目录: {temp_dir}")
            except Exception as e:
                print(f"清理任务 '{task_id}' 的临时目录 '{temp_dir}' 时出错: {e}")
    await httpx_client.aclose()
    print("应用关闭，资源已清理。")


# --- FastAPI 应用和路由设置 ---
tags_metadata = [
    {
        "name": "Service API",
        "description": "核心的服务API，用于提交、管理和下载翻译任务。",
    },
    {
        "name": "Application",
        "description": "应用本身的相关端点，如元信息和默认参数。",
    },
    {
        "name": "Temp",
        "description": "测试用接口。",
    },
]

app = FastAPI(
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
    title="DocuTranslate API",
    description=f"""
DocuTranslate 后端服务 API，提供文档翻译、状态查询、结果下载等功能。

**注意**: 所有任务状态都保存在服务进程的内存中，服务重启将导致所有任务信息丢失。

### 主要工作流程:
1.  **`POST /service/translate`**: 提交文件和包含`workflow_type`的翻译参数，启动一个后台任务。服务会自动生成并返回一个唯一的 `task_id`。
2.  **`GET /service/status/{{task_id}}`**: 使用获取到的 `task_id` 轮询此端点，获取任务的实时状态。
3.  **`GET /service/logs/{{task_id}}`**: (可选) 获取实时的翻译日志。
4.  **`GET /service/download/{{task_id}}/{{file_type}}`**: 任务完成后 (当 `download_ready` 为 `true` 时)，通过此端点下载结果文件。
5.  **`GET /service/attachment/{{task_id}}/{{identifier}}`**: (可选) 如果任务生成了附件（如术语表），通过此端点下载。
6.  **`GET /service/content/{{task_id}}/{{file_type}}`**: 任务完成后(当 `download_ready` 为 `true` 时)，以JSON格式获取文件内容。
7.  **`POST /service/cancel/{{task_id}}`**: (可选) 取消一个正在进行的任务。
8.  **`POST /service/release/{{task_id}}`**: (可选) 当任务不再需要时，释放其在服务器上占用的所有资源，包括临时文件。

**版本**: {__version__}
""",
    version=__version__,
    openapi_tags=tags_metadata,
)
# mimetypes.add_type("application/wasm", ".wasm")
service_router = APIRouter(prefix="/service", tags=["Service API"])
STATIC_DIR = resource_path("static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ===================================================================
# --- Pydantic Models for Service API ---
# ===================================================================


class GlossaryAgentConfigPayload(BaseModel):
    base_url: str = Field(
        ...,
        validation_alias=AliasChoices("base_url", "baseurl"),
        description="用于术语表生成的Agent的LLM API基础URL。",
        examples=["https://api.openai.com/v1"],
    )
    api_key: str = Field(
        ...,
        validation_alias=AliasChoices("api_key", "key"),
        description="用于术语表生成的Agent的LLM API密钥。",
        examples=["sk-agent-api-key"],
    )
    model_id: str = Field(
        ..., description="用于术语表生成的Agent的模型ID。", examples=["gpt-4-turbo"]
    )
    to_lang: str = Field(
        ..., description="术语表生成的目标语言。", examples=["简体中文", "English"]
    )
    temperature: float = Field(
        default=0.7, description="用于术语表生成的Agent的温度参数。"
    )
    concurrent: int = Field(default=30, description="Agent的最大并发请求数。")
    timeout: int = Field(
        default=default_params["timeout"], description="等待API回复的时间（秒）。"
    )
    thinking: ThinkingMode = Field(default="default", description="Agent的思考模式。")
    retry: int = Field(
        default=default_params["retry"], description="分块失败后的最大重试次数。"
    )
    system_proxy_enable: bool = Field(
        default=USE_PROXY, description="是否使用系统代理", examples=[True, False]
    )


# 1. 定义所有工作流共享的基础参数
class BaseWorkflowParams(BaseModel):
    skip_translate: bool = Field(
        default=False,
        description="是否跳过翻译步骤。如果为True，则仅执行文档解析和格式转换。",
    )
    base_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("base_url", "baseurl"),
        description="LLM API的基础URL。当 `skip_translate` 为 `False` 时必填。",
        examples=["https://api.openai.com/v1"],
    )
    api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("api_key", "key"),
        description="LLM API的密钥（可选）。",
        examples=["sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
    )
    model_id: Optional[str] = Field(
        default=None,
        description="要使用的LLM模型ID。当 `skip_translate` 为 `False` 时必填。",
        examples=["gpt-4o"],
    )
    to_lang: str = Field(
        default="中文", description="目标翻译语言。", examples=["简体中文", "English"]
    )
    chunk_size: int = Field(
        default=default_params["chunk_size"], description="文本分割的块大小（字符）。"
    )
    concurrent: int = Field(
        default=default_params["concurrent"], description="并发请求数。"
    )
    temperature: float = Field(
        default=default_params["temperature"], description="LLM温度参数。"
    )
    timeout: int = Field(
        default=default_params["timeout"], description="等待API回复的时间（秒）。"
    )
    thinking: ThinkingMode = Field(
        default=default_params["thinking"],
        description="Agent的思考模式。",
        examples=["default", "enable", "disable"],
    )
    retry: int = Field(
        default=default_params["retry"],
        description="某个分块翻译失败后的最大重试次数。",
    )
    system_proxy_enable: bool = Field(
        default=USE_PROXY, description="是否使用系统代理", examples=[True, False]
    )
    custom_prompt: Optional[str] = Field(
        None, description="用户自定义的翻译Prompt。", alias="custom_prompt"
    )
    glossary_dict: Optional[Dict[str, str]] = Field(
        None, description="术语表字典，key为原文，value为译文。"
    )
    glossary_generate_enable: bool = Field(
        default=False, description="是否开启术语表自动生成。"
    )
    glossary_agent_config: Optional[GlossaryAgentConfigPayload] = Field(
        None,
        description="用于术语表生成的Agent的配置。如果 `glossary_generate_enable` 为 `True`，此项必填。",
    )

    @model_validator(mode="before")
    @classmethod
    def check_translation_fields(cls, values):
        # 如果不跳过翻译 (值为False或字段不存在)，则验证相关字段必须存在且不为空
        if not values.get("skip_translate"):
            # Check for standard keys or their aliases
            if not (values.get("base_url") or values.get("baseurl")):
                raise ValueError(
                    "当 `skip_translate` 为 `False` 时, `base_url` 或 `baseurl` 字段是必须的。"
                )
            if not values.get("model_id"):
                raise ValueError(
                    "当 `skip_translate` 为 `False` 时, `model_id` 字段是必须的。"
                )
        # 如果跳过翻译，则不进行任何检查，允许 base_url 等字段为空
        return values


# 2. 为每个工作流创建独立的参数模型
class MarkdownWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal["markdown_based"] = Field(
        ..., description="指定使用基于Markdown的翻译工作流。"
    )
    convert_engine: ConvertEngineType = Field(
        "identity",
        description="选择将文件解析为markdown的引擎。如果输入文件是.md，此项可为`null`或不传。",
        examples=["identity", "mineru", "docling"],
    )
    mineru_token: Optional[str] = Field(
        None, description="当 `convert_engine` 为 'mineru' 时必填的API令牌。"
    )
    formula_ocr: bool = Field(
        True, description="是否对公式进行OCR识别。对 `mineru` 和 `docling` 均有效。"
    )
    code_ocr: bool = Field(
        True, description="是否对代码块进行OCR识别。仅 `docling` 引擎有效。"
    )
    model_version: Literal["pipeline", "vlm"] = Field(
        "vlm", description="Mineru模型的版本，'vlm'是更新的版本。仅 `mineru` 引擎有效。"
    )

    @field_validator("mineru_token")
    def check_mineru_token(cls, v, values):
        if values.data.get("convert_engine") == "mineru" and not v:
            raise ValueError(
                "当 `convert_engine` 为 'mineru' 时，`mineru_token` 字段是必须的。"
            )
        return v


class TextWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal["txt"] = Field(
        ..., description="指定使用纯文本的翻译工作流。"
    )
    insert_mode: Literal["replace", "append", "prepend"] = Field(
        "replace",
        description="翻译文本的插入模式。'replace'：替换原文，'append'：附加到原文后，'prepend'：附加到原文前。",
    )
    separator: str = Field(
        "\n",
        description="当 insert_mode 为 'append' 或 'prepend' 时，用于分隔原文和译文的分隔符。",
    )


class JsonWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal["json"] = Field(
        ..., description="指定使用JSON的翻译工作流。"
    )
    json_paths: List[str] = Field(
        ...,
        description="一个jsonpath-ng表达式列表，用于指定需要翻译的JSON字段。",
        examples=[["$.product.name", "$.product.description", "$.features[*]"]],
    )


class XlsxWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal["xlsx"] = Field(
        ..., description="指定使用XLSX的翻译工作流。"
    )
    insert_mode: Literal["replace", "append", "prepend"] = Field(
        "replace",
        description="翻译文本的插入模式。'replace'：替换原文，'append'：附加到原文后，'prepend'：附加到原文前。",
    )
    separator: str = Field(
        "\n",
        description="当 insert_mode 为 'append' 或 'prepend' 时，用于分隔原文和译文的分隔符。",
    )
    translate_regions: Optional[List[str]] = Field(
        None,
        description="指定翻译区域列表。示例: ['Sheet1!A1:B10', 'C:D', 'E5']。如果不指定表名 (如 'C:D')，则应用于所有表。如果为 None，则翻译整个文件中的所有文本。",
    )


class DocxWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal["docx"] = Field(
        ..., description="指定使用DOCX的翻译工作流。"
    )
    insert_mode: Literal["replace", "append", "prepend"] = Field(
        "replace",
        description="翻译文本的插入模式。'replace'：替换原文，'append'：附加到原文后，'prepend'：附加到原文前。",
    )
    separator: str = Field(
        "\n",
        description="当 insert_mode 为 'append' 或 'prepend' 时，用于分隔原文和译文的分隔符。",
    )


class SrtWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal["srt"] = Field(
        ..., description="指定使用SRT字幕的翻译工作流。"
    )
    insert_mode: Literal["replace", "append", "prepend"] = Field(
        "replace",
        description="翻译文本的插入模式。'replace'：替换原文，'append'：附加到原文后，'prepend'：附加到原文前。",
    )
    separator: str = Field(
        "\n",
        description="当 insert_mode 为 'append' 或 'prepend' 时，用于分隔原文和译文的分隔符。",
    )


class EpubWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal["epub"] = Field(
        ..., description="指定使用EPUB的翻译工作流。"
    )
    insert_mode: Literal["replace", "append", "prepend"] = Field(
        "replace",
        description="翻译文本的插入模式。'replace'：替换原文，'append'：附加到原文后，'prepend'：附加到原文前。",
    )
    separator: str = Field(
        "\n",
        description="当 insert_mode 为 'append' 或 'prepend' 时，用于分隔原文和译文的分隔符。",
    )


# --- HTML WORKFLOW PARAMS START ---
class HtmlWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal["html"] = Field(
        ..., description="指定使用HTML的翻译工作流。"
    )
    insert_mode: Literal["replace", "append", "prepend"] = Field(
        "replace",
        description="翻译文本的插入模式。'replace'：替换原文，'append'：附加到原文后，'prepend'：附加到原文前。",
    )
    separator: str = Field(
        " ",
        description="当 insert_mode 为 'append' 或 'prepend' 时，用于分隔原文和译文的分隔符。",
    )


# --- HTML WORKFLOW PARAMS END ---


# --- ASS WORKFLOW PARAMS START ---
class AssWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal["ass"] = Field(
        ..., description="指定使用ASS字幕的翻译工作流。"
    )
    insert_mode: Literal["replace", "append", "prepend"] = Field(
        "replace",
        description="翻译文本的插入模式。'replace'：替换原文，'append'：附加到原文后，'prepend'：附加到原文前。",
    )
    separator: str = Field(
        "\\N",
        description="当 insert_mode 为 'append' 或 'prepend' 时，用于分隔原文和译文的分隔符。ASS格式通常使用 \\N 作为换行符。",
    )


# --- ASS WORKFLOW PARAMS END ---


# 3. 使用可辨识联合类型（Discriminated Union）将它们组合起来
TranslatePayload = Annotated[
    Union[
        MarkdownWorkflowParams,
        TextWorkflowParams,
        JsonWorkflowParams,
        XlsxWorkflowParams,
        DocxWorkflowParams,
        SrtWorkflowParams,
        EpubWorkflowParams,
        HtmlWorkflowParams,
        AssWorkflowParams,
    ],
    Field(discriminator="workflow_type"),
]


# 4. 创建最终的请求体模型
class TranslateServiceRequest(BaseModel):
    file_name: str = Field(
        ...,
        description="上传的原始文件名，含扩展名。",
        examples=[
            "my_paper.pdf",
            "chapter1.txt",
            "data.xlsx",
            "video.srt",
            "my_book.epub",
            "index.html",
            "dialogue.ass",
        ],
    )
    file_content: str = Field(
        ..., description="Base64编码的文件内容。", examples=["JVBERi0xLjQK..."]
    )
    payload: TranslatePayload = Field(
        ..., description="包含工作流类型和相应参数的载荷。"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "file_name": "annual_report_203.pdf",
                    "file_content": "JVBERi0xLjcKJeLjz9MKMSAwIG9iago8PC9...",
                    "payload": {
                        "workflow_type": "markdown_based",
                        "skip_translate": False,
                        "base_url": "https://api.openai.com/v1",
                        "api_key": "sk-your-api-key-here",
                        "model_id": "gpt-4o",
                        "to_lang": "中文",
                        "chunk_size": default_params["chunk_size"],
                        "concurrent": default_params["concurrent"],
                        "temperature": default_params["temperature"],
                        "timeout": default_params["timeout"],
                        "thinking": "default",
                        "retry": default_params["retry"],
                        "glossary_generate_enable": False,
                        "convert_engine": "mineru",
                        "mineru_token": "your-mineru-token-if-any",
                        "formula_ocr": True,
                        "model_version": "vlm",
                    },
                },
                {
                    "file_name": "product_info.json",
                    "file_content": "ewogICAgImlkIjogIjEyMzQ1IiwK...",
                    "payload": {
                        "workflow_type": "json",
                        "skip_translate": False,
                        "base_url": "https://api.openai.com/v1",
                        "api_key": "sk-your-api-key-here",
                        "model_id": "gpt-4o",
                        "to_lang": "中文",
                        "chunk_size": default_params["chunk_size"],
                        "concurrent": default_params["concurrent"],
                        "temperature": default_params["temperature"],
                        "timeout": default_params["timeout"],
                        "thinking": "default",
                        "retry": default_params["retry"],
                        "glossary_generate_enable": False,
                        "json_paths": [
                            "$.product.name",
                            "$.product.description",
                            "$.features[*]",
                        ],
                    },
                },
                {
                    "file_name": "product_list.xlsx",
                    "file_content": "UEsDBBQAAAAIA... (base64-encoded xlsx)",
                    "payload": {
                        "workflow_type": "xlsx",
                        "skip_translate": False,
                        "base_url": "https://api.openai.com/v1",
                        "api_key": "sk-your-api-key-here",
                        "model_id": "gpt-4o",
                        "to_lang": "中文",
                        "chunk_size": default_params["chunk_size"],
                        "concurrent": default_params["concurrent"],
                        "temperature": default_params["temperature"],
                        "timeout": default_params["timeout"],
                        "thinking": "default",
                        "retry": default_params["retry"],
                        "glossary_generate_enable": False,
                        "insert_mode": "replace",
                        "separator": "\n",
                        "translate_regions": ["Sheet1!A1:B10", "C:D"],
                        "glossary_dict": {
                            "OpenAI": "开放人工智能",
                            "LLM": "大语言模型",
                        },
                    },
                },
                {
                    "file_name": "complex_terms.xlsx",
                    "file_content": "UEsDBBQAAAAIA... (base64-encoded xlsx)",
                    "payload": {
                        "workflow_type": "xlsx",
                        "base_url": "https://api.openai.com/v1",
                        "api_key": "sk-your-main-translator-key",
                        "model_id": "gpt-4o",
                        "to_lang": "中文",
                        "retry": default_params["retry"],
                        "glossary_generate_enable": True,
                        "glossary_agent_config": {
                            "base_url": "https://api.openai.com/v1",
                            "api_key": "sk-your-agent-key-for-glossary",
                            "model_id": "gpt-4-turbo",
                            "to_lang": "中文",
                            "temperature": 0.7,
                            "concurrent": 30,
                            "timeout": default_params["timeout"],
                            "thinking": "default",
                            "retry": default_params["retry"],
                        },
                    },
                },
                {
                    "file_name": "contract.docx",
                    "file_content": "UEsDBBQAAAAIA... (base64-encoded docx)",
                    "payload": {
                        "workflow_type": "docx",
                        "skip_translate": False,
                        "base_url": "https://api.openai.com/v1",
                        "api_key": "sk-your-api-key-here",
                        "model_id": "gpt-4o",
                        "to_lang": "中文",
                        "insert_mode": "replace",
                        "separator": "\n",
                        "chunk_size": default_params["chunk_size"],
                        "concurrent": default_params["concurrent"],
                        "temperature": default_params["temperature"],
                        "timeout": default_params["timeout"],
                        "thinking": "default",
                        "retry": default_params["retry"],
                    },
                },
                {
                    "file_name": "movie.srt",
                    "file_content": "MSAKMDA6MDA6MDEsMjAwIC0tPiAwMDowMD...",
                    "payload": {
                        "workflow_type": "srt",
                        "skip_translate": False,
                        "base_url": "https://api.openai.com/v1",
                        "api_key": "sk-your-api-key-here",
                        "model_id": "gpt-4o",
                        "to_lang": "中文",
                        "insert_mode": "replace",
                        "separator": "\n",
                        "chunk_size": default_params["chunk_size"],
                        "concurrent": default_params["concurrent"],
                        "temperature": default_params["temperature"],
                        "timeout": default_params["timeout"],
                        "thinking": "default",
                        "retry": default_params["retry"],
                    },
                },
                {
                    "file_name": "my_book.epub",
                    "file_content": "UEsDBBQAAAAIA... (base64-encoded epub)",
                    "payload": {
                        "workflow_type": "epub",
                        "skip_translate": False,
                        "base_url": "https://api.openai.com/v1",
                        "api_key": "sk-your-api-key-here",
                        "model_id": "gpt-4o",
                        "to_lang": "中文",
                        "insert_mode": "replace",
                        "separator": "\n",
                        "chunk_size": default_params["chunk_size"],
                        "concurrent": default_params["concurrent"],
                        "temperature": default_params["temperature"],
                        "timeout": default_params["timeout"],
                        "thinking": "default",
                        "retry": default_params["retry"],
                    },
                },
                {
                    "file_name": "company_about_us.html",
                    "file_content": "PGh0bWw+PGhlYWQ+PHRpdGxlPkFib3V0IFVzPC90aXRsZT48L2hlYWQ+PGJvZHk+PGgxPk91ciBDb21wYW55PC9oMT48cD5XZSBhcmUgYSBsZWFkaW5nIHByb3ZpZGVyIG9mIGlubm92YXRpdmUgc29sdXRpb25zLjwvcD48L2JvZHk+PC9odG1sPg==",
                    "payload": {
                        "workflow_type": "html",
                        "skip_translate": False,
                        "base_url": "https://api.openai.com/v1",
                        "api_key": "sk-your-api-key-here",
                        "model_id": "gpt-4o",
                        "to_lang": "中文",
                        "insert_mode": "replace",
                        "separator": " ",
                        "chunk_size": default_params["chunk_size"],
                        "concurrent": default_params["concurrent"],
                        "temperature": default_params["temperature"],
                        "timeout": default_params["timeout"],
                        "thinking": "default",
                        "retry": default_params["retry"],
                    },
                },
                {
                    "file_name": "dialogue.ass",
                    "file_content": "U2NyaXB0IEluZm8NC...",
                    "payload": {
                        "workflow_type": "ass",
                        "skip_translate": False,
                        "base_url": "https://api.openai.com/v1",
                        "api_key": "sk-your-api-key-here",
                        "model_id": "gpt-4o",
                        "to_lang": "中文",
                        "insert_mode": "replace",
                        "separator": "\\N",
                        "chunk_size": default_params["chunk_size"],
                        "concurrent": default_params["concurrent"],
                        "temperature": default_params["temperature"],
                        "timeout": default_params["timeout"],
                        "thinking": "default",
                        "retry": default_params["retry"],
                    },
                },
            ]
        }


# --- Background Task Logic ---
async def _perform_translation(
    task_id: str,
    payload: TranslatePayload,
    file_contents: bytes,
    original_filename: str,
):
    task_state = tasks_state[task_id]
    log_queue = tasks_log_queues[task_id]
    log_history = tasks_log_histories[task_id]

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
    temp_dir = None

    try:
        # 1. 根据工作流类型选择合适的 Workflow Class
        workflow_class = WORKFLOW_DICT.get(payload.workflow_type)
        if not workflow_class:
            raise ValueError(f"不支持的工作流类型: '{payload.workflow_type}'")

        workflow: Workflow

        # 辅助函数：构建术语表生成配置
        def build_glossary_agent_config():
            if payload.glossary_generate_enable and payload.glossary_agent_config:
                agent_payload = payload.glossary_agent_config
                return GlossaryAgentConfig(
                    logger=task_logger, **agent_payload.model_dump()
                )
            return None

        # 2. 根据 payload 的具体类型构建配置并实例化 workflow
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
                },
                exclude_none=True,
            )
            translator_args["glossary_generate_enable"] = (
                payload.glossary_generate_enable
            )
            translator_args["glossary_agent_config"] = build_glossary_agent_config()
            translator_config = MDTranslatorConfig(**translator_args)

            converter_config = None
            if payload.convert_engine == "mineru":
                converter_config = ConverterMineruConfig(
                    logger=task_logger,
                    mineru_token=payload.mineru_token,
                    formula_ocr=payload.formula_ocr,
                    model_version=payload.model_version,
                )
            elif payload.convert_engine == "docling" and DOCLING_EXIST:
                converter_config = ConverterDoclingConfig(
                    logger=task_logger,
                    code_ocr=payload.code_ocr,
                    formula_ocr=payload.formula_ocr,
                )
            html_exporter_config = MD2HTMLExporterConfig(cdn=True)
            workflow_config = MarkdownBasedWorkflowConfig(
                convert_engine=payload.convert_engine,
                converter_config=converter_config,
                translator_config=translator_config,
                html_exporter_config=html_exporter_config,
                logger=task_logger,
            )
            workflow = MarkdownBasedWorkflow(config=workflow_config)

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
                    "timeout",
                    "retry",
                    "system_proxy_enable",
                },
                exclude_none=True,
            )
            translator_args["glossary_generate_enable"] = (
                payload.glossary_generate_enable
            )
            translator_args["glossary_agent_config"] = build_glossary_agent_config()
            translator_config = TXTTranslatorConfig(**translator_args)

            html_exporter_config = TXT2HTMLExporterConfig(cdn=True)
            workflow_config = TXTWorkflowConfig(
                translator_config=translator_config,
                html_exporter_config=html_exporter_config,
                logger=task_logger,
            )
            workflow = TXTWorkflow(config=workflow_config)

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
                },
                exclude_none=True,
            )
            translator_args["glossary_generate_enable"] = (
                payload.glossary_generate_enable
            )
            translator_args["glossary_agent_config"] = build_glossary_agent_config()
            translator_config = JsonTranslatorConfig(**translator_args)

            html_exporter_config = Json2HTMLExporterConfig(cdn=True)
            workflow_config = JsonWorkflowConfig(
                translator_config=translator_config,
                html_exporter_config=html_exporter_config,
                logger=task_logger,
            )
            workflow = JsonWorkflow(config=workflow_config)

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
                },
                exclude_none=True,
            )
            translator_args["glossary_generate_enable"] = (
                payload.glossary_generate_enable
            )
            translator_args["glossary_agent_config"] = build_glossary_agent_config()
            translator_config = XlsxTranslatorConfig(**translator_args)

            html_exporter_config = Xlsx2HTMLExporterConfig(cdn=True)
            workflow_config = XlsxWorkflowConfig(
                translator_config=translator_config,
                html_exporter_config=html_exporter_config,
                logger=task_logger,
            )
            workflow = XlsxWorkflow(config=workflow_config)

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
                },
                exclude_none=True,
            )
            translator_args["glossary_generate_enable"] = (
                payload.glossary_generate_enable
            )
            translator_args["glossary_agent_config"] = build_glossary_agent_config()
            translator_config = DocxTranslatorConfig(**translator_args)

            html_exporter_config = Docx2HTMLExporterConfig(cdn=True)
            workflow_config = DocxWorkflowConfig(
                translator_config=translator_config,
                html_exporter_config=html_exporter_config,
                logger=task_logger,
            )
            workflow = DocxWorkflow(config=workflow_config)

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
                },
                exclude_none=True,
            )
            translator_args["glossary_generate_enable"] = (
                payload.glossary_generate_enable
            )
            translator_args["glossary_agent_config"] = build_glossary_agent_config()
            translator_config = SrtTranslatorConfig(**translator_args)

            html_exporter_config = Srt2HTMLExporterConfig(cdn=True)
            workflow_config = SrtWorkflowConfig(
                translator_config=translator_config,
                html_exporter_config=html_exporter_config,
                logger=task_logger,
            )
            workflow = SrtWorkflow(config=workflow_config)

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
                },
                exclude_none=True,
            )
            translator_args["glossary_generate_enable"] = (
                payload.glossary_generate_enable
            )
            translator_args["glossary_agent_config"] = build_glossary_agent_config()
            translator_config = EpubTranslatorConfig(**translator_args)

            html_exporter_config = Epub2HTMLExporterConfig(cdn=True)
            workflow_config = EpubWorkflowConfig(
                translator_config=translator_config,
                html_exporter_config=html_exporter_config,
                logger=task_logger,
            )
            workflow = EpubWorkflow(config=workflow_config)

        # --- HTML WORKFLOW LOGIC START ---
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
                },
                exclude_none=True,
            )
            translator_args["glossary_generate_enable"] = (
                payload.glossary_generate_enable
            )
            translator_args["glossary_agent_config"] = build_glossary_agent_config()
            translator_config = HtmlTranslatorConfig(**translator_args)

            workflow_config = HtmlWorkflowConfig(
                translator_config=translator_config, logger=task_logger
            )
            workflow = HtmlWorkflow(config=workflow_config)
        # --- HTML WORKFLOW LOGIC END ---

        # --- ASS WORKFLOW LOGIC START ---
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
                },
                exclude_none=True,
            )
            translator_args["glossary_generate_enable"] = (
                payload.glossary_generate_enable
            )
            translator_args["glossary_agent_config"] = build_glossary_agent_config()
            translator_config = AssTranslatorConfig(**translator_args)

            html_exporter_config = Ass2HTMLExporterConfig(cdn=True)
            workflow_config = AssWorkflowConfig(
                translator_config=translator_config,
                html_exporter_config=html_exporter_config,
                logger=task_logger,
            )
            workflow = AssWorkflow(config=workflow_config)
        # --- ASS WORKFLOW LOGIC END ---

        else:
            raise TypeError(f"工作流类型 '{payload.workflow_type}' 的处理逻辑未实现。")

        # 3. 读取文件内容并执行翻译
        file_stem = Path(original_filename).stem
        file_suffix = Path(original_filename).suffix
        workflow.read_bytes(content=file_contents, stem=file_stem, suffix=file_suffix)
        await workflow.translate_async()

        # 4. 任务成功，生成所有可下载文件并存储
        task_logger.info("翻译完成，正在生成临时结果文件...")
        temp_dir = tempfile.mkdtemp(prefix=f"docutranslate_{task_id}_")
        task_state["temp_dir"] = temp_dir
        downloadable_files = {}
        filename_stem = task_state["original_filename_stem"]

        # 检查CDN可用性
        is_cdn_available = True
        try:
            await httpx_client.head(
                "https://s4.zstatic.net/ajax/libs/KaTeX/0.16.9/contrib/auto-render.min.js",
                timeout=3,
            )
        except (httpx.TimeoutException, httpx.RequestError):
            is_cdn_available = False
            task_logger.warning("CDN连接失败，将使用本地JS进行渲染。")

        # 定义导出函数映射
        export_map = {}

        # 根据 workflow 的类型填充导出映射
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
            export_map["html"] = (
                lambda: workflow.export_to_html(html_config),
                f"{filename_stem}_translated.html",
                True,
            )
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

        # 循环生成文件
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

        # 处理附件文件
        attachment_files = {}
        attachment_object = workflow.get_attachment()
        if attachment_object and attachment_object.attachment_dict:
            task_logger.info(
                f"发现 {len(attachment_object.attachment_dict)} 个附件，正在处理..."
            )
            for identifier, doc in attachment_object.attachment_dict.items():
                try:
                    # 'doc' is a Document object
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

        # 5. 任务成功，更新最终状态
        end_time = time.time()
        duration = end_time - task_state["task_start_time"]
        task_state.update(
            {
                "status_message": f"翻译成功！用时 {duration:.2f} 秒。",
                "download_ready": True,
                "error_flag": False,
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
                "task_end_time": end_time,
            }
        )
    finally:
        # 无论成功失败，都清理内存中的 workflow 实例和临时目录（如果失败）
        task_state["workflow_instance"] = None
        task_state["is_processing"] = False
        task_state["current_task_ref"] = None

        if task_state["error_flag"] and temp_dir and os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir)
            task_logger.info(f"因任务失败，已清理临时目录")
            task_state["temp_dir"] = None

        task_logger.info(f"后台翻译任务 '{original_filename}' 处理结束。")
        task_logger.removeHandler(task_handler)


# --- 核心任务启动逻辑 ---
async def _start_translation_task(
    task_id: str,
    payload: TranslatePayload,
    file_contents: bytes,
    original_filename: str,
):
    if task_id not in tasks_state:
        tasks_state[task_id] = _create_default_task_state()
        tasks_log_queues[task_id] = asyncio.Queue()
        tasks_log_histories[task_id] = []
    task_state = tasks_state[task_id]

    if (
        task_state["is_processing"]
        and task_state["current_task_ref"]
        and not task_state["current_task_ref"].done()
    ):
        raise HTTPException(
            status_code=429, detail=f"任务ID '{task_id}' 正在进行中，请稍后再试。"
        )

    # 如果存在旧的临时文件，先清理
    if task_state.get("temp_dir") and os.path.isdir(task_state["temp_dir"]):
        shutil.rmtree(task_state["temp_dir"])

    task_state.update(
        {
            "is_processing": True,
            "status_message": "任务初始化中...",
            "error_flag": False,
            "download_ready": False,
            "workflow_instance": None,
            "original_filename_stem": Path(original_filename).stem,
            "original_filename": original_filename,
            "task_start_time": time.time(),
            "task_end_time": 0,
            "current_task_ref": None,
            "temp_dir": None,
            "downloadable_files": {},
            "attachment_files": {},
        }
    )

    log_history = tasks_log_histories[task_id]
    log_queue = tasks_log_queues[task_id]
    log_history.clear()
    while not log_queue.empty():
        try:
            log_queue.get_nowait()
        except asyncio.QueueEmpty:
            break

    initial_log_msg = f"收到新的翻译请求: {original_filename}"
    print(f"[{task_id}] {initial_log_msg}")
    log_history.append(initial_log_msg)
    await log_queue.put(initial_log_msg)

    try:
        loop = asyncio.get_running_loop()
        task = loop.create_task(
            _perform_translation(task_id, payload, file_contents, original_filename)
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


# --- 取消任务逻辑 ---
def _cancel_translation_logic(task_id: str):
    task_state = tasks_state.get(task_id)
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


# ===================================================================
# --- Service Endpoints (/service) ---
# ===================================================================


@service_router.post(
    "/translate",
    summary="提交翻译任务 (统一入口)",
    description="""
接收一个包含文件内容（Base64编码）和工作流参数的JSON请求，启动一个后台翻译任务。

- **工作流选择**: 请求体中的 `payload.workflow_type` 字段决定了本次任务的类型（如 `markdown_based`, `txt`, `json`, `xlsx`, `docx`, `srt`, `epub`, `html`, `ass`）。
- **动态参数**: 根据所选工作流，API需要不同的参数集。请参考下面的Schema或示例。
- **异步处理**: 此端点会立即返回任务ID，客户端需轮询状态接口获取进度。
""",
    responses={
        200: {
            "description": "翻译任务已成功启动。",
            "content": {
                "application/json": {
                    "example": {
                        "task_started": True,
                        "task_id": "a1b2c3d4",
                        "message": "翻译任务已成功启动，请稍候...",
                    }
                }
            },
        },
        400: {"description": "请求体无效，例如Base64解码失败。"},
        429: {
            "description": "服务器已有一个同ID的任务在处理中（理论上不应发生，因为ID是新生成的）。"
        },
        500: {"description": "启动后台任务时发生未知错误。"},
    },
)
async def service_translate(
    request: TranslateServiceRequest = Body(
        ..., description="翻译任务的详细参数和文件内容。"
    )
):
    task_id = uuid.uuid4().hex[:8]

    try:
        file_contents = base64.b64decode(request.file_content)
    except (binascii.Error, TypeError) as e:
        raise HTTPException(status_code=400, detail=f"无效的Base64文件内容: {e}")

    try:
        response_data = await _start_translation_task(
            task_id=task_id,
            payload=request.payload,
            file_contents=file_contents,
            original_filename=request.file_name,
        )
        return JSONResponse(content=response_data)
    except HTTPException as e:
        if e.status_code == 429:
            return JSONResponse(
                status_code=e.status_code,
                content={"task_started": False, "message": e.detail},
            )
        if e.status_code == 500:
            return JSONResponse(
                status_code=e.status_code,
                content={"task_started": False, "message": e.detail},
            )
        raise e


@service_router.post(
    "/cancel/{task_id}",
    summary="取消翻译任务",
    description="""根据任务ID取消一个正在进行中的翻译任务。如果任务已经完成、失败或已经被取消，则会返回错误。""",
)
async def service_cancel_translate(task_id: str):
    return _cancel_translation_logic(task_id)


@service_router.post(
    "/release/{task_id}",
    summary="释放任务资源",
    description="""根据任务ID释放其在服务器上占用的所有资源，包括状态、日志和缓存的翻译结果文件。如果任务正在进行，会先尝试取消该任务。此操作不可逆。""",
)
async def service_release_task(task_id: str):
    if task_id not in tasks_state:
        return JSONResponse(
            status_code=404,
            content={"released": False, "message": f"找不到任务ID '{task_id}'。"},
        )
    task_state = tasks_state.get(task_id)
    message_parts = []
    if (
        task_state
        and task_state.get("is_processing")
        and task_state.get("current_task_ref")
    ):
        try:
            print(f"[{task_id}] 任务正在进行中，将在释放前尝试取消。")
            _cancel_translation_logic(task_id)
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

    tasks_state.pop(task_id, None)
    tasks_log_queues.pop(task_id, None)
    tasks_log_histories.pop(task_id, None)
    print(f"[{task_id}] 资源已成功释放。")
    message_parts.append(f"任务 '{task_id}' 的资源已释放。")
    return JSONResponse(content={"released": True, "message": " ".join(message_parts)})


@service_router.get(
    "/status/{task_id}",
    summary="获取任务状态",
    description="根据任务ID获取任务的当前状态。当 `download_ready` 为 `true` 时，`downloads` 和 `attachment` 对象中会包含可用的下载链接。",
    responses={
        200: {
            "description": "成功获取任务状态。",
            "content": {
                "application/json": {
                    "examples": {
                        "processing": {
                            "summary": "进行中",
                            "value": {
                                "task_id": "a1b2c3d4",
                                "is_processing": True,
                                "status_message": "正在处理 'annual_report.pdf'...",
                                "error_flag": False,
                                "download_ready": False,
                                "original_filename_stem": "annual_report",
                                "original_filename": "annual_report.pdf",
                                "task_start_time": 1678889400.0,
                                "task_end_time": 0,
                                "downloads": {},
                                "attachment": {},
                            },
                        },
                        "completed_markdown": {
                            "summary": "已完成 (Markdown)",
                            "value": {
                                "task_id": "b2865b93",
                                "is_processing": False,
                                "status_message": "翻译成功！用时 123.45 秒。",
                                "error_flag": False,
                                "download_ready": True,
                                "original_filename_stem": "my_paper",
                                "original_filename": "my_paper.pdf",
                                "task_start_time": 1678889400.123,
                                "task_end_time": 1678889523.573,
                                "downloads": {
                                    "html": "/service/download/b2865b93/html",
                                    "markdown": "/service/download/b2865b93/markdown",
                                    "markdown_zip": "/service/download/b2865b93/markdown_zip",
                                },
                                "attachment": {},
                            },
                        },
                        "completed_with_attachment": {
                            "summary": "已完成 (带附件)",
                            "value": {
                                "task_id": "g1h2i3j4",
                                "is_processing": False,
                                "status_message": "翻译成功！用时 125.00 秒。",
                                "error_flag": False,
                                "download_ready": True,
                                "original_filename_stem": "complex_document",
                                "original_filename": "complex_document.docx",
                                "task_start_time": 1678891000.0,
                                "task_end_time": 1678891125.0,
                                "downloads": {
                                    "docx": "/service/download/g1h2i3j4/docx",
                                    "html": "/service/download/g1h2i3j4/html",
                                },
                                "attachment": {
                                    "glossary": "/service/attachment/g1h2i3j4/glossary"
                                },
                            },
                        },
                        "completed_xlsx": {
                            "summary": "已完成 (XLSX)",
                            "value": {
                                "task_id": "d7e8f9a0",
                                "is_processing": False,
                                "status_message": "翻译成功！用时 18.99 秒。",
                                "error_flag": False,
                                "download_ready": True,
                                "original_filename_stem": "sales_data",
                                "original_filename": "sales_data.xlsx",
                                "task_start_time": 1678889600.0,
                                "task_end_time": 1678889618.99,
                                "downloads": {
                                    "xlsx": "/service/download/d7e8f9a0/xlsx",
                                    "csv": "/service/download/d7e8f9a0/csv",
                                    "html": "/service/download/d7e8f9a0/html",
                                },
                                "attachment": {},
                            },
                        },
                        "completed_docx": {
                            "summary": "已完成 (DOCX)",
                            "value": {
                                "task_id": "f8a9c1b2",
                                "is_processing": False,
                                "status_message": "翻译成功！用时 25.10 秒。",
                                "error_flag": False,
                                "download_ready": True,
                                "original_filename_stem": "contract",
                                "original_filename": "contract.docx",
                                "task_start_time": 1678889500.123,
                                "task_end_time": 1678889525.223,
                                "downloads": {
                                    "docx": "/service/download/f8a9c1b2/docx",
                                    "html": "/service/download/f8a9c1b2/html",
                                },
                                "attachment": {},
                            },
                        },
                        "completed_epub": {
                            "summary": "已完成 (EPUB)",
                            "value": {
                                "task_id": "e9b8d7c6",
                                "is_processing": False,
                                "status_message": "翻译成功！用时 45.32 秒。",
                                "error_flag": False,
                                "download_ready": True,
                                "original_filename_stem": "my_book",
                                "original_filename": "my_book.epub",
                                "task_start_time": 1678890000.0,
                                "task_end_time": 1678890045.32,
                                "downloads": {
                                    "epub": "/service/download/e9b8d7c6/epub",
                                    "html": "/service/download/e9b8d7c6/html",
                                },
                                "attachment": {},
                            },
                        },
                        # --- HTML STATUS EXAMPLE START ---
                        "completed_html": {
                            "summary": "已完成 (HTML)",
                            "value": {
                                "task_id": "a1b2c3d4",
                                "is_processing": False,
                                "status_message": "翻译成功！用时 15.78 秒。",
                                "error_flag": False,
                                "download_ready": True,
                                "original_filename_stem": "about_us",
                                "original_filename": "about_us.html",
                                "task_start_time": 1678890100.0,
                                "task_end_time": 1678890115.78,
                                "downloads": {
                                    "html": "/service/download/a1b2c3d4/html"
                                },
                                "attachment": {},
                            },
                        },
                        # --- HTML STATUS EXAMPLE END ---
                        # --- ASS STATUS EXAMPLE START ---
                        "completed_ass": {
                            "summary": "已完成 (ASS)",
                            "value": {
                                "task_id": "a1b2c3d5",
                                "is_processing": False,
                                "status_message": "翻译成功！用时 12.34 秒。",
                                "error_flag": False,
                                "download_ready": True,
                                "original_filename_stem": "dialogue",
                                "original_filename": "dialogue.ass",
                                "task_start_time": 1678890200.0,
                                "task_end_time": 1678890212.34,
                                "downloads": {
                                    "ass": "/service/download/a1b2c3d5/ass",
                                    "html": "/service/download/a1b2c3d5/html",
                                },
                                "attachment": {},
                            },
                        },
                        # --- ASS STATUS EXAMPLE END ---
                        "error": {
                            "summary": "失败",
                            "value": {
                                "task_id": "c3d4e5f6",
                                "is_processing": False,
                                "status_message": "翻译过程中发生错误: LLM API key is invalid",
                                "error_flag": True,
                                "download_ready": False,
                                "original_filename_stem": "bad_config",
                                "original_filename": "bad_config.json",
                                "task_start_time": 1678889600.0,
                                "task_end_time": 1678889610.0,
                                "downloads": {},
                                "attachment": {},
                            },
                        },
                    }
                }
            },
        },
        404: {"description": "指定的任务ID不存在。"},
    },
)
async def service_get_status(
    task_id: str = FastApiPath(
        ..., description="要查询状态的任务的ID", examples=["b2865b93"]
    )
):
    task_state = tasks_state.get(task_id)
    if not task_state:
        raise HTTPException(status_code=404, detail=f"找不到任务ID '{task_id}'。")

    downloads = {}
    if task_state.get("download_ready") and task_state.get("downloadable_files"):
        for file_type in task_state["downloadable_files"].keys():
            downloads[file_type] = f"/service/download/{task_id}/{file_type}"

    attachments = {}
    if task_state.get("download_ready") and task_state.get("attachment_files"):
        for identifier in task_state["attachment_files"].keys():
            attachments[identifier] = f"/service/attachment/{task_id}/{identifier}"

    return JSONResponse(
        content={
            "task_id": task_id,
            "is_processing": task_state["is_processing"],
            "status_message": task_state["status_message"],
            "error_flag": task_state["error_flag"],
            "download_ready": task_state["download_ready"],
            "original_filename_stem": task_state["original_filename_stem"],
            "original_filename": task_state.get("original_filename"),
            "task_start_time": task_state["task_start_time"],
            "task_end_time": task_state["task_end_time"],
            "downloads": downloads,
            "attachment": attachments,
        }
    )


@service_router.get(
    "/logs/{task_id}",
    summary="获取任务增量日志",
    description="""以流式方式获取任务的增量日志。客户端每次调用此接口，都会返回自上次调用以来产生的新日志行。这对于实时展示翻译进度非常有用。如果任务ID不存在，则返回404。""",
)
async def service_get_logs(task_id: str):
    if task_id not in tasks_log_queues:
        raise HTTPException(
            status_code=404, detail=f"找不到任务ID '{task_id}' 的日志队列。"
        )
    log_queue = tasks_log_queues[task_id]
    new_logs = []
    while not log_queue.empty():
        try:
            new_logs.append(log_queue.get_nowait())
            log_queue.task_done()
        except asyncio.QueueEmpty:
            break
    return JSONResponse(content={"logs": new_logs})


FileType = Literal[
    "markdown",
    "markdown_zip",
    "html",
    "txt",
    "json",
    "xlsx",
    "csv",
    "docx",
    "srt",
    "epub",
    "ass",
]


@service_router.get(
    "/download/{task_id}/{file_type}",
    summary="下载翻译结果文件",
    responses={
        200: {
            "description": "成功返回文件流。文件名通过 Content-Disposition 头指定。",
            "content": {
                "text/html; charset=utf-8": {"schema": {"type": "string"}},
                "text/markdown; charset=utf-8": {"schema": {"type": "string"}},
                "text/plain; charset=utf-8": {"schema": {"type": "string"}},
                "text/csv; charset=utf-8": {"schema": {"type": "string"}},
                "application/zip": {"schema": {"type": "string", "format": "binary"}},
                "application/json": {"schema": {"type": "string", "format": "binary"}},
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {
                    "schema": {"type": "string", "format": "binary"}
                },
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
                    "schema": {"type": "string", "format": "binary"}
                },
                "application/epub+zip": {
                    "schema": {"type": "string", "format": "binary"}
                },
            },
        },
        404: {
            "description": "任务ID不存在，或该任务不支持所请求的文件类型，或临时文件已丢失。"
        },
        500: {"description": "在服务器上读取文件时发生内部错误。"},
    },
)
async def service_download_file(
    task_id: str = FastApiPath(
        ..., description="已完成任务的ID", examples=["b2865b93"]
    ),
    file_type: FileType = FastApiPath(
        ...,
        description="要下载的文件类型。",
        examples=["html", "json", "csv", "docx", "srt", "epub", "ass"],
    ),
):
    task_state = tasks_state.get(task_id)
    if not task_state:
        raise HTTPException(status_code=404, detail=f"找不到任务ID '{task_id}'。")

    file_info = task_state.get("downloadable_files", {}).get(file_type)
    if not file_info or not os.path.exists(file_info.get("path")):
        raise HTTPException(
            status_code=404,
            detail=f"任务 '{task_id}' 不支持下载 '{file_type}' 类型的文件，或文件已丢失。",
        )

    file_path = file_info["path"]
    filename = file_info["filename"]
    media_type = MEDIA_TYPES.get(file_type, "application/octet-stream")

    return FileResponse(path=file_path, media_type=media_type, filename=filename)


@service_router.get(
    "/attachment/{task_id}/{identifier}",
    summary="下载附件文件",
    description="根据任务ID和附件标识符下载在翻译过程中生成的附加文件，例如自动生成的术语表。",
    responses={
        200: {
            "description": "成功返回文件流。文件名通过 Content-Disposition 头指定。",
            "content": {
                "application/octet-stream": {
                    "schema": {"type": "string", "format": "binary"}
                },
            },
        },
        404: {
            "description": "任务ID不存在，或该任务没有指定的附件，或临时文件已丢失。"
        },
    },
)
async def service_download_attachment(
    task_id: str = FastApiPath(
        ..., description="已完成任务的ID", examples=["g1h2i3j4"]
    ),
    identifier: str = FastApiPath(
        ..., description="要下载的附件的标识符。", examples=["glossary"]
    ),
):
    task_state = tasks_state.get(task_id)
    if not task_state:
        raise HTTPException(status_code=404, detail=f"找不到任务ID '{task_id}'。")

    attachment_info = task_state.get("attachment_files", {}).get(identifier)
    if not attachment_info or not os.path.exists(attachment_info.get("path")):
        raise HTTPException(
            status_code=404,
            detail=f"任务 '{task_id}' 不存在标识符为 '{identifier}' 的附件，或文件已丢失。",
        )

    file_path = attachment_info["path"]
    filename = attachment_info["filename"]

    # Use a generic media type as attachments can be of various formats
    media_type = "application/octet-stream"

    return FileResponse(path=file_path, media_type=media_type, filename=filename)


@service_router.get(
    "/content/{task_id}/{file_type}",
    summary="下载翻译结果内容 (JSON)",
    description="""
以JSON格式获取指定文件类型的内容，而不是直接下载文件。

- **返回结构**: 返回一个JSON对象，包含文件名、文件类型和文件内容的Base64编码字符串。
- **内容编码**: 文件内容总是以 **Base64** 编码，客户端需要自行解码才能使用。
""",
    responses={
        200: {
            "description": "成功返回文件内容。",
            "content": {
                "application/json": {
                    "examples": {
                        "html_base64": {
                            "summary": "HTML 内容 (Base64)",
                            "value": {
                                "file_type": "html",
                                "filename": "my_doc_translated.html",
                                "content": "PGh0bWw+PGhlYWQ+...",
                            },
                        },
                        "docx_base64": {
                            "summary": "DOCX 内容 (Base64)",
                            "value": {
                                "file_type": "docx",
                                "filename": "my_doc_translated.docx",
                                "content": "UEsDBBQAAAAIA... (base64-encoded string)",
                            },
                        },
                        "epub_base64": {
                            "summary": "EPUB 内容 (Base64)",
                            "value": {
                                "file_type": "epub",
                                "filename": "my_book_translated.epub",
                                "content": "UEsDBBQAAAAIA... (base64-encoded string)",
                            },
                        },
                    }
                }
            },
        },
        404: {
            "description": "任务ID不存在，或该任务不支持所请求的文件类型，或临时文件已丢失。"
        },
        500: {"description": "在服务器上读取文件时发生内部错误。"},
    },
)
async def service_content(
    task_id: str = FastApiPath(
        ..., description="已完成任务的ID", examples=["b2865b93"]
    ),
    file_type: FileType = FastApiPath(
        ...,
        description="要获取内容的文件类型。",
        examples=["html", "json", "csv", "docx", "srt", "epub", "ass"],
    ),
):
    task_state = tasks_state.get(task_id)
    if not task_state:
        raise HTTPException(status_code=404, detail=f"找不到任务ID '{task_id}'。")

    file_info = task_state.get("downloadable_files", {}).get(file_type)
    if not file_info or not os.path.exists(file_info.get("path")):
        raise HTTPException(
            status_code=404,
            detail=f"任务 '{task_id}' 不支持获取 '{file_type}' 类型的内容，或文件已丢失。",
        )

    file_path = file_info["path"]
    filename = file_info["filename"]

    try:
        with open(file_path, "rb") as f:
            content_bytes = f.read()
        final_content = base64.b64encode(content_bytes).decode("utf-8")
        return JSONResponse(
            content={
                "file_type": file_type,
                "filename": filename,
                "content": final_content,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件时发生内部错误: {e}")


# ===================================================================
# --- 应用主路由和启动 ---
# ===================================================================
@service_router.get(
    "/engin-list", tags=["Application"], description="返回正在进行的可用的转换引擎"
)
async def service_get_engin_list():
    engin_list = ["mineru"]
    if DOCLING_EXIST:
        engin_list.append("docling")
    return JSONResponse(content=engin_list)


@service_router.get(
    "/task-list", tags=["Application"], description="返回正在进行的task_id列表"
)
async def service_get_task_list():
    return JSONResponse(content=list(tasks_state.keys()))


@service_router.get(
    "/default-params", tags=["Application"], description="返回一些默认参数"
)
def service_get_default_params():
    return JSONResponse(content=default_params)


@service_router.get("/meta", tags=["Application"], description="返回软件版本号")
async def service_get_app_version():
    return JSONResponse(content={"version": __version__})


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def main_page():
    index_path = Path(STATIC_DIR) / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    no_cache_headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    return FileResponse(index_path, headers=no_cache_headers)


@app.get("/admin", response_class=HTMLResponse, include_in_schema=False)
async def main_page_admin():
    index_path = Path(STATIC_DIR) / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    no_cache_headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    return FileResponse(index_path, headers=no_cache_headers)


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/swagger/swagger.js",
        swagger_css_url="/static/swagger/swagger.css",
    )


@app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="/static/redoc/redoc.js",
    )


@app.post("/temp/translate", tags=["Temp"])
async def temp_translate(
    base_url: str = Body(...),
    api_key: str = Body(...),
    model_id: str = Body(...),
    mineru_token: Optional[str] = Body(None),
    file_name: str = Body(...),
    file_content: str = Body(...),
    to_lang: str = Body("中文"),
    concurrent: int = Body(default_params["concurrent"]),
    temperature: float = Body(default_params["temperature"]),
    thinking: ThinkingMode = Body(default_params["thinking"]),
    chunk_size: int = Body(default_params["chunk_size"]),
    custom_prompt: Optional[str] = Body(None),
    model_version: Literal["pipeline", "vlm"] = Body("vlm"),
    glossary_dict: Optional[Dict[str, str]] = Body(None),
):
    file_name = Path(file_name)
    try:
        decoded_content = base64.b64decode(file_content)
    except (ValueError, binascii.Error):
        decoded_content = file_content.encode("utf-8")
    try:
        workflow_config = MarkdownBasedWorkflowConfig(
            convert_engine="mineru",
            converter_config=ConverterMineruConfig(
                mineru_token=mineru_token, model_version=model_version
            ),
            translator_config=MDTranslatorConfig(
                base_url=base_url,
                api_key=api_key,
                model_id=model_id,
                to_lang=to_lang,
                custom_prompt=custom_prompt,
                temperature=temperature,
                thinking=thinking,
                chunk_size=chunk_size,
                concurrent=concurrent,
                glossary_dict=glossary_dict,
            ),
            html_exporter_config=MD2HTMLExporterConfig(),
        )
        workflow = MarkdownBasedWorkflow(workflow_config)
        workflow.read_bytes(
            content=decoded_content, stem=file_name.stem, suffix=file_name.suffix
        )
        await workflow.translate_async()
        return {"success": True, "content": workflow.export_to_markdown()}
    except Exception as e:
        global_logger.error(f"临时翻译接口出现错误：{e.__repr__()}", exc_info=True)
        return {"success": False, "reason": e.__repr__()}


app.include_router(service_router)


def find_free_port(start_port):
    port = start_port
    while True:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
            port += 1


def run_app(port: int | None = None):
    initial_port = port or int(os.environ.get("DOCUTRANSLATE_PORT", 8010))
    try:
        port_to_use = find_free_port(initial_port)
        if port_to_use != initial_port:
            print(f"端口 {initial_port} 被占用，将使用端口 {port_to_use} 代替")
        print(f"正在启动 DocuTranslate WebUI 版本号：{__version__}")
        app.state.port_to_use = port_to_use
        uvicorn.run(app, host=None, port=port_to_use, workers=1)
    except Exception as e:
        print(f"启动失败: {e}")


if __name__ == "__main__":
    run_app()
