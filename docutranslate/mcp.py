# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
"""
DocuTranslate MCP Server

Model Context Protocol server for DocuTranslate, providing document translation
capabilities to AI assistants.
"""

import asyncio
import base64
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent, Resource, BlobResourceContents, EmbeddedResource
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from docutranslate import __version__
from docutranslate.sdk import Client, TranslationResult
from docutranslate.translator import default_params


# MCP Server configuration
SERVER_NAME = "docutranslate"
SERVER_VERSION = __version__


class DocuTranslateMCPServer:
    """MCP Server for DocuTranslate"""

    # Environment variable mapping
    ENV_VAR_MAPPING = {
        "DOCUTRANSLATE_API_KEY": "api_key",
        "DOCUTRANSLATE_BASE_URL": "base_url",
        "DOCUTRANSLATE_MODEL_ID": "model_id",
        "DOCUTRANSLATE_TO_LANG": "to_lang",
        "DOCUTRANSLATE_MINERU_TOKEN": "mineru_token",
        "DOCUTRANSLATE_CONVERT_ENGINE": "convert_engine",
        "DOCUTRANSLATE_CONCURRENT": "concurrent",
    }

    def __init__(self):
        if not MCP_AVAILABLE:
            raise ImportError(
                "MCP dependencies not installed. "
                "Install with: pip install docutranslate[mcp]"
            )

        self.server = Server(SERVER_NAME)
        self._setup_server()
        self._client: Optional[Client] = None
        self._client_config: Dict[str, Any] = {}
        self._config_source: str = "not_configured"  # "env_vars", "tool_config", "not_configured"

        # Try to initialize from environment variables
        self._init_from_env()

    def _init_from_env(self):
        """Initialize client from environment variables if available"""
        env_config: Dict[str, Any] = {}

        for env_var, config_key in self.ENV_VAR_MAPPING.items():
            value = os.environ.get(env_var)
            if value is not None:
                if config_key == "concurrent":
                    try:
                        env_config[config_key] = int(value)
                    except ValueError:
                        pass
                else:
                    env_config[config_key] = value

        # Check if we have the minimum required config from env vars
        required_keys = ["api_key", "base_url", "model_id"]
        has_minimum_config = all(key in env_config for key in required_keys)

        if has_minimum_config:
            try:
                self._client_config = env_config.copy()
                self._client = Client(
                    api_key=env_config.get("api_key"),
                    base_url=env_config.get("base_url"),
                    model_id=env_config.get("model_id"),
                    to_lang=env_config.get("to_lang", "中文"),
                    concurrent=env_config.get("concurrent", 10),
                    convert_engine=env_config.get("convert_engine", "identity"),
                    mineru_token=env_config.get("mineru_token", ""),
                )
                self._config_source = "env_vars"
            except Exception:
                # If env var config fails, just leave as not configured
                self._client = None
                self._client_config = {}
                self._config_source = "not_configured"

    def _setup_server(self):
        """Setup MCP server tools and resources"""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools"""
            return [
                Tool(
                    name="configure_client",
                    description="Configure the DocuTranslate client with LLM settings. "
                    "This will override any environment variable configuration.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "api_key": {
                                "type": "string",
                                "description": "AI platform API key"
                            },
                            "base_url": {
                                "type": "string",
                                "description": "AI platform base URL (e.g., https://api.openai.com/v1/)"
                            },
                            "model_id": {
                                "type": "string",
                                "description": "Model ID to use for translation"
                            },
                            "to_lang": {
                                "type": "string",
                                "description": "Target language (default: 中文)",
                                "default": "中文"
                            },
                            "concurrent": {
                                "type": "integer",
                                "description": "Number of concurrent requests (default: 10)",
                                "default": 10
                            },
                            "convert_engine": {
                                "type": "string",
                                "description": "PDF conversion engine: identity, mineru, docling, mineru_deploy",
                                "enum": ["identity", "mineru", "docling", "mineru_deploy"],
                                "default": "identity"
                            },
                            "mineru_token": {
                                "type": "string",
                                "description": "MinerU API token (for PDF parsing)"
                            },
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="get_status",
                    description="Get current server status and configuration information (without sensitive data).",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="translate_file",
                    description="Translate a document file from the local filesystem. "
                    "Supports PDF, DOCX, XLSX, MD, TXT, JSON, EPUB, SRT, ASS, PPTX, HTML formats.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file to translate"
                            },
                            "to_lang": {
                                "type": "string",
                                "description": "Target language (overrides client config)"
                            },
                            "workflow_type": {
                                "type": "string",
                                "description": "Workflow type (auto-detected if not specified)",
                                "enum": ["auto", "markdown_based", "txt", "json", "xlsx", "docx",
                                        "srt", "epub", "html", "ass", "pptx"],
                                "default": "auto"
                            },
                            "skip_translate": {
                                "type": "boolean",
                                "description": "Skip translation, only parse the document",
                                "default": False
                            },
                            "output_format": {
                                "type": "string",
                                "description": "Output format for the result",
                                "enum": ["html", "markdown", "markdown_zip", "txt", "json",
                                        "xlsx", "docx", "srt", "epub", "ass", "pptx"],
                            },
                            "output_dir": {
                                "type": "string",
                                "description": "Output directory for saving the result (default: ./output)",
                                "default": "./output"
                            },
                            "output_name": {
                                "type": "string",
                                "description": "Output filename (optional, auto-generated if not provided)"
                            },
                            "save_to_file": {
                                "type": "boolean",
                                "description": "Whether to save the result to file (default: True)",
                                "default": True
                            },
                        },
                        "required": ["file_path"]
                    }
                ),
                Tool(
                    name="translate_content",
                    description="Translate content provided as base64 encoded data.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "Base64 encoded file content"
                            },
                            "filename": {
                                "type": "string",
                                "description": "Filename with extension (for format detection)"
                            },
                            "to_lang": {
                                "type": "string",
                                "description": "Target language (overrides client config)"
                            },
                            "output_format": {
                                "type": "string",
                                "description": "Output format for the result",
                            },
                            "output_dir": {
                                "type": "string",
                                "description": "Output directory for saving the result (default: ./output)",
                                "default": "./output"
                            },
                            "output_name": {
                                "type": "string",
                                "description": "Output filename (optional, auto-generated if not provided)"
                            },
                            "save_to_file": {
                                "type": "boolean",
                                "description": "Whether to save the result to file (default: True)",
                                "default": True
                            },
                        },
                        "required": ["content", "filename"]
                    }
                ),
                Tool(
                    name="get_supported_formats",
                    description="Get list of supported file formats and output options.",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="get_client_config",
                    description="Get current client configuration (without sensitive data).",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
            ]

        @self.server.call_tool()
        async def call_tool(
            name: str,
            arguments: Dict[str, Any]
        ) -> List[TextContent]:
            """Handle tool calls"""
            if name == "configure_client":
                return await self._handle_configure_client(arguments)
            elif name == "translate_file":
                return await self._handle_translate_file(arguments)
            elif name == "translate_content":
                return await self._handle_translate_content(arguments)
            elif name == "get_supported_formats":
                return await self._handle_get_supported_formats()
            elif name == "get_client_config":
                return await self._handle_get_client_config()
            elif name == "get_status":
                return await self._handle_get_status()
            else:
                return [TextContent(
                    type="text",
                    text=f"Unknown tool: {name}"
                )]

        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            """List available resources"""
            return [
                Resource(
                    uri="docutranslate://info",
                    name="DocuTranslate Server Information",
                    description="Information about the DocuTranslate MCP server",
                    mimeType="application/json"
                ),
                Resource(
                    uri="docutranslate://formats",
                    name="Supported Formats",
                    description="List of supported file formats",
                    mimeType="application/json"
                )
            ]

        @self.server.read_resource()
        async def read_resource(uri: str) -> Union[str, bytes, BlobResourceContents]:
            """Read a resource"""
            if uri == "docutranslate://info":
                import json
                return json.dumps(self._get_status_info(), ensure_ascii=False, indent=2)
            elif uri == "docutranslate://formats":
                import json
                return json.dumps(self._get_formats_info(), ensure_ascii=False, indent=2)
            else:
                raise ValueError(f"Unknown resource: {uri}")

    async def _handle_configure_client(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle configure_client tool call"""
        try:
            self._client_config = arguments.copy()

            # Create client instance
            self._client = Client(
                api_key=arguments.get("api_key"),
                base_url=arguments.get("base_url"),
                model_id=arguments.get("model_id"),
                to_lang=arguments.get("to_lang", "中文"),
                concurrent=arguments.get("concurrent", 10),
                convert_engine=arguments.get("convert_engine", "identity"),
                mineru_token=arguments.get("mineru_token", ""),
            )
            self._config_source = "tool_config"

            # Don't include api_key in response
            safe_config = {k: v for k, v in arguments.items() if k != "api_key"}

            return [TextContent(
                type="text",
                text=f"Client configured successfully:\n{_format_json(safe_config)}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error configuring client: {str(e)}"
            )]

    async def _handle_translate_file(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle translate_file tool call"""
        if not self._client:
            return [TextContent(
                type="text",
                text="Error: Client not configured. Please set environment variables or call configure_client first."
            )]

        file_path = arguments["file_path"]
        if not os.path.exists(file_path):
            return [TextContent(
                type="text",
                text=f"Error: File not found: {file_path}"
            )]

        try:
            # Prepare translation options
            translate_kwargs = {}
            if "to_lang" in arguments:
                translate_kwargs["to_lang"] = arguments["to_lang"]
            if "workflow_type" in arguments:
                translate_kwargs["workflow_type"] = arguments["workflow_type"]
            if "skip_translate" in arguments:
                translate_kwargs["skip_translate"] = arguments["skip_translate"]

            # Merge with client config (for convert_engine, mineru_token, etc.)
            if "convert_engine" in self._client_config:
                translate_kwargs["convert_engine"] = self._client_config["convert_engine"]
            if "mineru_token" in self._client_config:
                translate_kwargs["mineru_token"] = self._client_config["mineru_token"]

            # Perform translation
            result = await self._client.translate_async(file_path, **translate_kwargs)

            # Get output format
            output_format = arguments.get("output_format")
            if not output_format:
                output_format = result.supported_formats[0] if result.supported_formats else "html"

            if output_format not in result.supported_formats:
                return [TextContent(
                    type="text",
                    text=f"Error: Format '{output_format}' not supported. "
                    f"Available formats: {result.supported_formats}"
                )]

            # Export result
            try:
                content_b64 = result.export(fmt=output_format)
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Error exporting result: {str(e)}"
                )]

            # Save to file if requested
            saved_path: Optional[str] = None
            save_to_file = arguments.get("save_to_file", True)
            if save_to_file:
                try:
                    output_dir = arguments.get("output_dir", "./output")
                    output_name = arguments.get("output_name")
                    saved_path = result.save(
                        output_dir=output_dir,
                        name=output_name,
                        fmt=output_format
                    )
                except Exception as e:
                    return [TextContent(
                        type="text",
                        text=f"Error saving result: {str(e)}"
                    )]

            # Build response
            output_filename = f"{Path(file_path).stem}_translated.{_get_extension(output_format)}"

            # For text-based formats, try to decode and show content preview
            content_preview = ""
            if output_format in ["html", "markdown", "txt", "json", "srt", "ass"]:
                try:
                    content_bytes = base64.b64decode(content_b64)
                    content_text = content_bytes.decode('utf-8')
                    # Show first 2000 characters as preview
                    preview_len = 2000
                    if len(content_text) > preview_len:
                        content_preview = f"\n\n--- Content Preview ({preview_len} chars) ---\n" + content_text[:preview_len] + "\n... [truncated]"
                    else:
                        content_preview = f"\n\n--- Content ---\n" + content_text
                except Exception:
                    pass

            # Build response text
            response_parts = [
                "Translation completed successfully!",
                f"Input: {file_path}",
                f"Output format: {output_format}",
                f"Output filename: {output_filename}",
                f"Supported formats: {result.supported_formats}",
            ]
            if saved_path:
                response_parts.append(f"Saved to: {saved_path}")
            response_parts.append(f"Content (base64): {content_b64}")

            return [
                TextContent(
                    type="text",
                    text="\n".join(response_parts) + content_preview
                )
            ]

        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error during translation: {str(e)}"
            )]

    async def _handle_translate_content(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle translate_content tool call"""
        if not self._client:
            return [TextContent(
                type="text",
                text="Error: Client not configured. Please set environment variables or call configure_client first."
            )]

        try:
            # Decode content
            content_b64 = arguments["content"]
            filename = arguments["filename"]
            content_bytes = base64.b64decode(content_b64)

            # Save to temporary file
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir) / filename
                temp_path.write_bytes(content_bytes)

                # Call translate_file with the temp file
                file_args = arguments.copy()
                file_args["file_path"] = str(temp_path)
                file_args.pop("content", None)
                file_args.pop("filename", None)

                return await self._handle_translate_file(file_args)

        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error processing content: {str(e)}"
            )]

    async def _handle_get_supported_formats(self) -> List[TextContent]:
        """Handle get_supported_formats tool call"""
        formats_info = self._get_formats_info()
        return [TextContent(
            type="text",
            text=f"Supported formats:\n{_format_json(formats_info)}"
        )]

    async def _handle_get_client_config(self) -> List[TextContent]:
        """Handle get_client_config tool call"""
        safe_config = {k: v for k, v in self._client_config.items() if k != "api_key"}
        return [TextContent(
            type="text",
            text=f"Client configuration:\n{_format_json(safe_config) if safe_config else 'Not configured'}"
        )]

    async def _handle_get_status(self) -> List[TextContent]:
        """Handle get_status tool call"""
        status_info = self._get_status_info()
        return [TextContent(
            type="text",
            text=f"Server Status:\n{_format_json(status_info)}"
        )]

    def _get_status_info(self) -> Dict[str, Any]:
        """Get comprehensive status information"""
        # Check which env vars are set
        env_vars_set = {}
        for env_var in self.ENV_VAR_MAPPING.keys():
            env_vars_set[env_var] = env_var in os.environ

        # Safe config (without sensitive data)
        safe_config = {k: v for k, v in self._client_config.items() if k != "api_key"}
        if "mineru_token" in safe_config and safe_config["mineru_token"]:
            safe_config["mineru_token"] = "***" if safe_config["mineru_token"] else ""

        return {
            "server": SERVER_NAME,
            "version": SERVER_VERSION,
            "status": "ready" if self._client else "not_configured",
            "config_source": self._config_source,
            "environment_variables": env_vars_set,
            "configuration": safe_config if safe_config else None,
        }

    def _get_formats_info(self) -> Dict[str, Any]:
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

    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


def _format_json(data: Any) -> str:
    """Format JSON for display"""
    import json
    return json.dumps(data, ensure_ascii=False, indent=2)


def _get_extension(format_name: str) -> str:
    """Get file extension for format name"""
    extensions = {
        "html": "html",
        "markdown": "md",
        "markdown_zip": "zip",
        "txt": "txt",
        "json": "json",
        "xlsx": "xlsx",
        "docx": "docx",
        "srt": "srt",
        "epub": "epub",
        "ass": "ass",
        "pptx": "pptx",
    }
    return extensions.get(format_name, "txt")


def _get_mime_type(format_name: str) -> str:
    """Get MIME type for format name"""
    mime_types = {
        "html": "text/html; charset=utf-8",
        "markdown": "text/markdown; charset=utf-8",
        "markdown_zip": "application/zip",
        "txt": "text/plain; charset=utf-8",
        "json": "application/json; charset=utf-8",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "srt": "text/plain; charset=utf-8",
        "epub": "application/epub+zip",
        "ass": "text/plain; charset=utf-8",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
    return mime_types.get(format_name, "application/octet-stream")


def run_mcp_server():
    """Run the MCP server (entry point)"""
    if not MCP_AVAILABLE:
        print(
            "Error: MCP dependencies not installed.\n"
            "Install with: pip install docutranslate[mcp]",
            file=sys.stderr
        )
        sys.exit(1)

    server = DocuTranslateMCPServer()
    asyncio.run(server.run())


def main():
    """Main entry point for module execution"""
    run_mcp_server()


if __name__ == "__main__":
    main()
