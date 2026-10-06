"""
Tests for agent module
"""
import asyncio
import json
import pytest
from unittest.mock import MagicMock
import logging

import httpx

from docutranslate.agents.agent import Agent, AgentConfig, AgentResultError, PartialAgentResultError


class ConcreteAgent:
    """Concrete implementation of Agent for testing"""

    def __init__(self, config):
        self.config = config


class TestAgentConfig:
    """Test AgentConfig dataclass"""

    def test_agent_config_default(self):
        """Test AgentConfig with default values"""
        config = AgentConfig(
            base_url="https://api.example.com",
            model_id="gpt-4"
        )
        assert config.logger is not None
        assert config.base_url == "https://api.example.com"
        assert config.model_id == "gpt-4"
        assert config.api_key is None
        assert config.temperature == 0.7
        assert config.concurrent == 30
        assert config.timeout == 1200
        assert config.connect_timeout == 5.0
        assert config.read_timeout is None
        assert config.write_timeout == 300.0
        assert config.pool_timeout == 10.0
        assert config.streaming is True
        assert config.stream_idle_timeout == 300.0
        assert config.non_stream_timeout is None
        assert config.thinking == "disable"
        assert config.retry == 2
        assert config.system_proxy_enable is False

    def test_agent_config_with_all_params(self):
        """Test AgentConfig with all parameters"""
        custom_logger = logging.getLogger("test")

        config = AgentConfig(
            logger=custom_logger,
            base_url="https://api.example.com",
            api_key="test-key",
            model_id="gpt-4",
            temperature=0.5,
            concurrent=10,
            timeout=600,
            connect_timeout=3.0,
            read_timeout=120.0,
            write_timeout=30.0,
            pool_timeout=2.0,
            thinking="enable",
            retry=3,
            system_proxy_enable=True
        )
        assert config.logger == custom_logger
        assert config.base_url == "https://api.example.com"
        assert config.api_key == "test-key"
        assert config.model_id == "gpt-4"
        assert config.temperature == 0.5
        assert config.concurrent == 10
        assert config.timeout == 600
        assert config.connect_timeout == 3.0
        assert config.read_timeout == 120.0
        assert config.write_timeout == 30.0
        assert config.pool_timeout == 2.0
        assert config.thinking == "enable"
        assert config.retry == 3
        assert config.system_proxy_enable is True


class TestAgentResultError:
    """Test AgentResultError exception"""

    def test_agent_result_error_creation(self):
        """Test creating AgentResultError"""
        error = AgentResultError("Test error message")
        assert isinstance(error, ValueError)
        assert str(error) == "Test error message"

    def test_agent_result_error_inheritance(self):
        """Test AgentResultError inherits from ValueError"""
        error = AgentResultError("Error")
        assert isinstance(error, ValueError)


class TestPartialAgentResultError:
    """Test PartialAgentResultError exception"""

    def test_partial_agent_result_error_creation(self):
        """Test creating PartialAgentResultError"""
        partial_result = {"key": "value"}
        error = PartialAgentResultError("Partial result", partial_result)
        assert isinstance(error, ValueError)
        assert str(error) == "Partial result"
        assert error.partial_result == partial_result
        assert error.append_prompt is None

    def test_partial_agent_result_error_with_append_prompt(self):
        """Test PartialAgentResultError with append_prompt"""
        partial_result = {"data": [1, 2, 3]}
        append_prompt = "Please continue"
        error = PartialAgentResultError("Incomplete", partial_result, append_prompt)
        assert error.partial_result == partial_result
        assert error.append_prompt == append_prompt


class TestAgentTotalTimeout:
    @staticmethod
    def _create_agent(timeout=0.05):
        return Agent(
            AgentConfig(
                base_url="https://api.example.com",
                model_id="test-model",
                concurrent=2,
                timeout=timeout,
                streaming=False,
                retry=2,
            )
        )

    async def test_async_batch_times_out_only_the_slow_chunk(self, monkeypatch):
        agent = self._create_agent()

        async def fake_send_async(*, prompt, **kwargs):
            if prompt == "slow":
                await asyncio.sleep(10)
            return f"translated:{prompt}"

        monkeypatch.setattr(agent, "send_async", fake_send_async)

        results = await agent.send_prompts_async(
            ["fast", "slow"],
            error_result_handler=lambda prompt, logger: f"fallback:{prompt}",
        )

        assert results == ["translated:fast", "fallback:slow"]
        assert agent.unresolved_error_count == 1

    def test_sync_batch_uses_the_same_total_timeout(self, monkeypatch):
        agent = self._create_agent()

        async def fake_send_async(*, prompt, **kwargs):
            await asyncio.sleep(10)
            return f"translated:{prompt}"

        monkeypatch.setattr(agent, "send_async", fake_send_async)

        results = agent.send_prompts(
            ["slow"],
            error_result_handler=lambda prompt, logger: f"fallback:{prompt}",
        )

        assert results == ["fallback:slow"]
        assert agent.unresolved_error_count == 1


class DelayedAsyncStream(httpx.AsyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks
        self.closed = False

    async def __aiter__(self):
        for delay, chunk in self.chunks:
            await asyncio.sleep(delay)
            yield chunk

    async def aclose(self):
        self.closed = True


class TestAgentStreaming:
    @staticmethod
    def _create_agent(read_timeout=0.1):
        return Agent(
            AgentConfig(
                base_url="https://api.example.com/v1",
                model_id="test-model",
                # 流式模式不应受这个很短的非流式总时限影响。
                timeout=0.05,
                read_timeout=read_timeout,
                stream_idle_timeout=read_timeout,
                retry=0,
            )
        )

    async def test_stream_activity_rearms_idle_timeout(self):
        chunks = [
            (0.03, 'data: {"choices":[{"delta":{"content":"你"}}]}\n\n'.encode()),
            (0.03, 'data: {"choices":[{"delta":{"content":"好"}}]}\n\n'.encode()),
            (0.03, b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n'),
            (0.03, b'data: [DONE]\n\n'),
        ]
        stream = DelayedAsyncStream(chunks)
        saw_stream_flag = False

        async def handler(request):
            nonlocal saw_stream_flag
            saw_stream_flag = json.loads(request.content)["stream"]
            return httpx.Response(200, headers={"content-type": "text/event-stream"}, stream=stream)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await self._create_agent().send_async(client, "hello", retry=False)

        assert result == "你好"
        assert saw_stream_flag is True
        assert stream.closed is True

    async def test_stream_idle_timeout_aborts_and_uses_fallback(self):
        stream = DelayedAsyncStream([
            (0, b': heartbeat\n\n'),
            (0.2, b'data: [DONE]\n\n'),
        ])

        async def handler(request):
            return httpx.Response(200, headers={"content-type": "text/event-stream"}, stream=stream)

        agent = self._create_agent(read_timeout=0.03)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await agent.send_async(
                client,
                "hello",
                retry=False,
                error_result_handler=lambda prompt, logger: f"fallback:{prompt}",
            )

        assert result == "fallback:hello"
        assert stream.closed is True

    async def test_non_streaming_json_response_remains_compatible(self):
        async def handler(request):
            assert json.loads(request.content)["stream"] is True
            return httpx.Response(200, json={
                "choices": [{
                    "message": {"content": "translated"},
                    "finish_reason": "stop",
                }]
            })

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await self._create_agent().send_async(client, "hello", retry=False)

        assert result == "translated"

    async def test_rejected_stream_request_falls_back_without_api_change(self):
        payloads = []

        async def handler(request):
            payload = json.loads(request.content)
            payloads.append(payload)
            if payload.get("stream") is True:
                return httpx.Response(400, json={"error": "stream is unsupported"})
            return httpx.Response(200, json={
                "choices": [{
                    "message": {"content": "fallback translated"},
                    "finish_reason": "stop",
                }]
            })

        agent = self._create_agent()
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await agent.send_async(client, "hello", retry=False)

        assert result == "fallback translated"
        assert len(payloads) == 2
        assert payloads[0]["stream"] is True
        assert "stream" not in payloads[1]
        assert agent._streaming_disabled is True

    async def test_non_streaming_uses_independent_hard_timeout(self):
        async def handler(request):
            await asyncio.sleep(0.2)
            return httpx.Response(200, json={
                "choices": [{
                    "message": {"content": "too late"},
                    "finish_reason": "stop",
                }]
            })

        agent = Agent(AgentConfig(
            base_url="https://api.example.com/v1",
            model_id="test-model",
            streaming=False,
            timeout=2,
            non_stream_timeout=0.03,
            retry=0,
        ))
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await agent.send_async(
                client,
                "hello",
                retry=False,
                error_result_handler=lambda prompt, logger: f"fallback:{prompt}",
            )

        assert result == "fallback:hello"
