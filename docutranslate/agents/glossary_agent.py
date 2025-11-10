# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import asyncio
import json
import re
from dataclasses import dataclass
from json import JSONDecodeError
from logging import Logger

import json_repair

from docutranslate.agents import AgentConfig, Agent
from docutranslate.agents.agent import AgentResultError
from docutranslate.utils.json_utils import segments2json_chunks


def generate_prompt(json_segments: str, to_lang: str):
    return f"""
You will receive a JSON-formatted list of paragraphs where keys are paragraph numbers and values are paragraph contents.
You need to extract person names and location names from these paragraphs and translate these terms into {to_lang}.
Finally, output a glossary of original terms:translated terms

Here is the input:

<input>
```json
{json_segments}
```
</input>

<Requirement>
- The original language is identified based on the context.The target language is {to_lang}
- The same src should only appear once in the glossary without repetition
- Do not include special tags or tags formatted as `<ph-xxxxxx>` in the glossary
- Do not include common nouns in the glossary.
- No explanation in Translated Term.
</Requirement>

The output format should be plain JSON text in a JSON array format:
{[{"src": "<Original Term>", "dst": "<Translated Term>"}]}

<example>
Assuming the source language is English and the target language is Chinese in the example
Input:
{{"0":"Jobs likes apples","1":"Bill Gates is sunbathing in Shanghai."}}
Output:
{r'[{"src": "Jobs", "dst": "乔布斯"}, {"src": "Bill Gates", "dst": "比尔盖茨"}, {"src": "Shanghai", "dst": "上海"}]'}
</example>
"""


def get_original_segments(prompt: str):
    match = re.search(r'<input>\n```json\n(.*)\n```\n</input>', prompt, re.DOTALL)
    if match:
        return match.group(1)
    else:
        raise ValueError("无法从prompt中提取初始文本")


def get_target_segments(result: str):
    match = re.search(r'```json(.*)```', result, re.DOTALL)
    if match:
        return match.group(1)
    else:
        return result


@dataclass(kw_only=True)
class GlossaryAgentConfig(AgentConfig):
    to_lang: str
    custom_prompt: str = None
    force_json: bool = False


class GlossaryAgent(Agent):
    def __init__(self, config: GlossaryAgentConfig):
        super().__init__(config)
        self.to_lang = config.to_lang
        self.force_json=config.force_json
        self.system_prompt = f"""
# Role
You are a professional glossary extractor
"""
        self.custom_prompt = config.custom_prompt
        if config.custom_prompt:
            self.system_prompt += "\n# **Important rules or background** \n" + self.custom_prompt + '\nEND\n'

    def _result_handler(self, result: str, origin_prompt: str, logger: Logger):
        result = get_target_segments(result)
        if result == "":
            if origin_prompt.strip() != "":
                logger.error("result为空值但原文不为空")
                raise AgentResultError("result为空值但原文不为空")
            return []
        try:
            repaired_result = json_repair.loads(result)
            if not isinstance(repaired_result, list):
                raise AgentResultError(f"GlossaryAgent返回结果不是list的json形式, result: {result}")
            return repaired_result
        except (RuntimeError, JSONDecodeError) as e:
            raise AgentResultError(f"结果不能正确解析: {e.__repr__()}")

    def _error_result_handler(self, origin_prompt: str, logger: Logger):
        origin_prompt = get_original_segments(origin_prompt)
        if origin_prompt.strip() == "":
            return []
        try:
            return json_repair.loads(origin_prompt)
        except (RuntimeError, JSONDecodeError):
            logger.error(f"原始prompt也不是有效的json格式: {origin_prompt}")
            return []  # 如果原始prompt也无效，返回空列表

    def send_segments(self, segments: list[str], chunk_size: int):
        self.logger.info(f"开始提取术语表,to_lang:{self.to_lang}")
        result = {}
        indexed_originals, chunks, merged_indices_list = segments2json_chunks(segments, chunk_size)
        prompts = [generate_prompt(json.dumps(chunk, ensure_ascii=False), self.to_lang) for chunk in chunks]
        translated_chunks = super().send_prompts(prompts=prompts, json_format=self.force_json,
                                                 result_handler=self._result_handler,
                                                 error_result_handler=self._error_result_handler)
        for chunk in translated_chunks:
            try:
                if not isinstance(chunk, list):
                    self.logger.error(f"接收到的chunk不是有效的列表，已跳过: {chunk}")
                    continue
                glossary_dict = {d["src"]: d["dst"] for d in chunk if isinstance(d, dict) and "src" in d and "dst" in d}
                result = glossary_dict | result
            except (TypeError, KeyError) as e:
                self.logger.error(f"处理glossary chunk时发生键或类型错误，已跳过。Chunk: {chunk}, 错误: {e.__repr__()}")
            except Exception as e:
                self.logger.error(f"处理glossary chunk时发生未知错误: {e.__repr__()}")

        self.logger.info("术语表提取完成")
        return result

    async def send_segments_async(self, segments: list[str], chunk_size: int):
        self.logger.info(f"开始提取术语表,to_lang:{self.to_lang}")
        result = {}
        indexed_originals, chunks, merged_indices_list = await asyncio.to_thread(segments2json_chunks, segments,
                                                                                 chunk_size)
        prompts = [generate_prompt(json.dumps(chunk, ensure_ascii=False), self.to_lang) for chunk in chunks]
        translated_chunks = await super().send_prompts_async(prompts=prompts, force_json=self.force_json,
                                                             result_handler=self._result_handler,
                                                             error_result_handler=self._error_result_handler)
        for chunk in translated_chunks:
            try:
                if not isinstance(chunk, list):
                    self.logger.error(f"接收到的chunk不是有效的列表，已跳过: {chunk}")
                    continue
                glossary_dict = {d["src"]: d["dst"] for d in chunk if isinstance(d, dict) and "src" in d and "dst" in d}
                result = result | glossary_dict
            except (TypeError, KeyError) as e:
                self.logger.error(f"处理glossary chunk时发生键或类型错误，已跳过。Chunk: {chunk}, 错误: {e.__repr__()}")
            except Exception as e:
                self.logger.error(f"处理glossary chunk时发生未知错误: {e.__repr__()}")

        self.logger.info("术语表提取完成")
        return result
