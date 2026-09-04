# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import asyncio
import codecs
import hashlib
import json
import logging
import re  # 新增：用于正则估算
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from contextvars import ContextVar
from dataclasses import dataclass, field
from threading import Lock
from typing import Literal, Callable, Any
from urllib.parse import urlparse

import httpx

from docutranslate.agents.provider import ProviderType, get_provider_by_domain
from docutranslate.agents.provider.token_counting import (
    ProviderTokenUsageParser,
    get_provider_token_usage_parser,
)
from docutranslate.agents.thinking.controller import (
    ReasoningController,
    parse_extra_body,
)
from docutranslate.config import LLM_STREAMING, NON_STREAM_TIMEOUT, STREAM_IDLE_TIMEOUT
from docutranslate.logger import global_logger
from docutranslate.utils.utils import get_httpx_proxies, mask_secrets

MAX_REQUESTS_PER_ERROR = 15
MAX_CONTINUE_FETCHES = 2  # 响应被截断时，最多继续获取的次数
SLOW_REQUEST_LOG_INTERVAL = 60.0
MAX_ERROR_BODY_LOG_LENGTH = 1000

ThinkingMode = Literal["enable", "disable", "default"]


@dataclass
class _RequestLogTrace:
    index: int
    total: int
    queued_at: float = field(default_factory=time.monotonic)
    started_at: float | None = None
    last_activity_at: float = field(default_factory=time.monotonic)
    rate_limit_wait: float = 0.0
    attempts: int = 0
    transport: str = "pending"
    phase: str = "等待并发槽"
    response_header_seconds: float | None = None
    first_data_seconds: float | None = None
    response_chunks: int = 0
    response_bytes: int = 0

    @property
    def label(self) -> str:
        return f"[分片 {self.index}/{self.total}]"


_REQUEST_LOG_TRACE: ContextVar[_RequestLogTrace | None] = ContextVar(
    "docutranslate_request_log_trace",
    default=None,
)


def _text_fingerprint(text: str) -> str:
    """Return a non-reversible identifier without logging document content."""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:12]


def _safe_error_text(value: Any, limit: int = MAX_ERROR_BODY_LOG_LENGTH) -> str:
    text = mask_secrets(str(value)).replace("\r", " ").replace("\n", " ")
    if len(text) > limit:
        return f"{text[:limit]}…(已截断，原长度 {len(text)})"
    return text


def _safe_endpoint(value: str) -> str:
    """Keep endpoint diagnostics while removing credentials and query values."""
    parsed = urlparse(value)
    hostname = parsed.hostname
    if not parsed.scheme or not hostname:
        return "<invalid-endpoint>"
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    try:
        port = f":{parsed.port}" if parsed.port is not None else ""
    except ValueError:
        return "<invalid-endpoint>"
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{hostname}{port}{path}"


def _parse_response_json(response: httpx.Response) -> dict:
    """
    解析API响应，正确处理前缀空行（如DeepSeek API在高负载时返回的空行）

    Args:
        response: httpx.Response 对象

    Returns:
        解析后的 JSON 字典

    Raises:
        json.JSONDecodeError: 如果响应无法解析为 JSON
    """
    text = response.text
    # 跳过开头的空行和空白字符，找到第一个非空白字符
    # 这可以处理 DeepSeek API 返回的前缀空行
    stripped_text = text.lstrip()
    if not stripped_text:
        raise json.JSONDecodeError("Expecting value", text, 0)
    # 从第一个非空白字符开始解析
    return json.loads(stripped_text)


def _content_to_text(content: Any) -> str:
    """将 OpenAI 兼容接口的多种 content 形态统一为字符串。"""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""

    parts = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict):
            text = item.get("text", item.get("content", ""))
            if isinstance(text, str):
                parts.append(text)
    return "".join(parts)


class _StreamingResponseAccumulator:
    """增量解析 OpenAI 兼容的 SSE/NDJSON，并聚合为原来的响应字典。"""

    def __init__(self):
        self._decoder = codecs.getincrementaldecoder("utf-8")()
        self._line_buffer = ""
        self._event_data: list[str] = []
        self._content: list[str] = []
        self._finish_reason = None
        self._usage: dict | None = None
        self._usage_key = "usage"
        self._saw_payload = False
        self.done = False

    def feed(self, chunk: bytes):
        self._feed_text(self._decoder.decode(chunk))

    def _feed_text(self, text: str):
        self._line_buffer += text
        while "\n" in self._line_buffer:
            line, self._line_buffer = self._line_buffer.split("\n", 1)
            self._handle_line(line.rstrip("\r"))

    def _handle_line(self, line: str):
        if not line:
            self._dispatch_event()
            return
        if line.startswith(":"):
            # SSE heartbeat/comment。收到原始字节时空闲计时器已经重置。
            return
        if line.startswith("data:"):
            self._event_data.append(line[5:].lstrip())
            return
        if line.startswith(("event:", "id:", "retry:")):
            return

        # 兼容部分本地 OpenAI 服务使用的 NDJSON。
        stripped = line.strip()
        if stripped.startswith("{"):
            self._consume_payload(stripped)

    def _dispatch_event(self):
        if not self._event_data:
            return
        payload = "\n".join(self._event_data)
        self._event_data.clear()
        self._consume_payload(payload)

    def _consume_payload(self, payload: str):
        if payload.strip() == "[DONE]":
            self.done = True
            return
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return
        if not isinstance(data, dict):
            return
        if data.get("error"):
            raise ValueError(f"流式响应返回错误: {data['error']}")

        self._saw_payload = True
        for usage_key in ("usage", "usageMetadata", "usage_metadata"):
            usage = data.get(usage_key)
            if isinstance(usage, dict):
                self._usage = usage
                self._usage_key = usage_key
                break

        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            return
        choice = choices[0]
        if not isinstance(choice, dict):
            return
        finish_reason = choice.get("finish_reason")
        if finish_reason is not None:
            self._finish_reason = finish_reason

        delta = choice.get("delta")
        message = choice.get("message")
        if isinstance(delta, dict):
            content = delta.get("content")
        elif isinstance(message, dict):
            content = message.get("content")
        else:
            content = choice.get("text")
        text = _content_to_text(content)
        if text:
            self._content.append(text)

    def finish(self, raw_body: bytes) -> dict:
        tail = self._decoder.decode(b"", final=True)
        if tail:
            self._feed_text(tail)
        if self._line_buffer:
            self._handle_line(self._line_buffer.rstrip("\r"))
            self._line_buffer = ""
        self._dispatch_event()

        if self._saw_payload:
            result = {
                "choices": [{
                    "message": {"content": "".join(self._content)},
                    "finish_reason": self._finish_reason,
                }]
            }
            if self._usage is not None:
                result[self._usage_key] = self._usage
            return result

        # 有些兼容服务会忽略 stream=true，直接返回普通 JSON。
        text = raw_body.decode("utf-8-sig").lstrip()
        if not text:
            raise json.JSONDecodeError("Expecting value", text, 0)
        return json.loads(text)


class AgentResultError(ValueError):
    """一个特殊的异常，用于表示结果由AI正常返回，但返回的结果有问题。该错误不计入总错误数"""

    def __init__(self, message):
        super().__init__(message)


class PartialAgentResultError(ValueError):
    """一个特殊的异常，用于表示结果不完整但包含了部分成功的数据，以便触发重试。该错误不计入总错误数"""

    def __init__(self, message, partial_result: dict, append_prompt: str = None):
        super().__init__(message)
        self.partial_result = partial_result
        self.append_prompt = append_prompt


@dataclass(kw_only=True)
class AgentConfig:
    logger: logging.Logger = global_logger
    base_url: str
    api_key: str | None = None
    model_id: str
    temperature: float = 0.7
    top_p: float = 0.9
    concurrent: int = 30
    timeout: int = 1200  # 单个分片包含限流等待、续写和全部重试的总时限（秒）
    connect_timeout: float = 5.0
    read_timeout: float | None = None  # None 时沿用 timeout，兼容旧版直接构造方式
    write_timeout: float = 300.0
    pool_timeout: float = 10.0
    thinking: ThinkingMode = "disable"
    retry: int = 2
    system_proxy_enable: bool = False
    force_json: bool = False
    rpm: int | None = None  # 每分钟请求数限制
    tpm: int | None = None  # 每分钟Token数限制
    provider: ProviderType | None = None
    progress_callback: Callable[[int,int],None]|None = None  # 进度回调 (current: int, total: int) -> None
    extra_body: str | None = None  # JSON字符串格式的额外请求体参数
    # 以下字段仅扩展内部传输策略，不改变现有公开方法和 Web/API 请求结构。
    streaming: bool = LLM_STREAMING
    stream_idle_timeout: float = STREAM_IDLE_TIMEOUT
    non_stream_timeout: float | None = NON_STREAM_TIMEOUT


class TotalErrorCounter:
    def __init__(self, logger: logging.Logger, max_errors_count=10):
        self.lock = Lock()
        self.count = 0
        self.logger = logger
        self.max_errors_count = max_errors_count

    def add(self):
        with self.lock:
            self.count += 1
            if self.count > self.max_errors_count:
                self.logger.info(f"错误响应过多")
            return self.reach_limit()

    def reach_limit(self):
        return self.count > self.max_errors_count


# --- 新增 RateLimiter 类 ---
class RateLimiter:
    """
    基于滑动窗口的速率限制器，支持 RPM 和 TPM 控制。
    同时支持 Async 和 Sync 调用。
    """

    def __init__(self, rpm: int | None, tpm: int | None):
        self.rpm = rpm
        self.tpm = tpm
        # 双端队列存储 (timestamp, value)，value对于RPM是1，对于TPM是token数量
        self.request_timestamps = deque()
        self.token_timestamps = deque()
        self.lock = Lock()  # 用于同步模式和保护共享数据

    def _cleanup_window(self, now: float):
        """清理60秒窗口之前的数据"""
        window_start = now - 60.0

        while self.request_timestamps and self.request_timestamps[0] <= window_start:
            self.request_timestamps.popleft()

        while self.token_timestamps and self.token_timestamps[0][0] <= window_start:
            self.token_timestamps.popleft()

    def _check_and_get_wait_time(self, tokens: int) -> float:
        """检查是否满足限制，返回需要等待的秒数。如果不需等待返回 0"""
        now = time.time()
        self._cleanup_window(now)

        wait_time = 0.0

        # Check RPM
        if self.rpm and len(self.request_timestamps) >= self.rpm:
            earliest = self.request_timestamps[0]
            wait_time = max(wait_time, 60 - (now - earliest))

        # Check TPM
        if self.tpm:
            current_tokens = sum(t[1] for t in self.token_timestamps)
            if current_tokens + tokens > self.tpm:
                if self.token_timestamps:
                    earliest = self.token_timestamps[0][0]
                    wait_time = max(wait_time, 60 - (now - earliest))
                else:
                    pass

        return wait_time

    def _record_usage(self, tokens: int):
        """记录使用量"""
        now = time.time()
        if self.rpm is not None:
            self.request_timestamps.append(now)
        if self.tpm is not None:
            self.token_timestamps.append((now, tokens))

    async def acquire_async(self, tokens: int = 0) -> float:
        """异步等待配额，并返回实际等待秒数。"""
        started_at = time.monotonic()
        if self.rpm is None and self.tpm is None:
            return 0.0

        while True:
            # print(f"[RateLimiter-Async] 准备获取锁...")
            with self.lock:
                # print(f"[RateLimiter-Async] 已加锁 (Checking)")

                wait_time = self._check_and_get_wait_time(tokens)
                if wait_time <= 0:
                    self._record_usage(tokens)
                    # print(f"[RateLimiter-Async] 释放锁 (成功获取配额)")
                    return time.monotonic() - started_at

                # print(f"[RateLimiter-Async] 释放锁 (需等待 {wait_time:.2f}s)")

            # 释放锁后等待
            await asyncio.sleep(wait_time + 0.1)

    def acquire_sync(self, tokens: int = 0) -> float:
        """同步等待配额（线程阻塞），并返回实际等待秒数。"""
        started_at = time.monotonic()
        if self.rpm is None and self.tpm is None:
            return 0.0

        while True:
            # print(f"[RateLimiter-Sync] 准备获取锁...")
            with self.lock:
                # print(f"[RateLimiter-Sync] 已加锁 (Checking)")

                wait_time = self._check_and_get_wait_time(tokens)
                if wait_time <= 0:
                    self._record_usage(tokens)
                    # print(f"[RateLimiter-Sync] 释放锁 (成功获取配额)")
                    return time.monotonic() - started_at

                # print(f"[RateLimiter-Sync] 释放锁 (需等待 {wait_time:.2f}s)")

            time.sleep(wait_time + 0.1)


def extract_token_info(
    response_data: dict,
    provider: ProviderType | str = "default",
    model_id: str = "",
) -> tuple[int, int, int, int, int]:
    """兼容入口：按 Provider 提取服务端返回的 Token 使用量。"""
    return get_provider_token_usage_parser(provider).parse(response_data)


class TokenCounter:
    def __init__(self, logger: logging.Logger):
        self.lock = Lock()
        self.input_tokens = 0
        self.cached_tokens = 0
        self.output_tokens = 0
        self.reasoning_tokens = 0
        self.total_tokens = 0
        self.logger = logger

    def add(
            self,
            input_tokens: int,
            cached_tokens: int,
            output_tokens: int,
            reasoning_tokens: int,
            api_total_tokens: int = 0,
    ):
        with self.lock:
            self.input_tokens += input_tokens
            self.cached_tokens += cached_tokens
            self.output_tokens += output_tokens
            self.reasoning_tokens += reasoning_tokens
            # 如果API返回了total_tokens，优先使用；否则自己计算
            if api_total_tokens > 0:
                self.total_tokens += api_total_tokens
            else:
                self.total_tokens += input_tokens + output_tokens

    def get_stats(self):
        with self.lock:
            return {
                "input_tokens": self.input_tokens,
                "cached_tokens": self.cached_tokens,
                "output_tokens": self.output_tokens,
                "reasoning_tokens": self.reasoning_tokens,
                "total_tokens": self.total_tokens,
            }

    def reset(self):
        with self.lock:
            self.input_tokens = 0
            self.cached_tokens = 0
            self.output_tokens = 0
            self.reasoning_tokens = 0
            self.total_tokens = 0


PreSendHandlerType = Callable[[str, str], tuple[str, str]]
ResultHandlerType = Callable[[str, str, logging.Logger], Any]
ErrorResultHandlerType = Callable[[str, logging.Logger], Any]


_COMPLEX_SCRIPT_PATTERN = re.compile(
    r'[\u2e80-\u9fff\u0400-\u04ff\u0600-\u06ff\u0e00-\u0e7f\u0900-\u097f]'
)


class Agent:

    def __init__(self, config: AgentConfig):
        self.baseurl = config.base_url.strip()
        if self.baseurl.endswith("/"):
            self.baseurl = self.baseurl[:-1]
        self.domain = urlparse(self.baseurl).netloc.strip()
        self.key = config.api_key.strip() if config.api_key else "xx"
        self.model_id = config.model_id.strip()
        self.system_prompt = ""
        self.temperature = config.temperature
        self.top_p = config.top_p
        self.max_concurrent = config.concurrent
        # 流式和非流式使用两套独立策略：流式仅限制连续静默时间；
        # 非流式保留硬总时限。旧 timeout/read_timeout 配置仍用于非流式。
        self.non_stream_total_timeout_seconds = (
            config.timeout if config.non_stream_timeout is None else config.non_stream_timeout
        )
        self.total_timeout_seconds = self.non_stream_total_timeout_seconds
        read_timeout = config.timeout if config.read_timeout is None else config.read_timeout
        self.timeout = httpx.Timeout(
            connect=config.connect_timeout,
            read=read_timeout,
            write=config.write_timeout,
            pool=config.pool_timeout,
        )
        self.stream_idle_timeout_seconds = config.stream_idle_timeout
        self.stream_timeout = httpx.Timeout(
            connect=config.connect_timeout,
            read=self.stream_idle_timeout_seconds,
            write=config.write_timeout,
            pool=config.pool_timeout,
        )
        self.streaming_enabled = config.streaming
        self._streaming_disabled = not config.streaming
        self.thinking = config.thinking
        self.logger = config.logger
        self.total_error_counter = TotalErrorCounter(logger=self.logger)
        self.unresolved_error_lock = Lock()
        self.unresolved_error_count = 0
        self.token_counter = TokenCounter(logger=self.logger)
        self._request_count = 0  # 记录请求数量
        self.retry = config.retry
        self.system_proxy_enable = config.system_proxy_enable
        self.progress_callback = config.progress_callback  # 进度回调

        # 新增：初始化速率限制器
        self.rate_limiter = RateLimiter(rpm=config.rpm, tpm=config.tpm)

        self.provider = config.provider if config.provider is not None else get_provider_by_domain(self.domain)
        self.token_usage_parser: ProviderTokenUsageParser = (
            get_provider_token_usage_parser(self.provider)
        )
        self.extra_body = config.extra_body
        parsed_extra_body = parse_extra_body(config.extra_body)
        self._extra_body_data = parsed_extra_body or {}
        self._extra_body_invalid = parsed_extra_body is None
        self.reasoning_controller = ReasoningController(
            provider=self.provider,
            model_id=self.model_id,
            base_url=self.baseurl,
            intent=self.thinking,
            user_extra_body=self._extra_body_data,
        )

    def _request_label(self, retry_count: int | None = None) -> str:
        trace = _REQUEST_LOG_TRACE.get()
        label = trace.label if trace is not None else "[单请求]"
        if retry_count is not None:
            return f"{label}[尝试 {retry_count + 1}/{self.retry + 1}]"
        return label

    def _log_attempt_failure(
            self,
            message: str,
            *,
            retry: bool,
            retry_count: int,
    ) -> None:
        log = self.logger.warning if retry and retry_count < self.retry else self.logger.error
        log(f"{self._request_label(retry_count)} {message}")

    async def _monitor_slow_request(self, trace: _RequestLogTrace) -> None:
        while True:
            await asyncio.sleep(SLOW_REQUEST_LOG_INTERVAL)
            now = time.monotonic()
            elapsed = now - trace.queued_at
            idle = now - trace.last_activity_at
            self.logger.info(
                f"{trace.label} 仍在处理: 阶段={trace.phase}, "
                f"累计={elapsed:.1f}s, 最近活动={idle:.1f}s前, "
                f"尝试={max(trace.attempts, 1)}, transport={trace.transport}, "
                f"chunks={trace.response_chunks}, bytes={trace.response_bytes}"
            )

    async def _request_completion_async(
            self,
            client: httpx.AsyncClient,
            data: dict,
            headers: dict,
    ) -> dict:
        try:
            return await self._request_completion_async_once(client, data, headers)
        except httpx.HTTPStatusError as error:
            fallback = self.reasoning_controller.fallback_request(data, error)
            if fallback is None:
                raise
            fallback_data, warning = fallback
            self.logger.warning(warning)
            return await self._request_completion_async_once(
                client, fallback_data, headers
            )

    async def _request_completion_async_once(
            self,
            client: httpx.AsyncClient,
            data: dict,
            headers: dict,
    ) -> dict:
        """请求一次 completion；优先流式，明确不支持时自动兼容非流式。"""
        trace = _REQUEST_LOG_TRACE.get()
        if self._streaming_disabled:
            return await self._request_non_stream_async(client, data, headers)

        stream_data = dict(data)
        stream_data["stream"] = True
        request_started_at = time.monotonic()
        if trace is not None:
            trace.transport = "stream"
            trace.phase = "等待流式响应头"
            trace.last_activity_at = request_started_at
        try:
            async with client.stream(
                    "POST",
                    f"{self.baseurl}/chat/completions",
                    json=stream_data,
                    headers=headers,
                    timeout=self.stream_timeout,
            ) as response:
                if trace is not None:
                    now = time.monotonic()
                    trace.response_header_seconds = now - request_started_at
                    trace.phase = "读取流式响应"
                    trace.last_activity_at = now
                if response.is_error:
                    await response.aread()
                response.raise_for_status()
                if response.is_stream_consumed:
                    accumulator = _StreamingResponseAccumulator()
                    accumulator.feed(response.content)
                    if trace is not None:
                        trace.first_data_seconds = time.monotonic() - request_started_at
                        trace.response_chunks += 1
                        trace.response_bytes += len(response.content)
                        trace.last_activity_at = time.monotonic()
                    return accumulator.finish(response.content)
                accumulator = _StreamingResponseAccumulator()
                raw_body = bytearray()
                # HTTPX 的 raw 迭代器会绕过 Content-Encoding 解码，导致 gzip
                # 压缩的 SSE 被直接当作 UTF-8 文本解析。bytes 迭代器会保留
                # 流式读取，同时按响应头增量解压 gzip/deflate 等编码。
                iterator = response.aiter_bytes()
                saw_data = False
                while not accumulator.done:
                    try:
                        chunk = await asyncio.wait_for(
                            anext(iterator), timeout=self.stream_idle_timeout_seconds
                        )
                    except StopAsyncIteration:
                        break
                    except TimeoutError as exc:
                        raise httpx.ReadTimeout(
                            f"流式响应连续 {self.stream_idle_timeout_seconds} 秒无活动",
                            request=response.request,
                        ) from exc
                    if not chunk:
                        continue
                    now = time.monotonic()
                    if trace is not None:
                        if not saw_data:
                            trace.first_data_seconds = now - request_started_at
                        trace.response_chunks += 1
                        trace.response_bytes += len(chunk)
                        trace.last_activity_at = now
                    saw_data = True
                    raw_body.extend(chunk)
                    accumulator.feed(chunk)
                return accumulator.finish(bytes(raw_body))
        except httpx.HTTPStatusError as stream_error:
            if self.reasoning_controller.is_parameter_compatibility_error(
                stream_error, data
            ):
                raise
            # 仅对常见的“不支持 stream 参数/端点”状态进行一次非流式兼容尝试。
            if stream_error.response.status_code not in {400, 404, 405, 415, 422, 501}:
                raise
            self.logger.warning(
                f"当前 LLM 接口拒绝流式请求 ({stream_error.response.status_code})，"
                "尝试兼容非流式响应。"
            )
            self._streaming_disabled = True
            result = await self._request_non_stream_async(client, data, headers)
            return result

    async def _request_non_stream_async(
            self,
            client: httpx.AsyncClient,
            data: dict,
            headers: dict,
    ) -> dict:
        """执行非流式请求，并施加与流式空闲窗口独立的硬总时限。"""
        trace = _REQUEST_LOG_TRACE.get()
        request_started_at = time.monotonic()
        if trace is not None:
            trace.transport = "non-stream"
            trace.phase = "等待非流式完整响应"
            trace.last_activity_at = request_started_at
        total_timeout = asyncio.timeout(self.non_stream_total_timeout_seconds)
        try:
            async with total_timeout:
                response = await client.post(
                    f"{self.baseurl}/chat/completions",
                    json=data,
                    headers=headers,
                    timeout=self.timeout,
                )
                if trace is not None:
                    now = time.monotonic()
                    trace.response_header_seconds = now - request_started_at
                    trace.first_data_seconds = now - request_started_at
                    trace.response_chunks += 1
                    trace.response_bytes += len(response.content)
                    trace.last_activity_at = now
                    trace.phase = "解析非流式响应"
        except TimeoutError as exc:
            if not total_timeout.expired():
                raise
            raise httpx.ReadTimeout(
                f"非流式请求超过硬总时限 {self.non_stream_total_timeout_seconds} 秒"
            ) from exc
        response.raise_for_status()
        return _parse_response_json(response)

    def _request_completion_sync(
            self,
            client: httpx.Client,
            data: dict,
            headers: dict,
    ) -> dict:
        try:
            return self._request_completion_sync_once(client, data, headers)
        except httpx.HTTPStatusError as error:
            fallback = self.reasoning_controller.fallback_request(data, error)
            if fallback is None:
                raise
            fallback_data, warning = fallback
            self.logger.warning(warning)
            return self._request_completion_sync_once(client, fallback_data, headers)

    def _request_completion_sync_once(
            self,
            client: httpx.Client,
            data: dict,
            headers: dict,
    ) -> dict:
        """同步入口的流式兼容实现；实际 socket 空闲检测由 HTTPX read timeout 完成。"""
        if self._streaming_disabled:
            response = client.post(
                f"{self.baseurl}/chat/completions",
                json=data,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return _parse_response_json(response)

        stream_data = dict(data)
        stream_data["stream"] = True
        try:
            with client.stream(
                    "POST",
                    f"{self.baseurl}/chat/completions",
                    json=stream_data,
                    headers=headers,
                    timeout=self.stream_timeout,
            ) as response:
                if response.is_error:
                    response.read()
                response.raise_for_status()
                if response.is_stream_consumed:
                    accumulator = _StreamingResponseAccumulator()
                    accumulator.feed(response.content)
                    return accumulator.finish(response.content)
                accumulator = _StreamingResponseAccumulator()
                raw_body = bytearray()
                # 与异步路径一致，让 HTTPX 在解析 SSE 前增量处理
                # Content-Encoding（尤其是部分网关默认启用的 gzip）。
                for chunk in response.iter_bytes():
                    if not chunk:
                        continue
                    raw_body.extend(chunk)
                    accumulator.feed(chunk)
                    if accumulator.done:
                        break
                return accumulator.finish(bytes(raw_body))
        except httpx.HTTPStatusError as stream_error:
            if self.reasoning_controller.is_parameter_compatibility_error(
                stream_error, data
            ):
                raise
            if stream_error.response.status_code not in {400, 404, 405, 415, 422, 501}:
                raise
            self.logger.warning(
                f"当前 LLM 接口拒绝流式请求 ({stream_error.response.status_code})，"
                "尝试兼容非流式响应。"
            )
            self._streaming_disabled = True
            response = client.post(
                f"{self.baseurl}/chat/completions",
                json=data,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = _parse_response_json(response)
            return result

    def _estimate_tokens(self, text: str) -> int:
        """保留原有的发送前 TPM 估算方式。"""
        if not text:
            return 0
        complex_char_count = len(_COMPLEX_SCRIPT_PATTERN.findall(text))
        simple_char_count = len(text) - complex_char_count
        estimated = (complex_char_count * 1.0) + (simple_char_count * 0.3)
        return int(estimated) + 1

    def _sanitize_result(self, text: str) -> str:
        """
        清理响应内容：如果内容以 <think>...</think> 开头，移除该部分。
        使用 DOTALL 模式以匹配跨行的 thinking 内容。
        """
        if not text:
            return text
        # 匹配开头的 <think> 标签块，允许标签前后有空白字符
        # .*? 非贪婪匹配，确保只匹配第一个闭合标签
        return re.sub(r'^\s*<think>.*?</think>', '', text, flags=re.DOTALL)

    def get_continue_prompt(self, accumulated_result: str, prompt: str) -> str:
        """
        获取继续获取时的提示词。
        子类可以重写此方法来自定义继续获取的行为。

        默认行为：直接拼接内容，让模型继续输出。
        """
        return f"{prompt}\n\n[系统提示：请继续完成之前的响应。之前已输出内容为：\n---\n{accumulated_result}\n---\n请从中断处继续输出剩余内容。]"

    def merge_continue_result(self, accumulated_result: str, additional_result: str) -> str:
        """
        合并继续获取的结果。
        子类可以重写此方法来处理追加模式的数组合并。

        默认行为：直接拼接字符串。
        """
        return accumulated_result + additional_result

    def _add_thinking_mode(self, data: dict):
        """Apply semantic thinking intent through the provider/model adapter."""
        warning = self.reasoning_controller.apply(data)
        if warning:
            self.logger.warning(warning)

    def _prepare_request_data(
            self, prompt: str, system_prompt: str, temperature=None, top_p=None, json_format=False
    ):
        if temperature is None:
            temperature = self.temperature
        if top_p is None:
            top_p = self.top_p
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.key}",
        }
        data = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "top_p": top_p,
        }

        # 先应用平台适配。default 通常不发送控制字段，但适配器可以加入
        # reasoning_split 这类仅影响响应形态、不改变模型思考行为的参数。
        self._add_thinking_mode(data)

        # 再应用用户的 extra_body（用户配置优先，可以覆盖思考模式）
        if self.extra_body and self.extra_body.strip():
            if not self._extra_body_invalid:
                data.update(self._extra_body_data)
            else:
                self.logger.warning(
                    "无法解析 extra_body JSON: "
                    f"chars={len(self.extra_body)}, id={_text_fingerprint(self.extra_body)}"
                )

        if json_format:
            data["response_format"] = {"type": "json_object"}

        return headers, data

    async def _continue_fetch_async(
            self,
            client: httpx.AsyncClient,
            prompt: str,
            system_prompt: str,
            force_json: bool,
            pre_send_handler: PreSendHandlerType,
            result_handler: ResultHandlerType,
            error_result_handler: ErrorResultHandlerType,
            retry_count: int,
            accumulated_result: str = "",
            continue_count: int = 0,
    ) -> Any:
        """
        当 finish_reason 为 length 时，继续获取剩余内容。
        注意：很多 API 并不支持这种"继续获取"模式，可能直接返回 stop 或不返回 length。
        本方法具有退化机制：如果 API 不支持继续获取，会返回已累计的结果。
        最多继续获取 MAX_CONTINUE_FETCHES 次，防止无限循环。
        """
        if continue_count >= MAX_CONTINUE_FETCHES:
            self.logger.warning(
                f"已达到最大继续获取次数 ({MAX_CONTINUE_FETCHES})，返回已累计结果 ({len(accumulated_result)} 字符)")
            # 移除可能存在的 <think> 块
            accumulated_result = self._sanitize_result(accumulated_result)
            return (
                accumulated_result
                if result_handler is None
                else result_handler(accumulated_result, prompt, self.logger)
            )

        self.logger.info(
            f"继续获取剩余内容 (已累计 {len(accumulated_result)} 字符, 第 {continue_count + 1}/{MAX_CONTINUE_FETCHES} 次)...")

        # 构造继续请求的提示
        # 调用子类的 get_continue_prompt 方法，允许子类自定义继续获取的行为
        continue_prompt = self.get_continue_prompt(accumulated_result, prompt)

        if pre_send_handler:
            system_prompt, continue_prompt = pre_send_handler(system_prompt, continue_prompt)

        # 速率限制检查
        estimated_tokens = self._estimate_tokens(system_prompt) + self._estimate_tokens(continue_prompt)
        await self.rate_limiter.acquire_async(tokens=estimated_tokens)

        headers, data = self._prepare_request_data(continue_prompt, system_prompt, json_format=force_json)

        try:
            response_data = await self._request_completion_async(client, data, headers)

            # 安全提取 choices 和 content
            choices = response_data.get("choices", [])
            if not choices:
                raise ValueError("API响应格式错误：缺少 choices 字段")

            choice = choices[0]
            finish_reason = choice.get("finish_reason", None)
            message = choice.get("message", {})
            additional_result = message.get("content", "")

            input_tokens, cached_tokens, output_tokens, reasoning_tokens, api_total_tokens = (
                self.token_usage_parser.parse(response_data)
            )
            self.token_counter.add(input_tokens, cached_tokens, output_tokens, reasoning_tokens, api_total_tokens)

            # 累加结果（使用 merge_continue_result 方法处理追加模式的合并）
            accumulated_result = self.merge_continue_result(accumulated_result, additional_result)

            # 如果仍然是 length，继续获取（限制最大轮数防止无限循环）
            if finish_reason == "length":
                return await self._continue_fetch_async(
                    client=client,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    force_json=force_json,
                    pre_send_handler=pre_send_handler,
                    result_handler=result_handler,
                    error_result_handler=error_result_handler,
                    retry_count=retry_count,
                    accumulated_result=accumulated_result,
                    continue_count=continue_count + 1,
                )

            # 非 length 结束，返回累加结果
            try:
                # 最终清理结果
                accumulated_result = self._sanitize_result(accumulated_result)
                return (
                    accumulated_result
                    if result_handler is None
                    else result_handler(accumulated_result, prompt, self.logger)
                )
            except PartialAgentResultError as e:
                # 继续获取成功但结果部分不完整，返回已合并的部分结果
                self.logger.warning(f"继续获取完成但结果部分不完整: {e}")
                if e.partial_result:
                    return e.partial_result
                # 如果没有部分结果，尝试从已获取的内容中解析
                return accumulated_result
            except AgentResultError as e:
                # 继续获取成功但结果完全无效
                self.logger.warning(f"继续获取完成但结果无效: {e}")
                return accumulated_result

        except (httpx.HTTPStatusError, httpx.RequestError, KeyError, IndexError, ValueError) as e:
            self.logger.error(f"继续获取内容失败: {repr(e)}")
            # 退化：返回已获取的部分结果，而不是报错
            if accumulated_result:
                self.logger.warning(f"API不支持继续获取，返回已获取的部分结果 ({len(accumulated_result)} 字符)")
                # 即使是部分结果，也尝试清理一下
                accumulated_result = self._sanitize_result(accumulated_result)
                return (
                    accumulated_result
                    if result_handler is None
                    else result_handler(accumulated_result, prompt, self.logger)
                )
            # 如果没有部分结果，调用错误处理器
            return (
                prompt
                if error_result_handler is None
                else error_result_handler(prompt, self.logger)
            )

    async def send_async(
            self,
            client: httpx.AsyncClient,
            prompt: str,
            system_prompt: None | str = None,
            retry=True,
            retry_count=0,
            force_json=False,
            pre_send_handler: PreSendHandlerType = None,
            result_handler: ResultHandlerType = None,
            error_result_handler: ErrorResultHandlerType = None,
            best_partial_result: dict | None = None,
    ) -> Any:
        if system_prompt is None:
            system_prompt = self.system_prompt
        if pre_send_handler:
            system_prompt, prompt = pre_send_handler(system_prompt, prompt)

        # 新增：速率限制检查
        # 计算估算的 tokens (system + user)
        estimated_tokens = self._estimate_tokens(system_prompt) + self._estimate_tokens(prompt)
        # 等待配额
        trace = _REQUEST_LOG_TRACE.get()
        if trace is not None:
            trace.attempts = max(trace.attempts, retry_count + 1)
            trace.phase = "等待 RPM/TPM 配额"
            trace.last_activity_at = time.monotonic()
        rate_limit_wait = await self.rate_limiter.acquire_async(tokens=estimated_tokens)
        if trace is not None:
            trace.rate_limit_wait += rate_limit_wait
            trace.phase = "发送 LLM 请求"
            trace.last_activity_at = time.monotonic()

        headers, data = self._prepare_request_data(prompt, system_prompt, json_format=force_json)
        should_retry = False
        is_hard_error = False
        current_partial_result = None
        input_tokens = 0
        output_tokens = 0
        try:
            response_data = await self._request_completion_async(client, data, headers)

            # 检查 finish_reason
            choices = response_data.get("choices", [])
            if not choices:
                raise ValueError("API响应格式错误：缺少 choices 字段")

            finish_reason = choices[0].get("finish_reason", None)
            result = choices[0].get("message", {}).get("content", "")

            # 处理不同的 finish_reason
            if finish_reason == "stop":
                # 正常结束
                pass
            elif finish_reason == "length":
                # 长度限制，尝试继续获取
                self.logger.warning(
                    f"{self._request_label(retry_count)} 响应因长度限制被截断，尝试继续获取"
                )
                # 注意：这里传入原始result，清理工作在 _continue_fetch_async 最终返回时统一处理
                return await self._continue_fetch_async(
                    client=client,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    force_json=force_json,
                    pre_send_handler=pre_send_handler,
                    result_handler=result_handler,
                    error_result_handler=error_result_handler,
                    retry_count=retry_count,
                    accumulated_result=result,
                )
            elif finish_reason in ("tool_calls", "function_call"):
                # 工具调用场景，当前代码可能不支持，直接返回已获取结果
                self.logger.warning(
                    f"{self._request_label(retry_count)} finish_reason={finish_reason}，"
                    "当前不支持工具调用，返回已获取内容"
                )
                result = self._sanitize_result(result)
                return result if result else (
                    prompt if error_result_handler is None
                    else error_result_handler(prompt, self.logger)
                )
            elif finish_reason == "content_filter":
                # 内容被过滤
                self.logger.error(f"{self._request_label(retry_count)} 响应内容被过滤")
                raise ValueError("内容被过滤")
            elif finish_reason is None:
                # 某些 API 可能不返回 finish_reason，将其视为正常结束
                self.logger.debug(
                    f"{self._request_label(retry_count)} API未返回 finish_reason，视为正常结束"
                )
            else:
                # 其他未知的 finish_reason，记录警告并返回结果
                self.logger.warning(
                    f"{self._request_label(retry_count)} 未知 finish_reason={finish_reason}，"
                    "返回已获取内容"
                )

            input_tokens, cached_tokens, output_tokens, reasoning_tokens, api_total_tokens = (
                self.token_usage_parser.parse(response_data)
            )

            self.token_counter.add(
                input_tokens, cached_tokens, output_tokens, reasoning_tokens, api_total_tokens
            )

            if retry_count > 0:
                self.logger.info(f"{self._request_label(retry_count)} 重试成功")

            # 清理 <think> 标签后再处理结果
            result = self._sanitize_result(result)

            return (
                result
                if result_handler is None
                else result_handler(result, prompt, self.logger)
            )

        except AgentResultError as e:
            self._log_attempt_failure(
                f"AI返回结果有误: {_safe_error_text(e)}",
                retry=retry,
                retry_count=retry_count,
            )
            should_retry = True
        except PartialAgentResultError as e:
            self._log_attempt_failure(
                f"收到部分返回结果: {_safe_error_text(e)}",
                retry=retry,
                retry_count=retry_count,
            )
            current_partial_result = e.partial_result
            should_retry = True
            if e.append_prompt:
                prompt += e.append_prompt

        except httpx.HTTPStatusError as e:
            request_id = e.response.headers.get("x-request-id", "-")
            self._log_attempt_failure(
                f"LLM HTTP状态错误: status={e.response.status_code}, "
                f"request_id={request_id}, body={_safe_error_text(e.response.text)}",
                retry=retry,
                retry_count=retry_count,
            )
            should_retry = True
            is_hard_error = True
            # 如果是因为 Rate Limit (429) 错误，最好在这里多睡一会儿，虽然我们有了本地 Limiter
            if e.response.status_code == 429:
                self.logger.info(f"{self._request_label(retry_count)} 触发限流，等待 5.0s")
                await asyncio.sleep(5)

        except httpx.RequestError as e:
            if isinstance(e, httpx.TimeoutException):
                detail = _safe_error_text(e)
                if "流式响应连续" in detail:
                    message = f"流式空闲超时: {detail}"
                elif "非流式请求超过硬总时限" in detail:
                    message = f"非流式硬总超时: {detail}"
                else:
                    message = f"网络阶段超时: {type(e).__name__}: {detail}"
            elif isinstance(e, httpx.ReadError):
                message = (
                    f"读取响应失败: {type(e).__name__}: {_safe_error_text(e)} "
                    "(服务器可能关闭连接或网络中断)"
                )
            elif isinstance(e, httpx.ConnectError):
                message = (
                    f"连接失败: {type(e).__name__}: {_safe_error_text(e)} "
                    "(请检查网络或 base_url)"
                )
            elif isinstance(e, httpx.WriteError):
                message = f"发送请求数据失败: {type(e).__name__}: {_safe_error_text(e)}"
            else:
                message = f"网络请求错误: {type(e).__name__}: {_safe_error_text(e)}"
            self._log_attempt_failure(
                message,
                retry=retry,
                retry_count=retry_count,
            )
            should_retry = True
            is_hard_error = True
        except (KeyError, IndexError, ValueError, json.JSONDecodeError) as e:
            self._log_attempt_failure(
                f"LLM响应格式或值错误: {_safe_error_text(repr(e))}",
                retry=retry,
                retry_count=retry_count,
            )
            should_retry = True
            is_hard_error = True

        if current_partial_result:
            best_partial_result = current_partial_result

        if should_retry and retry and retry_count < self.retry:
            if is_hard_error:
                if retry_count == 0:
                    if self.total_error_counter.add():
                        self.logger.error("错误次数过多，已达到上限，不再重试。")
                        with self.unresolved_error_lock:
                            self.unresolved_error_count += 1
                        return (
                            best_partial_result
                            if best_partial_result
                            else (
                                prompt
                                if error_result_handler is None
                                else error_result_handler(prompt, self.logger)
                            )
                        )
                elif self.total_error_counter.reach_limit():
                    self.logger.error("错误次数过多，已达到上限，不再为该请求重试。")
                    with self.unresolved_error_lock:
                        self.unresolved_error_count += 1
                    return (
                        best_partial_result
                        if best_partial_result
                        else (
                            prompt
                            if error_result_handler is None
                            else error_result_handler(prompt, self.logger)
                        )
                    )

            # 指数退避
            retry_delay = 0.5 * (2 ** retry_count)
            self.logger.info(
                f"{self._request_label(retry_count)} 将在 {retry_delay:.1f}s 后重试"
            )
            await asyncio.sleep(retry_delay)
            return await self.send_async(
                client,
                prompt,
                system_prompt,
                retry=True,
                retry_count=retry_count + 1,
                force_json=force_json,
                pre_send_handler=pre_send_handler,
                result_handler=result_handler,
                error_result_handler=error_result_handler,
                best_partial_result=best_partial_result,
            )
        else:
            if should_retry:
                self.logger.error(f"{self._request_label(retry_count)} 所有尝试均失败")
                with self.unresolved_error_lock:
                    self.unresolved_error_count += 1

            if best_partial_result:
                self.logger.info(
                    f"{self._request_label(retry_count)} 存在部分翻译结果，将使用该结果"
                )
                return best_partial_result

            return (
                prompt
                if error_result_handler is None
                else error_result_handler(prompt, self.logger)
            )

    async def send_prompts_async(
            self,
            prompts: list[str],
            system_prompt: str | None = None,
            max_concurrent: int | None = None,
            force_json=False,
            pre_send_handler: PreSendHandlerType = None,
            result_handler: ResultHandlerType = None,
            error_result_handler: ErrorResultHandlerType = None,
    ) -> list[Any]:
        max_concurrent = (
            self.max_concurrent if max_concurrent is None else max_concurrent
        )
        total = len(prompts)
        rpm_info = f", RPM:{self.rate_limiter.rpm}" if self.rate_limiter.rpm else ""
        tpm_info = f", TPM:{self.rate_limiter.tpm}" if self.rate_limiter.tpm else ""
        transport_mode = "non-stream" if self._streaming_disabled else "stream"

        self.logger.info(
            f"provider:{self.provider},base-url:{_safe_endpoint(self.baseurl)},model-id:{self.model_id},concurrent:{max_concurrent}{rpm_info}{tpm_info},temperature:{self.temperature},"
            f"transport:{transport_mode},timeouts(stream-idle:{self.stream_idle_timeout_seconds}s,stream-total:none,"
            f"non-stream-total:{self.non_stream_total_timeout_seconds}s,non-stream-read:{self.timeout.read}s,"
            f"connect:{self.timeout.connect}s,write:{self.timeout.write}s,pool:{self.timeout.pool}s),"
            f"system_proxy:{self.system_proxy_enable},json_output:{force_json}"
        )
        self.logger.info(f"预计发送{total}个请求")

        self.total_error_counter.max_errors_count = (
                len(prompts) // MAX_REQUESTS_PER_ERROR
        )

        self.unresolved_error_count = 0
        self.token_counter.reset()
        self._request_count = len(prompts)  # 记录请求数量

        count = 0
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = []

        proxies = get_httpx_proxies(asyn=True) if self.system_proxy_enable else None

        limits = httpx.Limits(
            max_connections=self.max_concurrent * 2,
            max_keepalive_connections=self.max_concurrent,
        )

        async with httpx.AsyncClient(
                trust_env=False, mounts=proxies, verify=False, limits=limits
        ) as client:
            async def send_with_semaphore(p_text: str, prompt_index: int):
                nonlocal count
                trace = _RequestLogTrace(index=prompt_index, total=total)
                context_token = _REQUEST_LOG_TRACE.set(trace)
                monitor_task = asyncio.create_task(self._monitor_slow_request(trace))
                try:
                    async with semaphore:
                        trace.started_at = time.monotonic()
                        trace.last_activity_at = trace.started_at
                        trace.phase = "准备请求"
                        queue_wait = trace.started_at - trace.queued_at
                        prompt_estimate = self._estimate_tokens(p_text)
                        self.logger.info(
                            f"{trace.label} 开始: id={_text_fingerprint(p_text)}, "
                            f"chars={len(p_text)}, estimated_tokens={prompt_estimate}, "
                            f"queue_wait={queue_wait:.2f}s"
                        )

                        # 注意：我们在 semaphore 内部调用 send_async。
                        # 并发槽与 RPM/TPM 等待分别计时，便于判断慢在哪一层。
                        async def perform_send():
                            return await self.send_async(
                                client=client,
                                prompt=p_text,
                                system_prompt=system_prompt,
                                force_json=force_json,
                                pre_send_handler=pre_send_handler,
                                result_handler=result_handler,
                                error_result_handler=error_result_handler,
                            )

                        if self._streaming_disabled:
                            total_timeout = asyncio.timeout(
                                self.non_stream_total_timeout_seconds
                            )
                            try:
                                async with total_timeout:
                                    result = await perform_send()
                            except TimeoutError:
                                if not total_timeout.expired():
                                    raise
                                self.logger.error(
                                    f"{trace.label} 非流式分片硬总超时: "
                                    f"limit={self.non_stream_total_timeout_seconds}s，"
                                    "已终止并使用降级结果"
                                )
                                with self.unresolved_error_lock:
                                    self.unresolved_error_count += 1
                                result = (
                                    p_text
                                    if error_result_handler is None
                                    else error_result_handler(p_text, self.logger)
                                )
                        else:
                            # 流式请求没有墙钟总时限，只由滑动空闲窗口判定。
                            result = await perform_send()

                    count += 1
                    completed_at = time.monotonic()
                    trace.phase = "完成"
                    trace.last_activity_at = completed_at
                    total_elapsed = completed_at - trace.queued_at
                    queue_wait = (trace.started_at or trace.queued_at) - trace.queued_at
                    first_data = (
                        f"{trace.first_data_seconds:.2f}s"
                        if trace.first_data_seconds is not None
                        else "n/a"
                    )
                    response_headers = (
                        f"{trace.response_header_seconds:.2f}s"
                        if trace.response_header_seconds is not None
                        else "n/a"
                    )
                    self.logger.info(
                        f"{trace.label} 完成: progress={count}/{total}, "
                        f"total={total_elapsed:.2f}s, queue={queue_wait:.2f}s, "
                        f"rate_limit={trace.rate_limit_wait:.2f}s, "
                        f"headers={response_headers}, first_data={first_data}, "
                        f"attempts={max(trace.attempts, 1)}, "
                        f"transport={trace.transport}, chunks={trace.response_chunks}, "
                        f"bytes={trace.response_bytes}"
                    )
                    if self.progress_callback:
                        self.progress_callback(count, total)
                    return result
                except asyncio.CancelledError:
                    self.logger.info(f"{trace.label} 已取消")
                    raise
                except Exception as exc:
                    elapsed = time.monotonic() - trace.queued_at
                    self.logger.error(
                        f"{trace.label} 异常结束: elapsed={elapsed:.2f}s, "
                        f"type={type(exc).__name__}, detail={_safe_error_text(exc)}"
                    )
                    raise
                finally:
                    monitor_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await monitor_task
                    _REQUEST_LOG_TRACE.reset(context_token)

            results: list[Any] = [None] * total

            async def send_and_store(p_text: str, prompt_index: int):
                results[prompt_index - 1] = await send_with_semaphore(
                    p_text, prompt_index
                )

            # DeepSeek 的自动上下文缓存需要先观察到不同请求间的共同前缀。
            # 三个及以上分片时顺序完成前两个请求，再并发发送余下分片，
            # 让后续请求更可能复用刚持久化的稳定 prompt 前缀。
            warmup_count = 2 if self.provider == "deepseek" and total >= 3 else 0
            if warmup_count:
                self.logger.info("DeepSeek缓存预热: 顺序处理前2个分片")
                for prompt_index in range(1, warmup_count + 1):
                    await send_and_store(prompts[prompt_index - 1], prompt_index)

            for prompt_index, p_text in enumerate(
                    prompts[warmup_count:], start=warmup_count + 1
            ):
                task = asyncio.create_task(send_and_store(p_text, prompt_index))
                tasks.append(task)

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=False)

            self.logger.info(
                f"所有请求处理完毕: requests={total}, "
                f"unresolved_errors={self.unresolved_error_count}"
            )

            token_stats = self.token_counter.get_stats()
            cache_hit_rate = (
                token_stats["cached_tokens"] / token_stats["input_tokens"]
                if token_stats["input_tokens"] > 0
                else 0.0
            )
            self.logger.info(
                f"Token使用统计: input={token_stats['input_tokens']}, "
                f"cached={token_stats['cached_tokens']}, cache_hit_rate={cache_hit_rate:.1%}, "
                f"output={token_stats['output_tokens']}, "
                f"reasoning={token_stats['reasoning_tokens']}, "
                f"total={token_stats['total_tokens']}"
            )

            return results

    def _continue_fetch(
            self,
            client: httpx.Client,
            prompt: str,
            system_prompt: str,
            force_json: bool,
            pre_send_handler,
            result_handler,
            error_result_handler,
            retry_count: int,
            accumulated_result: str = "",
            continue_count: int = 0,
    ) -> Any:
        """
        当 finish_reason 为 length 时，继续获取剩余内容（同步版本）。
        注意：很多 API 并不支持这种"继续获取"模式，可能直接返回 stop 或不返回 length。
        本方法具有退化机制：如果 API 不支持继续获取，会返回已累计的结果。
        最多继续获取 MAX_CONTINUE_FETCHES 次，防止无限循环。
        """
        if continue_count >= MAX_CONTINUE_FETCHES:
            self.logger.warning(
                f"已达到最大继续获取次数 ({MAX_CONTINUE_FETCHES})，返回已累计结果 ({len(accumulated_result)} 字符)")
            # 清理
            accumulated_result = self._sanitize_result(accumulated_result)
            return (
                accumulated_result
                if result_handler is None
                else result_handler(accumulated_result, prompt, self.logger)
            )

        self.logger.info(
            f"继续获取剩余内容 (已累计 {len(accumulated_result)} 字符, 第 {continue_count + 1}/{MAX_CONTINUE_FETCHES} 次)...")

        # 构造继续请求的提示
        # 调用子类的 get_continue_prompt 方法，允许子类自定义继续获取的行为
        continue_prompt = self.get_continue_prompt(accumulated_result, prompt)

        if pre_send_handler:
            system_prompt, continue_prompt = pre_send_handler(system_prompt, continue_prompt)

        estimated_tokens = self._estimate_tokens(system_prompt) + self._estimate_tokens(continue_prompt)
        self.rate_limiter.acquire_sync(tokens=estimated_tokens)

        headers, data = self._prepare_request_data(continue_prompt, system_prompt, json_format=force_json)

        try:
            response_data = self._request_completion_sync(client, data, headers)

            # 安全提取 choices 和 content
            choices = response_data.get("choices", [])
            if not choices:
                raise ValueError("API响应格式错误：缺少 choices 字段")

            choice = choices[0]
            finish_reason = choice.get("finish_reason", None)
            message = choice.get("message", {})
            additional_result = message.get("content", "")

            input_tokens, cached_tokens, output_tokens, reasoning_tokens, api_total_tokens = (
                self.token_usage_parser.parse(response_data)
            )
            self.token_counter.add(input_tokens, cached_tokens, output_tokens, reasoning_tokens, api_total_tokens)

            # 累加结果（使用 merge_continue_result 方法处理追加模式的合并）
            accumulated_result = self.merge_continue_result(accumulated_result, additional_result)

            if finish_reason == "length":
                return self._continue_fetch(
                    client=client,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    force_json=force_json,
                    pre_send_handler=pre_send_handler,
                    result_handler=result_handler,
                    error_result_handler=error_result_handler,
                    retry_count=retry_count,
                    accumulated_result=accumulated_result,
                    continue_count=continue_count + 1,
                )

            # 非 length 结束，返回累加结果
            try:
                # 最终清理结果
                accumulated_result = self._sanitize_result(accumulated_result)
                return (
                    accumulated_result
                    if result_handler is None
                    else result_handler(accumulated_result, prompt, self.logger)
                )
            except PartialAgentResultError as e:
                # 继续获取成功但结果部分不完整，返回已合并的部分结果
                self.logger.warning(f"继续获取完成但结果部分不完整: {e}")
                if e.partial_result:
                    return e.partial_result
                # 如果没有部分结果，尝试从已获取的内容中解析
                return accumulated_result
            except AgentResultError as e:
                # 继续获取成功但结果完全无效
                self.logger.warning(f"继续获取完成但结果无效: {e}")
                return accumulated_result

        except (httpx.HTTPStatusError, httpx.RequestError, KeyError, IndexError, ValueError) as e:
            self.logger.error(f"继续获取内容失败: {repr(e)}")
            # 退化：返回已获取的部分结果，而不是报错
            if accumulated_result:
                self.logger.warning(f"API不支持继续获取，返回已获取的部分结果 ({len(accumulated_result)} 字符)")
                accumulated_result = self._sanitize_result(accumulated_result)
                return (
                    accumulated_result
                    if result_handler is None
                    else result_handler(accumulated_result, prompt, self.logger)
                )
            return (
                prompt
                if error_result_handler is None
                else error_result_handler(prompt, self.logger)
            )

    def send(
            self,
            client: httpx.Client,
            prompt: str,
            system_prompt: None | str = None,
            retry=True,
            retry_count=0,
            force_json=False,
            pre_send_handler=None,
            result_handler=None,
            error_result_handler=None,
            best_partial_result: dict | None = None,
    ) -> Any:
        if system_prompt is None:
            system_prompt = self.system_prompt
        if pre_send_handler:
            system_prompt, prompt = pre_send_handler(system_prompt, prompt)

        # 新增：同步环境下的速率限制
        estimated_tokens = self._estimate_tokens(system_prompt) + self._estimate_tokens(prompt)
        trace = _REQUEST_LOG_TRACE.get()
        if trace is not None:
            trace.attempts = max(trace.attempts, retry_count + 1)
            trace.phase = "等待 RPM/TPM 配额"
        rate_limit_wait = self.rate_limiter.acquire_sync(tokens=estimated_tokens)
        if trace is not None:
            trace.rate_limit_wait += rate_limit_wait
            trace.phase = "发送 LLM 请求"
            trace.last_activity_at = time.monotonic()

        headers, data = self._prepare_request_data(prompt, system_prompt, json_format=force_json)
        should_retry = False
        is_hard_error = False
        current_partial_result = None

        try:
            response_data = self._request_completion_sync(client, data, headers)

            # 检查 finish_reason
            choices = response_data.get("choices", [])
            if not choices:
                raise ValueError("API响应格式错误：缺少 choices 字段")

            finish_reason = choices[0].get("finish_reason", None)
            result = choices[0].get("message", {}).get("content", "")

            # 处理不同的 finish_reason
            if finish_reason == "stop":
                # 正常结束
                pass
            elif finish_reason == "length":
                # 长度限制，尝试继续获取
                self.logger.warning(
                    f"{self._request_label(retry_count)} 响应因长度限制被截断，尝试继续获取"
                )
                # 注意：这里传入原始result，清理工作在 _continue_fetch 最终返回时统一处理
                return self._continue_fetch(
                    client=client,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    force_json=force_json,
                    pre_send_handler=pre_send_handler,
                    result_handler=result_handler,
                    error_result_handler=error_result_handler,
                    retry_count=retry_count,
                    accumulated_result=result,
                )
            elif finish_reason in ("tool_calls", "function_call"):
                # 工具调用场景，当前代码可能不支持，直接返回已获取结果
                self.logger.warning(
                    f"{self._request_label(retry_count)} finish_reason={finish_reason}，"
                    "当前不支持工具调用，返回已获取内容"
                )
                result = self._sanitize_result(result)
                return result if result else (
                    prompt if error_result_handler is None
                    else error_result_handler(prompt, self.logger)
                )
            elif finish_reason == "content_filter":
                # 内容被过滤
                self.logger.error(f"{self._request_label(retry_count)} 响应内容被过滤")
                raise ValueError("内容被过滤")
            elif finish_reason is None:
                # 某些 API 可能不返回 finish_reason，将其视为正常结束
                self.logger.debug(
                    f"{self._request_label(retry_count)} API未返回 finish_reason，视为正常结束"
                )
            else:
                # 其他未知的 finish_reason，记录警告并返回结果
                self.logger.warning(
                    f"{self._request_label(retry_count)} 未知 finish_reason={finish_reason}，"
                    "返回已获取内容"
                )

            input_tokens, cached_tokens, output_tokens, reasoning_tokens, api_total_tokens = (
                self.token_usage_parser.parse(response_data)
            )

            self.token_counter.add(
                input_tokens, cached_tokens, output_tokens, reasoning_tokens, api_total_tokens
            )

            if retry_count > 0:
                self.logger.info(f"{self._request_label(retry_count)} 重试成功")

            # 清理 <think> 标签后再处理结果
            result = self._sanitize_result(result)

            return (
                result
                if result_handler is None
                else result_handler(result, prompt, self.logger)
            )
        except AgentResultError as e:
            self._log_attempt_failure(
                f"AI返回结果有误: {_safe_error_text(e)}",
                retry=retry,
                retry_count=retry_count,
            )
            should_retry = True
        except PartialAgentResultError as e:
            self._log_attempt_failure(
                f"收到部分翻译结果: {_safe_error_text(e)}",
                retry=retry,
                retry_count=retry_count,
            )
            current_partial_result = e.partial_result
            should_retry = True

        except httpx.HTTPStatusError as e:
            request_id = e.response.headers.get("x-request-id", "-")
            self._log_attempt_failure(
                f"LLM HTTP状态错误: status={e.response.status_code}, "
                f"request_id={request_id}, body={_safe_error_text(e.response.text)}",
                retry=retry,
                retry_count=retry_count,
            )
            should_retry = True
            is_hard_error = True
            if e.response.status_code == 429:
                self.logger.info(f"{self._request_label(retry_count)} 触发限流，等待 5.0s")
                time.sleep(5)

        except httpx.RequestError as e:
            if isinstance(e, httpx.TimeoutException):
                detail = _safe_error_text(e)
                if "流式响应连续" in detail:
                    message = f"流式空闲超时: {detail}"
                elif "非流式请求超过硬总时限" in detail:
                    message = f"非流式硬总超时: {detail}"
                else:
                    message = f"网络阶段超时: {type(e).__name__}: {detail}"
            elif isinstance(e, httpx.ReadError):
                message = (
                    f"读取响应失败: {type(e).__name__}: {_safe_error_text(e)} "
                    "(服务器可能关闭连接或网络中断)"
                )
            elif isinstance(e, httpx.ConnectError):
                message = (
                    f"连接失败: {type(e).__name__}: {_safe_error_text(e)} "
                    "(请检查网络或 base_url)"
                )
            elif isinstance(e, httpx.WriteError):
                message = f"发送请求数据失败: {type(e).__name__}: {_safe_error_text(e)}"
            else:
                message = f"网络请求错误: {type(e).__name__}: {_safe_error_text(e)}"
            self._log_attempt_failure(
                message,
                retry=retry,
                retry_count=retry_count,
            )
            should_retry = True
            is_hard_error = True
        except (KeyError, IndexError, ValueError, json.JSONDecodeError) as e:
            self._log_attempt_failure(
                f"LLM响应格式或值错误: {_safe_error_text(repr(e))}",
                retry=retry,
                retry_count=retry_count,
            )
            should_retry = True
            is_hard_error = True

        if current_partial_result:
            best_partial_result = current_partial_result

        if should_retry and retry and retry_count < self.retry:
            if is_hard_error:
                if retry_count == 0:
                    if self.total_error_counter.add():
                        self.logger.error("错误次数过多，已达到上限，不再重试。")
                        with self.unresolved_error_lock:
                            self.unresolved_error_count += 1
                        return (
                            best_partial_result
                            if best_partial_result
                            else (
                                prompt
                                if error_result_handler is None
                                else error_result_handler(prompt, self.logger)
                            )
                        )
                elif self.total_error_counter.reach_limit():
                    self.logger.error("错误次数过多，已达到上限，不再为该请求重试。")
                    with self.unresolved_error_lock:
                        self.unresolved_error_count += 1
                    return (
                        best_partial_result
                        if best_partial_result
                        else (
                            prompt
                            if error_result_handler is None
                            else error_result_handler(prompt, self.logger)
                        )
                    )

            retry_delay = 0.5 * (2 ** retry_count)
            self.logger.info(
                f"{self._request_label(retry_count)} 将在 {retry_delay:.1f}s 后重试"
            )
            time.sleep(retry_delay)
            return self.send(
                client,
                prompt,
                system_prompt,
                retry=True,
                retry_count=retry_count + 1,
                force_json=force_json,
                pre_send_handler=pre_send_handler,
                result_handler=result_handler,
                error_result_handler=error_result_handler,
                best_partial_result=best_partial_result,
            )
        else:
            if should_retry:
                self.logger.error(f"{self._request_label(retry_count)} 所有尝试均失败")
                with self.unresolved_error_lock:
                    self.unresolved_error_count += 1

            if best_partial_result:
                self.logger.info(
                    f"{self._request_label(retry_count)} 存在部分翻译结果，将使用该结果"
                )
                return best_partial_result

            return (
                prompt
                if error_result_handler is None
                else error_result_handler(prompt, self.logger)
            )

    def send_prompts(
            self,
            prompts: list[str],
            system_prompt: str | None = None,
            json_format=False,
            pre_send_handler: PreSendHandlerType = None,
            result_handler: ResultHandlerType = None,
            error_result_handler: ErrorResultHandlerType = None,
    ) -> list[Any]:
        def run_async_batch() -> list[Any]:
            return asyncio.run(
                self.send_prompts_async(
                    prompts=prompts,
                    system_prompt=system_prompt,
                    force_json=json_format,
                    pre_send_handler=pre_send_handler,
                    result_handler=result_handler,
                    error_result_handler=error_result_handler,
                )
            )

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # 常规同步调用：直接创建临时事件循环。
            return run_async_batch()

        # 若同步 API 被误用于已有事件循环中，不能在同一线程调用 asyncio.run。
        # 使用一个桥接线程保持原有同步行为；实际 HTTP 工作仍由可取消的异步实现完成。
        with ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(run_async_batch).result()

    def get_full_stats(self) -> dict:
        """
        获取完整统计信息，包括token统计、请求数、未解决错误数和错误率。

        Returns:
            dict: 包含完整统计信息的字典
        """
        token_stats = self.token_counter.get_stats()
        request_count = getattr(self, '_request_count', 0)
        unresolved = self.unresolved_error_count
        error_rate = unresolved / request_count if request_count > 0 else 0.0
        return {
            "input_tokens": token_stats["input_tokens"],
            "cached_tokens": token_stats["cached_tokens"],
            "output_tokens": token_stats["output_tokens"],
            "reasoning_tokens": token_stats["reasoning_tokens"],
            "total_tokens": token_stats["total_tokens"],
            "request_count": request_count,
            "unresolved_errors": unresolved,
            "unresolved_error_rate": error_rate
        }
