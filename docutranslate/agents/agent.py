# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import asyncio
import itertools
import logging
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock
from typing import Literal, Callable, Any
from urllib.parse import urlparse

import httpx
import tiktoken

from docutranslate.agents.thinking.thinking_factory import get_thinking_mode, ProviderType
from docutranslate.logger import global_logger
from docutranslate.utils.utils import get_httpx_proxies

MAX_REQUESTS_PER_ERROR = 15

ThinkingMode = Literal["enable", "disable", "default"]


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
    concurrent: int = 30
    timeout: int = 1200
    thinking: ThinkingMode = "disable"
    retry: int = 2
    system_proxy_enable: bool = False
    force_json: bool = False
    rpm: int | None = None  # 每分钟请求数限制
    tpm: int | None = None  # 每分钟Token数限制
    provider:ProviderType|None=None


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


class PromptsCounter:
    def __init__(self, total: int, logger: logging.Logger):
        self.lock = Lock()
        self.count = 0
        self.total = total
        self.logger = logger

    def add(self):
        with self.lock:
            self.count += 1
            self.logger.info(f"多线程-已完成：{self.count}/{self.total}")


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

    async def acquire_async(self, tokens: int = 0):
        """异步等待配额"""
        if self.rpm is None and self.tpm is None:
            return

        while True:
            # print(f"[RateLimiter-Async] 准备获取锁...")
            with self.lock:
                # print(f"[RateLimiter-Async] 已加锁 (Checking)")

                wait_time = self._check_and_get_wait_time(tokens)
                if wait_time <= 0:
                    self._record_usage(tokens)
                    # print(f"[RateLimiter-Async] 释放锁 (成功获取配额)")
                    return

                # print(f"[RateLimiter-Async] 释放锁 (需等待 {wait_time:.2f}s)")

            # 释放锁后等待
            await asyncio.sleep(wait_time + 0.1)

    def acquire_sync(self, tokens: int = 0):
        """同步等待配额（线程阻塞）"""
        if self.rpm is None and self.tpm is None:
            return

        while True:
            # print(f"[RateLimiter-Sync] 准备获取锁...")
            with self.lock:
                # print(f"[RateLimiter-Sync] 已加锁 (Checking)")

                wait_time = self._check_and_get_wait_time(tokens)
                if wait_time <= 0:
                    self._record_usage(tokens)
                    # print(f"[RateLimiter-Sync] 释放锁 (成功获取配额)")
                    return

                # print(f"[RateLimiter-Sync] 释放锁 (需等待 {wait_time:.2f}s)")

            time.sleep(wait_time + 0.1)


def extract_token_info(response_data: dict) -> tuple[int, int, int, int]:
    """(保持原样) 从API响应中提取token信息"""
    if "usage" not in response_data:
        return 0, 0, 0, 0

    usage = response_data["usage"]
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)

    cached_tokens = 0
    reasoning_tokens = 0
    try:
        if (
                "input_tokens_details" in usage
                and "cached_tokens" in usage["input_tokens_details"]
        ):
            cached_tokens = usage["input_tokens_details"]["cached_tokens"]
        elif (
                "prompt_tokens_details" in usage
                and "cached_tokens" in usage["prompt_tokens_details"]
        ):
            cached_tokens = usage["prompt_tokens_details"]["cached_tokens"]
        elif "prompt_cache_hit_tokens" in usage:
            cached_tokens = usage["prompt_cache_hit_tokens"]

        if (
                "output_tokens_details" in usage
                and "reasoning_tokens" in usage["output_tokens_details"]
        ):
            reasoning_tokens = usage["output_tokens_details"]["reasoning_tokens"]
        elif (
                "completion_tokens_details" in usage
                and "reasoning_tokens" in usage["completion_tokens_details"]
        ):
            reasoning_tokens = usage["completion_tokens_details"]["reasoning_tokens"]
        return input_tokens, cached_tokens, output_tokens, reasoning_tokens
    except TypeError:
        return -1, -1, -1, -1


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
    ):
        with self.lock:
            self.input_tokens += input_tokens
            self.cached_tokens += cached_tokens
            self.output_tokens += output_tokens
            self.reasoning_tokens += reasoning_tokens
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
        self.max_concurrent = config.concurrent
        self.timeout = httpx.Timeout(connect=5, read=config.timeout, write=300, pool=10)
        self.thinking = config.thinking
        self.logger = config.logger
        self.total_error_counter = TotalErrorCounter(logger=self.logger)
        self.unresolved_error_lock = Lock()
        self.unresolved_error_count = 0
        self.token_counter = TokenCounter(logger=self.logger)
        self.retry = config.retry
        self.system_proxy_enable = config.system_proxy_enable

        # 新增：初始化速率限制器
        self.rate_limiter = RateLimiter(rpm=config.rpm, tpm=config.tpm)
        # 新增：初始化 encoding 用于估算
        self.encoding = self._get_encoding_for_model(self.model_id)

        self.provider=config.provider if config.provider is not None else self.domain

    def _get_encoding_for_model(self, model_name: str):
        """获取 tiktoken encoding，如果失败则使用 cl100k_base 兜底"""
        try:
            return tiktoken.encoding_for_model(model_name)
        except KeyError:
            # 对于未知模型或自定义模型ID，使用 GPT-4 的默认编码器
            return tiktoken.get_encoding("cl100k_base")

    def _estimate_tokens(self, text: str) -> int:
        """估算文本的 Token 数量"""
        if not text:
            return 0
        try:
            # 这是一个近似值，不包含特殊 token 格式的开销，但用于限流足够了
            return len(self.encoding.encode(text))
        except Exception:
            # 极端兜底：每4个字符算1个token
            return len(text) // 4

    def _add_thinking_mode(self, data: dict):
        thinking_mode_result = get_thinking_mode(self.provider, data.get("model"))
        if thinking_mode_result is None:
            return
        field_thinking, val_enable, val_disable = thinking_mode_result
        if self.thinking == "enable":
            data[field_thinking] = val_enable
        elif self.thinking == "disable":
            data[field_thinking] = val_disable

    def _prepare_request_data(
            self, prompt: str, system_prompt: str, temperature=None, top_p=0.9, json_format=False
    ):
        if temperature is None:
            temperature = self.temperature
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
        if self.thinking != "default":
            self._add_thinking_mode(data)
        if json_format:
            data["response_format"] = {"type": "json_object"}
        return headers, data

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
        await self.rate_limiter.acquire_async(tokens=estimated_tokens)

        headers, data = self._prepare_request_data(prompt, system_prompt, json_format=force_json)
        should_retry = False
        is_hard_error = False
        current_partial_result = None
        input_tokens = 0
        output_tokens = 0

        try:
            response = await client.post(
                f"{self.baseurl}/chat/completions",
                json=data,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = response.json()["choices"][0]["message"]["content"]

            response_data = response.json()
            input_tokens, cached_tokens, output_tokens, reasoning_tokens = (
                extract_token_info(response_data)
            )

            self.token_counter.add(
                input_tokens, cached_tokens, output_tokens, reasoning_tokens
            )

            if retry_count > 0:
                self.logger.info(f"重试成功 (第 {retry_count}/{self.retry} 次尝试)。")

            return (
                result
                if result_handler is None
                else result_handler(result, prompt, self.logger)
            )

        except AgentResultError as e:
            self.logger.error(f"AI返回结果有误: {e}")
            should_retry = True
        except PartialAgentResultError as e:
            self.logger.error(f"收到部分返回结果，将尝试重试: {e}")
            current_partial_result = e.partial_result
            should_retry = True
            if e.append_prompt:
                prompt += e.append_prompt

        except httpx.HTTPStatusError as e:
            self.logger.error(
                f"AI请求HTTP状态错误 (async): {e.response.status_code} - {e.response.text}"
            )
            should_retry = True
            is_hard_error = True
            # 如果是因为 Rate Limit (429) 错误，最好在这里多睡一会儿，虽然我们有了本地 Limiter
            if e.response.status_code == 429:
                await asyncio.sleep(5)

        except httpx.RequestError as e:
            self.logger.error(f"AI请求连接错误 (async): {repr(e)}")
            should_retry = True
            is_hard_error = True
        except (KeyError, IndexError, ValueError) as e:
            self.logger.error(f"AI响应格式或值错误 (async), 将尝试重试: {repr(e)}")
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

            self.logger.info(f"正在重试第 {retry_count + 1}/{self.retry} 次...")
            # 指数退避
            await asyncio.sleep(0.5 * (2 ** retry_count))
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
                self.logger.error(f"所有重试均失败，已达到重试次数上限。")
                with self.unresolved_error_lock:
                    self.unresolved_error_count += 1

            if best_partial_result:
                self.logger.info("所有重试失败，但存在部分翻译结果，将使用该结果。")
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

        self.logger.info(
            f"provider:{self.provider},base-url:{self.baseurl},model-id:{self.model_id},concurrent:{max_concurrent}{rpm_info}{tpm_info},temperature:{self.temperature},system_proxy:{self.system_proxy_enable},json_output:{force_json}"
        )
        self.logger.info(f"预计发送{total}个请求")

        self.total_error_counter.max_errors_count = (
                len(prompts) // MAX_REQUESTS_PER_ERROR
        )

        self.unresolved_error_count = 0
        self.token_counter.reset()

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

            async def send_with_semaphore(p_text: str):
                async with semaphore:
                    # 注意：我们在 semaphore 内部调用 send_async
                    # send_async 内部会调用 rate_limiter.acquire_async
                    # 这样可以防止并发过高，同时 rate_limiter 防止频率过快
                    result = await self.send_async(
                        client=client,
                        prompt=p_text,
                        system_prompt=system_prompt,
                        force_json=force_json,
                        pre_send_handler=pre_send_handler,
                        result_handler=result_handler,
                        error_result_handler=error_result_handler,
                    )
                    nonlocal count
                    count += 1
                    self.logger.info(f"协程-已完成{count}/{total}")
                    return result

            for p_text in prompts:
                task = asyncio.create_task(send_with_semaphore(p_text))
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=False)

            self.logger.info(
                f"所有请求处理完毕。未解决的错误总数: {self.unresolved_error_count}"
            )

            token_stats = self.token_counter.get_stats()
            self.logger.info(
                f"Token使用统计 - 输入: {token_stats['input_tokens'] / 1000:.2f}K(含cached: {token_stats['cached_tokens'] / 1000:.2f}K), "
                f"输出: {token_stats['output_tokens'] / 1000:.2f}K(含reasoning: {token_stats['reasoning_tokens'] / 1000:.2f}K), "
                f"总计: {token_stats['total_tokens'] / 1000:.2f}K"
            )

            return results

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
        self.rate_limiter.acquire_sync(tokens=estimated_tokens)

        headers, data = self._prepare_request_data(prompt, system_prompt, json_format=force_json)
        should_retry = False
        is_hard_error = False
        current_partial_result = None
        input_tokens = 0
        output_tokens = 0

        try:
            response = client.post(
                f"{self.baseurl}/chat/completions",
                json=data,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()

            result = response.json()["choices"][0]["message"]["content"]

            response_data = response.json()
            input_tokens, cached_tokens, output_tokens, reasoning_tokens = (
                extract_token_info(response_data)
            )

            self.token_counter.add(
                input_tokens, cached_tokens, output_tokens, reasoning_tokens
            )

            if retry_count > 0:
                self.logger.info(f"重试成功 (第 {retry_count}/{self.retry} 次尝试)。")

            return (
                result
                if result_handler is None
                else result_handler(result, prompt, self.logger)
            )
        except AgentResultError as e:
            self.logger.error(f"AI返回结果有误: {e}")
            should_retry = True
        except PartialAgentResultError as e:
            self.logger.error(f"收到部分翻译结果，将尝试重试: {e}")
            current_partial_result = e.partial_result
            should_retry = True

        except httpx.HTTPStatusError as e:
            self.logger.error(
                f"AI请求HTTP状态错误 (sync): {e.response.status_code} - {e.response.text}"
            )
            should_retry = True
            is_hard_error = True
            if e.response.status_code == 429:
                time.sleep(5)

        except httpx.RequestError as e:
            self.logger.error(f"AI请求连接错误 (sync): {repr(e)}\nprompt:{prompt}")
            should_retry = True
            is_hard_error = True
        except (KeyError, IndexError, ValueError) as e:
            self.logger.error(f"AI响应格式或值错误 (sync), 将尝试重试: {repr(e)}")
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

            self.logger.info(f"正在重试第 {retry_count + 1}/{self.retry} 次...")
            time.sleep(0.5 * (2 ** retry_count))
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
                self.logger.error(f"所有重试均失败，已达到重试次数上限。")
                with self.unresolved_error_lock:
                    self.unresolved_error_count += 1

            if best_partial_result:
                self.logger.info("所有重试失败，但存在部分翻译结果，将使用该结果。")
                return best_partial_result

            return (
                prompt
                if error_result_handler is None
                else error_result_handler(prompt, self.logger)
            )

    def _send_prompt_count(
            self,
            client: httpx.Client,
            prompt: str,
            system_prompt: None | str,
            force_json,
            count: PromptsCounter,
            pre_send_handler,
            result_handler,
            error_result_handler
    ) -> Any:
        # 该方法在 ThreadPoolExecutor 中运行
        result = self.send(
            client,
            prompt,
            system_prompt,
            force_json=force_json,
            pre_send_handler=pre_send_handler,
            result_handler=result_handler,
            error_result_handler=error_result_handler,
        )
        count.add()
        return result

    def send_prompts(
            self,
            prompts: list[str],
            system_prompt: str | None = None,
            json_format=False,
            pre_send_handler: PreSendHandlerType = None,
            result_handler: ResultHandlerType = None,
            error_result_handler: ErrorResultHandlerType = None,
    ) -> list[Any]:
        rpm_info = f", RPM:{self.rate_limiter.rpm}" if self.rate_limiter.rpm else ""
        tpm_info = f", TPM:{self.rate_limiter.tpm}" if self.rate_limiter.tpm else ""

        self.logger.info(
            f"provider:{self.provider},base-url:{self.baseurl},model-id:{self.model_id},concurrent:{self.max_concurrent}{rpm_info}{tpm_info},temperature:{self.temperature},system_proxy:{self.system_proxy_enable},json_output:{json_format}"
        )
        self.logger.info(
            f"预计发送{len(prompts)}个请求"
        )
        self.total_error_counter.max_errors_count = (
                len(prompts) // MAX_REQUESTS_PER_ERROR
        )

        self.unresolved_error_count = 0
        self.token_counter.reset()

        counter = PromptsCounter(len(prompts), self.logger)

        system_prompts = itertools.repeat(system_prompt, len(prompts))
        json_formats = itertools.repeat(json_format, len(prompts))
        counters = itertools.repeat(counter, len(prompts))
        pre_send_handlers = itertools.repeat(pre_send_handler, len(prompts))
        result_handlers = itertools.repeat(result_handler, len(prompts))
        error_result_handlers = itertools.repeat(error_result_handler, len(prompts))
        limits = httpx.Limits(
            max_connections=self.max_concurrent * 2,
            max_keepalive_connections=self.max_concurrent,
        )
        proxies = get_httpx_proxies(asyn=False) if self.system_proxy_enable else None

        with httpx.Client(
                trust_env=False, mounts=proxies, verify=False, limits=limits
        ) as client:
            clients = itertools.repeat(client, len(prompts))
            with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
                results_iterator = executor.map(
                    self._send_prompt_count,
                    clients,
                    prompts,
                    system_prompts,
                    json_formats,
                    counters,
                    pre_send_handlers,
                    result_handlers,
                    error_result_handlers,
                )
                output_list = list(results_iterator)

        self.logger.info(
            f"所有请求处理完毕。未解决的错误总数: {self.unresolved_error_count}"
        )

        token_stats = self.token_counter.get_stats()
        self.logger.info(
            f"Token使用统计 - 输入: {token_stats['input_tokens'] / 1000:.2f}K(含cached: {token_stats['cached_tokens'] / 1000:.2f}K), "
            f"输出: {token_stats['output_tokens'] / 1000:.2f}K(含reasoning: {token_stats['reasoning_tokens'] / 1000:.2f}K), "
            f"总计: {token_stats['total_tokens'] / 1000:.2f}K"
        )

        return output_list