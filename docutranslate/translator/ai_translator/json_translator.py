# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import json_repair
import json
from dataclasses import dataclass
from typing import Self, Any, Tuple, List

from jsonpath_ng.ext import parse

from docutranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator


@dataclass
class JsonTranslatorConfig(AiTranslatorConfig):
    json_paths: list[str]


class JsonTranslator(AiTranslator):
    def __init__(self, config: JsonTranslatorConfig):
        super().__init__(config=config)
        self.chunk_size = config.chunk_size
        self.translate_agent = None
        if not self.skip_translate:
            agent_config = SegmentsTranslateAgentConfig(
                custom_prompt=config.custom_prompt,
                to_lang=config.to_lang,
                base_url=config.base_url,
                api_key=config.api_key,
                model_id=config.model_id,
                temperature=config.temperature,
                thinking=config.thinking,
                concurrent=config.concurrent,
                timeout=config.timeout,
                logger=self.logger,
                glossary_dict=config.glossary_dict,
                retry=config.retry,
                system_proxy_enable=config.system_proxy_enable,
                json_format=config.force_json
            )
            self.translate_agent = SegmentsTranslateAgent(agent_config)
        self.json_paths = config.json_paths

    def _get_key_or_index_from_path(self, path) -> Any:
        """从jsonpath_ng的Path对象中提取键或索引。"""
        if hasattr(path, 'fields') and path.fields:
            return path.fields[0]
        if hasattr(path, 'index'):
            return path.index
        return None

    def _collect_strings_for_translation(self, content: dict) -> Tuple[List[str], List[Tuple[Any, Any]]]:
        """
        根据jsonpath查找匹配项，并递归地从中收集所有字符串以进行翻译。
        为了防止重复，会跟踪每个字符串的精确位置。

        返回:
            - original_texts: 一个包含所有待翻译字符串的列表。
            - update_targets: 一个包含更新信息的目标列表，每个元素为 (container, key_or_index)。
        """
        original_texts = []
        update_targets = []
        # 使用 (id(container), key_or_index) 来唯一标识一个位置，防止重复添加
        seen_targets = set()

        # 辅助递归函数，用于遍历json对象
        def _traverse(node: Any, container: Any, key_or_index: Any):
            # 如果当前节点是字符串，并且其位置尚未被记录
            target_id = (id(container), key_or_index)
            if isinstance(node, str):
                if target_id not in seen_targets:
                    original_texts.append(node)
                    update_targets.append((container, key_or_index))
                    seen_targets.add(target_id)
            # 如果是字典，则遍历其所有子节点
            elif isinstance(node, dict):
                for k, v in node.items():
                    _traverse(v, node, k)
            # 如果是列表，则遍历其所有子节点
            elif isinstance(node, list):
                for i, item in enumerate(node):
                    _traverse(item, node, i)

        # 1. 查找所有顶层匹配项
        all_matches = []
        for path_str in self.json_paths:
            jsonpath_expr = parse(path_str)
            all_matches.extend(jsonpath_expr.find(content))

        # 2. 遍历匹配项并启动递归收集
        for match in all_matches:
            parent = match.context.value if match.context else None
            key_or_index = self._get_key_or_index_from_path(match.path)

            # 直接在匹配到的值上启动遍历
            _traverse(match.value, parent, key_or_index)

        return original_texts, update_targets

    def _apply_translations(self, update_targets: List[Tuple[Any, Any]], translated_texts: List[str]):
        """
        使用翻译后的文本更新原始JSON内容。
        """
        if len(update_targets) != len(translated_texts):
            raise ValueError("The number of translation targets does not match the number of translated texts.")

        for target, text in zip(update_targets, translated_texts):
            container, key_or_index = target
            # 确保容器和键/索引是有效的，然后执行更新
            if container is not None and key_or_index is not None:
                container[key_or_index] = text

    def translate(self, document: Document) -> Self:
        """
        主方法：提取、翻译并更新JSON文档中的指定内容。

        流程:
        1. 解析输入的JSON文档。
        2. 根据jsonpath找到匹配对象，并递归遍历它们以提取所有字符串。
        3. 批量发送提取的字符串进行翻译。
        4. 将翻译回来的文本根据其原始位置，更新回JSON对象中。
        5. 将更新后的 content 写回 document。
        """
        content = json_repair.loads(document.content.decode())

        # 步骤 1: 提取所有需要翻译的字符串及其位置
        original_texts, update_targets = self._collect_strings_for_translation(content)

        if not original_texts:
            return self

        if self.glossary_agent:
            self.glossary_dict_gen = self.glossary_agent.send_segments(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

        # 步骤 2: 批量翻译提取出的文本
        if self.translate_agent:
            translated_texts = self.translate_agent.send_segments(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts

        if len(original_texts) != len(translated_texts):
            raise ValueError("翻译服务返回的项目数量与发送的数量不匹配。")

        # 步骤 3: 将翻译结果写回原始JSON对象
        self._apply_translations(update_targets, translated_texts)
        document.content = json.dumps(content, ensure_ascii=False, indent=2).encode('utf-8')

        return self

    async def translate_async(self, document: Document) -> Self:
        content = json_repair.loads(document.content.decode())

        # 步骤 1: 提取所有需要翻译的字符串及其位置
        original_texts, update_targets = self._collect_strings_for_translation(content)

        if not original_texts:
            return self

        if self.glossary_agent:
            self.glossary_dict_gen = await self.glossary_agent.send_segments_async(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

        # 步骤 2: 批量翻译提取出的文本
        if self.translate_agent:
            translated_texts = await self.translate_agent.send_segments_async(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts

        if len(original_texts) != len(translated_texts):
            raise ValueError("翻译服务返回的项目数量与发送的数量不匹配。")

        # 步骤 3: 将翻译结果写回原始JSON对象
        self._apply_translations(update_targets, translated_texts)

        document.content = json.dumps(content, ensure_ascii=False, indent=2).encode('utf-8')
        return self
