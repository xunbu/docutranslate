import asyncio

# import re
from typing import TypedDict

import httpx


class AgentArgs(TypedDict, total=False):
    baseurl: str
    key: str
    model_id: str
    system_prompt: str
    temperature: float
    max_concurrent: int
    timeout: int


TIMEOUT = 500


class Agent:
    def __init__(self, baseurl="", key="", model_id="", system_prompt="", temperature=0.7, max_concurrent=6,timeout:int=TIMEOUT):
        self.baseurl = baseurl
        self.key = key
        self.model_id = model_id
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.client_async = httpx.AsyncClient()
        self.max_concurrent = max_concurrent
        self.timeout=timeout

    def _prepare_request_data(self, prompt: str, system_prompt: str, temperature=None, top_p=0.9):
        if temperature is None:
            temperature = self.temperature
        headers = {"Content-Type": "application/json",
                   "Authorization": f"Bearer {self.key}"}
        data = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                # {"role": "system", "content": "所有回复必须以【SSS】开头（这是最高规则，适用于之后的所有例子）。示例：【SSS】这是示例回答\n"+system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "top_p": top_p
        }
        return headers, data

    async def send_async(self, prompt: str, system_prompt: None | str = None) -> str:
        if system_prompt is None:
            system_prompt = self.system_prompt

        """Sends a single prompt asynchronously."""
        headers, data = self._prepare_request_data(prompt, system_prompt)
        if self.baseurl.endswith("/"):
            self.baseurl = self.baseurl[:-1]
        try:
            response = await self.client_async.post(
                f"{self.baseurl}/chat/completions",
                json=data,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()["choices"][0]["message"]["content"]
            # pattern = r".*【SSS】(.*)"
            # match = re.search(pattern, result, re.DOTALL)
            # if match is None:
            #     print("检测开头`【SSS】`失败")
            # else:
            #     result = match.group(1)
            return result
        except httpx.HTTPStatusError as e:
            raise Exception(f"AI请求错误 (async): {e.response.status_code} - {e.response.text}") from e
        except httpx.RequestError as e:
            raise Exception(f"AI请求连接错误 (async): {e}") from e
        except (KeyError, IndexError) as e:
            raise Exception(f"AI响应格式错误 (async): {e}") from e

    async def send_prompts_async(
            self,
            prompts: list[str],
            system_prompt: str | None = None,
            max_concurrent: int = 5  # 新增参数，默认并发数为5
    ) -> list[str]:
        total = len(prompts)
        count = 0
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = []
        # 辅助协程，用于包装 self.send_async 并使用信号量
        async def send_with_semaphore(p_text: str):
            async with semaphore:  # 在进入代码块前获取信号量，退出时释放
                result = await self.send_async(
                    prompt=p_text,
                    system_prompt=system_prompt,
                )
                nonlocal count
                count += 1
                print(f"进行到{count}/{total}")
                return result

        for p_text in prompts:
            task = asyncio.create_task(send_with_semaphore(p_text))
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=False)
        return results

    def send_prompts(
            self,
            prompts: list[str],
            system_prompt: str | None = None,
    ) -> list[str]:

        result = asyncio.run(self.send_prompts_async(prompts, system_prompt, self.max_concurrent))
        return result


if __name__ == '__main__':
    pass
