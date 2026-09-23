import io
import zipfile

import httpx
import pytest

from docutranslate.converter.x2md import converter_mineru_deploy as mineru_deploy
from docutranslate.ir.document import Document


def _zip_result(markdown: str = "# parsed") -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("demo/auto/demo.md", markdown)
    return output.getvalue()


def _document() -> Document:
    return Document.from_bytes(content=b"fake-pdf", suffix=".pdf", stem="demo")


class _SyncTaskClient:
    def __init__(self):
        self.posts = []
        self.status_calls = 0

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        return httpx.Response(
            202,
            json={
                "task_id": "task-1",
                "status_url": "/tasks/task-1",
                "result_url": "/tasks/task-1/result",
            },
        )

    def get(self, url, **kwargs):
        if url.endswith("/result"):
            return httpx.Response(
                200,
                content=_zip_result(),
                headers={"content-type": "application/zip"},
            )
        self.status_calls += 1
        status = "pending" if self.status_calls == 1 else "completed"
        return httpx.Response(200, json={"status": status})


class _AsyncTaskClient(_SyncTaskClient):
    async def post(self, url, **kwargs):
        return super().post(url, **kwargs)

    async def get(self, url, **kwargs):
        return super().get(url, **kwargs)


def _converter() -> mineru_deploy.ConverterMineruDeploy:
    converter = mineru_deploy.ConverterMineruDeploy(
        mineru_deploy.ConverterMineruDeployConfig(
            base_url="http://mineru.local:8000",
            backend="hybrid-auto-engine",
            effort="high",
            image_analysis=True,
        )
    )
    converter.poll_interval = 0.001
    return converter


def test_latest_task_api_sync(monkeypatch):
    fake_client = _SyncTaskClient()
    monkeypatch.setattr(mineru_deploy, "client", fake_client)

    converter = _converter()
    result = converter.convert(_document())

    assert result.content.decode() == "# parsed"
    assert fake_client.posts[0][0] == "http://mineru.local:8000/tasks"
    form = fake_client.posts[0][1]["data"]
    assert form["backend"] == "hybrid-engine"
    assert form["effort"] == "high"
    assert form["image_analysis"] == "true"
    assert form["return_original_file"] == "false"
    assert form["client_side_output_generation"] == "false"
    assert "output_dir" not in form


@pytest.mark.asyncio
async def test_latest_task_api_async(monkeypatch):
    fake_client = _AsyncTaskClient()
    monkeypatch.setattr(mineru_deploy, "client_async", fake_client)

    result = await _converter().convert_async(_document())

    assert result.content.decode() == "# parsed"
    assert fake_client.status_calls == 2


def test_falls_back_to_legacy_file_parse(monkeypatch):
    class LegacyClient:
        def request(self, method, url, **kwargs):
            assert method == "GET" and url.endswith("/v1/health")
            return httpx.Response(404)

        def __init__(self):
            self.posts = []

        def post(self, url, **kwargs):
            self.posts.append((url, kwargs))
            if url.endswith("/tasks"):
                return httpx.Response(404, json={"detail": "Not Found"})
            return httpx.Response(
                200,
                content=_zip_result("legacy"),
                headers={"content-type": "application/zip"},
            )

    fake_client = LegacyClient()
    monkeypatch.setattr(mineru_deploy, "client", fake_client)

    result = _converter().convert(_document())

    assert result.content.decode() == "legacy"
    assert fake_client.posts[1][0].endswith("/file_parse")
    legacy_form = fake_client.posts[1][1]["data"]
    assert legacy_form["backend"] == "hybrid-auto-engine"
    assert legacy_form["output_dir"] == "./output"
    assert legacy_form["response_format_zip"] == "true"
    assert "effort" not in legacy_form
    assert "image_analysis" not in legacy_form
    assert "return_original_file" not in legacy_form
    assert "client_side_output_generation" not in legacy_form
