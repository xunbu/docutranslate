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
from docutranslate.utils.json_utils import segments2json_chunks, fix_json_string, parse_json_response


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
{{"3":"source text 3","4":"source text 4"}}
```

Output(target language: {to_lang}):

```json
[{{"id":"3","t":"translated 3"}},{{"id":"4","t":"translated 4"}}]
```

Note: Use "id" for the segment ID and "t" for the translated text.
For statements that must be combined during translation, employ merging at the minimal structural level. The total number of keys must remain unchanged after merging, and any empty values should be retained.
Below is an example of how merging should be done when necessary:

input:
```json
{{"3":"汤姆说:“杰克你","4":"好”。"}}
```
output:
```json
[{{"id":"3","t":"Tom says:\"Hello Jack.\""}},{{"id":"4","t":""}}]
```
</example>
Please return the translated JSON directly without including any additional information and preserve special tags or untranslatable elements (such as code, brand names, technical terms) as they are.
"""


def get_original_segments(prompt: str):
    match = re.search(r'<input>\n```json\n(.*)\n```\n</input>', prompt, re.DOTALL)
    if match:
        return match.group(1)
    else:
        raise ValueError("无法从prompt中提取初始文本")


def get_target_segments(result: str):
    """使用统一解析函数解析JSON响应"""
    return parse_json_response(result)


@dataclass(kw_only=True)
class SegmentsTranslateAgentConfig(AgentConfig):
    to_lang: str
    custom_prompt: str | None = None
    glossary_dict: dict[str, str] | None = None
    force_json:bool = False


class SegmentsTranslateAgent(Agent):
    def __init__(self, config: SegmentsTranslateAgentConfig):
        super().__init__(config)
        self.to_lang = config.to_lang
        self.force_json = config.force_json
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

    def get_continue_prompt(self, accumulated_result: str, prompt: str) -> str:
        """
        继续获取时的提示词。
        只返回新增的数组元素，而不是完整的JSON数组。
        """
        # 从原始prompt中提取原文的ID范围，帮助模型正确继续
        try:
            original_segments = get_original_segments(prompt)
            original_data = json_repair.loads(original_segments)
            original_ids = list(original_data.keys())
            if original_ids:
                min_id = min(original_ids, key=lambda x: int(x) if x.isdigit() else float('inf'))
                max_id = max(original_ids, key=lambda x: int(x) if x.isdigit() else 0)
                id_range_info = f"原文ID范围: {min_id} - {max_id}"
            else:
                id_range_info = ""
        except Exception:
            id_range_info = ""

        return f"""你之前的翻译输出被截断了。

之前已输出的内容:
```json
{accumulated_result}
```

请继续输出后续的翻译内容。只输出新增的数组元素，格式为JSON数组。

{id_range_info}

重要规则：
- 仔细分析之前已输出的内容，找出最后一个已翻译的ID
- 只输出从"最后一个已翻译的ID + 1"开始的新ID
- 不要重复之前已输出的任何元素
- 例如：如果之前最后输出到 id="3"，请继续从 id="4" 开始
- 只输出新增的部分，不要输出之前已有的内容
- 格式：[{{"id":"4","t":"翻译4"}}, {{"id":"5","t":"翻译5"}}]
"""

    def merge_continue_result(self, accumulated_result: str, additional_result: str) -> str:
        """
        合并继续获取的结果。
        处理追加模式的数组合并：将追加的数组元素合并到已有的数组中。
        自动去重：如果 additional 中有重复的 ID，保留 accumulated 中的版本。
        """
        try:
            # 尝试解析两个部分
            accumulated = parse_json_response(accumulated_result)
            additional = parse_json_response(additional_result)

            # 如果都是列表，合并并去重
            if isinstance(accumulated, list) and isinstance(additional, list):
                # 收集 accumulated 中的 ID
                existing_ids = {item.get("id") for item in accumulated if "id" in item}

                # 只添加 additional 中不重复的 ID
                for item in additional:
                    if item.get("id") not in existing_ids:
                        accumulated.append(item)
                        existing_ids.add(item.get("id"))

                return json.dumps(accumulated, ensure_ascii=False)
        except Exception as e:
            # 如果解析失败，回退到直接拼接
            pass
        return accumulated_result + additional_result

    def _result_handler(self, result: str, origin_prompt: str, logger: Logger):
        """
        处理成功的API响应。
        - 输入格式: [{"id":"1","t":"翻译"}, ...]
        - 输出格式: {"1": "翻译", "2": "翻译2"}
        - 如果ID完全匹配，返回翻译结果。
        - 如果ID不匹配，构造一个部分成功的结果，并通过 PartialTranslationError 异常抛出，以触发重试。
        - 其他错误（如JSON解析失败、模型偷懒）则抛出普通 ValueError 触发重试。
        """
        original_segments = get_original_segments(origin_prompt)
        repaired_result = get_target_segments(result)  # 直接返回解析后的 list 或 dict
        if not repaired_result:
            if original_segments.strip() != "":
                raise AgentResultError("result为空值但原文不为空")
            return {}

        try:
            original_chunk = json_repair.loads(original_segments)

            # 兼容处理：如果返回的是 dict（旧格式）而非 array
            if isinstance(repaired_result, dict):
                repaired_array = [{"id": k, "t": v} for k, v in repaired_result.items()]
            elif isinstance(repaired_result, list):
                repaired_array = repaired_result
            else:
                raise AgentResultError(f"Agent返回结果不是array的json形式, result: {result}")

            # 检查是否与原文完全相同（疑似翻译失败）
            if repaired_array == [{"id": k, "t": v} for k, v in original_chunk.items()]:
                raise AgentResultError("翻译结果与原文完全相同，疑似翻译失败，将进行重试。")

            # 转换为 dict 便于处理
            result_dict = {item["id"]: item["t"] for item in repaired_array if "id" in item and "t" in item}
            original_keys = set(original_chunk.keys())
            result_keys = set(result_dict.keys())

            # 如果ID不完全匹配
            if original_keys != result_keys:
                # 构造一个最完整的"部分结果"
                final_chunk = {}
                common_keys = original_keys.intersection(result_keys)
                missing_keys = original_keys - result_keys
                extra_keys = result_keys - original_keys

                # 只保留原文有的ID，丢弃多余的ID（可能是模型幻觉）
                if extra_keys:
                    logger.warning(f"检测到多余的ID（可能是模型幻觉，已丢弃）: {extra_keys}")

                # 合并已翻译的部分和缺失的部分
                for key in common_keys:
                    final_chunk[key] = str(result_dict[key])
                for key in missing_keys:
                    final_chunk[key] = str(original_chunk[key])

                # 如果所有ID都匹配了，直接返回
                if not missing_keys and not extra_keys:
                    return final_chunk

                # 如果有缺失的ID，抛出部分结果异常
                if missing_keys:
                    logger.warning(f"缺失的ID: {missing_keys}")
                    raise PartialAgentResultError("ID不匹配，触发重试", partial_result=final_chunk, append_prompt=f"\nBe careful not to omit any IDs from the input; do not combine sentences when translating.\n")

            # 如果ID完全匹配（理想情况），正常返回
            for key, value in result_dict.items():
                result_dict[key] = str(value)

            return result_dict

        except (RuntimeError, JSONDecodeError) as e:
            # 对于JSON解析等硬性错误，继续抛出普通ValueError
            raise AgentResultError(f"结果处理失败: {e.__repr__()}")

    def _error_result_handler(self, origin_prompt: str, logger: Logger):
        """
        处理在所有重试后仍然失败的请求。
        作为备用方案，返回原文内容，并将所有值转换为字符串。
        """
        original_segments = get_original_segments(origin_prompt)
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
        translated_chunks = super().send_prompts(prompts=prompts, json_format=self.force_json,
                                                 pre_send_handler=self._pre_send_handler,
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

        translated_chunks = await super().send_prompts_async(prompts=prompts, force_json=self.force_json,
                                                             pre_send_handler=self._pre_send_handler,
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
            self.glossary_dict = self.glossary_dict | update_dict
