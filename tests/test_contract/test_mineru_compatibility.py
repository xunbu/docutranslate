import io
import json
import zipfile

import httpx
import pytest

from docutranslate.converter.x2md import converter_mineru as cloud
from docutranslate.converter.x2md import converter_mineru_deploy as deploy
from docutranslate.core.schemas import MarkdownWorkflowParams, UniversalParamsMixin
from docutranslate.ir.document import Document


def document(suffix=".pdf"):
    return Document.from_bytes(b"test input", suffix=suffix, stem="demo")


def archive():
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as z:
        z.writestr("full.md", "# result\n![image](images/demo.png)")
        z.writestr("images/demo.png", b"image-data")
    return output.getvalue()


class V1Server:
    def __init__(self, *, deduplicated=False, status="completed", health_status=200):
        self.requests = []
        self.job = None
        self.deduplicated = deduplicated
        self.status = status
        self.health_status = health_status

    def __call__(self, request):
        self.requests.append(request)
        path = request.url.path
        if path == "/tasks":
            return httpx.Response(404)
        if path == "/v1/health":
            return httpx.Response(self.health_status, json={"version": "4.0.0", "features": {
                "sources": ["file_id"], "output_formats": ["zip", "markdown"],
            }})
        if path == "/v1/uploads":
            payload = json.loads(request.content)
            assert payload["bytes"] == len(b"test input")
            assert len(payload["sha256sum"]) == 64
            if self.deduplicated:
                return httpx.Response(200, json={"id": "upload-1", "status": "completed", "file": {"id": "input-1"}})
            return httpx.Response(201, json={"id": "upload-1", "status": "pending",
                "upload_url": "https://storage.example/upload", "upload_method": "PUT",
                "upload_headers": {"x-upload": "signed"}})
        if path == "/upload":
            assert request.headers.get("authorization") is None
            assert request.headers["x-upload"] == "signed"
            assert request.content == b"test input"
            return httpx.Response(200)
        if path == "/v1/uploads/upload-1/complete":
            return httpx.Response(200, json={"status": "completed", "file": {"id": "input-1"}})
        if path == "/v1/parse/jobs":
            self.job = json.loads(request.content)
            return httpx.Response(202, json={"job_id": "job-1", "status": "queued"})
        if path == "/v1/parse/jobs/job-1":
            return httpx.Response(200, json={"job_id": "job-1", "status": self.status, "files": [{
                "status": self.status, "output_files": {"zip": {"file_id": "output-1"}},
                "error": {"code": "test-error", "message": "test error"},
            }]})
        if path == "/v1/files/output-1/content":
            return httpx.Response(200, content=archive())
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")


def converter(**kwargs):
    result = deploy.ConverterMineruDeploy(deploy.ConverterMineruDeployConfig(
        base_url="https://mineru.example", **kwargs))
    result.poll_interval = 0.001
    return result


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("deduplicated", [False, True])
@pytest.mark.asyncio
async def test_v1_full_cycle_preserves_markdown_and_images(monkeypatch, asynchronous, deduplicated):
    server = V1Server(deduplicated=deduplicated)
    transport = httpx.MockTransport(server)
    c = converter(api_key="secret", start_page_id=2, end_page_id=4, effort="high")
    if asynchronous:
        async with httpx.AsyncClient(transport=transport) as client:
            monkeypatch.setattr(deploy, "client_async", client)
            result = await c.convert_async(document())
    else:
        with httpx.Client(transport=transport) as client:
            monkeypatch.setattr(deploy, "client", client)
            result = c.convert(document())
    assert "data:image/png;base64," in result.content.decode()
    assert c.attachments[0].identifier == "mineru_deploy"
    assert server.job == {"files": [{"source": {"type": "file_id", "file_id": "input-1"},
                                    "page_range": "3-5"}],
                          "tier": "advanced", "ocr_mode": "auto", "output_formats": ["zip"]}
    for request in server.requests:
        if request.url.host == "mineru.example":
            assert request.headers["authorization"] == "Bearer secret"


@pytest.mark.parametrize("backend,tier", [("pipeline", "basic"), ("vlm-auto-engine", "standard"),
    ("hybrid-auto-engine", "standard"), ("flash", "flash"), ("advanced", "advanced")])
def test_old_backend_names_and_new_tiers(backend, tier):
    c = converter(backend=backend)
    payload = c._v1_adapter().job_payload(document(), "file")
    assert payload["tier"] == tier
    assert payload["files"][0]["page_range"] == "all"
    for cls, extra in [(MarkdownWorkflowParams, {"workflow_type": "markdown_based"}), (UniversalParamsMixin, {})]:
        params = cls(convert_engine="mineru_deploy", mineru_deploy_backend=backend, **extra)
        assert params.mineru_deploy_backend


def test_native_documents_and_open_ended_page_range():
    c = converter(start_page_id=2)
    assert c._v1_adapter().job_payload(document(), "f")["files"][0]["page_range"] == "3-r1"
    native = c._v1_adapter().job_payload(document(".docx"), "f")
    assert native["tier"] == "flash"
    assert "page_range" not in native["files"][0]


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("status", ["failed", "partial", "canceled", "unknown"])
@pytest.mark.asyncio
async def test_terminal_failures_never_fall_back_or_resubmit(monkeypatch, asynchronous, status):
    server = V1Server(status=status)
    transport = httpx.MockTransport(server)
    c = converter()
    with pytest.raises(RuntimeError, match=f"status={status}"):
        if asynchronous:
            async with httpx.AsyncClient(transport=transport) as client:
                monkeypatch.setattr(deploy, "client_async", client)
                await c.convert_async(document())
        else:
            with httpx.Client(transport=transport) as client:
                monkeypatch.setattr(deploy, "client", client)
                c.convert(document())
    assert sum(r.url.path == "/v1/parse/jobs" for r in server.requests) == 1


@pytest.mark.parametrize("status", [401, 403, 429, 500])
def test_discovery_errors_are_not_treated_as_legacy(monkeypatch, status):
    server = V1Server(health_status=status)
    with httpx.Client(transport=httpx.MockTransport(server)) as client:
        monkeypatch.setattr(deploy, "client", client)
        with pytest.raises(RuntimeError, match=f"HTTP {status}"):
            converter().convert(document())
    assert [r.url.path for r in server.requests] == ["/tasks", "/v1/health"]


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("version", [2, 3])
@pytest.mark.asyncio
async def test_legacy_protocols_still_work_without_caller_changes(monkeypatch, asynchronous, version):
    requests = []
    def handler(request):
        requests.append(request)
        if request.url.path == "/tasks":
            if version == 2:
                return httpx.Response(404)
            assert b'hybrid-engine' in request.content
            return httpx.Response(202, json={"task_id": "old-task"})
        if request.url.path == "/v1/health":
            return httpx.Response(404)
        if request.url.path == "/file_parse":
            assert b'hybrid-auto-engine' in request.content
            assert b'name="effort"' not in request.content
            return httpx.Response(200, content=archive())
        if request.url.path == "/tasks/old-task":
            return httpx.Response(200, json={"status": "completed"})
        if request.url.path == "/tasks/old-task/result":
            return httpx.Response(200, content=archive())
        raise AssertionError(request.url)
    c = converter(backend="hybrid-auto-engine")
    transport = httpx.MockTransport(handler)
    if asynchronous:
        async with httpx.AsyncClient(transport=transport) as client:
            monkeypatch.setattr(deploy, "client_async", client)
            result = await c.convert_async(document())
    else:
        with httpx.Client(transport=transport) as client:
            monkeypatch.setattr(deploy, "client", client)
            result = c.convert(document())
    assert result.content.startswith(b"# result")


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("version", [2, 3])
@pytest.mark.asyncio
async def test_authenticated_legacy_protocols_keep_key_on_service_only(monkeypatch, asynchronous, version):
    requests = []
    def handler(request):
        requests.append(request)
        if request.url.host == "storage.example":
            assert request.headers.get("authorization") is None
            return httpx.Response(200, content=archive())
        assert request.headers.get("authorization") == "Bearer secret"
        if request.url.path == "/tasks":
            return httpx.Response(404) if version == 2 else httpx.Response(202, json={
                "task_id": "old-task", "result_url": "https://storage.example/result"})
        if request.url.path == "/v1/health":
            return httpx.Response(404)
        if request.url.path == "/file_parse":
            return httpx.Response(200, content=archive())
        if request.url.path == "/tasks/old-task":
            return httpx.Response(200, json={"status": "completed"})
        raise AssertionError(request.url)
    c = converter(api_key="secret")
    transport = httpx.MockTransport(handler)
    if asynchronous:
        async with httpx.AsyncClient(transport=transport) as client:
            monkeypatch.setattr(deploy, "client_async", client)
            result = await c.convert_async(document())
    else:
        with httpx.Client(transport=transport) as client:
            monkeypatch.setattr(deploy, "client", client)
            result = c.convert(document())
    assert result.content.startswith(b"# result")


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.asyncio
async def test_cloud_upload_poll_download_contract(monkeypatch, asynchronous):
    polls = 0
    monkeypatch.setattr(cloud.time, "sleep", lambda _: None)
    async def no_sleep(_):
        pass
    monkeypatch.setattr(cloud.asyncio, "sleep", no_sleep)
    def handler(request):
        nonlocal polls
        if request.url.path == "/api/v4/file-urls/batch":
            body = json.loads(request.content)
            assert body["model_version"] == "MinerU-HTML"
            assert request.headers["authorization"] == "Bearer token"
            return httpx.Response(200, json={"code": 0, "data": {"batch_id": "batch", "file_urls": ["https://storage.example/input"]}})
        if request.url.path == "/input":
            assert "authorization" not in request.headers
            return httpx.Response(200)
        if request.url.path == "/api/v4/extract-results/batch/batch":
            polls += 1
            results = [] if polls == 1 else [{"state": "converting"}] if polls == 2 else [{"state": "done", "full_zip_url": "https://storage.example/result"}]
            return httpx.Response(200, json={"code": 0, "data": {"extract_result": results}})
        if request.url.path == "/result":
            assert "authorization" not in request.headers
            return httpx.Response(200, content=archive())
        raise AssertionError(request.url)
    c = cloud.ConverterMineru(cloud.ConverterMineruConfig(mineru_token="token"))
    transport = httpx.MockTransport(handler)
    if asynchronous:
        async with httpx.AsyncClient(transport=transport) as client:
            monkeypatch.setattr(cloud, "client_async", client)
            result = await c.convert_async(document(".html"))
    else:
        with httpx.Client(transport=transport) as client:
            monkeypatch.setattr(cloud, "client", client)
            result = c.convert(document(".html"))
    assert "data:image/png;base64," in result.content.decode()
    assert polls == 3
    assert c.max_pages == 200


def test_cloud_errors_keep_diagnostics():
    with pytest.raises(RuntimeError, match="A0211.*expired.*trace"):
        cloud.ConverterMineru._batch_result({"code": "A0211", "msg": "expired", "trace_id": "trace"})
    assert cloud.ConverterMineru._batch_result({"code": 0, "data": {"extract_result": []}}) is None


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.asyncio
async def test_v1_poll_timeout(monkeypatch, asynchronous):
    server = V1Server(status="running")
    c = converter()
    c.task_timeout = 0
    transport = httpx.MockTransport(server)
    with pytest.raises(TimeoutError, match="exceeded"):
        if asynchronous:
            async with httpx.AsyncClient(transport=transport) as client:
                monkeypatch.setattr(deploy, "client_async", client)
                await c.convert_async(document())
        else:
            with httpx.Client(transport=transport) as client:
                monkeypatch.setattr(deploy, "client", client)
                c.convert(document())


@pytest.mark.parametrize("model", ["pipeline", "vlm", "MinerU-HTML"])
def test_cloud_models_are_accepted_in_all_payload_modes(model):
    for cls, extra in [(MarkdownWorkflowParams, {"workflow_type": "markdown_based"}), (UniversalParamsMixin, {})]:
        result = cls(convert_engine="mineru", mineru_token="token", model_version=model, **extra)
        assert result.model_version == model


def test_v1_same_origin_upload_keeps_auth_and_proxy_prefix():
    c = converter(api_key="key")
    adapter = c._v1_adapter()
    adapter.base_url = "https://mineru.example/proxy"
    _, url, kwargs = adapter._request("PUT", "v1/uploads/u/content", headers={"x-upload": "value"})
    assert url == "https://mineru.example/proxy/v1/uploads/u/content"
    assert kwargs["headers"] == {"x-upload": "value", "Authorization": "Bearer key"}
    _, _, kwargs = adapter._request("PUT", "https://mineru.example:444/upload")
    assert "Authorization" not in kwargs["headers"]


def test_cloud_pdf_chunking_uses_current_limit():
    from pypdf import PdfWriter, PdfReader
    writer = PdfWriter()
    for _ in range(201):
        writer.add_blank_page(width=72, height=72)
    buffer = io.BytesIO()
    writer.write(buffer)
    c = cloud.ConverterMineru(cloud.ConverterMineruConfig(mineru_token="token"))
    chunks = c._split_pdf(buffer.getvalue())
    assert [len(PdfReader(io.BytesIO(chunk)).pages) for chunk in chunks] == [200, 1]


@pytest.mark.parametrize("backend", ["hybrid-auto-engine", "pipeline", "standard", "advanced"])
@pytest.mark.asyncio
async def test_sdk_keeps_constructor_options_without_new_call_arguments(monkeypatch, tmp_path, backend):
    import docutranslate.sdk as sdk
    source = tmp_path / "input.pdf"
    source.write_bytes(b"test input")
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
    client = sdk.Client(convert_engine="mineru_deploy", mineru_deploy_backend=backend,
                        mineru_deploy_start_page_id=2, mineru_deploy_end_page_id=4)
    await client.translate_async(str(source), skip_translate=True)
    payload = captured["payload"]
    assert payload.mineru_deploy_backend == {"hybrid-auto-engine": "hybrid-engine"}.get(backend, backend)
    assert (payload.mineru_deploy_start_page_id, payload.mineru_deploy_end_page_id) == (2, 4)


def test_factory_keeps_new_tier_and_old_options():
    from docutranslate.core.factory import create_workflow_from_payload
    payload = MarkdownWorkflowParams(workflow_type="markdown_based", convert_engine="mineru_deploy",
        mineru_deploy_backend="advanced", mineru_deploy_parse_method="ocr", mineru_deploy_formula_enable=False,
        mineru_deploy_start_page_id=1, mineru_deploy_end_page_id=6, skip_translate=True)
    workflow = create_workflow_from_payload(payload)
    config = workflow.config.converter_config
    assert (config.backend, config.parse_method, config.formula_enable) == ("advanced", "ocr", False)
    assert (config.start_page_id, config.end_page_id) == (1, 6)


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("bad_part", ["features", "file", "outputs", "json"])
@pytest.mark.asyncio
async def test_v1_malformed_responses_are_protocol_errors(monkeypatch, asynchronous, bad_part):
    server = V1Server()
    def handler(request):
        response = server(request)
        if request.url.path == "/v1/health":
            if bad_part == "json":
                return httpx.Response(200, text="not json")
            if bad_part == "features":
                return httpx.Response(200, json={"features": None})
        if request.url.path == "/v1/parse/jobs/job-1":
            if bad_part == "file":
                return httpx.Response(200, json={"status": "completed", "files": [None]})
            if bad_part == "outputs":
                return httpx.Response(200, json={"status": "completed", "files": [{"status": "completed", "output_files": []}]})
        return response
    transport = httpx.MockTransport(handler)
    with pytest.raises(RuntimeError, match="MinerU V1"):
        if asynchronous:
            async with httpx.AsyncClient(transport=transport) as client:
                monkeypatch.setattr(deploy, "client_async", client)
                await converter().convert_async(document())
        else:
            with httpx.Client(transport=transport) as client:
                monkeypatch.setattr(deploy, "client", client)
                converter().convert(document())


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.asyncio
async def test_v1_redirect_auth_stays_same_origin(monkeypatch, asynchronous):
    server = V1Server()
    def handler(request):
        if request.url.path == "/v1/files/output-1/content":
            return httpx.Response(302, headers={"location": "/download"})
        if request.url.path == "/download":
            assert request.headers.get("authorization") == "Bearer key"
            return httpx.Response(302, headers={"location": "https://storage.example/final"})
        if request.url.path == "/final":
            assert "authorization" not in request.headers
            return httpx.Response(200, content=archive())
        return server(request)
    c = converter(api_key="key")
    transport = httpx.MockTransport(handler)
    if asynchronous:
        async with httpx.AsyncClient(transport=transport) as client:
            monkeypatch.setattr(deploy, "client_async", client)
            result = await c.convert_async(document())
    else:
        with httpx.Client(transport=transport) as client:
            monkeypatch.setattr(deploy, "client", client)
            result = c.convert(document())
    assert result.content.startswith(b"# result")


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.asyncio
async def test_v1_does_not_poll_after_sleep_exhausts_deadline(monkeypatch, asynchronous):
    from docutranslate.converter.x2md import mineru_v1
    now = [0.0]
    monkeypatch.setattr(mineru_v1.time, "monotonic", lambda: now[0])
    def sleep(seconds):
        now[0] += seconds
    async def async_sleep(seconds):
        sleep(seconds)
    monkeypatch.setattr(mineru_v1.time, "sleep", sleep)
    monkeypatch.setattr(mineru_v1.asyncio, "sleep", async_sleep)
    c = converter()
    c.task_timeout = 0.5
    c.poll_interval = 1
    server = V1Server(status="running")
    transport = httpx.MockTransport(server)
    with pytest.raises(TimeoutError):
        if asynchronous:
            async with httpx.AsyncClient(transport=transport) as client:
                monkeypatch.setattr(deploy, "client_async", client)
                await c.convert_async(document())
        else:
            with httpx.Client(transport=transport) as client:
                monkeypatch.setattr(deploy, "client", client)
                c.convert(document())
    assert not any(r.url.path == "/v1/parse/jobs/job-1" for r in server.requests)


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("result", [{"state": "unexpected"}, {"progress": 20}, {"state": "done"}])
@pytest.mark.asyncio
async def test_cloud_invalid_state_fails_without_endless_polling(monkeypatch, asynchronous, result):
    requests = []
    def handler(request):
        requests.append(request)
        assert len(requests) == 1, "Invalid states must not be polled indefinitely"
        return httpx.Response(200, json={"code": 0, "data": {"extract_result": [result]}})
    monkeypatch.setattr(cloud.time, "sleep", lambda _: None)
    async def no_sleep(_):
        pass
    monkeypatch.setattr(cloud.asyncio, "sleep", no_sleep)
    c = cloud.ConverterMineru(cloud.ConverterMineruConfig(mineru_token="token"))
    transport = httpx.MockTransport(handler)
    with pytest.raises(RuntimeError, match="MinerU"):
        if asynchronous:
            async with httpx.AsyncClient(transport=transport) as client:
                monkeypatch.setattr(cloud, "client_async", client)
                await c.get_file_url_async("batch")
        else:
            with httpx.Client(transport=transport) as client:
                monkeypatch.setattr(cloud, "client", client)
                c.get_file_url("batch")


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.asyncio
async def test_cloud_pending_tasks_obey_wait_limit(monkeypatch, asynchronous):
    now, requests = [0.0], []
    monkeypatch.setattr(cloud.time, "monotonic", lambda: now[0])
    def sleep(seconds):
        now[0] += seconds
    async def async_sleep(seconds):
        sleep(seconds)
    monkeypatch.setattr(cloud.time, "sleep", sleep)
    monkeypatch.setattr(cloud.asyncio, "sleep", async_sleep)
    def handler(request):
        requests.append(request)
        assert len(requests) == 1, "No poll should start after the deadline"
        return httpx.Response(200, json={"code": 0, "data": {"extract_result": [{"state": "pending"}]}})
    c = cloud.ConverterMineru(cloud.ConverterMineruConfig(mineru_token="token"))
    c.task_timeout = 0.5
    transport = httpx.MockTransport(handler)
    with pytest.raises(TimeoutError):
        if asynchronous:
            async with httpx.AsyncClient(transport=transport) as client:
                monkeypatch.setattr(cloud, "client_async", client)
                await c.get_file_url_async("batch")
        else:
            with httpx.Client(transport=transport) as client:
                monkeypatch.setattr(cloud, "client", client)
                c.get_file_url("batch")
