"""Continuation-request regressions.

When a response is cut off (``finish_reason == "length"``) the follow-up request
used to bypass the retry policy, swallow transient failures, and re-apply
``pre_send_handler`` on an already processed prompt (glossary injected twice).
"""
import json

import httpx
import pytest

from docutranslate.agents.agent import Agent, AgentConfig

GLOSSARY_MARKER = "<incremental_glossary>"


def _completion(content: str, finish_reason: str = "stop") -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": content}, "finish_reason": finish_reason}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        },
    )


async def _run(handler, *, retry=1, pre_send_handler=None):
    agent = Agent(
        AgentConfig(
            base_url="https://example.invalid/v1",
            model_id="mock",
            api_key="k",
            provider="openai",
            streaming=False,
            retry=retry,
        )
    )
    requests = []

    def wrapped(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return handler(len(requests), request)

    transport = httpx.MockTransport(wrapped)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await agent.send_async(
            client, "original prompt", pre_send_handler=pre_send_handler
        )
    return result, requests


async def test_continuation_failure_is_retried():
    def handler(index, request):
        if index == 1:
            return _completion("A", "length")
        if index == 2:
            return httpx.Response(500, json={"error": "synthetic"}, request=request)
        return _completion("B", "stop")

    result, requests = await _run(handler, retry=1)

    assert result == "AB"
    assert len(requests) == 3


async def test_continuation_gives_up_after_retries_with_partial_result():
    def handler(index, request):
        if index == 1:
            return _completion("A", "length")
        return httpx.Response(500, json={"error": "synthetic"}, request=request)

    result, requests = await _run(handler, retry=1)

    assert result == "A"
    assert len(requests) == 3  # first request + one retry + give-up retry cycle


@pytest.mark.parametrize("use_marker", [True])
async def test_preprocessing_applied_once_per_request(use_marker):
    def handler(index, request):
        if index == 1:
            return _completion("A", "length")
        return _completion("B", "stop")

    def preprocess(system, prompt):
        return system, GLOSSARY_MARKER + "\n" + prompt

    _, requests = await _run(handler, retry=0, pre_send_handler=preprocess)

    assert len(requests) == 2
    first_prompt = requests[0]["messages"][-1]["content"]
    continuation_prompt = requests[1]["messages"][-1]["content"]
    assert first_prompt.count(GLOSSARY_MARKER) == 1
    assert continuation_prompt.count(GLOSSARY_MARKER) == 1
