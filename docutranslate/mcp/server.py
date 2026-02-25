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
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from mcp.server.fastmcp import FastMCP, Context
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from docutranslate import __version__
from docutranslate.translator import default_params
from docutranslate.core.schemas import TranslatePayload
from pydantic import TypeAdapter

# Shared server layer imports
from docutranslate.server import (
    TranslationService,
    get_translation_service,
)


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
            "docx": ["docx", "html"],
            "xlsx": ["xlsx", "html"],
            "pptx": ["pptx"],
            "epub": ["epub", "html"],
            "txt": ["txt", "html"],
            "json": ["json", "html"],
            "srt": ["srt", "html"],
            "ass": ["ass", "html"],
            "html": ["html"],
        },
        "pdf_conversion_engines": ["mineru", "docling", "mineru_deploy", "identity"],
        "default_params": default_params
    }


def _task_state_to_dict(task_id: str, task_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Convert task state to a dict for MCP response"""
    if not task_state:
        return {
            "task_id": task_id,
            "status": "not_found",
            "error": "Task not found"
        }

    # Map to status string
    if task_state.get("is_processing"):
        status = "running"
    elif task_state.get("error_flag"):
        status = "failed"
    elif task_state.get("download_ready"):
        status = "completed"
    else:
        status = "pending"

    result = {
        "task_id": task_id,
        "status": status,
        "progress_percent": task_state.get("progress_percent", 0),
        "status_message": task_state.get("status_message", ""),
        "created_at": None,  # Not tracked in the shared state
        "started_at": datetime.fromtimestamp(task_state["task_start_time"]).isoformat() if task_state.get("task_start_time") else None,
        "completed_at": datetime.fromtimestamp(task_state["task_end_time"]).isoformat() if task_state.get("task_end_time") else None,
        "error": task_state.get("status_message") if task_state.get("error_flag") else None,
    }

    # Add full downloadable files info if available
    if task_state.get("download_ready"):
        downloadable_files = task_state.get("downloadable_files", {})
        attachment_files = task_state.get("attachment_files", {})

        if downloadable_files:
            result["downloadable_files"] = {}
            for fmt, file_info in downloadable_files.items():
                result["downloadable_files"][fmt] = {
                    "filename": file_info["filename"],
                    "temp_path": file_info["path"]
                }

        if attachment_files:
            result["attachment_files"] = {}
            for name, file_info in attachment_files.items():
                result["attachment_files"][name] = {
                    "filename": file_info["filename"],
                    "temp_path": file_info["path"]
                }

    return result


def create_mcp_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    translation_service: Optional[TranslationService] = None,
) -> FastMCP:
    """Create and configure the FastMCP server

    Args:
        host: Host address for SSE/streamable-http transport
        port: Port number for SSE/streamable-http transport
        translation_service: Optional TranslationService instance (uses global if not provided)

    Returns:
        Configured FastMCP server
    """
    if not MCP_AVAILABLE:
        raise ImportError(
            "MCP dependencies not installed. "
            "Install with: pip install docutranslate[mcp]"
        )

    # Use provided translation service or get the global one
    service = translation_service or get_translation_service()

    # Create FastMCP instance
    mcp = FastMCP(
        name=SERVER_NAME,
        instructions="DocuTranslate MCP server for document translation. "
                     "Step 1: Use submit_task to start a translation task, "
                     "Step 2: Use get_task_status to check progress - when completed, "
                     "it will show all available formats and attachments, "
                     "Step 3: Use download_file to save translations or attachments, "
                     "Step 4: Use release_task to clean up resources when done. "
                     "The translation uses the full workflow engine from DocuTranslate.",
        host=host,
        port=port,
    )

    @mcp.tool()
    async def get_status() -> str:
        """Get current server status and configuration information."""
        status_info = {
            "server": "docutranslate",
            "version": __version__,
            "status": "ready",
        }
        return f"Server Status:\n{_format_json(status_info)}"

    @mcp.tool()
    async def configure_client(
        # Note: This is kept for API compatibility but doesn't do anything
        # since we use the shared TranslationService that doesn't require pre-configuration
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_id: Optional[str] = None,
        to_lang: str = "中文",
        concurrent: int = 10,
        convert_engine: str = "identity",
        mineru_token: str = "",
    ) -> str:
        """Configure the DocuTranslate client (for API compatibility).
        Note: In the shared server mode, configuration is provided per-translation.

        Args:
            api_key: AI platform API key (provided per translation)
            base_url: AI platform base URL (provided per translation)
            model_id: Model ID to use (provided per translation)
            to_lang: Target language (provided per translation)
            concurrent: Number of concurrent requests (provided per translation)
            convert_engine: PDF conversion engine (provided per translation)
            mineru_token: MinerU API token (provided per translation)
        """
        return (
            "Note: In shared server mode, client configuration is provided "
            "per-translation. Use submit_task with the appropriate parameters. "
            "The shared TranslationService is ready to use."
        )

    @mcp.tool()
    async def get_client_config() -> str:
        """Get current client configuration (for API compatibility)."""
        return (
            "Client configuration: In shared server mode, configuration "
            "is provided per-translation using the api_key, base_url, and "
            "model_id parameters in submit_task or translate_file."
        )

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
    ) -> str:
        """Submit a translation task (asynchronous, returns immediately).
        Use get_task_status to check progress. When complete, it will show
        all available formats and attachments. Use download_file to save files.
        Supports PDF, DOCX, XLSX, MD, TXT, JSON, EPUB, SRT, ASS, PPTX, HTML formats.

        Args:
            file_path: Path to the file to translate
            api_key: AI platform API key
            base_url: AI platform base URL
            model_id: Model ID to use
            to_lang: Target language (default: 中文)
            workflow_type: Workflow type (auto-detected if not specified)
            skip_translate: Skip translation, only parse the document
            glossary_generate_enable: Enable automatic glossary generation
            glossary_dict_json: Glossary dictionary JSON string, format: {"原文":"译文"}
            glossary_agent_config_json: Glossary agent config JSON string (contains base_url, model_id, etc.)
        """
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"

        # Read the file
        try:
            with open(file_path, "rb") as f:
                file_contents = f.read()
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

        # Build payload dict - use AutoWorkflowParams with extra=allow
        # This avoids validation errors for workflow-specific optional fields
        payload_dict = {
            "workflow_type": workflow_type,
            "to_lang": to_lang or "中文",
            "skip_translate": skip_translate,
            "glossary_generate_enable": glossary_generate_enable,
            "glossary_dict": parsed_glossary_dict,
            "glossary_agent_config": parsed_glossary_agent,
        }

        # Add optional AI config if provided
        if api_key:
            payload_dict["api_key"] = api_key
        if base_url:
            payload_dict["base_url"] = base_url
        if model_id:
            payload_dict["model_id"] = model_id

        try:
            # Validate and create payload - AutoWorkflowParams allows extra fields
            payload = TypeAdapter(TranslatePayload).validate_python(payload_dict)
        except Exception as e:
            return f"Error validating parameters: {e}"

        # Create task_id and start translation
        task_id = os.path.basename(file_path)[:8] + "_" + base64.urlsafe_b64encode(os.urandom(4)).decode()[:8]

        try:
            # Store original file path for reference
            if not hasattr(service, "_mcp_output_options"):
                service._mcp_output_options = {}
            service._mcp_output_options[task_id] = {
                "original_file_path": file_path,
            }

            response = await service.start_translation(
                task_id=task_id,
                payload=payload,
                file_contents=file_contents,
                original_filename=os.path.basename(file_path),
            )
            return f"Translation task submitted successfully.\ntask_id: {task_id}\n\nUse get_task_status to check progress. When completed, it will show all available formats for download."
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
                if task_state.get("is_processing") != initial_processing or task_state.get("progress_percent", 0) != initial_progress:
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
            response_parts.append("Use download_file to save translations or attachments to your local file system.")
            response_parts.append("After downloading all needed files, use release_task to clean up temporary files.")
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
    ) -> str:
        """Download a translated file or attachment to local file system.

        Args:
            task_id: The task ID from submit_task
            file_name: The format name (e.g., 'docx', 'html') or attachment name (e.g., 'glossary') to download
            output_dir: Output directory for saving the file (default: ./output)
            output_name: Output filename (optional, auto-generated if not provided)
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

        return f"File saved successfully:\nFile: {file_name}\nSaved to: {saved_path}"

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
        try:
            result = await service.release_task(task_id)
            return f"Task {task_id} released successfully. {result['message']}"
        except Exception as e:
            return f"Error releasing task: {e}"

    @mcp.tool()
    async def translate_file(
        ctx: Context,
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
    ) -> str:
        """Translate a document file (synchronous mode - waits for completion).
        Returns task_id and available formats. Use download_file to save files.
        For async mode, use submit_task instead.
        Supports PDF, DOCX, XLSX, MD, TXT, JSON, EPUB, SRT, ASS, PPTX, HTML formats.

        Args:
            file_path: Path to the file to translate
            api_key: AI platform API key
            base_url: AI platform base URL
            model_id: Model ID to use
            to_lang: Target language
            workflow_type: Workflow type (auto-detected if not specified)
            skip_translate: Skip translation, only parse the document
            glossary_generate_enable: Enable automatic glossary generation
            glossary_dict_json: Glossary dictionary JSON string, format: {"原文":"译文"}
            glossary_agent_config_json: Glossary agent config JSON string (contains base_url, model_id, etc.)
        """
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"

        # Submit the task first
        submit_result = await submit_task(
            file_path=file_path,
            api_key=api_key,
            base_url=base_url,
            model_id=model_id,
            to_lang=to_lang,
            workflow_type=workflow_type,
            skip_translate=skip_translate,
            glossary_generate_enable=glossary_generate_enable,
            glossary_dict_json=glossary_dict_json,
            glossary_agent_config_json=glossary_agent_config_json,
        )

        if "Error" in submit_result:
            return submit_result

        # Extract task_id from the result
        import re
        match = re.search(r"task_id: ([a-zA-Z0-9_\-]+)", submit_result)
        if not match:
            return f"Error: Could not extract task_id from response: {submit_result}"

        task_id = match.group(1)

        # Wait for completion
        await ctx.report_progress(0, 100, "Translation started...")

        while True:
            task_state = service.get_task_state(task_id)
            if not task_state:
                return f"Error: Task disappeared"

            if not task_state.get("is_processing"):
                break

            progress = task_state.get("progress_percent", 0)
            message = task_state.get("status_message", "Processing...")
            await ctx.report_progress(progress, 100, message)
            await asyncio.sleep(0.5)

        await ctx.report_progress(100, 100, "Done!")

        # Get the result
        return await get_task_status(task_id, wait_seconds=0)

    @mcp.tool()
    async def translate_content(
        ctx: Context,
        content: str,
        filename: str,
        api_key: str = "",
        base_url: str = "",
        model_id: str = "",
        to_lang: Optional[str] = None,
    ) -> str:
        """Translate content provided as base64 encoded data (synchronous mode).
        Returns task_id and available formats. Use download_file to save files.

        Args:
            content: Base64 encoded file content
            filename: Filename with extension (for format detection)
            api_key: AI platform API key
            base_url: AI platform base URL
            model_id: Model ID to use
            to_lang: Target language
        """
        try:
            # Decode content
            content_bytes = base64.b64decode(content)

            # Save to temporary file
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir) / filename
                temp_path.write_bytes(content_bytes)

                # Call translate_file with the temp file
                return await translate_file(
                    ctx=ctx,
                    file_path=str(temp_path),
                    api_key=api_key,
                    base_url=base_url,
                    model_id=model_id,
                    to_lang=to_lang,
                    workflow_type="auto",
                    skip_translate=False,
                )

        except Exception as e:
            return f"Error processing content: {str(e)}"

    @mcp.tool()
    async def load_glossary_file(file_path: str) -> str:
        """Load a glossary file (JSON or CSV) and return it as a JSON string for use in submit_task.

        Supports:
        - JSON files with format: {"原文": "译文", "Original": "Translated"}
        - CSV files with two columns: first column = original, second column = translated

        Args:
            file_path: Path to the glossary file (.json or .csv)
        """
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"

        import json

        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    glossary_dict = json.load(f)
                if not isinstance(glossary_dict, dict):
                    return "Error: JSON file must contain a dictionary"

            elif ext == ".csv":
                import csv
                glossary_dict = {}
                with open(file_path, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
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

    @mcp.tool()
    async def get_supported_formats() -> str:
        """Get list of supported file formats and output options."""
        formats_info = _get_formats_info()
        return f"Supported formats:\n{_format_json(formats_info)}"

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
):
    """Get the SSE Starlette app for mounting to existing FastAPI.

    Args:
        translation_service: Optional TranslationService instance (uses global if not provided)
        host: Host address (optional, not used when mounted)
        port: Port number (optional, not used when mounted)

    Returns:
        Starlette application that can be mounted to FastAPI
    """
    mcp = create_mcp_server(host=host, port=port, translation_service=translation_service)
    return mcp.sse_app()


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
    if not MCP_AVAILABLE:
        print(
            "Error: MCP dependencies not installed.\n"
            "Install with: pip install docutranslate[mcp]",
            file=sys.stderr
        )
        sys.exit(1)

    # Initialize the translation service with a dummy HTTP client for standalone mode
    service = translation_service or get_translation_service()
    if service.httpx_client is None:
        import httpx

        async def init_service():
            service.httpx_client = httpx.AsyncClient()
            service.main_event_loop = asyncio.get_running_loop()

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(init_service())
        except RuntimeError:
            # No loop running yet, will be initialized when needed
            pass

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
