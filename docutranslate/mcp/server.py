# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
"""
DocuTranslate MCP Server

Model Context Protocol server for DocuTranslate, providing document translation
capabilities to AI assistants.

This implementation uses the shared TranslationService from the server layer
to ensure consistent task management between the Web backend and MCP server.
"""

import asyncio
import base64
import os
from pathlib import Path
from typing import Any, Dict, Optional, List


def _load_dotenv():
    """Load environment variables from .env file if python-dotenv is available"""
    try:
        from dotenv import load_dotenv
        # Try to load .env from current directory first, then parent directories
        env_path = None
        current_dir = Path.cwd()
        for dir_path in [current_dir] + list(current_dir.parents):
            candidate = dir_path / ".env"
            if candidate.exists():
                env_path = candidate
                break
        if env_path:
            load_dotenv(env_path)
    except ImportError:
        # python-dotenv not installed, silently skip
        pass


# Load .env file on module import
_load_dotenv()

# Shared server layer imports
from docutranslate.server import (
    TranslationService,
    get_translation_service,
)

from docutranslate import __version__
from docutranslate.core.schemas import TranslatePayload
from pydantic import TypeAdapter

# MCP Server configuration
SERVER_NAME = "docutranslate"
SERVER_VERSION = __version__


def _format_json(data: Any) -> str:
    """Format JSON for display"""
    import json
    return json.dumps(data, ensure_ascii=False, indent=2)


def _get_formats_info() -> Dict[str, Any]:
    """Get information about supported formats"""
    return {
        "input_formats": [
            "pdf", "docx", "doc", "xlsx", "xls", "csv", "md", "markdown",
            "txt", "json", "epub", "srt", "ass", "pptx", "ppt", "html", "htm",
            "png", "jpg"
        ],
        "output_formats_by_workflow": {
            "markdown_based": ["html", "markdown", "markdown_zip", "docx"],
            "txt": ["txt"],
            "json": ["json"],
            "xlsx": ["xlsx", "csv", "html"],
            "docx": ["docx", "html"],
            "srt": ["srt", "html"],
            "epub": ["epub", "html"],
            "html": ["html"],
            "ass": ["ass", "html"],
            "pptx": ["pptx", "html"],
        },
    }


def _task_state_to_dict(task_id: str, task_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Convert task state to a serializable dict"""
    if not task_state:
        return {"task_id": task_id, "status": "not_found", "error": "Task not found"}

    status = "idle"
    if task_state.get("is_processing"):
        status = "running"
    elif task_state.get("error_flag"):
        status = "error"
    elif task_state.get("download_ready"):
        status = "completed"

    return {
        "task_id": task_id,
        "status": status,
        "status_message": task_state.get("status_message", ""),
        "progress_percent": task_state.get("progress_percent", 0),
        "download_ready": task_state.get("download_ready", False),
        "downloadable_files": task_state.get("downloadable_files", {}),
        "attachment_files": task_state.get("attachment_files", {}),
    }


# ===========================================================================
# Conditional MCP functionality - only available if mcp dependencies are installed
# ===========================================================================

try:
    from mcp.server.fastmcp import FastMCP, Context

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    FastMCP = None
    Context = None

if MCP_AVAILABLE and FastMCP is not None and Context is not None:

    def create_mcp_server(
            host: str = "127.0.0.1",
            port: int = 8000,
            translation_service: Optional[TranslationService] = None,
    ):
        """Create and configure the FastMCP server

        Args:
            host: Host address for SSE/streamable-http transport
            port: Port number for SSE/streamable-http transport
            translation_service: Optional TranslationService instance (uses global if not provided)

        Returns:
            Configured FastMCP server
        """
        # Use provided translation service or get the global one
        service = translation_service or get_translation_service()

        # Client configuration - load from environment variables first
        client_config = {
            "api_key": os.environ.get("DOCUTRANSLATE_API_KEY", ""),
            "base_url": os.environ.get("DOCUTRANSLATE_BASE_URL", ""),
            "model_id": os.environ.get("DOCUTRANSLATE_MODEL_ID", ""),
            "to_lang": os.environ.get("DOCUTRANSLATE_TO_LANG", "中文"),
            "concurrent": int(os.environ.get("DOCUTRANSLATE_CONCURRENT", "10")),
            "convert_engine": os.environ.get("DOCUTRANSLATE_CONVERT_ENGINE", ""),
            "mineru_token": os.environ.get("DOCUTRANSLATE_MINERU_TOKEN", ""),
        }

        # Create FastMCP instance
        mcp = FastMCP(
            name=SERVER_NAME,
            instructions="DocuTranslate MCP server for document translation. "
                         "Step 1: Use submit_task to start a translation task, "
                         "Step 2: Use get_task_status to check progress - when completed, "
                         "it will show all available formats and attachments, "
                         "Step 3: Use download_file to save translations or attachments (set auto_release=True to automatically clean up resources after download), "
                         "Step 4 (optional): Use release_task to manually clean up resources when done. "
                         "The translation uses the full workflow engine from DocuTranslate.",
            host=host,
            port=port,
        )

        @mcp.tool()
        async def get_status() -> str:
            """Get current server status and configuration information."""
            # Ensure service is properly initialized with event loop
            if service.main_event_loop is None:
                service.main_event_loop = asyncio.get_running_loop()
            is_configured = bool(
                client_config.get("api_key") and client_config.get("base_url") and client_config.get("model_id"))
            status_info = {
                "server": "docutranslate",
                "version": __version__,
                "status": "ready",
                "client_configured": is_configured,
                "active_tasks": len(service.tasks_state),
            }
            return f"Server Status:\n{_format_json(status_info)}"

        @mcp.tool()
        async def configure_client(
                api_key: Optional[str] = None,
                base_url: Optional[str] = None,
                model_id: Optional[str] = None,
                to_lang: Optional[str] = None,
                concurrent: Optional[int] = None,
                convert_engine: Optional[str] = None,
                mineru_token: Optional[str] = None,
        ) -> str:
            """Configure the DocuTranslate client LLM settings.
            If already configured via environment variables, this tool can override them.

            Args:
                api_key: AI platform API key
                base_url: AI platform base URL
                model_id: Model ID to use
                to_lang: Target language (default: 中文)
                concurrent: Number of concurrent requests (default: 10)
                convert_engine: PDF conversion engine
                mineru_token: MinerU API token
            """
            if api_key is not None:
                client_config["api_key"] = api_key
            if base_url is not None:
                client_config["base_url"] = base_url
            if model_id is not None:
                client_config["model_id"] = model_id
            if to_lang is not None:
                client_config["to_lang"] = to_lang
            if concurrent is not None:
                client_config["concurrent"] = concurrent
            if convert_engine is not None:
                client_config["convert_engine"] = convert_engine
            if mineru_token is not None:
                client_config["mineru_token"] = mineru_token

            # Check if we have the required config
            has_required = bool(
                client_config.get("api_key") and client_config.get("base_url") and client_config.get("model_id"))

            if has_required:
                return (
                    "Client configuration updated successfully.\n"
                    "You can now use submit_task without providing api_key, base_url, and model_id every time."
                )
            else:
                missing = []
                if not client_config.get("api_key"):
                    missing.append("api_key")
                if not client_config.get("base_url"):
                    missing.append("base_url")
                if not client_config.get("model_id"):
                    missing.append("model_id")
                return (
                    f"Configuration updated, but missing required fields: {', '.join(missing)}\n"
                    "Please provide all required fields to use the translation service."
                )

        @mcp.tool()
        async def get_client_config() -> str:
            """Get current client configuration (without sensitive data like API keys)."""
            # Mask sensitive data
            masked_config = client_config.copy()
            if masked_config.get("api_key"):
                key = masked_config["api_key"]
                masked_config["api_key"] = key[:4] + "..." + key[-4:] if len(key) > 8 else "****"
            if masked_config.get("mineru_token"):
                token = masked_config["mineru_token"]
                masked_config["mineru_token"] = token[:4] + "..." + token[-4:] if len(token) > 8 else "****"
            return f"Current Client Configuration:\n{_format_json(masked_config)}"

        @mcp.tool()
        async def submit_task(
                file_path: str,
                api_key: str = "",
                base_url: str = "",
                model_id: str = "",
                to_lang: Optional[str] = None,
                workflow_type: str = "auto",
                skip_translate: bool = False,
                glossary_generate_enable: bool = False,
                glossary_dict_json: str = "",
                glossary_agent_config_json: str = "",
                extra_body_json: str = "",
                # LLM 进阶参数
                chunk_size: Optional[int] = None,
                concurrent: Optional[int] = None,
                temperature: Optional[float] = None,
                top_p: Optional[float] = None,
                timeout: Optional[int] = None,
                thinking: Optional[str] = None,
                retry: Optional[int] = None,
                system_proxy_enable: Optional[bool] = None,
                custom_prompt: str = "",
                force_json: Optional[bool] = None,
                rpm: Optional[int] = None,
                tpm: Optional[int] = None,
                provider: Optional[str] = None,
                # Markdown 工作流参数
                convert_engine: Optional[str] = None,
                md2docx_engine: Optional[str] = None,
                mineru_token: str = "",
                model_version: Optional[str] = None,
                formula_ocr: Optional[bool] = None,
                code_ocr: Optional[bool] = None,
                mineru_language: Optional[str] = None,
                mineru_deploy_base_url: Optional[str] = None,
                mineru_deploy_backend: Optional[str] = None,
                mineru_deploy_parse_method: Optional[str] = None,
                mineru_deploy_table_enable: Optional[bool] = None,
                mineru_deploy_formula_enable: Optional[bool] = None,
                mineru_deploy_start_page_id: Optional[int] = None,
                mineru_deploy_end_page_id: Optional[int] = None,
                mineru_deploy_lang_list: Optional[List[str]] = None,
                mineru_deploy_server_url: str = "",
                # 其他工作流参数
                insert_mode: Optional[str] = None,
                separator: Optional[str] = None,
                segment_mode: Optional[str] = None,
                translate_regions: Optional[List[str]] = None,
                json_paths: Optional[List[str]] = None,
        ) -> str:
            """Submit a translation task (asynchronous, returns immediately).
            Use get_task_status to check progress. When complete, it will show
            all available formats and attachments. Use download_file to save files.
            Supports PDF, DOCX, XLSX, MD, TXT, JSON, EPUB, SRT, ASS, PPTX, HTML formats.

            Args:
                file_path: Path to the file to translate, or a URL starting with http:// or https://
                api_key: AI platform API key
                base_url: AI platform base URL
                model_id: Model ID to use
                to_lang: Target language (default: 中文)
                workflow_type: Workflow type (auto-detected if not specified)
                skip_translate: Skip translation, only parse the document
                glossary_generate_enable: Enable automatic glossary generation
                glossary_dict_json: Glossary dictionary JSON string, format: {"原文":"译文"}
                glossary_agent_config_json: Glossary agent config JSON string (contains base_url, model_id, etc.)
                extra_body_json: Extra request body parameters JSON string, will be merged into API request
                chunk_size: Text chunk size for translation
                concurrent: Number of concurrent requests
                temperature: LLM temperature parameter
                timeout: Request timeout in seconds
                thinking: Thinking mode (default, enable, disable)
                retry: Number of retries for failed chunks
                system_proxy_enable: Enable system proxy
                custom_prompt: Custom system prompt
                force_json: Force JSON output
                rpm: RPM limit (Requests Per Minute)
                tpm: TPM limit (Tokens Per Minute)
                provider: LLM provider identifier
                convert_engine: PDF conversion engine (identity, mineru, docling, mineru_deploy)
                md2docx_engine: Markdown to docx engine (python, pandoc, auto)
                mineru_token: MinerU Cloud API Token
                model_version: MinerU Cloud model version (pipeline, vlm)
                formula_ocr: Enable formula OCR
                code_ocr: Enable code block OCR
                mineru_language: MinerU Cloud language option (ch, ch_server, en, japan, korean, chinese_cht, ta, te, ka, el, th, latin, arabic, cyrillic, east_slavic, devanagari)
                mineru_deploy_base_url: MinerU local deployment base URL
                mineru_deploy_backend: MinerU local backend type
                mineru_deploy_parse_method: MinerU parse method (auto, txt, ocr)
                mineru_deploy_table_enable: Enable table parsing
                mineru_deploy_formula_enable: Enable formula parsing
                mineru_deploy_start_page_id: Start page ID
                mineru_deploy_end_page_id: End page ID
                mineru_deploy_lang_list: Language list
                mineru_deploy_server_url: MinerU Server URL
                insert_mode: Insert mode (replace, append, prepend)
                separator: Separator for append/prepend
                segment_mode: [Txt only] Segment mode (line, paragraph, none)
                translate_regions: [Xlsx only] Translation regions list
                json_paths: [Json only] JsonPath expressions list
            """
            # Ensure service is properly initialized with event loop and httpx_client
            if service.main_event_loop is None:
                service.main_event_loop = asyncio.get_running_loop()
            if service.httpx_client is None:
                import httpx
                service.httpx_client = httpx.AsyncClient()

            # Check if file_path is a URL
            is_url = file_path.startswith("http://") or file_path.startswith("https://")
            original_filename = None

            if is_url:
                # Download from URL directly into memory
                try:
                    from urllib.parse import urlparse

                    # Parse URL to get filename
                    parsed_url = urlparse(file_path)
                    url_path = parsed_url.path
                    original_filename = os.path.basename(url_path)
                    if not original_filename:
                        original_filename = "downloaded_file"

                    # Download the file directly into memory
                    response = await service.httpx_client.get(file_path, timeout=300.0)
                    response.raise_for_status()
                    file_contents = response.content
                except Exception as e:
                    return f"Error downloading file from URL: {e}"
            else:
                # Local file - check if exists
                if not os.path.exists(file_path):
                    return f"Error: File not found: {file_path}"

                # Read the file
                try:
                    with open(file_path, "rb") as f:
                        file_contents = f.read()
                    original_filename = os.path.basename(file_path)
                except Exception as e:
                    return f"Error reading file: {e}"

            import json

            # Parse glossary dict if provided
            parsed_glossary_dict = None
            if glossary_dict_json and glossary_dict_json.strip():
                try:
                    parsed_glossary_dict = json.loads(glossary_dict_json)
                    if not isinstance(parsed_glossary_dict, dict):
                        return "Error: glossary_dict_json must be a dictionary"
                except Exception as e:
                    return f"Error parsing glossary_dict_json: {e}"

            # Parse glossary agent config if provided
            parsed_glossary_agent = None
            if glossary_agent_config_json and glossary_agent_config_json.strip():
                try:
                    parsed_glossary_agent = json.loads(glossary_agent_config_json)
                except Exception as e:
                    return f"Error parsing glossary_agent_config_json: {e}"

            # Parse extra_body if provided
            if extra_body_json and extra_body_json.strip():
                try:
                    parsed_extra = json.loads(extra_body_json)
                    if not isinstance(parsed_extra, dict):
                        return "Error: extra_body_json must be a JSON object"
                except Exception as e:
                    return f"Error parsing extra_body_json: {e}"

            # Build payload dict - use AutoWorkflowParams with extra=allow
            # This avoids validation errors for workflow-specific optional fields
            # Use client_config for defaults if parameters not provided
            payload_dict = {
                "workflow_type": workflow_type,
                "to_lang": to_lang or client_config["to_lang"] or "中文",
                "skip_translate": skip_translate,
                "glossary_generate_enable": glossary_generate_enable,
                "glossary_dict": parsed_glossary_dict,
                "glossary_agent_config": parsed_glossary_agent,
            }
            # Add extra_body if provided
            if extra_body_json and extra_body_json.strip():
                payload_dict["extra_body"] = extra_body_json

            # Add AI config - use parameter if provided, otherwise use client_config
            use_api_key = api_key or client_config["api_key"]
            use_base_url = base_url or client_config["base_url"]
            use_model_id = model_id or client_config["model_id"]

            if use_api_key:
                payload_dict["api_key"] = use_api_key
            if use_base_url:
                payload_dict["base_url"] = use_base_url
            if use_model_id:
                payload_dict["model_id"] = use_model_id

            # Add LLM advanced parameters if provided
            if chunk_size is not None:
                payload_dict["chunk_size"] = chunk_size
            use_concurrent = concurrent if concurrent is not None else client_config["concurrent"]
            if use_concurrent is not None:
                payload_dict["concurrent"] = use_concurrent
            if temperature is not None:
                payload_dict["temperature"] = temperature
            if top_p is not None:
                payload_dict["top_p"] = top_p
            if timeout is not None:
                payload_dict["timeout"] = timeout
            if thinking is not None:
                payload_dict["thinking"] = thinking
            if retry is not None:
                payload_dict["retry"] = retry
            if system_proxy_enable is not None:
                payload_dict["system_proxy_enable"] = system_proxy_enable
            if custom_prompt:
                payload_dict["custom_prompt"] = custom_prompt
            if force_json is not None:
                payload_dict["force_json"] = force_json
            if rpm is not None:
                payload_dict["rpm"] = rpm
            if tpm is not None:
                payload_dict["tpm"] = tpm
            if provider:
                payload_dict["provider"] = provider

            # Add Markdown workflow parameters if provided
            use_convert_engine = convert_engine or client_config["convert_engine"]
            if use_convert_engine:
                payload_dict["convert_engine"] = use_convert_engine
            if md2docx_engine:
                payload_dict["md2docx_engine"] = md2docx_engine
            use_mineru_token = mineru_token or client_config["mineru_token"]
            if use_mineru_token:
                payload_dict["mineru_token"] = use_mineru_token
            if model_version:
                payload_dict["model_version"] = model_version
            if formula_ocr is not None:
                payload_dict["formula_ocr"] = formula_ocr
            if code_ocr is not None:
                payload_dict["code_ocr"] = code_ocr
            if mineru_language:
                payload_dict["mineru_language"] = mineru_language
            if mineru_deploy_base_url:
                payload_dict["mineru_deploy_base_url"] = mineru_deploy_base_url
            if mineru_deploy_backend:
                payload_dict["mineru_deploy_backend"] = mineru_deploy_backend
            if mineru_deploy_parse_method:
                payload_dict["mineru_deploy_parse_method"] = mineru_deploy_parse_method
            if mineru_deploy_table_enable is not None:
                payload_dict["mineru_deploy_table_enable"] = mineru_deploy_table_enable
            if mineru_deploy_formula_enable is not None:
                payload_dict["mineru_deploy_formula_enable"] = mineru_deploy_formula_enable
            if mineru_deploy_start_page_id is not None:
                payload_dict["mineru_deploy_start_page_id"] = mineru_deploy_start_page_id
            if mineru_deploy_end_page_id is not None:
                payload_dict["mineru_deploy_end_page_id"] = mineru_deploy_end_page_id
            if mineru_deploy_lang_list:
                payload_dict["mineru_deploy_lang_list"] = mineru_deploy_lang_list
            if mineru_deploy_server_url:
                payload_dict["mineru_deploy_server_url"] = mineru_deploy_server_url

            # Add other workflow parameters if provided
            if insert_mode:
                payload_dict["insert_mode"] = insert_mode
            if separator:
                payload_dict["separator"] = separator
            if segment_mode:
                payload_dict["segment_mode"] = segment_mode
            if translate_regions:
                payload_dict["translate_regions"] = translate_regions
            if json_paths:
                payload_dict["json_paths"] = json_paths

            try:
                # Validate and create payload - AutoWorkflowParams allows extra fields
                payload = TypeAdapter(TranslatePayload).validate_python(payload_dict)
            except Exception as e:
                return f"Error validating parameters: {e}"

            # Create task_id and start translation
            display_file_path = file_path
            task_id = original_filename[:8] + "_" + base64.urlsafe_b64encode(os.urandom(4)).decode()[:8]

            try:
                # Store original file path for reference
                if not hasattr(service, "_mcp_output_options"):
                    service._mcp_output_options = {}
                service._mcp_output_options[task_id] = {
                    "original_file_path": display_file_path,
                }

                response = await service.start_translation(
                    task_id=task_id,
                    payload=payload,
                    file_contents=file_contents,
                    original_filename=original_filename,
                )
                return f"Translation task submitted successfully.\ntask_id: {task_id}\nInput: {display_file_path}\n\nUse get_task_status to check progress. When completed, it will show all available formats for download."
            except Exception as e:
                return f"Error starting translation: {e}"

        @mcp.tool()
        async def get_task_status(task_id: str, wait_seconds: float = 0) -> str:
            """Get status of a translation task.
            When task is completed, returns all available formats and attachments for download.
            Use download_file to save files to local.

            Args:
                task_id: The task ID from submit_task
                wait_seconds: Maximum seconds to wait for status change before returning (0 = return immediately)
            """
            task_state = service.get_task_state(task_id)

            if wait_seconds > 0 and task_state:
                # Wait for status change or timeout
                initial_processing = task_state.get("is_processing")
                initial_progress = task_state.get("progress_percent", 0)
                deadline = asyncio.get_event_loop().time() + wait_seconds

                while asyncio.get_event_loop().time() < deadline:
                    await asyncio.sleep(0.2)
                    task_state = service.get_task_state(task_id)
                    if not task_state:
                        break
                    if task_state.get("is_processing") != initial_processing or task_state.get("progress_percent",
                                                                                               0) != initial_progress:
                        break

            status_dict = _task_state_to_dict(task_id, task_state)
            status = status_dict["status"]

            # If completed, show user-friendly format with download info
            if status == "completed":
                response_parts = [
                    "Translation completed successfully!",
                    f"Task ID: {task_id}",
                    "",
                    "Available formats:",
                ]

                # Get output options for original file info
                output_options = {}
                if hasattr(service, "_mcp_output_options"):
                    output_options = service._mcp_output_options.get(task_id, {})
                original_file_path = output_options.get("original_file_path", "")
                if original_file_path:
                    response_parts.insert(1, f"Input: {original_file_path}")

                downloadable_files = status_dict.get("downloadable_files", {})
                for fmt, info in downloadable_files.items():
                    response_parts.append(f"  - {fmt}: {info['filename']}")

                attachment_files = status_dict.get("attachment_files", {})
                if attachment_files:
                    response_parts.append("")
                    response_parts.append("Attachments (e.g., glossary):")
                    for name, info in attachment_files.items():
                        response_parts.append(f"  - {name}: {info['filename']}")

                response_parts.append("")
                response_parts.append(
                    "Use download_file to save translations or attachments to your local file system.")
                response_parts.append(
                    "After downloading all needed files, use release_task to clean up temporary files.")
                response_parts.append("")
                response_parts.append("Full status details:")
                response_parts.append(_format_json(status_dict))

                return "\n".join(response_parts)

            # For other statuses, just return the JSON
            return f"Task Status:\n{_format_json(status_dict)}"

        @mcp.tool()
        async def download_file(
                task_id: str,
                file_name: str,
                output_dir: str = "./output",
                output_name: Optional[str] = None,
                auto_release: bool = False,
        ) -> str:
            """Download a translated file or attachment to local file system.

            Args:
                task_id: The task ID from submit_task
                file_name: The format name (e.g., 'docx', 'html') or attachment name (e.g., 'glossary') to download
                output_dir: Output directory for saving the file (default: ./output)
                output_name: Output filename (optional, auto-generated if not provided)
                auto_release: Automatically release task resources after successful download (default: False)
            """
            task_state = service.get_task_state(task_id)
            if not task_state:
                return f"Error: Task not found: {task_id}"

            if not task_state.get("download_ready"):
                return "Error: No result available yet"

            # Get downloadable files and attachments
            downloadable_files = task_state.get("downloadable_files", {})
            attachment_files = task_state.get("attachment_files", {})

            # Find the file - check both downloadable and attachments
            all_files = {**downloadable_files, **attachment_files}

            if file_name not in all_files:
                available = list(all_files.keys())
                return f"Error: File '{file_name}' not available. Available: {available}"

            file_info = all_files[file_name]
            temp_file_path = file_info["path"]
            filename = file_info["filename"]

            # Read the file
            try:
                with open(temp_file_path, "rb") as f:
                    content_bytes = f.read()
            except Exception as e:
                return f"Error reading result file: {e}"

            # Save to file
            try:
                os.makedirs(output_dir, exist_ok=True)
                if output_name:
                    save_filename = output_name
                else:
                    save_filename = filename
                saved_path = os.path.join(output_dir, save_filename)
                with open(saved_path, "wb") as f:
                    f.write(content_bytes)
            except Exception as e:
                return f"Error saving file: {e}"

            response = f"File saved successfully:\nFile: {file_name}\nSaved to: {saved_path}"

            # Auto release task if requested
            if auto_release:
                try:
                    # Clean up output options
                    if hasattr(service, "_mcp_output_options") and task_id in service._mcp_output_options:
                        del service._mcp_output_options[task_id]

                    release_result = await service.release_task(task_id)
                    response += f"\n\nTask {task_id} released automatically. {release_result['message']}"
                except Exception as e:
                    response += f"\n\nWarning: Failed to auto-release task: {e}"

            return response

        @mcp.tool()
        async def cancel_task(task_id: str) -> str:
            """Cancel a pending or running task.

            Args:
                task_id: The task ID to cancel
            """
            try:
                result = service.cancel_task(task_id)
                return f"Task {task_id} cancelled successfully"
            except Exception as e:
                return f"Error: {e}"

        @mcp.tool()
        async def release_task(task_id: str) -> str:
            """Release task resources (temp files, memory, etc.) after translation is complete
            and all files have been downloaded.

            Args:
                task_id: The task ID to release
            """
            # Clean up output options
            if hasattr(service, "_mcp_output_options") and task_id in service._mcp_output_options:
                del service._mcp_output_options[task_id]

            try:
                result = await service.release_task(task_id)
                return f"Task {task_id} released successfully. {result['message']}"
            except Exception as e:
                return f"Error releasing task: {e}"

        @mcp.tool()
        async def load_glossary_file(file_path: str) -> str:
            """Load a glossary file (JSON or CSV) and return it as a JSON string for use in submit_task.

            Supports:
            - JSON files with format: {"原文": "译文", "Original": "Translated"}
            - CSV files with two columns: first column = original, second column = translated

            Args:
                file_path: Path to the glossary file (.json or .csv), or a URL starting with http:// or https://
            """
            import json
            import io

            # Check if file_path is a URL
            is_url = file_path.startswith("http://") or file_path.startswith("https://")
            content_bytes = None
            ext = None

            if is_url:
                # Download from URL directly into memory
                try:
                    from urllib.parse import urlparse

                    # Parse URL to get filename and extension
                    parsed_url = urlparse(file_path)
                    url_path = parsed_url.path
                    filename = os.path.basename(url_path)
                    ext = os.path.splitext(filename)[1].lower()
                    if not ext:
                        return "Error: Cannot determine file extension from URL"

                    # Ensure httpx_client is available
                    if service.httpx_client is None:
                        import httpx
                        service.httpx_client = httpx.AsyncClient()

                    # Download the file directly into memory
                    response = await service.httpx_client.get(file_path, timeout=60.0)
                    response.raise_for_status()
                    content_bytes = response.content
                except Exception as e:
                    return f"Error downloading glossary from URL: {e}"
            else:
                # Local file - check if exists
                if not os.path.exists(file_path):
                    return f"Error: File not found: {file_path}"
                ext = os.path.splitext(file_path)[1].lower()

                # Read the file
                try:
                    with open(file_path, "rb") as f:
                        content_bytes = f.read()
                except Exception as e:
                    return f"Error reading file: {e}"

            try:
                if ext == ".json":
                    glossary_dict = json.loads(content_bytes.decode("utf-8"))
                    if not isinstance(glossary_dict, dict):
                        return "Error: JSON file must contain a dictionary"

                elif ext == ".csv":
                    import csv
                    glossary_dict = {}
                    content_text = content_bytes.decode("utf-8")
                    reader = csv.reader(io.StringIO(content_text))
                    for row in reader:
                        if len(row) >= 2:
                            key = row[0].strip()
                            value = row[1].strip()
                            if key and value:
                                glossary_dict[key] = value

                else:
                    return f"Error: Unsupported file format: {ext}. Use .json or .csv"

                glossary_json = json.dumps(glossary_dict, ensure_ascii=False)
                return f"Glossary loaded successfully ({len(glossary_dict)} entries).\n\nUse this in submit_task:\nglossary_dict_json='''{glossary_json}'''"

            except Exception as e:
                return f"Error loading glossary file: {e}"

        @mcp.resource("docutranslate://info", name="DocuTranslate Server Information")
        async def get_info_resource() -> str:
            """Information about the DocuTranslate MCP server"""
            status_info = {
                "server": "docutranslate",
                "version": __version__,
                "status": "ready",
            }
            return _format_json(status_info)

        @mcp.resource("docutranslate://formats", name="Supported Formats")
        async def get_formats_resource() -> str:
            """List of supported file formats"""
            return _format_json(_get_formats_info())

        return mcp


    def get_sse_app(
            translation_service: Optional[TranslationService] = None,
            host: str = "127.0.0.1",
            port: int = 8000,
            enable_cors: bool = False,
            allow_origin_regex: str = r"^(https?://.*|null|file://.*)$",
    ):
        """Get the SSE Starlette app for mounting to existing FastAPI.

        Args:
            translation_service: Optional TranslationService instance (uses global if not provided)
            host: Host address (optional, not used when mounted)
            port: Port number (optional, not used when mounted)
            enable_cors: Whether to enable CORS for the SSE app
            allow_origin_regex: Regex for allowed CORS origins

        Returns:
            Starlette application that can be mounted to FastAPI
        """
        mcp = create_mcp_server(host=host, port=port, translation_service=translation_service)
        sse_app = mcp.sse_app()

        if enable_cors:
            from starlette.middleware.cors import CORSMiddleware
            sse_app.add_middleware(
                CORSMiddleware,
                allow_origin_regex=allow_origin_regex,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        return sse_app


    def run_mcp_server(
            transport: str = "stdio",
            host: str = "127.0.0.1",
            port: int = 8000,
            translation_service: Optional[TranslationService] = None,
    ):
        """Run the MCP server (entry point)

        Args:
            transport: Transport protocol to use ("stdio", "sse", or "streamable-http")
            host: Host address for SSE/streamable-http transport
            port: Port number for SSE/streamable-http transport
            translation_service: Optional TranslationService instance (uses global if not provided)
        """
        # Initialize the translation service with an HTTP client for standalone mode
        service = translation_service or get_translation_service()
        if service.httpx_client is None:
            import httpx

            # Create httpx client immediately (not async)
            # The client will be used in async context later
            service.httpx_client = httpx.AsyncClient()

        mcp = create_mcp_server(host=host, port=port, translation_service=service)

        # For SSE transport, mount at /mcp prefix
        if transport in ("sse", "streamable-http"):
            # Create a wrapper app with /mcp prefix
            from starlette.applications import Starlette

            wrapper_app = Starlette()
            sse_app = mcp.sse_app()
            wrapper_app.mount("/mcp", sse_app, name="mcp")

            # Run the wrapper app with uvicorn
            import uvicorn
            print(f"Starting MCP SSE server at http://{host}:{port}/mcp/sse")
            uvicorn.run(wrapper_app, host=host, port=port)
        else:
            # Run stdio transport normally
            # Note: For stdio mode, we rely on:
            # 1. release_task() to clean up per-task resources (temp files)
            # 2. OS process termination to clean up httpx client (socket handles)
            # This is acceptable for short-lived MCP stdio processes
            mcp.run(transport=transport)


    def main():
        """Main entry point for module execution"""
        import argparse

        parser = argparse.ArgumentParser(
            description="DocuTranslate MCP Server"
        )
        parser.add_argument(
            "--transport",
            type=str,
            default="stdio",
            choices=["stdio", "sse", "streamable-http"],
            help="Transport protocol to use (default: stdio)"
        )
        parser.add_argument(
            "--host",
            type=str,
            default="127.0.0.1",
            help="Host address for SSE/streamable-http transport (default: 127.0.0.1)"
        )
        parser.add_argument(
            "--port",
            type=int,
            default=8000,
            help="Port number for SSE/streamable-http transport (default: 8000)"
        )

        args = parser.parse_args()
        run_mcp_server(
            transport=args.transport,
            host=args.host,
            port=args.port
        )


    if __name__ == "__main__":
        main()


else:
    # MCP dependencies not installed - define placeholder functions
    MCP_AVAILABLE = False


    def _mcp_not_available(*args, **kwargs):
        raise ImportError(
            "MCP dependencies not installed. "
            "Install with: pip install docutranslate[mcp]"
        )


    create_mcp_server = _mcp_not_available
    get_sse_app = _mcp_not_available
    run_mcp_server = _mcp_not_available
