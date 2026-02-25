# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
"""
DocuTranslate MCP Server Package

This package provides a Model Context Protocol (MCP) server for DocuTranslate,
enabling AI assistants to use document translation capabilities.

Features:
- Async task queue mode: submit translation and get task_id immediately
- Task status querying
- Multiple transport protocols support (stdio, sse, streamable-http)
- Can be mounted to existing FastAPI app

Quick Start:
    ```bash
    # Install with MCP dependencies
    pip install docutranslate[mcp]

    # Run stdio server (for Claude Desktop, etc.)
    docutranslate --mcp

    # Run SSE server (for Cherry Studio)
    docutranslate --mcp --transport sse
    ```

Mount to existing FastAPI:
    ```python
    from fastapi import FastAPI
    from docutranslate.mcp import get_sse_app

    app = FastAPI()
    mcp_app = get_sse_app()
    app.mount("/mcp", mcp_app)
    ```

For more details, see the README.md in this package.
"""

from docutranslate.mcp.server import (
    create_mcp_server,
    run_mcp_server,
    get_sse_app,
    MCP_AVAILABLE,
)

__all__ = [
    "create_mcp_server",
    "run_mcp_server",
    "get_sse_app",
    "MCP_AVAILABLE",
]
