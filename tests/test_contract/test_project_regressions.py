from pathlib import Path
import importlib

import pytest
from pydantic import TypeAdapter

from docutranslate.cacher import MDBasedCovertCacher
from docutranslate.converter.x2md.converter_mineru_deploy import ConverterMineruDeployConfig
from docutranslate.core.schemas import TranslatePayload
from docutranslate.ir.document import Document
from docutranslate.ir.markdown_document import MarkdownDocument
from docutranslate.sdk import Client
from docutranslate.server.core import TranslationService, get_workflow_type_from_filename


def doc(value):
    return Document.from_bytes(value.encode(), suffix=".pdf", stem=value)


def md(value):
    return MarkdownDocument.from_bytes(value.encode(), suffix=".md", stem=value)


def test_cache_does_not_reuse_output_from_another_deployment():
    cache = MDBasedCovertCacher()
    first = ConverterMineruDeployConfig(base_url="https://first.example", api_key="one")
    other_server = ConverterMineruDeployConfig(base_url="https://second.example", api_key="one")
    other_account = ConverterMineruDeployConfig(base_url=first.base_url, api_key="two")
    cache.cache_result(md("first-server-result"), doc("input"), "mineru_deploy", first)
    assert cache.get_cached_result(doc("input"), "mineru_deploy", other_server) is None
    assert cache.get_cached_result(doc("input"), "mineru_deploy", other_account) is None


def test_cache_preserves_source_filename_identity():
    cache = MDBasedCovertCacher()
    first = Document.from_bytes(b"same content", suffix=".md", stem="first")
    second = Document.from_bytes(b"same content", suffix=".md", stem="second")
    cache.cache_result(md("first"), first, "identity", None)
    assert cache.get_cached_result(second, "identity", None) is None


def test_cache_limit_and_recently_used_eviction(monkeypatch):
    monkeypatch.setattr(importlib.import_module("docutranslate.cacher.md_based_convert_cacher"), "CACHE_NUM", "2")
    cache = MDBasedCovertCacher()
    cache.cache_result(md("a"), doc("a"), "identity", None)
    cache.cache_result(md("b"), doc("b"), "identity", None)
    assert cache.get_cached_result(doc("a"), "identity", None) is not None
    cache.cache_result(md("c"), doc("c"), "identity", None)
    assert len(cache.cache_dict) == 2
    assert cache.get_cached_result(doc("a"), "identity", None) is not None
    assert cache.get_cached_result(doc("b"), "identity", None) is None


def test_zero_cache_limit_disables_caching(monkeypatch):
    monkeypatch.setattr(importlib.import_module("docutranslate.cacher.md_based_convert_cacher"), "CACHE_NUM", "0")
    cache = MDBasedCovertCacher()
    cache.cache_result(md("a"), doc("a"), "identity", None)
    assert cache.get_cached_result(doc("a"), "identity", None) is None


@pytest.mark.parametrize("suffix", [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".jp2", ".PNG"])
@pytest.mark.asyncio
async def test_sdk_and_http_auto_modes_route_images_to_parser(monkeypatch, suffix):
    client = Client()
    path = Path("image" + suffix)
    assert client._detect_workflow(path) == "markdown_based"
    assert get_workflow_type_from_filename(path.name) == "markdown_based"
    params = {"workflow_type": "markdown_based"}
    client._patch_defaults(params, path)
    assert params["convert_engine"] == "mineru"
    service = TranslationService()
    captured = {}
    async def perform(task_id, payload, content, filename):
        captured["payload"] = payload
    monkeypatch.setattr(service, "_perform_translation", perform)
    payload = TypeAdapter(TranslatePayload).validate_python({"workflow_type": "auto", "skip_translate": True})
    await service.start_translation("image-route", payload, b"image", path.name)
    await service.tasks_state["image-route"]["current_task_ref"]
    assert captured["payload"].convert_engine == "mineru"


def test_markdown_extension_uses_identity():
    client = Client()
    assert client._detect_workflow(Path("readme.markdown")) == "markdown_based"
    params = {"workflow_type": "markdown_based"}
    client._patch_defaults(params, Path("readme.markdown"))
    assert params["convert_engine"] == "identity"


def test_markdown_zip_auto_routes_to_markdown_workflow():
    path = Path("archive.zip")
    client = Client()
    assert client._detect_workflow(path) == "markdown_based"
    assert get_workflow_type_from_filename(path.name) == "markdown_based"
    params = {"workflow_type": "markdown_based"}
    client._patch_defaults(params, path)
    assert params["convert_engine"] == "identity"


@pytest.mark.asyncio
async def test_sdk_auto_imports_markdown_zip(tmp_path):
    import base64
    import zipfile
    source = tmp_path / "archive.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("doc.md", "# hello")
    result = await Client().translate_async(str(source), skip_translate=True)
    assert base64.b64decode(result.export("markdown")) == b"# hello"


@pytest.mark.asyncio
async def test_json_upload_rejects_corrupt_base64_and_accepts_line_wrapping(monkeypatch):
    from fastapi import HTTPException
    from docutranslate.app import TranslateServiceRequest, service_translate
    import docutranslate.app as app_module

    def request(content):
        return TranslateServiceRequest(file_name="plain.txt", file_content=content,
                                       payload={"workflow_type": "txt", "skip_translate": True})

    with pytest.raises(HTTPException) as exc:
        await service_translate(request("aGVsbG8!"))
    assert exc.value.status_code == 400

    captured = {}
    async def start_translation(**kwargs):
        captured.update(kwargs)
        return {"task_started": True, "task_id": kwargs["task_id"]}
    monkeypatch.setattr(app_module.translation_service, "start_translation", start_translation)
    response = await service_translate(request("aGVs\nbG8="))
    assert response.status_code == 200
    assert captured["file_contents"] == b"hello"


@pytest.mark.asyncio
async def test_release_waits_for_cancelled_task_cleanup():
    import asyncio
    from docutranslate.server.core import _create_default_task_state
    service = TranslationService()
    cleaned = []
    async def worker():
        try:
            await asyncio.Event().wait()
        finally:
            await asyncio.sleep(0)
            cleaned.append(True)
    task = asyncio.create_task(worker())
    await asyncio.sleep(0)
    state = _create_default_task_state()
    state.update(is_processing=True, current_task_ref=task)
    service.tasks_state["release-test"] = state
    await service.release_task("release-test")
    assert cleaned == [True]
    assert "release-test" not in service.tasks_state


@pytest.mark.asyncio
async def test_server_reports_failure_when_every_export_fails(monkeypatch):
    import asyncio
    import time
    from docutranslate.core.schemas import TextWorkflowParams
    from docutranslate.server.core import _create_default_task_state

    service = TranslationService()
    service.main_event_loop = asyncio.get_running_loop()
    state = _create_default_task_state()
    state.update(task_start_time=time.time(), original_filename_stem="plain")
    service.tasks_state["failed-export"] = state
    service.tasks_log_queues["failed-export"] = asyncio.Queue()
    service.tasks_log_histories["failed-export"] = []

    class Workflow:
        def read_bytes(self, **kwargs):
            pass
        async def translate_async(self):
            pass
        def get_statistics(self):
            return {}
    def fail_export():
        raise ValueError("export failed")
    monkeypatch.setattr(service, "_create_workflow", lambda *args: Workflow())
    monkeypatch.setattr(service, "_build_export_map", lambda *args: {
        "txt": (fail_export, "plain_translated.txt", True)})
    await service._perform_translation("failed-export", TextWorkflowParams(
        workflow_type="txt", skip_translate=True), b"hello", "plain.txt")
    assert state["error_flag"] is True
    assert state["download_ready"] is False
    assert state["temp_dir"] is None


@pytest.mark.parametrize("filename,expected", [("scan.pdf", "mineru"), ("scan.jpeg", "mineru"), ("notes.markdown", "identity")])
@pytest.mark.asyncio
async def test_sdk_default_constructor_reaches_correct_engine(monkeypatch, tmp_path, filename, expected):
    import docutranslate.sdk as sdk
    source = tmp_path / filename
    source.write_bytes(b"test content")
    captured = {}
    class Workflow:
        def read_path(self, path):
            pass
        async def translate_async(self):
            pass
    def factory(payload):
        captured["payload"] = payload
        return Workflow()
    monkeypatch.setattr(sdk, "create_workflow_from_payload", factory)
    await Client().translate_async(str(source), skip_translate=True)
    assert captured["payload"].convert_engine == expected
    # Explicit per-call overrides remain honored.
    await Client().translate_async(str(source), convert_engine="identity", skip_translate=True)
    assert captured["payload"].convert_engine == "identity"


@pytest.mark.parametrize("filename,format_name", [("plain.txt", "txt"), ("notes.md", "markdown")])
@pytest.mark.asyncio
async def test_sdk_skip_translation_still_produces_export(tmp_path, filename, format_name):
    import base64
    source = tmp_path / filename
    source.write_text("hello", encoding="utf-8")
    result = await Client().translate_async(str(source), skip_translate=True)
    assert base64.b64decode(result.export(format_name)).decode("utf-8").strip() == "hello"


def test_markdown_zip_export_keeps_member_inside_archive(tmp_path, monkeypatch):
    import io
    import zipfile
    import docutranslate.utils.markdown_utils as markdown_utils

    class LocalTemporaryDirectory:
        def __enter__(self):
            self.inner = tmp_path / "inner"
            self.inner.mkdir()
            return str(self.inner)
        def __exit__(self, *args):
            return False

    monkeypatch.setattr(markdown_utils.tempfile, "TemporaryDirectory", LocalTemporaryDirectory)
    content = markdown_utils.unembed_base64_images_to_zip("hello", "../outside.md")
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        assert archive.namelist() == ["outside.md"]
        assert archive.read("outside.md") == b"hello"
    assert not (tmp_path / "outside.md").exists()
