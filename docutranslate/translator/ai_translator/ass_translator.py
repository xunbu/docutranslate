# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import asyncio
from dataclasses import dataclass
from typing import Self, Literal, List, Optional

import pysubs2

from docutranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator


@dataclass
class AssTranslatorConfig(AiTranslatorConfig):
    insert_mode: Literal["replace", "append", "prepend"] = "replace"
    separator: str = "\\N"  # ASS 中换行符是 \N
    # 未来可扩展：指定样式名或时间范围，当前暂不实现，翻译所有 Dialogue
    translate_regions: Optional[List[str]] = None  # 暂保留接口，但当前忽略


class AssTranslator(AiTranslator):
    def __init__(self, config: AssTranslatorConfig):
        super().__init__(config=config)
        self.chunk_size = config.chunk_size
        self.translate_agent = None
        glossary_dict = self.glossary.glossary_dict if self.glossary else None
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
                glossary_dict=glossary_dict,
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
        self.translate_regions = config.translate_regions  # 暂不处理，保留接口

    def _pre_translate(self, document: Document):
        """
        解析 ASS 文件，提取所有 Dialogue 行的文本。
        返回：subs 对象、待翻译条目列表、原文列表
        """
        try:
            content_str = document.content.decode('utf-8-sig')  # ASS 通常带 BOM
        except UnicodeDecodeError:
            content_str = document.content.decode('utf-8')

        subs = pysubs2.SSAFile.from_string(content_str)
        lines_to_translate = []

        for i, line in enumerate(subs):
            if line.type == "Dialogue":
                # 仅翻译文本部分，保留样式、时间等
                if isinstance(line.text, str) and line.text.strip():
                    lines_to_translate.append({
                        "index": i,  # 记录在 subs 中的位置
                        "original_text": line.text,
                        "line": line  # 保留引用，便于后续修改
                    })

        original_texts = [item["original_text"] for item in lines_to_translate]
        return subs, lines_to_translate, original_texts

    def _after_translate(self, subs, lines_to_translate, translated_texts, original_texts):
        """
        将翻译结果写回 ASS 对象，根据 insert_mode 处理。
        """
        for i, item in enumerate(lines_to_translate):
            line = item["line"]
            translated_text = translated_texts[i]
            original_text = original_texts[i]

            if self.insert_mode == "replace":
                line.text = translated_text
            elif self.insert_mode == "append":
                line.text = original_text + self.separator + translated_text
            elif self.insert_mode == "prepend":
                line.text = translated_text + self.separator + original_text
            else:
                self.logger.error(f"不支持的插入模式: {self.insert_mode}")

        # 输出为字符串，再编码为 bytes
        output_str = subs.to_string(format_="ass")
        return output_str.encode('utf-8-sig')  # 带 BOM，兼容播放器

    def translate(self, document: Document) -> Self:
        subs, lines_to_translate, original_texts = self._pre_translate(document)

        if not lines_to_translate:
            print("\n未找到需要翻译的字幕行。")
            return self

        if self.glossary_agent:
            glossary_dict_gen = self.glossary_agent.send_segments(original_texts, self.chunk_size)
            if self.glossary:
                self.glossary.update(glossary_dict_gen)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(glossary_dict_gen)

        if self.translate_agent:
            translated_texts = self.translate_agent.send_segments(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts

        document.content = self._after_translate(subs, lines_to_translate, translated_texts, original_texts)
        return self

    async def translate_async(self, document: Document) -> Self:
        subs, lines_to_translate, original_texts = await asyncio.to_thread(self._pre_translate, document)

        if not lines_to_translate:
            print("\n未找到需要翻译的字幕行。")
            return self

        if self.glossary_agent:
            glossary_dict_gen = await self.glossary_agent.send_segments_async(original_texts, self.chunk_size)
            if self.glossary:
                self.glossary.update(glossary_dict_gen)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(glossary_dict_gen)

        if self.translate_agent:
            translated_texts = await self.translate_agent.send_segments_async(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts

        document.content = await asyncio.to_thread(
            self._after_translate, subs, lines_to_translate, translated_texts, original_texts
        )
        return self
