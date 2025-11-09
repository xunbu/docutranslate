# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import asyncio
import itertools
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock
from typing import Literal, Callable, Any
from urllib.parse import urlparse

import httpx

from docutranslate.agents.thinking.thinking_factory import get_thinking_mode
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

    def __init__(self, message, partial_result: dict):
        super().__init__(message)
        self.partial_result = partial_result


@dataclass(kw_only=True)
class AgentConfig:
    logger: logging.Logger = global_logger
    base_url: str
    api_key: str | None = None
    model_id: str
    temperature: float = 0.7
    concurrent: int = 30
    timeout: int = 1200  # 单位(秒)，这个值是httpx.TimeOut中read的值,并非总的超时时间
    thinking: ThinkingMode = "disable"
    retry: int = 2
    system_proxy_enable: bool = False


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


# 仅使用多线程时用以计数
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


def extract_token_info(response_data: dict) -> tuple[int, int, int, int]:
    """
    从API响应中提取token信息

    支持多种response格式:
    1. 格式1: usage.input_tokens_details.cached_tokens 和 usage.output_tokens_details.reasoning_tokens
    2. 格式2: usage.prompt_tokens_details.cached_tokens
    3. 格式3: usage.prompt_cache_hit_tokens 和 usage.completion_tokens_details.reasoning_tokens

    Args:
        response_data: API响应数据

    Returns:
        tuple: (input_tokens, cached_tokens, output_tokens, reasoning_tokens)
    """
    if "usage" not in response_data:
        return 0, 0, 0, 0

    usage = response_data["usage"]
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)

    # 初始化token详细统计
    cached_tokens = 0
    reasoning_tokens = 0
    try:
        # 尝试从不同格式获取cached_tokens
        # 格式1: input_tokens_details.cached_tokens
        if (
            "input_tokens_details" in usage
            and "cached_tokens" in usage["input_tokens_details"]
        ):
            cached_tokens = usage["input_tokens_details"]["cached_tokens"]
        # 格式2: prompt_tokens_details.cached_tokens
        elif (
            "prompt_tokens_details" in usage
            and "cached_tokens" in usage["prompt_tokens_details"]
        ):
            cached_tokens = usage["prompt_tokens_details"]["cached_tokens"]
        # 格式3: prompt_cache_hit_tokens (直接在usage下)
        elif "prompt_cache_hit_tokens" in usage:
            cached_tokens = usage["prompt_cache_hit_tokens"]

        # 尝试从不同格式获取reasoning_tokens
        # 格式1: output_tokens_details.reasoning_tokens
        if (
            "output_tokens_details" in usage
            and "reasoning_tokens" in usage["output_tokens_details"]
        ):
            reasoning_tokens = usage["output_tokens_details"]["reasoning_tokens"]
        # 格式2: completion_tokens_details.reasoning_tokens
        elif (
            "completion_tokens_details" in usage
            and "reasoning_tokens" in usage["completion_tokens_details"]
        ):
            reasoning_tokens = usage["completion_tokens_details"]["reasoning_tokens"]
        return input_tokens, cached_tokens, output_tokens, reasoning_tokens
    except TypeError as e:
        # print(f"获取token失败，跳过token计数:{e.__repr__()}")
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
            # self.logger.debug(
            #     f"Token使用统计 - 输入: {self.input_tokens}(含cached: {self.cached_tokens}), "
            #     f"输出: {self.output_tokens}(含reasoning: {self.reasoning_tokens}), 总计: {self.total_tokens}"
            # )

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
        self.domain = urlparse(self.baseurl).netloc
        self.key = config.api_key.strip() if config.api_key else "xx"
        self.model_id = config.model_id.strip()
        self.system_prompt = ""
        self.temperature = config.temperature
        self.max_concurrent = config.concurrent
        self.timeout = httpx.Timeout(connect=5, read=config.timeout, write=300, pool=10)
        self.thinking = config.thinking
        self.logger = config.logger
        self.total_error_counter = TotalErrorCounter(logger=self.logger)
        # 新增：用于统计最终未解决的错误
        self.unresolved_error_lock = Lock()
        self.unresolved_error_count = 0
        # 新增：用于统计token使用情况
        self.token_counter = TokenCounter(logger=self.logger)

        self.retry = config.retry

        self.system_proxy_enable = config.system_proxy_enable

    def _add_thinking_mode(self, data: dict):
        thinking_mode_result=get_thinking_mode(self.domain,data.get("model"))
        if thinking_mode_result is None:
            return
        field_thinking, val_enable, val_disable = thinking_mode_result
        if self.thinking == "enable":
            data[field_thinking] = val_enable
        elif self.thinking == "disable":
            data[field_thinking] = val_disable


    def _prepare_request_data(
        self, prompt: str, system_prompt: str, temperature=None, top_p=0.9,json_format=False
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
        json_format=False,
        pre_send_handler: PreSendHandlerType = None,
        result_handler: ResultHandlerType = None,
        error_result_handler: ErrorResultHandlerType = None,
        best_partial_result: dict | None = None,
    ) -> Any:
        if system_prompt is None:
            system_prompt = self.system_prompt
        if pre_send_handler:
            system_prompt, prompt = pre_send_handler(system_prompt, prompt)
        # print(f"system_prompt:\n{system_prompt}")
        # print(f"【测试】prompt:\n{prompt}")
        headers, data = self._prepare_request_data(prompt, system_prompt,json_format=json_format)
        should_retry = False
        is_hard_error = False  # 新增标志，用于区分是否为硬错误
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
            # print(f"【测试】json:\n{data}")
            response.raise_for_status()
            # print(f"【测试】resp:\n{response.json()}")
            result = response.json()["choices"][0]["message"]["content"]
            # print(f"【测试】\nprompt:\n{prompt}\nresp:\n{result}")
            # 获取token使用情况
            response_data = response.json()
            input_tokens, cached_tokens, output_tokens, reasoning_tokens = (
                extract_token_info(response_data)
            )

            # 更新token计数器
            self.token_counter.add(
                input_tokens, cached_tokens, output_tokens, reasoning_tokens
            )

            if retry_count > 0:
                self.logger.info(f"重试成功 (第 {retry_count}/{self.retry} 次尝试)。")

            # print(f"result:=============================================================\n{result}\n================\n")
            return (
                result
                if result_handler is None
                else result_handler(result, prompt, self.logger)
            )

        except AgentResultError as e:
            self.logger.error(f"AI返回结果有误: {e}")
            should_retry = True
        # 专门捕获部分翻译错误（软错误）
        except PartialAgentResultError as e:
            # print(f"【测试】\nprompt:\n{prompt}\nresp:\n{result}")
            self.logger.error(f"收到部分返回结果，将尝试重试: {e}")
            current_partial_result = e.partial_result
            should_retry = True
            # is_hard_error 保持 False

        # 捕获硬错误
        except httpx.HTTPStatusError as e:
            self.logger.error(
                f"AI请求HTTP状态错误 (async): {e.response.status_code} - {e.response.text}"
            )
            should_retry = True
            is_hard_error = True
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
            # 仅在硬错误时才增加总错误计数
            if is_hard_error:
                if retry_count == 0:
                    if self.total_error_counter.add():
                        self.logger.error("错误次数过多，已达到上限，不再重试。")
                        # 新增：当因为达到错误上限而不再重试时，增加未解决错误计数
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
                    # 新增：当因为达到错误上限而不再重试时，增加未解决错误计数
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
            await asyncio.sleep(0.5)
            return await self.send_async(
                client,
                prompt,
                system_prompt,
                retry=True,
                retry_count=retry_count + 1,
                pre_send_handler=pre_send_handler,
                result_handler=result_handler,
                error_result_handler=error_result_handler,
                best_partial_result=best_partial_result,
            )
        else:
            if should_retry:
                self.logger.error(f"所有重试均失败，已达到重试次数上限。")
                # 新增：当所有重试失败后，增加未解决错误计数
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
        json_format=False,
        pre_send_handler: PreSendHandlerType = None,
        result_handler: ResultHandlerType = None,
        error_result_handler: ErrorResultHandlerType = None,
    ) -> list[Any]:
        max_concurrent = (
            self.max_concurrent if max_concurrent is None else max_concurrent
        )
        total = len(prompts)
        self.logger.info(
            f"base-url:{self.baseurl},model-id:{self.model_id},concurrent:{max_concurrent},temperature:{self.temperature},system_proxy:{self.system_proxy_enable}"
        )
        self.logger.info(f"预计发送{total}个请求，并发请求数:{max_concurrent}")
        self.total_error_counter.max_errors_count = (
            len(prompts) // MAX_REQUESTS_PER_ERROR
        )

        # 新增：在每次批量发送前重置计数器
        self.unresolved_error_count = 0
        # 重置token计数器
        self.token_counter.reset()

        count = 0
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = []

        proxies = get_httpx_proxies(asyn=True) if self.system_proxy_enable else None

        limits = httpx.Limits(
            max_connections=self.max_concurrent * 2,  # 为重试和并发预留空间
            max_keepalive_connections=self.max_concurrent,  # 保持活动的连接数
        )

        async with httpx.AsyncClient(
            trust_env=False, mounts=proxies, verify=False, limits=limits
        ) as client:

            async def send_with_semaphore(p_text: str):
                async with semaphore:
                    result = await self.send_async(
                        client=client,
                        prompt=p_text,
                        system_prompt=system_prompt,
                        json_format=json_format,
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

            # 新增：在所有任务完成后打印未解决的错误总数
            self.logger.info(
                f"所有请求处理完毕。未解决的错误总数: {self.unresolved_error_count}"
            )

            # 新增：打印token使用统计
            token_stats = self.token_counter.get_stats()
            if token_stats["input_tokens"] < 0:
                self.logger.info("Token统计失败")
            else:
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
        json_format=False,
        pre_send_handler=None,
        result_handler=None,
        error_result_handler=None,
        best_partial_result: dict | None = None,
    ) -> Any:
        if system_prompt is None:
            system_prompt = self.system_prompt
        if pre_send_handler:
            system_prompt, prompt = pre_send_handler(system_prompt, prompt)

        headers, data = self._prepare_request_data(prompt, system_prompt,json_format=json_format)
        should_retry = False
        is_hard_error = False  # 新增标志，用于区分是否为硬错误
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

            # 获取token使用情况
            response_data = response.json()
            input_tokens, cached_tokens, output_tokens, reasoning_tokens = (
                extract_token_info(response_data)
            )

            # 更新token计数器
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
        # 专门捕获部分翻译错误（软错误）
        except PartialAgentResultError as e:
            self.logger.error(f"收到部分翻译结果，将尝试重试: {e}")
            current_partial_result = e.partial_result
            should_retry = True
            # is_hard_error 保持 False

        # 捕获硬错误
        except httpx.HTTPStatusError as e:
            self.logger.error(
                f"AI请求HTTP状态错误 (sync): {e.response.status_code} - {e.response.text}"
            )
            should_retry = True
            is_hard_error = True
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
            # 仅在硬错误时才增加总错误计数
            if is_hard_error:
                if retry_count == 0:
                    if self.total_error_counter.add():
                        self.logger.error("错误次数过多，已达到上限，不再重试。")
                        # 新增：当因为达到错误上限而不再重试时，增加未解决错误计数
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
                    # 新增：当因为达到错误上限而不再重试时，增加未解决错误计数
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
            time.sleep(0.5)
            return self.send(
                client,
                prompt,
                system_prompt,
                retry=True,
                retry_count=retry_count + 1,
                pre_send_handler=pre_send_handler,
                result_handler=result_handler,
                error_result_handler=error_result_handler,
                best_partial_result=best_partial_result,
            )
        else:
            if should_retry:
                self.logger.error(f"所有重试均失败，已达到重试次数上限。")
                # 新增：当所有重试失败后，增加未解决错误计数
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
        json_format,
        count: PromptsCounter,
        pre_send_handler,
        result_handler,
        error_result_handler
    ) -> Any:
        result = self.send(
            client,
            prompt,
            system_prompt,
            json_format=json_format,
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
        self.logger.info(
            f"base-url:{self.baseurl},model-id:{self.model_id},concurrent:{self.max_concurrent},temperature:{self.temperature},system_proxy:{self.system_proxy_enable}"
        )
        self.logger.info(
            f"预计发送{len(prompts)}个请求，并发请求数:{self.max_concurrent}"
        )
        self.total_error_counter.max_errors_count = (
            len(prompts) // MAX_REQUESTS_PER_ERROR
        )

        # 新增：在每次批量发送前重置计数器
        self.unresolved_error_count = 0
        # 重置token计数器
        self.token_counter.reset()

        counter = PromptsCounter(len(prompts), self.logger)

        system_prompts = itertools.repeat(system_prompt, len(prompts))
        json_formats = itertools.repeat(json_format, len(prompts))
        counters = itertools.repeat(counter, len(prompts))
        pre_send_handlers = itertools.repeat(pre_send_handler, len(prompts))
        result_handlers = itertools.repeat(result_handler, len(prompts))
        error_result_handlers = itertools.repeat(error_result_handler, len(prompts))
        limits = httpx.Limits(
            max_connections=self.max_concurrent * 2,  # 允许连接复用
            max_keepalive_connections=self.max_concurrent,  # 保持活跃连接
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

        # 新增：在所有任务完成后打印未解决的错误总数
        self.logger.info(
            f"所有请求处理完毕。未解决的错误总数: {self.unresolved_error_count}"
        )

        # 新增：打印token使用统计
        token_stats = self.token_counter.get_stats()
        if token_stats["input_tokens"] < 0:
            self.logger.info("Token统计失败")
        else:
            self.logger.info(
                f"Token使用统计 - 输入: {token_stats['input_tokens'] / 1000:.2f}K(含cached: {token_stats['cached_tokens'] / 1000:.2f}K), "
                f"输出: {token_stats['output_tokens'] / 1000:.2f}K(含reasoning: {token_stats['reasoning_tokens'] / 1000:.2f}K), "
                f"总计: {token_stats['total_tokens'] / 1000:.2f}K"
            )

        return output_list


if __name__ == "__main__":
    pass
