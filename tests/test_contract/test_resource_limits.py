"""Resource-limit regressions: upload size, temp-dir sweep, task-registry bound."""
import asyncio
import os
import tempfile
import time

import pytest
from fastapi.testclient import TestClient

from docutranslate import app as app_module
from docutranslate.app import MaxBodySizeMiddleware, app, translation_service
from docutranslate.logger import global_logger
from docutranslate.server import core as core_module
from docutranslate.server.core import _create_default_task_state, cleanup_stale_temp_dirs


@pytest.fixture
def client():
    previous_level = global_logger.level
    previous_propagate = global_logger.propagate
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        global_logger.setLevel(previous_level)
        global_logger.propagate = previous_propagate


async def test_max_body_middleware_rejects_large_content_length():
    async def inner(scope, receive, send):  # pragma: no cover - must not be reached
        raise AssertionError("inner app should not be called")

    middleware = MaxBodySizeMiddleware(inner, max_bytes=10)
    scope = {"type": "http", "headers": [(b"content-length", b"1000")]}
    sent = []

    async def receive():
        return {"type": "http.request", "body": b""}

    async def send(message):
        sent.append(message)

    await middleware(scope, receive, send)

    assert sent and sent[0]["status"] == 413


class _FakeWorkflow:
    def read_bytes(self, **kwargs):
        return None

    async def translate_async(self):
        return self

    def get_attachment(self):
        return None

    def get_statistics(self):
        return {}


def test_endpoint_enforces_upload_limit(client, monkeypatch):
    monkeypatch.setattr(app_module, "_MAX_UPLOAD_BYTES", 16)

    response = client.post(
        "/service/flat-translate",
        files={"file": ("big.md", b"x" * 200, "text/markdown")},
        data={"workflow_type": "auto", "skip_translate": "true"},
    )

    assert response.status_code == 413, response.text


def test_cleanup_stale_temp_dirs_only_removes_old_dirs():
    base = tempfile.gettempdir()
    old_dir = tempfile.mkdtemp(prefix="docutranslate_test_old_")
    new_dir = tempfile.mkdtemp(prefix="docutranslate_test_new_")
    other_dir = tempfile.mkdtemp(prefix="unrelated_test_")
    try:
        old_time = time.time() - 48 * 3600
        os.utime(old_dir, (old_time, old_time))

        removed = cleanup_stale_temp_dirs(max_age_hours=24)

        assert removed >= 1
        assert not os.path.isdir(old_dir)
        assert os.path.isdir(new_dir)
        assert os.path.isdir(other_dir)
    finally:
        for path in (new_dir, other_dir, old_dir):
            if os.path.isdir(path):
                import shutil

                shutil.rmtree(path, ignore_errors=True)


def test_task_registry_is_bounded(monkeypatch, tmp_path):
    monkeypatch.setattr(core_module, "TASK_MAX_COUNT", 2)
    service = translation_service
    saved_state = dict(service.tasks_state)
    saved_queues = dict(service.tasks_log_queues)
    saved_histories = dict(service.tasks_log_histories)
    try:
        service.tasks_state.clear()
        service.tasks_log_queues.clear()
        service.tasks_log_histories.clear()

        temp_dir = tmp_path / "docutranslate_evict"
        temp_dir.mkdir()
        for index in range(4):
            state = _create_default_task_state()
            state.update({"is_processing": False, "task_start_time": index, "temp_dir": str(temp_dir)})
            service.tasks_state[f"task-{index}"] = state
            service.tasks_log_queues[f"task-{index}"] = asyncio.Queue()
            service.tasks_log_histories[f"task-{index}"] = []

        service._evict_finished_tasks()

        assert len(service.tasks_state) == 2
        assert "task-0" not in service.tasks_state
        assert "task-1" not in service.tasks_state
        assert "task-3" in service.tasks_state
    finally:
        service.tasks_state.clear()
        service.tasks_state.update(saved_state)
        service.tasks_log_queues.clear()
        service.tasks_log_queues.update(saved_queues)
        service.tasks_log_histories.clear()
        service.tasks_log_histories.update(saved_histories)
