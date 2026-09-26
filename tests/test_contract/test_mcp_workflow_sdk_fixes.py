import importlib.util
import asyncio
import logging
import base64
import json
import sys
import types
from pathlib import Path

import pytest
import httpx
from pydantic import TypeAdapter

from docutranslate.core.schemas import MarkdownWorkflowParams, TranslatePayload
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


@pytest.mark.parametrize("use_async", [False, True])
@pytest.mark.parametrize("custom_glossary", [False, True])
def test_sdk_skip_translation_also_skips_glossary_generation(
    tmp_path, monkeypatch, use_async, custom_glossary
):
    def unexpected_agent(*args, **kwargs):
        raise AssertionError("Skipping translation must not create a glossary agent")

    monkeypatch.setattr(
        "docutranslate.translator.ai_translator.base.GlossaryAgent", unexpected_agent
    )
    source = tmp_path / "sample.txt"
    source.write_text("Hello world", encoding="utf-8")
    glossary = {"hello": "你好"}
    options = {"glossary_generate_enable": True, "glossary_dict": glossary}
    if custom_glossary:
        options["glossary_agent_config"] = {
            "base_url": "https://example.invalid/v1", "api_key": "test-key",
            "model_id": "test-model", "to_lang": "简体中文",
        }
    client = Client(**options)
    if use_async:
        result = asyncio.run(client.translate_async(str(source), skip_translate=True))
    else:
        result = client.translate(str(source), skip_translate=True)

    assert base64.b64decode(result.export("txt")).decode("utf-8") == "Hello world"
    assert result.workflow._translator.glossary.glossary_dict == glossary
    assert result.workflow.get_statistics()["total"]["request_count"] == 0


@pytest.mark.parametrize("use_async", [False, True])
@pytest.mark.parametrize("constructor_options,call_options,expected_engine", [
    ({}, {}, MarkdownWorkflowParams.model_fields["md2docx_engine"].default),
    ({}, {"md2docx_engine": None}, None),
    ({"md2docx_engine": "python"}, {}, "python"),
    ({"md2docx_engine": "python"}, {"md2docx_engine": None}, None),
    ({"md2docx_engine": None}, {}, None),
    ({"md2docx_engine": None}, {"md2docx_engine": "python"}, "python"),
])
def test_sdk_markdown_docx_engine_overrides(
    tmp_path, use_async, constructor_options, call_options, expected_engine
):
    source = tmp_path / "sample.md"
    source.write_text("# Heading\n\nHello world", encoding="utf-8")
    client = Client(**constructor_options)
    options = {"skip_translate": True, "glossary_generate_enable": False, **call_options}
    if use_async:
        result = asyncio.run(client.translate_async(str(source), **options))
    else:
        result = client.translate(str(source), **options)

    config = result.workflow.config.md2docx_exporter_config
    assert (config.engine if config is not None else None) == expected_engine
    assert ("docx" in result.supported_formats) == (expected_engine is not None)
    assert b"Hello world" in base64.b64decode(result.export("markdown"))
    if expected_engine is None:
        with pytest.raises(ValueError, match="docx"):
            result.export("docx")
        with pytest.raises(ValueError, match="docx"):
            result.save(str(tmp_path / "exports"), fmt="docx")


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


@pytest.mark.parametrize("skip_translate", [False, True])
@pytest.mark.parametrize("supplied,env_key,force,env_set,expected", [
    (None, "env-key", False, True, "env-key"),
    ("", "env-key", False, True, "env-key"),
    ("request-key", "env-key", False, True, "request-key"),
    ("request-key", "env-key", True, True, "env-key"),
    ("request-key", "", True, False, "request-key"),
    (None, "", False, False, ""),
])
def test_local_mineru_key_environment_precedence(
    monkeypatch, skip_translate, supplied, env_key, force, env_set, expected
):
    import docutranslate.core.schemas as schemas
    from docutranslate.core.factory import create_workflow_from_payload
    monkeypatch.setattr(schemas, "MINERU_DEPLOY_API_KEY", env_key)
    monkeypatch.setattr(schemas, "ENV_FORCE_OVERRIDE", force)
    monkeypatch.setitem(schemas.ENV_SET, "mineru_deploy_api_key", env_set)
    payload = schemas.MarkdownWorkflowParams(
        workflow_type="markdown_based", convert_engine="mineru_deploy",
        skip_translate=skip_translate, mineru_deploy_api_key=supplied,
        base_url="https://example.invalid/v1", api_key="llm-key", model_id="test",
    )
    assert payload.mineru_deploy_api_key == expected
    assert create_workflow_from_payload(payload).config.converter_config.api_key == expected
    service_workflow = TranslationService()._create_workflow(
        payload, logging.getLogger("test-mineru-key"), None, lambda: None, "python"
    )
    assert service_workflow.config.converter_config.api_key == expected


@pytest.mark.parametrize("use_async", [False, True])
@pytest.mark.parametrize("call_options,expected", [
    ({}, "client-key"), ({"mineru_deploy_api_key": "request-key"}, "request-key"),
    ({"mineru_deploy_api_key": ""}, "env-key"),
])
def test_sdk_forwards_local_mineru_key(monkeypatch, tmp_path, use_async, call_options, expected):
    import docutranslate.sdk as sdk
    import docutranslate.core.schemas as schemas
    monkeypatch.setattr(schemas, "MINERU_DEPLOY_API_KEY", "env-key")
    monkeypatch.setattr(schemas, "ENV_FORCE_OVERRIDE", False)
    captured = []
    class Workflow:
        def read_path(self, path):
            pass
        async def translate_async(self):
            pass
    def factory(payload):
        captured.append(payload)
        return Workflow()
    monkeypatch.setattr(sdk, "create_workflow_from_payload", factory)
    source = tmp_path / "paper.pdf"
    source.write_bytes(b"synthetic pdf")
    client = Client(convert_engine="mineru_deploy", mineru_deploy_api_key="client-key")
    if use_async:
        asyncio.run(client.translate_async(str(source), skip_translate=True, **call_options))
    else:
        client.translate(str(source), skip_translate=True, **call_options)
    assert captured[0].mineru_deploy_api_key == expected


@pytest.mark.asyncio
async def test_server_auto_workflow_preserves_local_mineru_key(monkeypatch):
    service = TranslationService()
    captured = []
    async def perform(task_id, payload, file_contents, original_filename):
        captured.append(payload)
    monkeypatch.setattr(service, "_perform_translation", perform)
    payload = TypeAdapter(TranslatePayload).validate_python({
        "workflow_type": "auto", "skip_translate": True, "convert_engine": "mineru_deploy",
        "mineru_deploy_api_key": "local-service-key",
    })
    await service.start_translation("local-auth", payload, b"synthetic", "paper.pdf")
    await service.tasks_state["local-auth"]["current_task_ref"]
    assert captured[0].mineru_deploy_api_key == "local-service-key"


@pytest.mark.asyncio
async def test_mcp_local_mineru_key_configuration_and_masking(fake_mcp_server_module, tmp_path, monkeypatch):
    module = fake_mcp_server_module
    monkeypatch.setattr(module, "MINERU_DEPLOY_API_KEY", "environment-service-key")
    service = FakeService()
    mcp = module.create_mcp_server(translation_service=service)
    source = tmp_path / "paper.pdf"
    source.write_bytes(b"synthetic")
    submit = mcp.tools["submit_task"]
    options = {"workflow_type": "markdown_based", "convert_engine": "mineru_deploy", "skip_translate": True}
    await submit(str(source), **options)
    await mcp.tools["configure_client"](mineru_deploy_api_key="configured-service-key")
    await submit(str(source), **options)
    await submit(str(source), **options, mineru_deploy_api_key="per-task-service-key")
    assert [p.mineru_deploy_api_key for p in service.payloads] == [
        "environment-service-key", "configured-service-key", "per-task-service-key",
    ]
    config_text = await mcp.tools["get_client_config"]()
    assert "configured-service-key" not in config_text
    assert json.loads(config_text.split("\n", 1)[1])["mineru_deploy_api_key"] == "****"


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ["json", "file", "flat"])
async def test_http_accepts_local_mineru_key(monkeypatch, endpoint):
    import docutranslate.app as app_module
    captured = []
    async def start_translation(**kwargs):
        captured.append(kwargs["payload"])
        return {"task_started": True, "task_id": kwargs["task_id"]}
    monkeypatch.setattr(app_module.translation_service, "start_translation", start_translation)
    monkeypatch.setattr(app_module.translation_service, "get_task_state", lambda _: {"download_ready": True})
    payload = {"workflow_type": "markdown_based", "convert_engine": "mineru_deploy",
               "skip_translate": True, "mineru_deploy_api_key": "http-service-key"}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app_module.app),
                                 base_url="http://test") as client:
        if endpoint == "json":
            response = await client.post("/service/translate", json={
                "file_name": "paper.pdf", "file_content": "dGVzdA==", "payload": payload,
            })
        elif endpoint == "file":
            response = await client.post("/service/translate/file", data={"payload": json.dumps(payload)},
                                         files={"file": ("paper.pdf", b"test", "application/pdf")})
        else:
            response = await client.post("/service/flat-translate", data={**payload, "skip_translate": "true"},
                                         files={"file": ("paper.pdf", b"test", "application/pdf")})
    assert response.status_code == 200, response.text
    assert captured[0].mineru_deploy_api_key == "http-service-key"
    assert "http-service-key" not in response.text
