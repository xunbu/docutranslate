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
    """
    insert_mode: Literal["replace", "append", "prepend"] = "replace"
    separator: str = "\n"


class TXTTranslator(AiTranslator):
    """
    一个用于翻译纯文本 (.txt) 文件的翻译器。
    它会按行读取文件内容，对每一行进行翻译，然后根据配置将译文写回。
    """

    def __init__(self, config: TXTTranslatorConfig):
        """
        初始化 TXTTranslator。

        Args:
            config (TxtTranslatorConfig): 翻译器的配置。
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
                retry=config.retry
            )
            self.translate_agent = SegmentsTranslateAgent(agent_config)
        self.insert_mode = config.insert_mode
        self.separator = config.separator

    def _pre_translate(self, document: Document) -> List[str]:
        """
        预处理步骤：解析TXT文件，按行分割文本。

        Args:
            document (Document): 待处理的文档对象。

        Returns:
            List[str]: 待翻译的原文文本行列表。
        """
        try:
            # 使用 utf-8-sig 解码以处理可能存在的BOM (Byte Order Mark)
            txt_content = document.content.decode('utf-8-sig')
        except (UnicodeDecodeError, AttributeError) as e:
            self.logger.error(f"无法解码TXT文件内容，请确保文件编码为UTF-8: {e}")
            return []

        # 按行分割文本，并保留空行，因为它们可能是格式的一部分
        original_texts = txt_content.splitlines()

        return original_texts

    def _after_translate(self, translated_texts: List[str], original_texts: List[str]) -> bytes:
        """
        翻译后处理步骤：将译文根据配置模式与原文合并，并生成新的TXT文件内容。

        Args:
            translated_texts (List[str]): 翻译后的文本行列表。
            original_texts (List[str]): 原始文本行列表。

        Returns:
            bytes: 新的TXT文件内容的字节流。
        """
        processed_lines = []
        for i, original_text in enumerate(original_texts):
            # 如果原文是空行或仅包含空白字符，则直接保留，不进行翻译处理
            if not original_text.strip():
                processed_lines.append(original_text)
                continue

            translated_text = translated_texts[i]

            # 根据插入模式更新内容
            if self.insert_mode == "replace":
                processed_lines.append(translated_text)
            elif self.insert_mode == "append":
                # strip() 避免在原文和译文间产生多余的空白
                processed_lines.append(original_text.strip() + self.separator + translated_text.strip())
            elif self.insert_mode == "prepend":
                processed_lines.append(translated_text.strip() + self.separator + original_text.strip())
            else:
                self.logger.error(f"不正确的TxtTranslatorConfig参数: insert_mode='{self.insert_mode}'")
                # 默认回退到替换模式，避免程序中断
                processed_lines.append(translated_text)

        # 将所有处理后的行重新合成为一个字符串，以换行符分隔
        new_txt_content_str = "\n".join(processed_lines)

        # 返回UTF-8编码的字节流
        return new_txt_content_str.encode('utf-8')

    def translate(self, document: Document) -> Self:
        """
        同步翻译TXT文档。

        Args:
            document (Document): 待翻译的文档对象。

        Returns:
            Self: 返回翻译器实例，以支持链式调用。
        """
        original_texts = self._pre_translate(document)

        if not original_texts:
            self.logger.info("\n文件中没有找到需要翻译的文本内容。")
            return self

        # 过滤掉仅包含空白字符的行，避免不必要的翻译API调用
        texts_to_translate = [text for text in original_texts if text.strip()]

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

        # 将翻译结果映射回原始行列表，非翻译行保持不变
        final_translated_texts = [translated_texts_map.get(text, text) for text in original_texts]

        # --- 步骤 3: 后处理并更新文档内容 ---
        document.content = self._after_translate(final_translated_texts, original_texts)
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
        original_texts = await asyncio.to_thread(self._pre_translate, document)

        if not original_texts:
            self.logger.info("\n文件中没有找到需要翻译的文本内容。")
            return self

        # 过滤掉仅包含空白字符的行
        texts_to_translate = [text for text in original_texts if text.strip()]

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

        # 将翻译结果映射回原始行列表
        final_translated_texts = [translated_texts_map.get(text, text) for text in original_texts]

        # --- 步骤 3: 后处理并更新文档内容 (I/O密集型) ---
        document.content = await asyncio.to_thread(
            self._after_translate, final_translated_texts, original_texts
        )
        return self