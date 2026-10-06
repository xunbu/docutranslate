"""Regression tests for availability fixes in the HTTP surface.

* ``/service/flat-translate`` used to default ``convert_engine`` to ``"mineru"``,
  which disabled the server-side extension-based detection and made every plain
  Markdown upload fail with ``mineru_token 字段是必须的``.
* The same endpoint re-labelled ``HTTPException(400/429)`` raised by
  ``start_translation`` as HTTP 500.
* ``DOCUTRANSLATE_CACHE_NUM`` was parsed from the raw environment inside the
  conversion pipeline, so an invalid or empty value broke every conversion.
"""
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from docutranslate.app import app, translation_service
from docutranslate.logger import global_logger

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MARKDOWN = b"# Hello\n\nThis is a test document.\n"


@pytest.fixture
def client():
    # Entering the app lifespan raises the global logger to INFO; restore it so
    # that later test modules still observe the import-time configuration.
    previous_level = global_logger.level
    previous_propagate = global_logger.propagate
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        global_logger.setLevel(previous_level)
        global_logger.propagate = previous_propagate


def test_flat_translate_accepts_plain_markdown_with_defaults(client):
    response = client.post(
        "/service/flat-translate",
        files={"file": ("probe_doc.md", MARKDOWN, "text/markdown")},
        data={"workflow_type": "auto", "skip_translate": "true"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "success"
    assert "markdown" in body["downloads"]


def test_flat_translate_omits_convert_engine_so_server_can_detect_it(client, monkeypatch):
    """The form default must stay empty, otherwise auto-detection is disabled."""
    captured = {}

    async def capture(task_id, payload, file_contents, original_filename):
        captured["payload"] = payload
        raise HTTPException(status_code=400, detail="stop-after-capture")

    monkeypatch.setattr(translation_service, "start_translation", capture)

    response = client.post(
        "/service/flat-translate",
        files={"file": ("probe_doc.md", MARKDOWN, "text/markdown")},
        data={"workflow_type": "auto", "skip_translate": "true"},
    )

    assert getattr(captured["payload"], "convert_engine", None) is None
    assert response.status_code == 400


@pytest.mark.parametrize("status_code", [400, 429])
def test_flat_translate_preserves_start_translation_status(client, monkeypatch, status_code):
    """HTTPException from start_translation must not be re-labelled as HTTP 500."""

    async def fail(task_id, payload, file_contents, original_filename):
        raise HTTPException(status_code=status_code, detail="synthetic upstream rejection")

    monkeypatch.setattr(translation_service, "start_translation", fail)

    response = client.post(
        "/service/flat-translate",
        files={"file": ("probe_doc.md", MARKDOWN, "text/markdown")},
        data={"workflow_type": "auto", "skip_translate": "true"},
    )

    assert response.status_code == status_code, response.text
    assert "synthetic upstream rejection" in response.text
    assert "内部翻译错误" not in response.text


def test_flat_translate_still_honours_explicit_engine(client):
    response = client.post(
        "/service/flat-translate",
        files={"file": ("probe_doc.md", MARKDOWN, "text/markdown")},
        data={"workflow_type": "auto", "skip_translate": "true", "convert_engine": "identity"},
    )

    assert response.status_code == 200, response.text
    assert "markdown" in response.json()["downloads"]


@pytest.mark.parametrize("raw_value", ["ten", "", "  ", "3.5"])
def test_invalid_cache_num_env_does_not_break_caching(raw_value):
    """The value must be validated once, not int()-ed inside cache_result."""
    code = (
        "import os\n"
        f"os.environ['DOCUTRANSLATE_CACHE_NUM'] = {raw_value!r}\n"
        "from docutranslate.cacher.md_based_convert_cacher import CACHE_NUM\n"
        "value = int(CACHE_NUM)\n"
        "assert value >= 0, value\n"
        "print('cache_num=', value)\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "cache_num= 10" in completed.stdout
