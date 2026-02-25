# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
# docutranslate.app.py
import asyncio
import base64
import binascii
import json
import logging
import os
import socket
import uuid
from contextlib import asynccontextmanager, closing
from pathlib import Path
from typing import (
    List,
    Optional,
    Literal,
)

import httpx
import uvicorn
from fastapi import (
    FastAPI,
    HTTPException,
    APIRouter,
    Body,
    Path as FastApiPath,
    UploadFile,
    File,
    Form,
    Request
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import (
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
    get_redoc_html,
)
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    Json,
    TypeAdapter,
)

from docutranslate import __version__
from docutranslate.core.schemas import TranslatePayload
from docutranslate.exporter.md.types import ConvertEngineType
from docutranslate.global_values.conditional_import import DOCLING_EXIST
from docutranslate.logger import global_logger
# Shared server layer imports
from docutranslate.server import (
    TranslationService,
    get_translation_service,
    MEDIA_TYPES,
)
from docutranslate.translator import default_params
from docutranslate.utils.resource_utils import resource_path

# MCP integration imports (optional)
try:
    import docutranslate.mcp
    from docutranslate.mcp import get_sse_app
    MCP_AVAILABLE = docutranslate.mcp.MCP_AVAILABLE
except ImportError:
    MCP_AVAILABLE = False

# --- Shared Translation Service ---
translation_service: TranslationService = get_translation_service()

# --- FastAPI application and router setup ---
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


# --- Application lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global httpx_client
    app.state.main_event_loop = asyncio.get_running_loop()
    httpx_client = httpx.AsyncClient()

    # Initialize the translation service
    translation_service.initialize(httpx_client, app.state.main_event_loop)
    translation_service.clear_all()

    global_logger.propagate = False
    global_logger.setLevel(logging.INFO)
    print("应用启动完成，多任务状态已初始化。")
    if hasattr(app.state, "port_to_use"):
        print(f"服务接口文档: http://127.0.0.1:{app.state.port_to_use}/docs")
        print(f"请用浏览器访问 http://127.0.0.1:{app.state.port_to_use}\n")
        if getattr(app.state, "with_mcp", False) and MCP_AVAILABLE:
            print(f"MCP SSE endpoint available at: http://127.0.0.1:{app.state.port_to_use}/mcp/sse")

    yield  # Application running...

    # --- Shutdown phase ---
    print("正在关闭应用，开始清理资源...")

    # Cleanup all tasks via translation service
    await translation_service.cleanup_all()

    # Close HTTP client
    await httpx_client.aclose()
    print("应用关闭，资源已彻底释放。")


app = FastAPI(
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
    title="DocuTranslate API",
    description=f"""
DocuTranslate 后端服务 API，提供文档翻译、状态查询、结果下载等功能。

**注意**: 所有任务状态都保存在服务进程的内存中，服务重启将导致所有任务信息丢失。

### 主要工作流程:
1.  **`POST /service/translate`** 或 **`POST /service/translate/file`**: 提交文件和包含`workflow_type`的翻译参数，启动一个后台任务。服务会自动生成并返回一个唯一的 `task_id`。
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
)
service_router = APIRouter(prefix="/service", tags=["Service API"])
STATIC_DIR = resource_path("static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ===================================================================
# --- MCP Integration (optional) ---
# ===================================================================

def setup_mcp_integration(
        enable: bool = False,
        host: str = "127.0.0.1",
        port: int = 8000,
) -> Optional[TranslationService]:
    """
    Setup MCP integration with shared translation service.

    Args:
        enable: Whether to enable MCP SSE endpoint
        host: Host for MCP
        port: Port for MCP

    Returns:
        TranslationService instance if MCP is enabled, None otherwise
    """
    if not enable:
        return None

    if not MCP_AVAILABLE:
        print("\n" + "=" * 60)
        print("WARNING: MCP dependencies not installed.")
        print("To use --with-mcp, please install MCP dependencies:")
        print("  pip install docutranslate[mcp]")
        print("=" * 60 + "\n")
        return None

    try:
        print("Setting up MCP integration...")

        # Mount MCP at /mcp path - pass the shared translation service
        # and the actual host/port that the web server is running on
        mcp_app = get_sse_app(
            translation_service=translation_service,
            host=host,
            port=port,
        )
        app.mount("/mcp", mcp_app, name="mcp")

        return translation_service
    except Exception as e:
        print(f"Failed to setup MCP integration: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_mcp_translation_service() -> Optional[TranslationService]:
    """Get the shared translation service (if available)."""
    return translation_service


# ===================================================================
# --- Pydantic Models for Service API ---
# ===================================================================


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
            "presentation.pptx",
        ],
    )
    file_content: str = Field(
        ..., description="Base64编码的文件内容。", examples=["JVBERi0xLjcKJeLjz9MKMSAwIG9iago8PC/..."]
    )
    payload: TranslatePayload = Field(
        ..., description="包含工作流类型和相应参数的载荷。"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "file_name": "auto_detect_doc.pdf",
                    "file_content": "JVBERi0xLjcKJeLjz9MKMSAwIG9iago8PC/...",
                    "payload": {
                        "workflow_type": "auto",
                        "base_url": "https://api.openai.com/v1",
                        "api_key": "sk-your-api-key-here",
                        "model_id": "gpt-4o",
                        "to_lang": "中文",
                    },
                },
                {
                    "file_name": "local_test.pdf",
                    "file_content": "JVBERi0xLjcKJeLjz9MKMSAwIG9iago8PC/...",
                    "payload": {
                        "workflow_type": "markdown_based",
                        "skip_translate": True,
                        "to_lang": "中文",
                        "convert_engine": "mineru_deploy",
                        "mineru_deploy_base_url": "http://127.0.0.1:8000",
                        "mineru_deploy_backend": "pipeline",
                        "mineru_deploy_formula_enable": True,
                        "mineru_deploy_start_page_id": 0,
                        "mineru_deploy_end_page_id": 5,
                    },
                },
            ]
        }
    )


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
                    "force_json",
                    "rpm",
                    "tpm",
                    "provider",
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
                    "segment_mode",
                    "timeout",
                    "retry",
                    "system_proxy_enable",
                    "force_json",
                    "rpm",
                    "tpm",
                    "provider",  # Added provider
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
                    "force_json",
                    "rpm",
                    "tpm",
                    "provider",  # Added provider
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
                    "force_json",
                    "rpm",
                    "tpm",
                    "provider",  # Added provider
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
                    "force_json",
                    "rpm",
                    "tpm",
                    "provider",  # Added provider
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
                    "force_json",
                    "rpm",
                    "tpm",
                    "provider",  # Added provider
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
                    "force_json",
                    "rpm",
                    "tpm",
                    "provider",  # Added provider
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
                    "force_json",
                    "rpm",
                    "tpm",
                    "provider",
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
                    "force_json",
                    "rpm",
                    "tpm",
                    "provider",  # Added provider
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

        # --- PPTX WORKFLOW LOGIC START ---
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
                    "provider",  # Added provider
                },
                exclude_none=True,
            )
            translator_args["glossary_generate_enable"] = (
                payload.glossary_generate_enable
            )
            translator_args["glossary_agent_config"] = build_glossary_agent_config()
            translator_config = PPTXTranslatorConfig(**translator_args)

            html_exporter_config = PPTX2HTMLExporterConfig(cdn=True)
            workflow_config = PPTXWorkflowConfig(
                translator_config=translator_config,
                html_exporter_config=html_exporter_config,
                logger=task_logger,
            )
            workflow = PPTXWorkflow(config=workflow_config)
        # --- PPTX WORKFLOW LOGIC END ---

        else:
            raise TypeError(f"工作流类型 '{payload.workflow_type}' 的处理逻辑未实现。")

        # 3. 读取文件内容并执行翻译
        # --- 修改点: 使用 safe stem (从 task_state 中获取) 而不是重新从 original_filename 解析 ---
        # 这样确保了 workflow 内部的文件名也是截断过的，避免内部处理时路径过长
        file_stem = task_state["original_filename_stem"]
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
        if isinstance(workflow, PPTXExportable):
            export_map["pptx"] = (
                workflow.export_to_pptx,
                f"{filename_stem}_translated.pptx",
                False,
            )

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
            elif isinstance(workflow, PPTXWorkflow):
                html_config = PPTX2HTMLExporterConfig(cdn=is_cdn_available)
            export_map["html"] = (
                lambda: workflow.export_to_html(html_config),
                f"{filename_stem}_translated.html",
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
    # --- 新增: Auto 工作流路由逻辑 ---
    if payload.workflow_type == "auto":
        detected_type = get_workflow_type_from_filename(original_filename)
        print(f"[{task_id}] 自动识别工作流: {original_filename} -> {detected_type}")

        # 将参数转换为目标具体工作流类型所需的字典
        payload_data = payload.model_dump()
        payload_data["workflow_type"] = detected_type

        # 针对特定格式的默认策略
        if detected_type == "json" and not payload_data.get("json_paths"):
            payload_data["json_paths"] = ["$..*"]  # 默认翻译所有内容

        if detected_type == "markdown_based" and not payload_data.get("convert_engine"):
            if Path(original_filename).suffix.lower() == ".pdf":
                payload_data["convert_engine"] = "mineru" if not DOCLING_EXIST else "docling"
            else:
                payload_data["convert_engine"] = "identity"

        # 重新校验为具体的 Payload 类型
        try:
            payload = TypeAdapter(TranslatePayload).validate_python(payload_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"自动转换工作流参数失败: {e}")
    # -----------------------------

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

    raw_stem = Path(original_filename).stem
    safe_stem = raw_stem[:50] if len(raw_stem) > 50 else raw_stem

    task_state.update(
        {
            "is_processing": True,
            "status_message": "任务初始化中...",
            "error_flag": False,
            "download_ready": False,
            "workflow_instance": None,
            "original_filename_stem": safe_stem,  # 存入安全的stem
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

- **工作流选择**: `payload.workflow_type` 决定任务类型（如 `markdown_based`, `txt`, `json`, `xlsx`, `docx`, `srt`, `epub`, `html`, `ass`, `pptx`, `auto`）。
- **Auto 模式**: 当设置为 `auto` 时，后端将根据 `file_name` 的扩展名自动选择最合适的工作流。
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
        response_data = await translation_service.start_translation(
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
    "/translate/file",
    summary="提交翻译任务 (文件上传)",
    description="""
通过 `multipart/form-data` 方式上传文件并启动翻译任务。

此接口适用于直接上传二进制文件（如 PDF, Docx 等），无需先进行 Base64 编码。
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
        422: {"description": "请求参数验证失败，例如 JSON 格式错误。"},
        429: {
            "description": "服务器已有一个同ID的任务在处理中（理论上不应发生，因为ID是新生成的）。"
        },
        500: {"description": "启动后台任务时发生未知错误。"},
    },
)
async def service_translate_file(
        file: UploadFile = File(..., description="要翻译的文件"),
        payload: Json[TranslatePayload] = Form(
            ..., description="包含工作流参数的JSON字符串 (详见接口文档说明)。"
        ),
):
    task_id = uuid.uuid4().hex[:8]

    try:
        file_contents = await file.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取上传文件失败: {e}")

    try:
        response_data = await translation_service.start_translation(
            task_id=task_id,
            payload=payload,
            file_contents=file_contents,
            original_filename=file.filename or "uploaded_file",
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
    description="根据任务ID取消一个正在进行中的翻译任务。如果任务已经完成、失败或已经被取消，则会返回错误。",
    responses={
        200: {"description": "成功取消任务。"},
        404: {"description": "任务ID不存在。"},
        400: {"description": "任务已结束，无法取消。"},
    },
)
async def service_cancel_translate(
        task_id: str = FastApiPath(..., description="要取消的任务ID", examples=["a1b2c3d4"])
):
    return translation_service.cancel_task(task_id)


@service_router.post(
    "/release/{task_id}",
    summary="释放任务资源",
    description="根据任务ID释放其在服务器上占用的所有资源，包括状态、日志和缓存的翻译结果文件。如果任务正在进行，会先尝试取消该任务。此操作不可逆。",
    responses={
        200: {"description": "成功释放任务资源。"},
        404: {"description": "任务ID不存在。"},
    },
)
async def service_release_task(
        task_id: str = FastApiPath(..., description="要释放资源的任务ID", examples=["a1b2c3d4"])
):
    result = await translation_service.release_task(task_id)
    if not result["released"]:
        return JSONResponse(
            status_code=404,
            content=result,
        )
    return JSONResponse(content=result)


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
                                "progress_percent": 45,
                                "original_filename_stem": "annual_report",
                                "original_filename": "annual_report.pdf",
                                "task_start_time": 1678889400.0,
                                "task_end_time": 0,
                                "downloads": {},
                                "attachment": {},
                            },
                        },
                        "completed": {
                            "summary": "已完成",
                            "value": {
                                "task_id": "b2865b93",
                                "is_processing": False,
                                "status_message": "翻译成功！用时 123.45 秒。",
                                "error_flag": False,
                                "download_ready": True,
                                "progress_percent": 100,
                                "original_filename_stem": "my_paper",
                                "original_filename": "my_paper.pdf",
                                "task_start_time": 1678889400.123,
                                "task_end_time": 1678889523.573,
                                "downloads": {
                                    "html": "/service/download/b2865b93/html",
                                    "markdown": "/service/download/b2865b93/markdown",
                                },
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
    task_state = translation_service.get_task_state(task_id)
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
            "progress_percent": task_state.get("progress_percent", 0),
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
    description="以流式方式获取任务的增量日志。客户端每次调用此接口，都会返回自上次调用以来产生的新日志行。",
    responses={
        200: {"description": "成功返回增量日志。"},
        404: {"description": "任务ID不存在。"},
    },
)
async def service_get_logs(
        task_id: str = FastApiPath(..., description="要获取日志的任务ID", examples=["a1b2c3d4"])
):
    new_logs = await translation_service.get_new_logs(task_id)
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
    "pptx",
]


@service_router.get(
    "/download/{task_id}/{file_type}",
    summary="下载翻译结果文件",
    responses={
        200: {
            "description": "成功返回文件流。文件名通过 Content-Disposition 头指定。",
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
            examples=["html", "json", "csv", "docx", "srt", "epub", "ass", "pptx"],
        ),
):
    file_info = translation_service.get_downloadable_file_path(task_id, file_type)
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
    attachment_info = translation_service.get_attachment_file_path(task_id, identifier)
    if not attachment_info or not os.path.exists(attachment_info.get("path")):
        raise HTTPException(
            status_code=404,
            detail=f"任务 '{task_id}' 不存在标识符为 '{identifier}' 的附件，或文件已丢失。",
        )

    file_path = attachment_info["path"]
    filename = attachment_info["filename"]
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
            examples=["html", "json", "csv", "docx", "srt", "epub", "ass", "pptx"],
        ),
):
    file_info = translation_service.get_downloadable_file_path(task_id, file_type)
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
# --- Application endpoints ---
# ===================================================================


@service_router.get(
    "/engin-list",
    summary="获取可用的转换引擎",
    description="返回当前服务支持的文档转换引擎列表，包括 MinerU Cloud、MinerU Local 和 Docling（如果已安装）。",
    tags=["Application"],
    responses={
        200: {
            "description": "成功返回可用的转换引擎列表。",
            "content": {
                "application/json": {
                    "example": ["mineru", "mineru_deploy", "docling"]
                }
            }
        }
    },
)
async def service_get_engin_list():
    engin_list = ["mineru", "mineru_deploy"]
    if DOCLING_EXIST:
        engin_list.append("docling")
    return JSONResponse(content=engin_list)


@service_router.get(
    "/task-list",
    summary="获取任务列表",
    description="返回当前所有正在处理或已完成的翻译任务ID列表。",
    tags=["Application"],
    responses={
        200: {
            "description": "成功返回任务ID列表。",
            "content": {
                "application/json": {
                    "example": ["a1b2c3d4", "e5f6g7h8"]
                }
            }
        }
    },
)
async def service_get_task_list():
    return JSONResponse(content=translation_service.list_tasks())


@service_router.get(
    "/default-params",
    summary="获取默认参数",
    description="返回服务使用的默认参数，包括并发数、分块大小、温度、超时等配置。",
    tags=["Application"],
    responses={
        200: {
            "description": "成功返回默认参数。",
            "content": {
                "application/json": {
                    "example": {
                        "chunk_size": 2000,
                        "concurrent": 10,
                        "temperature": 0.3,
                        "timeout": 60,
                        "retry": 3,
                        "thinking": "default"
                    }
                }
            }
        }
    },
)
def service_get_default_params():
    return JSONResponse(content=default_params)


@service_router.get(
    "/meta",
    summary="获取应用信息",
    description="返回当前服务的版本号等元信息。",
    tags=["Application"],
    responses={
        200: {
            "description": "成功返回应用信息。",
            "content": {
                "application/json": {
                    "example": {"version": "1.0.0"}
                }
            }
        }
    },
)
async def service_get_app_version():
    return JSONResponse(content={"version": __version__})


@service_router.post(
    "/flat-translate",
    summary="translate(sync)",
    description="""
上传文件并直接等待翻译完成，无需轮询状态。
所有参数均已扁平化展开，直接通过 Form 表单提交。
""",
    response_model=None,
    responses={
        200: {"description": "翻译成功，返回翻译后的文件内容。"},
        500: {"description": "翻译过程中发生错误。"},
    },
)
async def service_flat_translate(
        request: Request,
        file: UploadFile = File(..., description="要翻译的文件"),
        model_id: str = Form("", description="模型ID (例如: gpt-4o, glm-4-air)，当 skip_translate=False 时必填"),
        base_url: Optional[str] = Form("",
                                       description="LLM API 基础 URL (如不填则依赖环境变量或默认值，当 skip_translate=False 时必填)"),
        api_key: str = Form("xx", description="API Key (默认xx)"),
        to_lang: str = Form("中文", description="目标翻译语言"),
        workflow_type: str = Form("auto",
                                  description="工作流类型: auto, markdown_based, txt, json, xlsx, docx, srt, epub, html, ass, pptx"),
        skip_translate: bool = Form(False, description="是否跳过翻译仅进行格式解析"),
        concurrent: int = Form(default_params["concurrent"], description="并发请求数"),
        chunk_size: int = Form(default_params["chunk_size"], description="文本分块大小"),
        temperature: float = Form(default_params["temperature"], description="温度 (0-1)"),
        timeout: int = Form(default_params["timeout"], description="单次请求超时时间(秒)"),
        retry: int = Form(default_params["retry"], description="失败重试次数"),
        thinking: str = Form("default", description="思考模式: default, enable, disable"),
        custom_prompt: Optional[str] = Form("", description="自定义系统提示词"),
        system_proxy_enable: bool = Form(default_params["system_proxy_enable"], description="是否启用系统代理"),
        force_json: bool = Form(False, description="强制 LLM 输出 JSON 格式"),
        rpm: Optional[int] = Form(None, description="RPM (每分钟请求数) 限制"),
        tpm: Optional[int] = Form(None, description="TPM (每分钟 Token 数) 限制"),
        provider: Optional[str] = Form("", description="LLM 提供商标识 (用于特定平台的特殊处理)"),
        insert_mode: str = Form("replace", description="插入模式: replace(替换), append(追加), prepend(前置)"),
        separator: str = Form("\n", description="追加/前置时的分隔符"),
        segment_mode: str = Form("line", description="[Txt专用] 分段模式: line(按行), paragraph(按段), none(全文)"),
        translate_regions: Optional[List[str]] = Form(None, description="[Xlsx专用] 翻译区域列表, 如 'Sheet1!A1:B10'"),
        convert_engine: Optional[ConvertEngineType] = Form("mineru",
                                                           description="[PDF/MD] 解析引擎: mineru, docling, identity,mineru_deploy"),
        mineru_token: Optional[str] = Form("", description="[MinerU Cloud] API Token"),
        model_version: str = Form("vlm", description="[MinerU Cloud] 模型版本: vlm, pipeline"),
        formula_ocr: bool = Form(True, description="[PDF] 是否启用公式识别"),
        code_ocr: bool = Form(True, description="[Docling] 是否启用代码块识别"),
        mineru_deploy_base_url: str = Form("http://127.0.0.1:8000", description="[MinerU Local] 服务地址"),
        mineru_deploy_backend: str = Form("hybrid-auto-engine",
                                          description="[MinerU Local] 后端类型: pipeline, vlm-auto-engine, vlm-http-client, hybrid-auto-engine, hybrid-http-client"),
        mineru_deploy_parse_method: str = Form("auto", description="[MinerU Local] 解析方法: auto, txt, ocr"),
        mineru_deploy_formula_enable: bool = Form(True, description="[MinerU Local] 是否启用公式"),
        mineru_deploy_table_enable: bool = Form(True, description="[MinerU Local] 是否启用表格"),
        mineru_deploy_start_page_id: int = Form(0, description="[MinerU Local] 起始页码"),
        mineru_deploy_end_page_id: int = Form(99999, description="[MinerU Local] 结束页码"),
        mineru_deploy_lang_list: Optional[List[str]] = Form(None, description="[MinerU Local] 语言列表"),
        mineru_deploy_server_url: Optional[str] = Form("",
                                                       description="[MinerU Local] Server URL (backend='vlm-http-client'时使用)"),
        json_paths: Optional[List[str]] = Form(None, description="[Json专用] JsonPath 表达式列表, 如 '$.name'"),
        glossary_generate_enable: bool = Form(False, description="是否开启术语表自动生成"),
        glossary_dict_json: Optional[str] = Form("", description="术语表字典 JSON 字符串, 格式: {'原文':'译文'}"),
        glossary_agent_config_json: Optional[str] = Form("",
                                                         description="术语表 Agent 配置 JSON 字符串 (包含 base_url, model_id 等)")
):
    task_id = uuid.uuid4().hex[:8]

    try:
        file_contents = await file.read()
        original_filename = file.filename or "uploaded_file"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件读取失败: {e}")

    if workflow_type == "auto":
        ext = Path(original_filename).suffix.lower().lstrip(".")
        if ext in ["md", "pdf"]:
            workflow_type = "markdown_based"
        elif ext == "txt":
            workflow_type = "txt"
        elif ext == "json":
            workflow_type = "json"
        elif ext == "xlsx":
            workflow_type = "xlsx"
        elif ext == "docx":
            workflow_type = "docx"
        elif ext == "srt":
            workflow_type = "srt"
        elif ext == "epub":
            workflow_type = "epub"
        elif ext in ["html", "htm"]:
            workflow_type = "html"
        elif ext == "ass":
            workflow_type = "ass"
        elif ext == "pptx":
            workflow_type = "pptx"
        else:
            workflow_type = "txt"

    parsed_glossary_dict = None
    if glossary_dict_json and glossary_dict_json.strip():
        try:
            parsed_glossary_dict = json.loads(glossary_dict_json)
            if not isinstance(parsed_glossary_dict, dict):
                raise ValueError("必须是字典")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"glossary_dict_json 解析失败: {e}")

    parsed_glossary_agent = None
    if glossary_agent_config_json and glossary_agent_config_json.strip():
        try:
            parsed_glossary_agent = json.loads(glossary_agent_config_json)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"glossary_agent_config_json 解析失败: {e}")

    payload_dict = {
        "workflow_type": workflow_type,
        "base_url": base_url,
        "api_key": api_key,
        "model_id": model_id,
        "to_lang": to_lang,
        "skip_translate": skip_translate,
        "concurrent": concurrent,
        "chunk_size": chunk_size,
        "temperature": temperature,
        "timeout": timeout,
        "retry": retry,
        "thinking": thinking,
        "custom_prompt": custom_prompt,
        "system_proxy_enable": system_proxy_enable,
        "force_json": force_json,
        "rpm": rpm,
        "tpm": tpm,
        "provider": provider,
        "insert_mode": insert_mode,
        "separator": separator,
        "segment_mode": segment_mode,
        "translate_regions": translate_regions,
        "convert_engine": convert_engine,
        "mineru_token": mineru_token,
        "model_version": model_version,
        "formula_ocr": formula_ocr,
        "code_ocr": code_ocr,
        "mineru_deploy_base_url": mineru_deploy_base_url,
        "mineru_deploy_backend": mineru_deploy_backend,
        "mineru_deploy_parse_method": mineru_deploy_parse_method,
        "mineru_deploy_formula_enable": mineru_deploy_formula_enable,
        "mineru_deploy_table_enable": mineru_deploy_table_enable,
        "mineru_deploy_start_page_id": mineru_deploy_start_page_id,
        "mineru_deploy_end_page_id": mineru_deploy_end_page_id,
        "mineru_deploy_lang_list": mineru_deploy_lang_list,
        "mineru_deploy_server_url": mineru_deploy_server_url,
        "json_paths": json_paths,
        "glossary_generate_enable": glossary_generate_enable,
        "glossary_dict": parsed_glossary_dict,
        "glossary_agent_config": parsed_glossary_agent
    }

    payload_dict = {
        k: v for k, v in payload_dict.items()
        if v is not None and (not isinstance(v, str) or v != "")
    }

    if workflow_type == "json" and not payload_dict.get("json_paths"):
        payload_dict["json_paths"] = ["$..*"]

    if workflow_type == "markdown_based" and "convert_engine" not in payload_dict:
        ext = Path(original_filename).suffix.lower()
        if ext == ".pdf":
            payload_dict["convert_engine"] = "mineru" if not DOCLING_EXIST else "docling"
        else:
            payload_dict["convert_engine"] = "identity"

    try:
        payload_obj = TypeAdapter(TranslatePayload).validate_python(payload_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"参数配置校验失败: {str(e)}")

    try:
        await translation_service.start_translation(
            task_id=task_id,
            payload=payload_obj,
            file_contents=file_contents,
            original_filename=original_filename
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内部翻译错误: {str(e)}")

    task_state = translation_service.get_task_state(task_id)

    if not task_state:
        raise HTTPException(status_code=500, detail="任务状态丢失")

    if task_state.get("error_flag"):
        error_msg = task_state.get("status_message", "未知错误")
        temp_dir = task_state.get("temp_dir")
        if temp_dir and os.path.isdir(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)
        await translation_service.release_task(task_id)
        raise HTTPException(status_code=500, detail=f"翻译任务失败: {error_msg}")

    task = task_state.get("current_task_ref")
    if task:
        await task

    task_state = translation_service.get_task_state(task_id)

    if task_state.get("error_flag"):
        error_msg = task_state.get("status_message", "未知错误")
        await translation_service.release_task(task_id)
        raise HTTPException(status_code=500, detail=f"翻译任务失败: {error_msg}")

    base_url_str = str(request.base_url).rstrip("/")
    downloads = {}
    if task_state.get("download_ready") and task_state.get("downloadable_files"):
        for file_type, info in task_state["downloadable_files"].items():
            downloads[file_type] = f"{base_url_str}/service/download/{task_id}/{file_type}"

    attachments = {}
    if task_state.get("download_ready") and task_state.get("attachment_files"):
        for identifier in task_state["attachment_files"]:
            attachments[identifier] = f"{base_url_str}/service/attachment/{task_id}/{identifier}"

    duration = task_state.get("task_end_time", 0) - task_state.get("task_start_time", 0)

    return JSONResponse(content={
        "status": "success",
        "task_id": task_id,
        "message": task_state.get("status_message"),
        "duration": round(duration, 2),
        "downloads": downloads,
        "attachments": attachments
    })


# ===================================================================
# --- Static pages and docs ---
# ===================================================================


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


app.include_router(service_router)


# ===================================================================
# --- Run function ---
# ===================================================================


def find_free_port(start_port):
    port = start_port
    while True:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
            port += 1


def run_app(host=None, port: int | None = None, enable_CORS=False,
            allow_origin_regex=r"^(https?://.*|null|file://.*)$",
            with_mcp: bool = False):
    initial_port = port or int(os.environ.get("DOCUTRANSLATE_PORT", 8010))
    try:
        port_to_use = find_free_port(initial_port)
        if port_to_use != initial_port:
            print(f"端口 {initial_port} 被占用，将使用端口 {port_to_use} 代替")
        print(f"正在启动 DocuTranslate WebUI 版本号：{__version__}")
        app.state.port_to_use = port_to_use
        app.state.with_mcp = with_mcp
        if enable_CORS:
            print(f"已开启跨域，allow_origin_regex：{allow_origin_regex}")
            app.add_middleware(
                CORSMiddleware,
                allow_origin_regex=allow_origin_regex,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        if with_mcp:
            # Use the same host and port as the web backend
            # If host is None, uvicorn defaults to 127.0.0.1
            mcp_host = host if host is not None else "127.0.0.1"
            setup_mcp_integration(
                enable=True,
                host=mcp_host,
                port=port_to_use,
            )

        uvicorn.run(app, host=host, port=port_to_use, workers=1)
    except Exception as e:
        print(f"启动失败: {e}")


if __name__ == "__main__":
    run_app()
