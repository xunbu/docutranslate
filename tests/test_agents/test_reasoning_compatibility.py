import gzip
import json
import logging

import httpx
import pytest

from docutranslate.agents.agent import (
    Agent,
    AgentConfig,
    _StreamingResponseAccumulator,
)
from docutranslate.agents.provider import get_provider_by_domain
from docutranslate.agents.provider.registry import get_reasoning_adapter
from docutranslate.agents.thinking.controller import (
    clear_reasoning_compatibility_cache,
)
from docutranslate.agents.thinking.thinking_factory import get_thinking_mode


class ChunkedAsyncStream(httpx.AsyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks

    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk


class ChunkedSyncStream(httpx.SyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks

    def __iter__(self):
        yield from self.chunks


def make_agent(
    provider,
    model,
    thinking,
    *,
    base_url="https://example.invalid/v1",
    extra_body=None,
    logger=None,
):
    return Agent(
        AgentConfig(
            base_url=base_url,
            api_key="test-key",
            model_id=model,
            provider=provider,
            thinking=thinking,
            streaming=False,
            extra_body=extra_body,
            logger=logger or logging.getLogger("reasoning-test"),
        )
    )


def request_data(agent):
    return agent._prepare_request_data("hello", "translate")[1]


def test_provider_owns_platform_reasoning_implementation():
    adapter = get_reasoning_adapter("deepseek")

    assert adapter.__class__.__module__ == "docutranslate.agents.provider.deepseek"


def test_legacy_thinking_factory_import_and_contract_remain_available():
    assert get_thinking_mode("deepseek", "deepseek-v4") == (
        "thinking",
        {"type": "enabled"},
        {"type": "disabled"},
    )


@pytest.mark.parametrize(
    ("provider", "model", "thinking", "expected"),
    [
        ("deepseek", "deepseek-v4-flash", "enable", {"thinking": {"type": "enabled"}}),
        ("deepseek", "deepseek-v4-pro", "disable", {"thinking": {"type": "disabled"}}),
        ("bigmodel", "glm-5", "enable", {"thinking": {"type": "enabled"}}),
        ("volces", "doubao-seed-2-0-pro", "disable", {"thinking": {"type": "disabled"}}),
        ("aliyuncs", "qwen3.8-max", "enable", {"enable_thinking": True}),
        ("siliconflow", "Qwen/Qwen3.5-27B", "disable", {"enable_thinking": False}),
        ("google", "gemini-2.5-flash", "disable", {"reasoning_effort": "none"}),
        ("ollama", "qwen3:8b", "enable", {"reasoning_effort": "medium"}),
        ("default", "gpt-5.6", "disable", {"reasoning_effort": "none"}),
        ("openrouter", "openai/gpt-5.6", "enable", {"reasoning": {"enabled": True, "exclude": True}}),
        ("mimo", "mimo-v2.5-pro", "enable", {"thinking": {"type": "enabled"}}),
        ("mimo", "mimo-v2.5", "disable", {"thinking": {"type": "disabled"}}),
        ("litellm", "translation-model", "enable", {"reasoning_effort": "medium"}),
        ("litellm", "translation-model", "disable", {"reasoning_effort": "none"}),
    ],
)
def test_provider_adapters_build_current_chat_completion_fields(
    provider, model, thinking, expected
):
    data = request_data(make_agent(provider, model, thinking))
    for key, value in expected.items():
        assert data[key] == value


def test_minimax_m3_uses_adaptive_protocol_and_splits_reasoning():
    enabled = request_data(make_agent("minimax", "MiniMax-M3", "enable"))
    disabled = request_data(make_agent("minimax", "MiniMax-M3", "disable"))
    default = request_data(make_agent("minimax", "MiniMax-M3", "default"))

    assert enabled["thinking"] == {"type": "adaptive"}
    assert enabled["reasoning_split"] is True
    assert disabled["thinking"] == {"type": "disabled"}
    assert "reasoning_split" not in disabled
    assert "thinking" not in default
    assert default["reasoning_split"] is True
    assert "reasoning_effort" not in enabled | disabled | default


@pytest.mark.parametrize(
    ("provider", "model"),
    [
        ("google", "gemini-3.7-flash"),
        ("aliyuncs", "qwen3-235b-a22b-thinking-2507"),
        ("minimax", "MiniMax-M2.7"),
        ("ollama", "gpt-oss:20b"),
    ],
)
def test_mandatory_reasoning_models_do_not_receive_invalid_disable_fields(
    provider, model
):
    data = request_data(make_agent(provider, model, "disable"))
    assert "thinking" not in data
    assert "enable_thinking" not in data
    assert "reasoning_effort" not in data


def test_non_reasoning_openai_model_omits_reasoning_field():
    data = request_data(make_agent("default", "gpt-4.1", "enable"))
    assert "reasoning_effort" not in data


@pytest.mark.parametrize(
    ("model", "expected_effort"),
    [
        ("gpt-5", "minimal"),
        ("gpt-5.1", "none"),
        ("gpt-5.6", "none"),
        ("gpt-5.1-codex-max", "none"),
        ("gpt-5.2-pro", "none"),
    ],
)
def test_openai_gpt5_disable_uses_supported_effort_values(model, expected_effort):
    data = request_data(make_agent("default", model, "disable"))
    assert data["reasoning_effort"] == expected_effort


@pytest.mark.parametrize(
    ("model", "expected_effort"),
    [
        ("gpt-5-pro", "high"),
        ("gpt-5.1-pro", "medium"),
    ],
)
def test_openai_gpt5_enable_default_effort(model, expected_effort):
    data = request_data(make_agent("default", model, "enable"))
    assert data["reasoning_effort"] == expected_effort


def test_openai_effort_catalog_matches_official_spec():
    adapter = get_reasoning_adapter("default")
    decision = adapter.decide("gpt-5.6", "enable")
    assert decision.capability.supported_efforts == (
        "none",
        "minimal",
        "low",
        "medium",
        "high",
        "xhigh",
    )


@pytest.mark.parametrize(
    ("model",),
    [
        ("glm-5.3",),
        ("glm-5.3-flash",),
        ("glm-4.7",),
    ],
)
def test_bigmodel_mandatory_reasoning_models_ignore_disable(model):
    data = request_data(make_agent("bigmodel", model, "disable"))
    assert "thinking" not in data
    assert "reasoning_effort" not in data


@pytest.mark.parametrize(
    ("model", "thinking", "expected"),
    [
        ("glm-5.3", "enable", {"type": "enabled"}),
        ("glm-4.7", "enable", {"type": "enabled"}),
        ("glm-4.6", "enable", {"type": "enabled"}),
        ("glm-5.2", "disable", {"type": "disabled"}),
    ],
)
def test_bigmodel_thinking_control_still_applies_to_non_mandatory(
    model, thinking, expected
):
    data = request_data(make_agent("bigmodel", model, thinking))
    assert data["thinking"] == expected


def test_bigmodel_mandatory_default_reports_support():
    adapter = get_reasoning_adapter("bigmodel")
    assert adapter.decide("glm-5.3", "default").capability.support == "mandatory"
    assert adapter.decide("glm-4.6", "default").capability.support == "optional"


def test_custom_gateway_does_not_guess_protocol_from_model_name():
    data = request_data(make_agent("default", "qwen3.5-custom", "enable"))
    assert data["reasoning_effort"] == "medium"
    assert "enable_thinking" not in data


def test_extra_body_keeps_final_precedence():
    data = request_data(
        make_agent(
            "minimax",
            "MiniMax-M3",
            "enable",
            extra_body=json.dumps(
                {"thinking": {"type": "disabled"}, "reasoning_split": False}
            ),
        )
    )
    assert data["thinking"] == {"type": "disabled"}
    assert data["reasoning_split"] is False


@pytest.mark.asyncio
async def test_invalid_reasoning_parameter_is_removed_once_and_cached():
    clear_reasoning_compatibility_cache()
    requests = []

    async def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        if "reasoning_effort" in body:
            return httpx.Response(
                400,
                json={"error": {"message": "Unsupported reasoning_effort parameter"}},
            )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "ok"}, "finish_reason": "stop"}
                ]
            },
        )

    agent = make_agent("default", "future-model", "enable")
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        headers, data = agent._prepare_request_data("hello", "translate")
        response = await agent._request_completion_async(client, data, headers)
        cached_data = agent._prepare_request_data("again", "translate")[1]

    assert response["choices"][0]["message"]["content"] == "ok"
    assert requests[0]["reasoning_effort"] == "medium"
    assert "reasoning_effort" not in requests[1]
    assert "reasoning_effort" not in cached_data


def test_sync_request_uses_the_same_reasoning_negotiation():
    clear_reasoning_compatibility_cache()
    requests = []

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        if "reasoning_effort" in body:
            return httpx.Response(
                422,
                json={"error": {"message": "Invalid reasoning_effort"}},
            )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "ok"}, "finish_reason": "stop"}
                ]
            },
        )

    agent = make_agent("default", "future-sync-model", "enable")
    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        headers, data = agent._prepare_request_data("hello", "translate")
        response = agent._request_completion_sync(client, data, headers)

    assert response["choices"][0]["message"]["content"] == "ok"
    assert len(requests) == 2
    assert "reasoning_effort" in requests[0]
    assert "reasoning_effort" not in requests[1]


@pytest.mark.asyncio
async def test_reasoning_error_does_not_permanently_disable_streaming():
    clear_reasoning_compatibility_cache()
    requests = []

    async def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        if "reasoning_effort" in body:
            return httpx.Response(
                400,
                json={"error": {"message": "Unknown reasoning_effort"}},
            )
        return httpx.Response(
            200,
            text=(
                'data: {"choices":[{"delta":{"content":"ok"},'
                '"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n'
            ),
            headers={"content-type": "text/event-stream"},
        )

    agent = Agent(
        AgentConfig(
            base_url="https://example.invalid/v1",
            api_key="test-key",
            model_id="future-stream-model",
            provider="default",
            thinking="enable",
            streaming=True,
        )
    )
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        headers, data = agent._prepare_request_data("hello", "translate")
        response = await agent._request_completion_async(client, data, headers)

    assert response["choices"][0]["message"]["content"] == "ok"
    assert agent._streaming_disabled is False
    assert all(request["stream"] is True for request in requests)


@pytest.mark.asyncio
async def test_user_reasoning_override_is_never_removed_by_negotiation():
    clear_reasoning_compatibility_cache()

    async def handler(request):
        return httpx.Response(
            400,
            json={"error": {"message": "Unsupported reasoning_effort parameter"}},
        )

    agent = make_agent(
        "default",
        "future-model",
        "enable",
        extra_body='{"reasoning_effort":"high"}',
    )
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        headers, data = agent._prepare_request_data("hello", "translate")
        with pytest.raises(httpx.HTTPStatusError):
            await agent._request_completion_async(client, data, headers)


def test_streaming_accumulator_ignores_reasoning_fields():
    accumulator = _StreamingResponseAccumulator()
    accumulator.feed(
        b'data: {"choices":[{"delta":{"reasoning_content":"private"}}]}\n\n'
    )
    accumulator.feed(
        b'data: {"choices":[{"delta":{"content":"translated"},"finish_reason":"stop"}]}\n\n'
    )
    accumulator.feed(b"data: [DONE]\n\n")

    result = accumulator.finish(b"")
    assert result["choices"][0]["message"]["content"] == "translated"


@pytest.mark.asyncio
async def test_async_gzip_stream_is_decoded_before_sse_parsing():
    body = gzip.compress(
        'data: {"choices":[{"delta":{"content":"compressed"}}]}\n\n'
        'data: [DONE]\n\n'.encode()
    )
    midpoint = len(body) // 2

    async def handler(request):
        return httpx.Response(
            200,
            headers={
                "content-type": "text/event-stream",
                "content-encoding": "gzip",
            },
            stream=ChunkedAsyncStream([body[:midpoint], body[midpoint:]]),
        )

    agent = Agent(AgentConfig(
        base_url="https://example.invalid/v1",
        model_id="test-model",
        streaming=True,
    ))
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        response = await agent._request_completion_async(
            client,
            {"model": "test-model", "messages": []},
            {},
        )

    assert response["choices"][0]["message"]["content"] == "compressed"


def test_sync_gzip_stream_is_decoded_before_sse_parsing():
    body = gzip.compress(
        'data: {"choices":[{"delta":{"content":"compressed"}}]}\n\n'
        'data: [DONE]\n\n'.encode()
    )
    midpoint = len(body) // 2

    def handler(request):
        return httpx.Response(
            200,
            headers={
                "content-type": "text/event-stream",
                "content-encoding": "gzip",
            },
            stream=ChunkedSyncStream([body[:midpoint], body[midpoint:]]),
        )

    agent = Agent(AgentConfig(
        base_url="https://example.invalid/v1",
        model_id="test-model",
        streaming=True,
    ))
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        response = agent._request_completion_sync(
            client,
            {"model": "test-model", "messages": []},
            {},
        )

    assert response["choices"][0]["message"]["content"] == "compressed"


def test_leading_minimax_think_block_is_removed_from_translation():
    agent = make_agent("minimax", "MiniMax-M3", "enable")
    assert agent._sanitize_result("<think>private</think>\nfinal") == "\nfinal"


@pytest.mark.parametrize(
    ("domain", "provider"),
    [
        ("api.minimaxi.com", "minimax"),
        ("openrouter.ai", "openrouter"),
        ("workspace.cn-beijing.maas.aliyuncs.com", "aliyuncs"),
        ("dashscope-intl.aliyuncs.com", "aliyuncs"),
        ("127.0.0.1:11434", "ollama"),
        ("api.xiaomimimo.com", "mimo"),
        ("token-plan-cn.xiaomimimo.com", "mimo"),
        ("litellm.internal:4000", "litellm"),
    ],
)
def test_provider_detection_covers_current_endpoint_variants(domain, provider):
    assert get_provider_by_domain(domain) == provider


def test_arbitrary_local_port_is_not_assumed_to_be_litellm():
    assert get_provider_by_domain("127.0.0.1:4000") == "default"
