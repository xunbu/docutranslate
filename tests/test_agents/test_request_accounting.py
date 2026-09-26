"""Request-level regressions using local HTTP transports, without API keys."""
import asyncio
import json

import httpx
import pytest

from docutranslate.agents.agent import Agent, AgentConfig, AgentResultError, PartialAgentResultError
from docutranslate.agents.markdown_agent import MDTranslateAgent, MDTranslateAgentConfig
from docutranslate.agents.segments_agent import SegmentsTranslateAgent, SegmentsTranslateAgentConfig


def completion(text, reason="stop", streaming=False):
    usage = {
        "prompt_tokens": 100, "prompt_cache_hit_tokens": 60,
        "completion_tokens": 20, "completion_tokens_details": {"reasoning_tokens": 5},
        "total_tokens": 120,
    }
    if not streaming:
        return httpx.Response(200, json={
            "choices": [{"message": {"content": text}, "finish_reason": reason}],
            "usage": usage,
        })
    # Include usage in both the finish event and a trailing usage-only event:
    # these describe the same request and must not be counted twice.
    events = [
        {"choices": [{"delta": {"content": text}}]},
        {"choices": [{"delta": {}, "finish_reason": reason}], "usage": usage},
        {"choices": [], "usage": usage},
    ]
    content = "".join(f"data: {json.dumps(event)}\n\n" for event in events)
    return httpx.Response(200, headers={"content-type": "text/event-stream"},
                          content=(content + "data: [DONE]\n\n").encode())


def invoke(agent, handler, use_async, **kwargs):
    transport = httpx.MockTransport(handler)
    if use_async:
        async def run():
            async with httpx.AsyncClient(transport=transport) as client:
                return await agent.send_async(client, "Hello world", **kwargs)
        return asyncio.run(run())
    with httpx.Client(transport=transport) as client:
        return agent.send(client, "Hello world", **kwargs)


def assert_usage(agent, requests):
    assert agent.token_counter.get_stats() == {
        "input_tokens": 100 * requests, "cached_tokens": 60 * requests,
        "output_tokens": 20 * requests, "reasoning_tokens": 5 * requests,
        "total_tokens": 120 * requests,
    }


@pytest.mark.parametrize("use_async", [False, True], ids=["sync", "async"])
@pytest.mark.parametrize("agent_class,config_class", [
    (SegmentsTranslateAgent, SegmentsTranslateAgentConfig),
    (MDTranslateAgent, MDTranslateAgentConfig),
], ids=["segments", "markdown"])
def test_retries_keep_one_glossary_and_identical_messages(use_async, agent_class, config_class):
    agent = agent_class(config_class(
        base_url="https://example.invalid/v1", model_id="test", provider="deepseek",
        to_lang="zh", streaming=False, retry=2, glossary_dict={"hello": "你好"},
    ))
    messages = []

    def handler(request):
        messages.append(json.loads(request.content)["messages"])
        if len(messages) == 1:
            return httpx.Response(500, json={"error": "synthetic failure"})
        return completion("invalid" if len(messages) == 2 else "你好世界")

    def validate(result, prompt, logger):
        if result == "invalid":
            raise AgentResultError("synthetic invalid translation")
        return result

    result = invoke(agent, handler, use_async, pre_send_handler=agent._pre_send_handler,
                    result_handler=validate)
    assert result == "你好世界"
    assert len(messages) == 3
    assert messages[0] == messages[1] == messages[2]
    assert messages[0][-1]["content"].count("<incremental_glossary>") == 1
    assert "hello=>你好" in messages[0][-1]["content"]
    assert "Hello world" in messages[0][-1]["content"]
    assert_usage(agent, 2)  # The invalid translation still consumed tokens.


@pytest.mark.parametrize("use_async", [False, True], ids=["sync", "async"])
def test_partial_retry_preserves_feedback_without_reapplying_preprocessing(use_async):
    agent = Agent(AgentConfig(base_url="https://example.invalid/v1", model_id="test",
                              provider="deepseek", streaming=False, retry=1))
    messages = []

    def handler(request):
        messages.append(json.loads(request.content)["messages"])
        return completion("partial" if len(messages) == 1 else "complete")

    def preprocess(system, prompt):
        return system + "\nStable rule", "Glossary: hello=>你好\n" + prompt

    def validate(result, prompt, logger):
        if result == "partial":
            raise PartialAgentResultError("missing segment", {"0": "你好"},
                                          append_prompt="\nPlease include the missing segment.")
        return result

    assert invoke(agent, handler, use_async, pre_send_handler=preprocess,
                  result_handler=validate) == "complete"
    assert len(messages) == 2
    assert messages[0][0] == messages[1][0]
    assert messages[1][-1]["content"] == (
        messages[0][-1]["content"] + "\nPlease include the missing segment."
    )
    assert_usage(agent, 2)


@pytest.mark.parametrize("use_async", [False, True], ids=["sync", "async"])
@pytest.mark.parametrize("streaming", [False, True], ids=["json", "sse"])
@pytest.mark.parametrize("reasons,expected", [
    (["stop"], "A"),
    (["length", "stop"], "AB"),
    (["length", "length", "stop"], "ABC"),
    (["length", "length", "length"], "ABC"),
    (["length", "http_error"], "A"),
], ids=["normal", "continue", "continue-twice", "continue-limit", "continue-failed"])
def test_every_completed_response_is_counted_once(use_async, streaming, reasons, expected):
    agent = Agent(AgentConfig(base_url="https://example.invalid/v1", model_id="test",
                              provider="deepseek", streaming=streaming, retry=0))
    calls = []

    def handler(request):
        index = len(calls)
        calls.append(json.loads(request.content))
        reason = reasons[index]
        if reason == "http_error":
            return httpx.Response(500, json={"error": "synthetic failure"})
        return completion(chr(ord("A") + index), reason, streaming)

    assert invoke(agent, handler, use_async) == expected
    assert len(calls) == len(reasons)
    assert_usage(agent, len(expected))
