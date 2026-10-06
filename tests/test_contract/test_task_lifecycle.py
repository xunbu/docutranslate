"""Task lifecycle regressions.

* A cancelled task used to leave its temporary directory behind (cleanup in the
  ``finally`` block was gated on ``error_flag``, which cancel never sets) and to
  report ``progress_percent = 100``.
* ``/service/flat-translate`` reported a cancelled/released task as HTTP 200
  ``success``, or crashed with ``AttributeError`` when the state was released.
"""
import asyncio
import os
import threading
import time

import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from docutranslate import app as app_module
from docutranslate.app import app, translation_service
from docutranslate.core.schemas import TranslatePayload
from docutranslate.logger import global_logger
from docutranslate.server.core import _create_default_task_state

MARKDOWN = b"# Hello\n\nbody\n"


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


class _FakeWorkflow:
    def read_bytes(self, **kwargs):
        return None

    async def translate_async(self):
        return self

    def get_attachment(self):
        return None

    def get_statistics(self):
        return {}


def _register_task(task_id: str) -> dict:
    state = _create_default_task_state()
    state.update({"is_processing": True, "status_message": "运行中", "progress_percent": 40})
    translation_service.tasks_state[task_id] = state
    translation_service.tasks_log_queues[task_id] = asyncio.Queue()
    translation_service.tasks_log_histories[task_id] = []
    return state


def _markdown_payload():
    return TypeAdapter(TranslatePayload).validate_python(
        {"workflow_type": "markdown_based", "skip_translate": True, "convert_engine": "identity"}
    )


async def test_cancel_during_export_cleans_temp_dir_and_keeps_progress(monkeypatch):
    task_id = "cancel-export-test"
    state = _register_task(task_id)

    monkeypatch.setattr(translation_service, "_create_workflow", lambda *a, **k: _FakeWorkflow())

    started = threading.Event()

    def fake_export_map(workflow, stem, cdn):
        def slow_export():
            started.set()
            time.sleep(5)
            return b"content"

        return {"markdown": (slow_export, "out.md", False)}

    monkeypatch.setattr(translation_service, "_build_export_map", fake_export_map)

    task = asyncio.create_task(
        translation_service._perform_translation(
            task_id, _markdown_payload(), MARKDOWN, "sample.md"
        )
    )

    for _ in range(500):
        if state.get("temp_dir") and started.is_set():
            break
        await asyncio.sleep(0.01)
    assert state.get("temp_dir"), "temp dir should exist before cancellation"

    temp_dir = state["temp_dir"]
    task.cancel()
    await task

    assert state["cancelled"] is True
    assert state["error_flag"] is False
    assert state["is_processing"] is False
    assert state["progress_percent"] != 100
    assert not os.path.isdir(temp_dir), "cancelled task must remove its temp dir"

    translation_service.tasks_state.pop(task_id, None)
    translation_service.tasks_log_queues.pop(task_id, None)
    translation_service.tasks_log_histories.pop(task_id, None)


async def test_failure_keeps_progress_below_100(monkeypatch):
    task_id = "failure-progress-test"
    state = _register_task(task_id)

    class _BoomWorkflow(_FakeWorkflow):
        def read_bytes(self, **kwargs):
            raise RuntimeError("synthetic parse failure")

    monkeypatch.setattr(translation_service, "_create_workflow", lambda *a, **k: _BoomWorkflow())

    await translation_service._perform_translation(
        task_id, _markdown_payload(), MARKDOWN, "sample.md"
    )

    assert state["error_flag"] is True
    assert state["progress_percent"] != 100

    translation_service.tasks_state.pop(task_id, None)
    translation_service.tasks_log_queues.pop(task_id, None)
    translation_service.tasks_log_histories.pop(task_id, None)


def test_flat_translate_reports_cancelled_task_as_conflict(client, monkeypatch):
    async def fake_start(task_id, payload, file_contents, original_filename):
        state = translation_service.tasks_state.setdefault(task_id, _create_default_task_state())
        state.update(
            {
                "cancelled": True,
                "error_flag": False,
                "is_processing": False,
                "status_message": "翻译任务已取消",
                "current_task_ref": None,
            }
        )
        return {"task_started": True, "task_id": task_id, "message": "started"}

    monkeypatch.setattr(translation_service, "start_translation", fake_start)

    response = client.post(
        "/service/flat-translate",
        files={"file": ("sample.md", MARKDOWN, "text/markdown")},
        data={"workflow_type": "auto", "skip_translate": "true"},
    )

    assert response.status_code == 409, response.text
    assert "取消" in response.text


def test_flat_translate_reports_released_task_as_gone(client, monkeypatch):
    async def fake_start(task_id, payload, file_contents, original_filename):
        state = translation_service.tasks_state.setdefault(task_id, _create_default_task_state())
        state.update(
            {"is_processing": True, "status_message": "运行中", "current_task_ref": None}
        )

        async def release_later():
            # 模拟并发 /release：等待期间状态被移除。
            await asyncio.sleep(0)
            translation_service.tasks_state.pop(task_id, None)

        state["current_task_ref"] = release_later()
        return {"task_started": True, "task_id": task_id, "message": "started"}

    monkeypatch.setattr(translation_service, "start_translation", fake_start)

    response = client.post(
        "/service/flat-translate",
        files={"file": ("sample.md", MARKDOWN, "text/markdown")},
        data={"workflow_type": "auto", "skip_translate": "true"},
    )

    assert response.status_code == 410, response.text
