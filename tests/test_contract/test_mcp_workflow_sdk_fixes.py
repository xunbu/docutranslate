import importlib.util
import base64
import json
import sys
import types
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from docutranslate.core.schemas import TranslatePayload
from docutranslate.sdk import Client, TranslationResult
from docutranslate.server.core import TranslationService


@pytest.mark.asyncio
async def test_auto_txt_workflow_preserves_segment_mode(monkeypatch):
    service = TranslationService()
    captured = {}

    async def perform_translation(task_id, payload, file_contents, original_filename):
        captured["payload"] = payload

    monkeypatch.setattr(service, "_perform_translation", perform_translation)
    payload = TypeAdapter(TranslatePayload).validate_python({
        "workflow_type": "auto", "skip_translate": True,
        "segment_mode": "paragraph",
    })

    await service.start_translation("segment-test", payload, b"one\n\ntwo", "sample.txt")
    await service.tasks_state["segment-test"]["current_task_ref"]

    assert captured["payload"].workflow_type == "txt"
    assert captured["payload"].segment_mode == "paragraph"


@pytest.mark.asyncio
async def test_sdk_exposes_workflow_export_formats(tmp_path):
    markdown = tmp_path / "sample.md"
    markdown.write_text("# Heading\n\nSome text", encoding="utf-8")
    markdown_result = await Client().translate_async(
        str(markdown), skip_translate=True, md2docx_engine="python"
    )
    assert "docx" in markdown_result.supported_formats
    assert base64.b64decode(markdown_result.export("docx")).startswith(b"PK")
    output_dir = tmp_path / "exports"
    assert Path(markdown_result.save(str(output_dir), fmt="docx")).read_bytes().startswith(b"PK")

    csv = tmp_path / "sample.csv"
    csv.write_text("name,value\nhello,world\n", encoding="utf-8")
    csv_result = await Client().translate_async(str(csv), skip_translate=True)
    assert {"xlsx", "csv", "html"}.issubset(csv_result.supported_formats)
    assert b"hello" in base64.b64decode(csv_result.export("csv"))
    assert b"hello" in Path(csv_result.save(str(output_dir), fmt="csv")).read_bytes()


def test_sdk_hides_disabled_markdown_docx():
    workflow = types.SimpleNamespace(config=types.SimpleNamespace(md2docx_exporter_config=None))
    result = TranslationResult(workflow, "markdown_based", "sample.md")
    assert "docx" not in result.supported_formats


@pytest.fixture
def fake_mcp_server_module(monkeypatch):
    class FakeFastMCP:
        def __init__(self, **kwargs):
            self.tools = {}
            self.run_transport = None

        def tool(self):
            def register(fn):
                self.tools[fn.__name__] = fn
                return fn
            return register

        def resource(self, *args, **kwargs):
            return lambda fn: fn

        def run(self, transport):
            self.run_transport = transport

        def sse_app(self):
            raise AssertionError("SSE app must not be used for Streamable HTTP")

    mcp_package = types.ModuleType("mcp")
    mcp_package.__path__ = []
    mcp_server_package = types.ModuleType("mcp.server")
    mcp_server_package.__path__ = []
    fastmcp_module = types.ModuleType("mcp.server.fastmcp")
    fastmcp_module.FastMCP = FakeFastMCP
    fastmcp_module.Context = type("Context", (), {})
    monkeypatch.setitem(sys.modules, "mcp", mcp_package)
    monkeypatch.setitem(sys.modules, "mcp.server", mcp_server_package)
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fastmcp_module)

    source = Path(__file__).parents[2] / "docutranslate" / "mcp" / "server.py"
    spec = importlib.util.spec_from_file_location("docutranslate.mcp._contract_server", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeService:
    def __init__(self):
        self.httpx_client = object()
        self.main_event_loop = None
        self.payloads = []

    async def start_translation(self, task_id, payload, file_contents, original_filename):
        self.payloads.append(payload)


@pytest.mark.asyncio
async def test_mcp_glossary_setting_inherits_config_and_can_be_overridden(
    fake_mcp_server_module, tmp_path, monkeypatch
):
    module = fake_mcp_server_module
    monkeypatch.setattr(module, "GLOSSARY_GENERATE_ENABLE", True)
    service = FakeService()
    mcp = module.create_mcp_server(translation_service=service)
    source = tmp_path / "sample.txt"
    source.write_text("hello", encoding="utf-8")

    submit = mcp.tools["submit_task"]
    await submit(str(source), workflow_type="txt", skip_translate=True)
    await submit(str(source), workflow_type="txt", skip_translate=True,
                 glossary_generate_enable=False)

    assert [payload.glossary_generate_enable for payload in service.payloads] == [True, False]


@pytest.mark.asyncio
async def test_mcp_config_hides_extra_body_and_url_credentials(
    fake_mcp_server_module, monkeypatch
):
    module = fake_mcp_server_module
    monkeypatch.setattr(module, "EXTRA_BODY", '{"token":"provider-secret"}')
    monkeypatch.setattr(module, "BASE_URL", "https://user:password@example.com/v1/secret")
    mcp = module.create_mcp_server(translation_service=FakeService())

    response = await mcp.tools["get_client_config"]()
    config = json.loads(response.split("\n", 1)[1])

    assert config["extra_body"] == "****"
    assert config["base_url"] == "https://example.com/..."
    assert "provider-secret" not in response
    assert "password" not in response


def test_streamable_http_uses_its_native_transport(fake_mcp_server_module, monkeypatch):
    module = fake_mcp_server_module
    service = FakeService()
    mcp = module.create_mcp_server(translation_service=service)
    monkeypatch.setattr(module, "create_mcp_server", lambda **kwargs: mcp)

    module.run_mcp_server(transport="streamable-http", translation_service=service)

    assert mcp.run_transport == "streamable-http"
