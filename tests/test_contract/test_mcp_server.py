"""MCP 服务器必须能按 mcp 2.x 的 API 建起来。

打包入口 `docutranslate/app.py` 的 __main__ 是 `run_app(with_mcp=True)`，也就是
发布的 exe/dmg 默认就要提供 MCP。mcp 2.x 把 FastMCP 改名为 MCPServer，且 host/port
改成传给 run()/sse_app()——这些测试锁住对 2.x API 的依赖，避免再次静默失效。
"""
import asyncio

import pytest

pytest.importorskip("mcp", reason="需要 mcp extra：uv sync --extra mcp")

from docutranslate.mcp import MCP_AVAILABLE, create_mcp_server  # noqa: E402

EXPECTED_TOOLS = {
    "get_status", "configure_client", "get_client_config", "submit_task",
    "get_task_status", "download_file", "cancel_task", "release_task",
    "load_glossary_file", "list_tasks", "get_task_logs",
}


def test_mcp_dependencies_are_usable():
    assert MCP_AVAILABLE is True, "mcp 依赖未安装或与代码不兼容"


def test_server_registers_every_tool_and_resource():
    server = create_mcp_server()

    tools = asyncio.run(server.list_tools())
    assert {tool.name for tool in tools} == EXPECTED_TOOLS

    resources = asyncio.run(server.list_resources())
    assert {str(r.uri) for r in resources} == {
        "docutranslate://info", "docutranslate://formats",
    }
