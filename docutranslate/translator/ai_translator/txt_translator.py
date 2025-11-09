# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
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
            - "replace": 用译文替换原文。
            - "append": 将译文追加到原文后面。
            - "prepend": 将译文前置到原文前面。
            默认为 "replace"。
        separator (str):
            在 "append" 或 "prepend" 模式下，用于分隔原文和译文的字符串。
            默认为换行符 "\n"。
        segment_mode (Literal["line", "paragraph", "none"]):
            分段模式。
            - "line": 按行分段（每行独立翻译）
            - "paragraph": 按段落分段（连续非空行合并为段落）
            - "none": 不分段（全文视为一个段落）
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
                system_proxy_enable=config.system_proxy_enable
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
        elif self.segment_mode == "paragraph":  # paragraph mode
            return self._segment_by_paragraph(txt_content)
        else:
            return [txt_content]

    def _segment_by_line(self, txt_content: str) -> List[str]:
        """
        按行分段模式：每行作为独立分段。

        Args:
            txt_content (str): 文本内容

        Returns:
            List[str]: 按行分段的文本列表
        """
        # 简单按行分割，保留所有行（包括空行）
        return txt_content.splitlines()

    def _segment_by_paragraph(self, txt_content: str) -> List[str]:
        """
        按段落分段模式：连续非空行合并为段落，空行单独处理。

        Args:
            txt_content (str): 文本内容

        Returns:
            List[str]: 按段落分段的文本列表
        """
        lines = txt_content.splitlines()
        segments = []  # 每个元素要么是文本段落，要么是空行标记

        i = 0
        while i < len(lines):
            if lines[i].strip():  # 非空行 → 文本段落
                # 收集连续的非空行
                paragraph_lines = []
                while i < len(lines) and lines[i].strip():
                    paragraph_lines.append(lines[i])
                    i += 1
                segments.append("\n".join(paragraph_lines))
            else:  # 空行 → 空行标记
                # 收集连续的空行
                empty_lines = []
                while i < len(lines) and not lines[i].strip():
                    empty_lines.append(lines[i])
                    i += 1
                # 用特殊标记表示空行组（保持数量信息）
                segments.append(f"@@EMPTY_LINES_{len(empty_lines)}@@")

        return segments

    def _after_translate(self, translated_texts: List[str], original_texts: List[str]) -> bytes:
        """
        翻译后处理步骤：根据分段模式重建文档。

        Args:
            translated_texts (List[str]): 翻译后的文本列表。
            original_texts (List[str]): 原始文本列表。

        Returns:
            bytes: 新的TXT文件内容的字节流。
        """
        if self.segment_mode == "line":
            return self._reconstruct_by_line(translated_texts, original_texts)
        elif self.segment_mode == "paragraph":  # paragraph mode
            return self._reconstruct_by_paragraph(translated_texts, original_texts)
        else:
            return self._reconstruct_none(translated_texts, original_texts)

    def _reconstruct_by_line(self, translated_texts: List[str], original_lines: List[str]) -> bytes:
        """
        按行模式重建文档。

        Args:
            translated_texts (List[str]): 翻译后的行列表
            original_lines (List[str]): 原始行列表

        Returns:
            bytes: 重建的文档内容
        """
        processed_lines = []
        for i, original_line in enumerate(original_lines):
            # 如果是空行，直接保留
            if not original_line.strip():
                processed_lines.append(original_line)
                continue

            translated_line = translated_texts[i]

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

    def _reconstruct_by_paragraph(self, translated_texts: List[str], original_segments: List[str]) -> bytes:
        """
        按段落模式重建文档。

        Args:
            translated_texts (List[str]): 翻译后的段落列表
            original_segments (List[str]): 原始分段列表

        Returns:
            bytes: 重建的文档内容
        """
        result_lines = []
        translated_index = 0

        for segment in original_segments:
            # 处理空行组
            if segment.startswith("@@EMPTY_LINES_"):
                empty_count = int(segment.split('_')[-2])  # 提取空行数量
                result_lines.extend([""] * empty_count)
                continue

            # 处理文本段落
            if translated_index < len(translated_texts):
                translated_text = translated_texts[translated_index]
                translated_index += 1

                # 根据插入模式处理
                if self.insert_mode == "replace":
                    result_lines.append(translated_text)
                elif self.insert_mode == "append":
                    result_lines.append(segment + self.separator + translated_text)
                elif self.insert_mode == "prepend":
                    result_lines.append(translated_text + self.separator + segment)
                else:
                    result_lines.append(translated_text)
            else:
                # 理论上不会发生，但安全处理
                result_lines.append(segment)

        return "\n".join(result_lines).encode('utf-8')

    def _reconstruct_none(self, translated_texts: List[str], original_texts: List[str]) -> bytes:
        """
        不分段模式重建文档。

        Args:
            translated_texts (List[str]): 翻译后的文本列表（应只包含一个元素）
            original_texts (List[str]): 原始文本列表（应只包含一个元素）

        Returns:
            bytes: 重建的文档内容
        """
        if not translated_texts or not original_texts:
            return b""

        original_text = original_texts[0]
        translated_text = translated_texts[0]

        # 根据插入模式处理
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

        Args:
            document (Document): 待翻译的文档对象。

        Returns:
            Self: 返回翻译器实例，以支持链式调用。
        """
        original_segments = self._pre_translate(document)

        if not original_segments:
            self.logger.info("\n文件中没有找到需要翻译的文本内容。")
            return self

        # 过滤出需要翻译的文本段（非空行标记）
        if self.segment_mode == "line":
            texts_to_translate = [text for text in original_segments if text.strip()]
        else:  # paragraph mode
            texts_to_translate = [text for text in original_segments if not text.startswith("@@EMPTY_LINES_")]

        # --- 步骤 1: (可选) 术语提取 ---
        if self.glossary_agent and texts_to_translate:
            self.glossary_dict_gen = self.glossary_agent.send_segments(texts_to_translate, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

        # --- 步骤 2: 调用翻译Agent ---
        translated_texts_map = {}
        if self.translate_agent and texts_to_translate:
            translated_segments = self.translate_agent.send_segments(texts_to_translate, self.chunk_size)
            translated_texts_map = dict(zip(texts_to_translate, translated_segments))

        # 将翻译结果映射回原始分段列表
        final_translated_texts = []
        for segment in original_segments:
            if self.segment_mode == "line":
                # 行模式：空行保留，非空行翻译
                if segment.strip() and segment in translated_texts_map:
                    final_translated_texts.append(translated_texts_map[segment])
                else:
                    final_translated_texts.append(segment)
            else:
                # 段落模式：空行标记保留，文本段落翻译
                if segment.startswith("@@EMPTY_LINES_"):
                    final_translated_texts.append(segment)  # 空行标记原样保留
                elif segment in translated_texts_map:
                    final_translated_texts.append(translated_texts_map[segment])
                else:
                    final_translated_texts.append(segment)

        # --- 步骤 3: 后处理并更新文档内容 ---
        document.content = self._after_translate(final_translated_texts, original_segments)
        return self

    async def translate_async(self, document: Document) -> Self:
        """
        异步翻译TXT文档。

        Args:
            document (Document): 待翻译的文档对象。

        Returns:
            Self: 返回翻译器实例，以支持链式调用。
        """
        # I/O密集型操作在线程中运行
        original_segments = await asyncio.to_thread(self._pre_translate, document)

        if not original_segments:
            self.logger.info("\n文件中没有找到需要翻译的文本内容。")
            return self

        # 过滤出需要翻译的文本段
        if self.segment_mode == "line":
            texts_to_translate = [text for text in original_segments if text.strip()]
        else:  # paragraph mode
            texts_to_translate = [text for text in original_segments if not text.startswith("@@EMPTY_LINES_")]

        # --- 步骤 1: (可选) 术语提取 (异步) ---
        if self.glossary_agent and texts_to_translate:
            self.glossary_dict_gen = await self.glossary_agent.send_segments_async(texts_to_translate, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

        # --- 步骤 2: 调用翻译Agent (异步) ---
        translated_texts_map = {}
        if self.translate_agent and texts_to_translate:
            translated_segments = await self.translate_agent.send_segments_async(texts_to_translate, self.chunk_size)
            translated_texts_map = dict(zip(texts_to_translate, translated_segments))

        # 将翻译结果映射回原始分段列表
        final_translated_texts = []
        for segment in original_segments:
            if self.segment_mode == "line":
                if segment.strip() and segment in translated_texts_map:
                    final_translated_texts.append(translated_texts_map[segment])
                else:
                    final_translated_texts.append(segment)
            else:
                if segment.startswith("@@EMPTY_LINES_"):
                    final_translated_texts.append(segment)
                elif segment in translated_texts_map:
                    final_translated_texts.append(translated_texts_map[segment])
                else:
                    final_translated_texts.append(segment)

        # --- 步骤 3: 后处理并更新文档内容 (I/O密集型) ---
        document.content = await asyncio.to_thread(
            self._after_translate, final_translated_texts, original_segments
        )
        return self
