# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
import re
from dataclasses import dataclass
from typing import Self, Literal, List

from docutranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator


@dataclass
class TXTTranslatorConfig(AiTranslatorConfig):
    """
    TXTTranslator的配置类。

    Attributes:
        insert_mode (Literal["replace", "append", "prepend"]):
            指定如何插入翻译文本的模式。
            ▪ "replace": 用译文替换原文。

            ▪ "append": 将译文追加到原文后面。

            ▪ "prepend": 将译文前置到原文前面。

            默认为 "replace"。
        separator (str):
            在 "append" 或 "prepend" 模式下，用于分隔原文和译文的字符串。
            默认为换行符 "\n"。
        segment_mode (Literal["line", "paragraph", "none"]):
            分段模式。
            ▪ "line": 按行分段（每行独立翻译）

            ▪ "paragraph": 按段落分段（连续非空行合并为段落）

            ▪ "none": 不分段（全文视为一个段落）

            默认为 "line"。
    """
    insert_mode: Literal["replace", "append", "prepend"] = "replace"
    separator: str = "\n"
    segment_mode: Literal["line", "paragraph", "none"] = "line"


class TXTTranslator(AiTranslator):
    """
    一个用于翻译纯文本 (.txt) 文件的翻译器。
    支持按行或按段落两种分段模式进行翻译。
    """

    def __init__(self, config: TXTTranslatorConfig):
        """
        初始化 TXTTranslator。

        Args:
            config (TXTTranslatorConfig): 翻译器的配置。
        """
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
                force_json=config.force_json,
                rpm=config.rpm,
                tpm=config.tpm,
                provider=config.provider,
            )
            self.translate_agent = SegmentsTranslateAgent(agent_config)
        self.insert_mode = config.insert_mode
        self.separator = config.separator
        self.segment_mode = config.segment_mode

    def _pre_translate(self, document: Document) -> List[str]:
        """
        预处理步骤：根据分段模式解析TXT文件。

        Args:
            document (Document): 待处理的文档对象。

        Returns:
            List[str]: 分段后的文本列表。
        """
        try:
            # 使用 utf-8-sig 解码以处理可能存在的BOM (Byte Order Mark)
            txt_content = document.content.decode('utf-8-sig')
        except (UnicodeDecodeError, AttributeError) as e:
            self.logger.error(f"无法解码TXT文件内容，请确保文件编码为UTF-8: {e}")
            return []

        if self.segment_mode == "line":
            return self._segment_by_line(txt_content)
        elif self.segment_mode == "paragraph":
            return self._segment_by_paragraph(txt_content)
        else:
            return [txt_content]

    def _segment_by_line(self, txt_content: str) -> List[str]:
        """
        按行分段模式：每行作为独立分段。
        """
        return txt_content.splitlines()

    def _segment_by_paragraph(self, txt_content: str) -> List[str]:
        """
        按段落分段模式：使用正则表达式按空行分割，并保留分隔符。
        """
        segments = re.split(r'(\n\s*\n)', txt_content)
        return [s for s in segments if s]

    def _after_translate(self, translated_texts: List[str], original_texts: List[str]) -> bytes:
        """
        翻译后处理步骤：根据分段模式重建文档。
        此函数现在接收两个长度完全相同的对齐列表。
        """
        if self.segment_mode == "line":
            return self._reconstruct_by_line(translated_texts, original_texts)
        elif self.segment_mode == "paragraph":
            return self._reconstruct_by_paragraph(translated_texts, original_texts)
        else:
            return self._reconstruct_none(translated_texts, original_texts)

    def _reconstruct_by_line(self, translated_lines: List[str], original_lines: List[str]) -> bytes:
        """
        按行模式重建文档。
        """
        processed_lines = []
        for i, original_line in enumerate(original_lines):
            # 如果原文是空行或仅包含空白字符，则直接保留
            if not original_line.strip():
                processed_lines.append(original_line)
                continue

            translated_line = translated_lines[i]

            # 根据插入模式更新内容
            if self.insert_mode == "replace":
                processed_lines.append(translated_line)
            elif self.insert_mode == "append":
                processed_lines.append(original_line.strip() + self.separator + translated_line.strip())
            elif self.insert_mode == "prepend":
                processed_lines.append(translated_line.strip() + self.separator + original_line.strip())
            else:
                self.logger.error(f"不正确的insert_mode参数: '{self.insert_mode}'")
                processed_lines.append(translated_line)

        return "\n".join(processed_lines).encode('utf-8')

    def _reconstruct_by_paragraph(self, translated_segments: List[str], original_segments: List[str]) -> bytes:
        """
        按段落模式重建文档。
        """
        result_parts = []
        for i, original_segment in enumerate(original_segments):
            # 如果 segment 是纯空白（即空行分隔符），直接保留
            if not original_segment.strip():
                result_parts.append(original_segment)
                continue

            translated_segment = translated_segments[i]

            # 根据插入模式处理
            if self.insert_mode == "replace":
                result_parts.append(translated_segment)
            elif self.insert_mode == "append":
                result_parts.append(original_segment + self.separator + translated_segment)
            elif self.insert_mode == "prepend":
                result_parts.append(translated_segment + self.separator + original_segment)
            else:
                result_parts.append(translated_segment)

        return "".join(result_parts).encode('utf-8')

    def _reconstruct_none(self, translated_texts: List[str], original_texts: List[str]) -> bytes:
        """
        不分段模式重建文档。
        """
        if not translated_texts or not original_texts:
            return b""

        original_text = original_texts[0]
        translated_text = translated_texts[0]

        if self.insert_mode == "replace":
            result_text = translated_text
        elif self.insert_mode == "append":
            result_text = original_text + self.separator + translated_text
        elif self.insert_mode == "prepend":
            result_text = translated_text + self.separator + original_text
        else:
            self.logger.error(f"不正确的insert_mode参数: '{self.insert_mode}'")
            result_text = translated_text

        return result_text.encode('utf-8')

    def translate(self, document: Document) -> Self:
        """
        同步翻译TXT文档。
        """
        original_segments = self._pre_translate(document)

        if not original_segments:
            self.logger.info("\n文件中没有找到需要翻译的文本内容。")
            return self

        texts_to_translate = [text for text in original_segments if text.strip()]

        if self.glossary_agent and texts_to_translate:
            self.glossary_dict_gen = self.glossary_agent.send_segments(texts_to_translate, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

        translated_texts_map = {}
        if self.translate_agent and texts_to_translate:
            translated_segments = self.translate_agent.send_segments(texts_to_translate, self.chunk_size)
            translated_texts_map = dict(zip(texts_to_translate, translated_segments))

        # 【核心逻辑】创建与原始分段列表等长的、完全对齐的最终翻译列表
        final_translated_texts = [translated_texts_map.get(text, text) for text in original_segments]

        document.content = self._after_translate(final_translated_texts, original_segments)
        return self

    async def translate_async(self, document: Document) -> Self:
        """
        异步翻译TXT文档。
        """
        original_segments = await asyncio.to_thread(self._pre_translate, document)

        if not original_segments:
            self.logger.info("\n文件中没有找到需要翻译的文本内容。")
            return self

        texts_to_translate = [text for text in original_segments if text.strip()]

        if self.glossary_agent and texts_to_translate:
            self.glossary_dict_gen = await self.glossary_agent.send_segments_async(texts_to_translate, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

        translated_texts_map = {}
        if self.translate_agent and texts_to_translate:
            translated_segments = await self.translate_agent.send_segments_async(texts_to_translate, self.chunk_size)
            translated_texts_map = dict(zip(texts_to_translate, translated_segments))

        # 【核心逻辑】创建与原始分段列表等长的、完全对齐的最终翻译列表
        final_translated_texts = [translated_texts_map.get(text, text) for text in original_segments]

        document.content = await asyncio.to_thread(
            self._after_translate, final_translated_texts, original_segments
        )
        return self