"""Task status must distinguish a complete translation from a partial one.

When every request of a chunk fails, the chunk is replaced by its source text and
the export still succeeds. Before this fix the task reported
``error_flag=False`` / ``progress_percent=100`` / ``"翻译完成！"``, so batch callers
could not tell a fully translated file from one whose chunks all fell back to the
original text (issue #62). The failure count was only reachable by reading
``statistics.total.unresolved_errors`` and nothing surfaced it.
"""
import asyncio
import time

import pytest

from docutranslate.agents import agent as agent_module
from docutranslate.core.schemas import MarkdownWorkflowParams
from docutranslate.core.task_status import (
    is_partial,
    statistics_totals,
    task_status,
    task_statistics,
)
from docutranslate.server.core import TranslationService, _create_default_task_state

MARKDOWN = (
    "# Title\n\n"
    + "\n\n".join(f"Paragraph {i} with enough English text to be chunked." for i in range(30))
    + "\n"
).encode()


def _statistics(unresolved: int, requests: int) -> dict:
    rate = unresolved / requests if requests else 0.0
    return {
        "glossary": None,
        "translation": {"request_count": requests, "unresolved_errors": unresolved,
                        "unresolved_error_rate": rate},
        "total": {"request_count": requests, "unresolved_errors": unresolved,
                  "unresolved_error_rate": rate},
    }


def _register(service, task_id: str) -> dict:
    state = _create_default_task_state()
    state.update(task_start_time=time.time(), original_filename_stem="demo",
                 original_filename="demo.md")
    service.tasks_state[task_id] = state
    service.tasks_log_queues[task_id] = asyncio.Queue()
    service.tasks_log_histories[task_id] = []
    return state


def _payload(**overrides) -> MarkdownWorkflowParams:
    options = dict(
        workflow_type="markdown_based",
        convert_engine="identity",
        base_url="https://example.invalid/v1",
        api_key="test-key",
        model_id="mock-model",
        to_lang="简体中文",
        chunk_size=400,
        concurrent=1,
        timeout=5,
        connect_timeout=2,
        read_timeout=5.0,
        retry=0,
        streaming=False,
        system_proxy_enable=False,
    )
    options.update(overrides)
    return MarkdownWorkflowParams(**options)


@pytest.fixture
def failing_llm(monkeypatch):
    """Route every LLM request to a transport that always answers HTTP 500."""
    import httpx

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            500, json={"error": {"message": "synthetic"}}, request=request
        )
    )
    real_client = httpx.AsyncClient

    class PatchedClient(real_client):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(agent_module.httpx, "AsyncClient", PatchedClient)
    return transport


def test_statistics_totals_tolerates_partial_payloads():
    assert statistics_totals(None) == {"request_count": 0, "unresolved_errors": 0,
                                       "unresolved_error_rate": 0.0}
    assert statistics_totals({}) == {"request_count": 0, "unresolved_errors": 0,
                                     "unresolved_error_rate": 0.0}
    assert statistics_totals({"total": None})["unresolved_errors"] == 0
    assert statistics_totals({"total": {"unresolved_errors": 3, "request_count": 4,
                                        "unresolved_error_rate": 0.75}}) == {
        "request_count": 4, "unresolved_errors": 3, "unresolved_error_rate": 0.75}


@pytest.mark.parametrize("state,expected", [
    ({"is_processing": True}, False),
    ({"cancelled": True, "download_ready": True, "statistics": _statistics(2, 2)}, False),
    ({"error_flag": True, "download_ready": True, "statistics": _statistics(2, 2)}, False),
    ({"download_ready": False, "statistics": _statistics(2, 2)}, False),
    ({"download_ready": True, "statistics": _statistics(0, 2)}, False),
    ({"download_ready": True, "statistics": _statistics(1, 2)}, True),
])
def test_is_partial_only_for_finished_tasks_with_failed_chunks(state, expected):
    assert is_partial(state) is expected


def test_status_stays_completed_so_downloads_keep_working():
    """``is_partial`` must not turn a downloadable result into an error status."""
    state = {"download_ready": True, "statistics": _statistics(2, 2)}
    assert task_status(state) == "completed"
    assert is_partial(state) is True


@pytest.mark.asyncio
async def test_failed_chunks_are_reported_in_status_and_statistics(failing_llm):
    """A task whose chunks all fail keeps its files, but says so."""
    service = TranslationService()
    service.main_event_loop = asyncio.get_running_loop()
    service.httpx_client = None
    task_id = "partial-report-test"
    state = _register(service, task_id)

    await service._perform_translation(task_id, _payload(), MARKDOWN, "demo.md")

    statistics = state["statistics"]
    totals = statistics_totals(statistics)
    assert totals["request_count"] > 0
    assert totals["unresolved_errors"] == totals["request_count"]

    # Still downloadable and still not an error: degraded output is not a crash.
    assert state["error_flag"] is False
    assert state["download_ready"] is True
    assert state["downloadable_files"]

    message = state["status_message"]
    assert "翻译完成" in message
    assert f"{totals['unresolved_errors']}/{totals['request_count']}" in message
    assert "保留了原文" in message
    assert is_partial(state) is True
    assert task_status(state) == "completed"
    assert task_statistics(state) is statistics

    service.tasks_state.pop(task_id, None)
    service.tasks_log_queues.pop(task_id, None)
    service.tasks_log_histories.pop(task_id, None)


@pytest.mark.asyncio
async def test_successful_translation_keeps_the_plain_completion_message():
    """The success path must stay byte-identical when every chunk succeeds."""
    service = TranslationService()
    service.main_event_loop = asyncio.get_running_loop()
    service.httpx_client = None
    task_id = "complete-report-test"
    state = _register(service, task_id)

    class Workflow:
        def read_bytes(self, **kwargs):
            pass

        async def translate_async(self):
            pass

        def get_attachment(self):
            return None

        def get_statistics(self):
            return _statistics(0, 3)

    service._create_workflow = lambda *args, **kwargs: Workflow()
    service._build_export_map = lambda *args, **kwargs: {
        "markdown": (lambda: "# done", "demo_translated.md", True)
    }

    await service._perform_translation(task_id, _payload(), MARKDOWN, "demo.md")

    assert state["error_flag"] is False
    assert state["download_ready"] is True
    assert state["status_message"].startswith("翻译完成！")
    assert is_partial(state) is False

    service.tasks_state.pop(task_id, None)
    service.tasks_log_queues.pop(task_id, None)
    service.tasks_log_histories.pop(task_id, None)
