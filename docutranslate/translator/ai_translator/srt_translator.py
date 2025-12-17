# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
from dataclasses import dataclass
from typing import Self, Literal

import srt  # 导入srt库来处理字幕文件

from docutranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator


@dataclass
class SrtTranslatorConfig(AiTranslatorConfig):
    insert_mode: Literal["replace", "append", "prepend"] = "replace"
    separator: str = "\n"


class SrtTranslator(AiTranslator):
    """
    一个用于翻译 SRT (.srt) 字幕文件的翻译器。
    它会提取每个字幕块的文本内容，进行翻译，然后根据配置将译文写回。
    """

    def __init__(self, config: SrtTranslatorConfig):
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
                tpm=config.tpm
            )
            self.translate_agent = SegmentsTranslateAgent(agent_config)
        self.insert_mode = config.insert_mode
        self.separator = config.separator

    def _pre_translate(self, document: Document):
        """
        预处理步骤：解析SRT文件，提取所有字幕文本。

        Returns:
            tuple: (解析后的字幕对象列表, 待翻译的原文文本列表)
        """
        try:
            # 使用 utf-8-sig 解码以处理可能存在的BOM (Byte Order Mark)
            srt_content = document.content.decode('utf-8-sig')
        except (UnicodeDecodeError, AttributeError) as e:
            self.logger.error(f"无法解码SRT文件内容，请确保文件编码为UTF-8: {e}")
            return [], []

        # 使用 srt 库解析内容
        try:
            subtitles = list(srt.parse(srt_content))
        except srt.SRTParseError as e:
            self.logger.error(f"解析SRT文件失败: {e}")
            return [], []

        # 提取所有原文文本，准备进行批量翻译
        original_texts = [sub.content for sub in subtitles]

        return subtitles, original_texts

    def _after_translate(self, subtitles: list[srt.Subtitle], translated_texts: list[str],
                         original_texts: list[str]) -> bytes:
        """
        翻译后处理步骤：将译文根据配置模式写回字幕对象，并生成新的SRT文件内容。

        Returns:
            bytes: 新的SRT文件内容的字节流。
        """
        for i, sub in enumerate(subtitles):
            translated_text = translated_texts[i]
            original_text = original_texts[i]

            # 根据插入模式更新字幕内容
            if self.insert_mode == "replace":
                sub.content = translated_text
            elif self.insert_mode == "append":
                # strip() 避免在原文和译文间产生多余的空白
                sub.content = original_text.strip() + self.separator + translated_text.strip()
            elif self.insert_mode == "prepend":
                sub.content = translated_text.strip() + self.separator + original_text.strip()
            else:
                self.logger.error(f"不正确的SrtTranslatorConfig参数: insert_mode='{self.insert_mode}'")
                # 默认回退到替换模式，避免程序中断
                sub.content = translated_text

        # 使用 srt 库将修改后的字幕对象列表重新合成为SRT格式的字符串
        new_srt_content_str = srt.compose(subtitles)

        # 返回UTF-8编码的字节流
        return new_srt_content_str.encode('utf-8')

    def translate(self, document: Document) -> Self:
        """
        同步翻译SRT文档。
        """
        subtitles, original_texts = self._pre_translate(document)

        if not original_texts:
            self.logger.info("\n文件中没有找到需要翻译的字幕内容。")
            return self
        if self.glossary_agent:
            self.glossary_dict_gen = self.glossary_agent.send_segments(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)
        # --- 步骤 2: 调用翻译Agent ---
        if self.translate_agent:
            translated_texts = self.translate_agent.send_segments(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts
        # --- 步骤 3: 后处理并更新文档内容 ---
        document.content = self._after_translate(subtitles, translated_texts, original_texts)
        return self

    async def translate_async(self, document: Document) -> Self:
        """
        异步翻译SRT文档。
        """
        # I/O密集型操作在线程中运行
        subtitles, original_texts = await asyncio.to_thread(self._pre_translate, document)

        if not original_texts:
            self.logger.info("\n文件中没有找到需要翻译的字幕内容。")
            return self

        if self.glossary_agent:
            self.glossary_dict_gen = await self.glossary_agent.send_segments_async(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

        # --- 步骤 2: 调用翻译Agent (异步) ---
        if self.translate_agent:
            translated_texts = await self.translate_agent.send_segments_async(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts
        # --- 步骤 3: 后处理并更新文档内容 (I/O密集型) ---
        document.content = await asyncio.to_thread(
            self._after_translate, subtitles, translated_texts, original_texts
        )
        return self
