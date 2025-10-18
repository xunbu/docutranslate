# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import asyncio
import json
import re
from dataclasses import dataclass
from json import JSONDecodeError
from logging import Logger

from json_repair import json_repair

from docutranslate.agents import AgentConfig, Agent
from docutranslate.agents.agent import PartialAgentResultError, AgentResultError
from docutranslate.glossary.glossary import Glossary
from docutranslate.utils.json_utils import segments2json_chunks, fix_json_string


def generate_prompt(json_segments: str, to_lang: str):
    return f"""
You will receive a sequence of original text segments to be translated, represented in JSON format. The keys are segment IDs, and the values are the text content to be translated.    
Here is the input:

<input>
```json
{json_segments}
```
</input>

For each Key-Value Pair in the JSON, translate the contents of the value into {to_lang}, Write the translation back into the value for that JSON.
> (Very important) The original text segments and translated segments must strictly correspond one-to-one. It is strictly forbidden for the IDs of the translated segments to differ from those of the original segments.
> The segment IDs in the output must exactly match those in the input. And all segment IDs in input must appear in the output.
> If necessary, two segments can only be translated together, the translation should be proportionally allocated to the corresponding key's value based on the word count ratio of the segments.

Here is an example of the expected format:

<example>
Input:

```json
{{
3:source,
4:source,
}}
```

Output(target language: {to_lang}):

```json
{{
3:translation,
4:translation,
}}
```

</example>
Please return the translated JSON directly without including any additional information and preserve special tags or untranslatable elements (such as code, brand names, technical terms) as they are.
"""

def get_original_segments(prompt:str):
    match = re.search(r'<input>\n```json\n(.*)\n```\n</input>', prompt, re.DOTALL)
    if match:
        return match.group(1)
    else:
        raise ValueError("无法从prompt中提取初始文本")

def get_target_segments(result:str):
    match = re.search(r'```json(.*)```', result, re.DOTALL)
    if match:
        return match.group(1)
    else:
        return result

@dataclass
class SegmentsTranslateAgentConfig(AgentConfig):
    to_lang: str
    custom_prompt: str | None = None
    glossary_dict: dict[str, str] | None = None


class SegmentsTranslateAgent(Agent):
    def __init__(self, config: SegmentsTranslateAgentConfig):
        super().__init__(config)
        self.to_lang = config.to_lang
        self.system_prompt = f"""
# Role
- You are a professional, authentic machine translation engine.
"""
        self.custom_prompt = config.custom_prompt
        if config.custom_prompt:
            self.system_prompt += "\n# **Important rules or background** \n" + self.custom_prompt + '\nEND\n'
        self.glossary_dict = config.glossary_dict

    def _pre_send_handler(self, system_prompt, prompt):
        if self.glossary_dict:
            glossary = Glossary(glossary_dict=self.glossary_dict)
            system_prompt += glossary.append_system_prompt(prompt)
        return system_prompt, prompt

    def _result_handler(self, result: str, origin_prompt: str, logger: Logger):
        """
        处理成功的API响应。
        - 如果键完全匹配，返回翻译结果。
        - 如果键不匹配，构造一个部分成功的结果，并通过 PartialTranslationError 异常抛出，以触发重试。
        - 其他错误（如JSON解析失败、模型偷懒）则抛出普通 ValueError 触发重试。
        """
        original_segments=get_original_segments(origin_prompt)
        result = get_target_segments(result)
        if result == "":
            if original_segments.strip() != "":
                raise AgentResultError("result为空值但原文不为空")
            return {}
        try:
            result = fix_json_string(result)
            original_chunk = json_repair.loads(original_segments)
            repaired_result = json_repair.loads(result)

            if not isinstance(repaired_result, dict):
                raise AgentResultError(f"Agent返回结果不是dict的json形式, result: {result}")

            if repaired_result == original_chunk:
                raise AgentResultError("翻译结果与原文完全相同，疑似翻译失败，将进行重试。")

            original_keys = set(original_chunk.keys())
            result_keys = set(repaired_result.keys())

            # 如果键不完全匹配
            if original_keys != result_keys:
                # 仍然先构造一个最完整的“部分结果”
                final_chunk = {}
                common_keys = original_keys.intersection(result_keys)
                missing_keys = original_keys - result_keys
                extra_keys = result_keys - original_keys

                logger.warning(f"翻译结果的键与原文不匹配！将尝试重试。")
                if missing_keys: logger.warning(f"缺失的键: {missing_keys}")
                if extra_keys: logger.warning(f"多余的键: {extra_keys}")

                for key in common_keys:
                    final_chunk[key] = str(repaired_result[key])
                for key in missing_keys:
                    final_chunk[key] = str(original_chunk[key])

                # 抛出自定义异常，将部分结果和错误信息一起传递出去
                raise PartialAgentResultError("键不匹配，触发重试", partial_result=final_chunk)

            # 如果键完全匹配（理想情况），正常返回
            for key, value in repaired_result.items():
                repaired_result[key] = str(value)

            return repaired_result

        except (RuntimeError, JSONDecodeError) as e:
            # 对于JSON解析等硬性错误，继续抛出普通ValueError
            raise AgentResultError(f"结果处理失败: {e.__repr__()}")

    def _error_result_handler(self, origin_prompt: str, logger: Logger):
        """
        处理在所有重试后仍然失败的请求。
        作为备用方案，返回原文内容，并将所有值转换为字符串。
        """
        original_segments=get_original_segments(origin_prompt)
        if original_segments == "":
            return {}
        try:
            original_chunk = json_repair.loads(original_segments)
            # 此处逻辑保留，作为最终的兜底方案
            for key, value in original_chunk.items():
                original_chunk[key] = f"{value}"
            return original_chunk
        except (RuntimeError, JSONDecodeError):
            logger.error(f"原始prompt也不是有效的json格式: {original_segments}")
            # 如果原始prompt本身也无效，返回一个清晰的错误对象
            return {"error": f"{original_segments}"}

    def send_segments(self, segments: list[str], chunk_size: int) -> list[str]:
        indexed_originals, chunks, merged_indices_list = segments2json_chunks(segments, chunk_size)
        prompts = [generate_prompt(json.dumps(chunk, ensure_ascii=False, indent=0), self.to_lang) for chunk in chunks]

        translated_chunks = super().send_prompts(prompts=prompts, pre_send_handler=self._pre_send_handler,
                                                 result_handler=self._result_handler,
                                                 error_result_handler=self._error_result_handler)

        indexed_translated = indexed_originals.copy()
        for chunk in translated_chunks:
            try:
                if not isinstance(chunk, dict):
                    self.logger.warning(f"接收到的chunk不是有效的字典，已跳过: {chunk}")
                    continue
                for key, val in chunk.items():
                    if key in indexed_translated:
                        indexed_translated[key] = val
                    else:
                        self.logger.warning(f"在结果chunk中发现未知键 '{key}'，已忽略。")
            except (AttributeError, TypeError) as e:
                self.logger.error(f"处理chunk时发生类型或属性错误，已跳过。Chunk: {chunk}, 错误: {e.__repr__()}")
            except Exception as e:
                self.logger.error(f"处理chunk时发生未知错误: {e.__repr__()}")

        # 重建最终列表
        result = []
        last_end = 0
        ls = list(indexed_translated.values())
        for start, end in merged_indices_list:
            result.extend(ls[last_end:start])
            merged_item = "".join(map(str, ls[start:end]))
            result.append(merged_item)
            last_end = end

        result.extend(ls[last_end:])
        return result

    async def send_segments_async(self, segments: list[str], chunk_size: int) -> list[str]:
        indexed_originals, chunks, merged_indices_list = await asyncio.to_thread(segments2json_chunks, segments,
                                                                                 chunk_size)
        prompts = [generate_prompt(json.dumps(chunk, ensure_ascii=False, indent=0), self.to_lang) for chunk in chunks]

        translated_chunks = await super().send_prompts_async(prompts=prompts, pre_send_handler=self._pre_send_handler,
                                                             result_handler=self._result_handler,
                                                             error_result_handler=self._error_result_handler)

        indexed_translated = indexed_originals.copy()
        for chunk in translated_chunks:
            try:
                if not isinstance(chunk, dict):
                    self.logger.error(f"接收到的chunk不是有效的字典，已跳过: {chunk}")
                    continue
                for key, val in chunk.items():
                    if key in indexed_translated:
                        # 此处不再需要 str(val)，因为 _result_handler 已经处理好了
                        indexed_translated[key] = val
                    else:
                        self.logger.warning(f"在结果chunk中发现未知键 '{key}'，已忽略。")
            except (AttributeError, TypeError) as e:
                self.logger.error(f"处理chunk时发生类型或属性错误，已跳过。Chunk: {chunk}, 错误: {e.__repr__()}")
            except Exception as e:
                self.logger.error(f"处理chunk时发生未知错误: {e.__repr__()}")

        # 重建最终列表
        result = []
        last_end = 0
        ls = list(indexed_translated.values())
        for start, end in merged_indices_list:
            result.extend(ls[last_end:start])
            merged_item = "".join(map(str, ls[start:end]))
            result.append(merged_item)
            last_end = end

        result.extend(ls[last_end:])
        return result

    def update_glossary_dict(self, update_dict: dict | None):
        if self.glossary_dict is None:
            self.glossary_dict = {}
        if update_dict is not None:
            self.glossary_dict = update_dict | self.glossary_dict
