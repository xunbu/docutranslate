"""Regression tests for the per-batch retry/error budget.

Before the fix ``max_errors_count = len(prompts) // MAX_REQUESTS_PER_ERROR`` was
0 for every batch smaller than 15 prompts, so the first hard error disabled all
retries and the chunk silently fell back to its source text. The counter was also
never reset, so a second batch on the same Agent inherited the first batch's
errors and stopped retrying almost immediately.
"""
import logging

import httpx
import pytest

from docutranslate.agents import agent as agent_module
from docutranslate.agents.agent import Agent, AgentConfig, MAX_REQUESTS_PER_ERROR


def _make_agent(retry: int = 1) -> Agent:
    return Agent(
        AgentConfig(
            logger=logging.getLogger("test.batch-error-budget"),
            base_url="https://example.invalid/v1",
            api_key="test-key",
            model_id="mock-model",
            provider="openai",
            concurrent=1,
            retry=retry,
            streaming=False,
        )
    )


class _CountingTransport(httpx.MockTransport):
    def __init__(self):
        self.requests = []
        super().__init__(self._handler)

    def _handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(500, json={"error": {"message": "synthetic"}}, request=request)


@pytest.fixture
def failing_http(monkeypatch):
    """Route every LLM request through a transport that always returns HTTP 500."""
    transport = _CountingTransport()
    real_client = httpx.AsyncClient

    class PatchedClient(real_client):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(agent_module.httpx, "AsyncClient", PatchedClient)
    return transport


@pytest.mark.parametrize("n_prompts", [1, 3, 5])
async def test_small_batches_retry_every_chunk(n_prompts, failing_http):
    """A batch below the threshold must let every chunk use its retries."""
    agent = _make_agent(retry=1)
    prompts = [f"chunk-{i}" for i in range(n_prompts)]

    await agent.send_prompts_async(prompts)

    # No global circuit breaker for small batches: every chunk retries once.
    assert agent.total_error_counter.max_errors_count == n_prompts
    assert len(failing_http.requests) == n_prompts * 2


async def test_error_budget_is_reset_for_each_batch(failing_http):
    """Reusing one Agent for several documents must not carry errors over."""
    agent = _make_agent(retry=1)
    prompts = [f"chunk-{i}" for i in range(3)]

    await agent.send_prompts_async(prompts)
    first_batch = len(failing_http.requests)

    await agent.send_prompts_async(prompts)
    second_batch = len(failing_http.requests) - first_batch

    assert first_batch == 6
    # Without the reset the accumulated errors would trip the breaker immediately
    # and the second batch would issue only 3 requests.
    assert second_batch == first_batch


async def test_large_batch_breaker_threshold(failing_http):
    """Large batches keep an outage breaker at half the batch size."""
    agent = _make_agent(retry=0)
    prompts = [f"chunk-{i}" for i in range(MAX_REQUESTS_PER_ERROR)]

    await agent.send_prompts_async(prompts)

    assert agent.total_error_counter.max_errors_count == MAX_REQUESTS_PER_ERROR // 2
    assert len(failing_http.requests) == len(prompts)


async def test_failed_chunks_report_unresolved_errors(failing_http):
    agent = _make_agent(retry=1)
    prompts = ["only"]

    results = await agent.send_prompts_async(prompts)

    assert results == prompts  # documented degradation: source text is returned
    assert agent.unresolved_error_count == 1
    assert agent.get_full_stats()["unresolved_error_rate"] == 1.0


async def test_successful_batch_reports_no_unresolved_errors(monkeypatch):
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
            request=request,
        )
    )
    real_client = httpx.AsyncClient

    class PatchedClient(real_client):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(agent_module.httpx, "AsyncClient", PatchedClient)
    agent = _make_agent(retry=1)

    assert await agent.send_prompts_async(["a", "b"]) == ["ok", "ok"]
    assert agent.unresolved_error_count == 0
