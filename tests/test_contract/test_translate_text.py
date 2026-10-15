"""Contract tests for the text-input translation endpoint.

``POST /service/translate/text`` accepts raw text (instead of an uploaded file),
enforces a configurable character limit, and reuses the regular async task
machinery (status polling / downloads / content) with ``input_source="text"``.
"""
import base64
import time

import pytest
from fastapi.testclient import TestClient

from docutranslate import app as app_module
from docutranslate.app import app, translation_service
from docutranslate.logger import global_logger


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


def _txt_payload():
    return {"workflow_type": "txt", "skip_translate": True, "to_lang": "中文"}


def _cleanup(task_id):
    translation_service.tasks_state.pop(task_id, None)
    translation_service.tasks_log_queues.pop(task_id, None)
    translation_service.tasks_log_histories.pop(task_id, None)


def test_rejects_non_txt_workflow(client):
    response = client.post(
        "/service/translate/text",
        json={"text": "hello", "payload": {"workflow_type": "docx", "skip_translate": True}},
    )
    assert response.status_code == 400, response.text
    assert "txt" in response.text


def test_rejects_empty_text(client):
    response = client.post(
        "/service/translate/text",
        json={"text": "   \n  ", "payload": _txt_payload()},
    )
    assert response.status_code == 400, response.text
    assert "不能为空" in response.text


def test_rejects_text_over_limit(client, monkeypatch):
    monkeypatch.setattr(app_module, "TEXT_INPUT_LIMIT", 5)
    response = client.post(
        "/service/translate/text",
        json={"text": "123456", "payload": _txt_payload()},
    )
    assert response.status_code == 413, response.text
    assert "超过上限" in response.text


def test_meta_exposes_text_input_limit(client):
    response = client.get("/service/meta")
    assert response.status_code == 200
    assert response.json()["text_input_limit"] == app_module.TEXT_INPUT_LIMIT


def test_text_task_lifecycle(client, monkeypatch):
    monkeypatch.setattr(translation_service, "_create_workflow", lambda *a, **k: _FakeWorkflow())

    def fake_export_map(workflow, stem, cdn):
        return {"txt": (lambda: "你好，世界", "text_input_translated.txt", True)}

    monkeypatch.setattr(translation_service, "_build_export_map", fake_export_map)

    response = client.post(
        "/service/translate/text",
        json={"text": "Hello world\nsecond line", "payload": _txt_payload()},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["task_started"] is True
    task_id = data["task_id"]

    try:
        status = {}
        for _ in range(100):
            status = client.get(f"/service/status/{task_id}").json()
            if not status["is_processing"]:
                break
            time.sleep(0.05)

        assert status["is_processing"] is False
        assert status["error_flag"] is False
        assert status["download_ready"] is True
        assert status["input_source"] == "text"
        assert status["downloads"]["txt"]

        content = client.get(f"/service/content/{task_id}/txt").json()
        decoded = base64.b64decode(content["content"]).decode("utf-8")
        assert decoded == "你好，世界"
    finally:
        _cleanup(task_id)
