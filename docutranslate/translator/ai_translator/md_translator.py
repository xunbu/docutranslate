# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
import re
from dataclasses import dataclass
from typing import Self, List

from docutranslate.agents import MDTranslateAgent
from docutranslate.agents.markdown_agent import MDTranslateAgentConfig
from docutranslate.context.md_mask_context import MDMaskUrisContext
from docutranslate.ir.markdown_document import MarkdownDocument
from docutranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator
from docutranslate.utils.markdown_splitter import split_markdown_text, join_markdown_texts


@dataclass
class MDTranslatorConfig(AiTranslatorConfig):
    ...


class MDTranslator(AiTranslator):
    def __init__(self, config: MDTranslatorConfig):
        super().__init__(config=config)
        self.chunk_size = config.chunk_size
        self.translate_agent = None
        if not self.skip_translate:
            agent_config = MDTranslateAgentConfig(custom_prompt=config.custom_prompt,
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
                                                  system_proxy_enable=config.system_proxy_enable)
            self.translate_agent = MDTranslateAgent(agent_config)

    @staticmethod
    def _is_placeholder(text: str) -> bool:
        """检查文本块是否仅包含图片占位符"""
        # 匹配 <ph-xxxxxx> 格式，允许前后有空白
        return bool(re.match(r'^\s*<ph-[a-zA-Z0-9]+>\s*$', text))

    def translate(self, document: MarkdownDocument) -> Self:
        self.logger.info("正在翻译markdown")
        with MDMaskUrisContext(document):
            chunks: list[str] = split_markdown_text(document.content.decode(), self.chunk_size)

            # 预处理：分离出需要翻译的文本块和不需要翻译的占位符块
            translate_indices: List[int] = []
            translate_chunks: List[str] = []
            final_result: List[str] = list(chunks)  # 浅拷贝，预填充原始值

            for i, chunk in enumerate(chunks):
                if self._is_placeholder(chunk):
                    # 如果是占位符，不需要处理，final_result中该位置保持原样
                    continue
                else:
                    translate_indices.append(i)
                    translate_chunks.append(chunk)

            if self.glossary_agent and translate_chunks:
                # 仅对需要翻译的文本提取术语
                self.glossary_dict_gen = self.glossary_agent.send_segments(translate_chunks, self.chunk_size)
                if self.translate_agent:
                    self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

            self.logger.info(f"markdown分为{len(chunks)}块 (其中需翻译{len(translate_chunks)}块)")

            if self.translate_agent and translate_chunks:
                translated_sub_results: list[str] = self.translate_agent.send_chunks(translate_chunks)

                # 将翻译结果回填到对应位置
                for idx, translated_text in zip(translate_indices, translated_sub_results):
                    final_result[idx] = translated_text

            # 如果没有翻译代理或者没有需要翻译的块，final_result 已经包含了正确的内容（原始chunks）

            content = join_markdown_texts(final_result)
            # 做一些加强鲁棒性的操作
            content = content.replace(r'\（', r'\(')
            content = content.replace(r'\）', r'\)')

            document.content = content.encode()
        self.logger.info("翻译完成")
        return self

    async def translate_async(self, document: MarkdownDocument) -> Self:
        self.logger.info("正在翻译markdown")
        with MDMaskUrisContext(document):
            chunks: list[str] = split_markdown_text(document.content.decode(), self.chunk_size)

            # 预处理：分离出需要翻译的文本块和不需要翻译的占位符块
            translate_indices: List[int] = []
            translate_chunks: List[str] = []
            final_result: List[str] = list(chunks)

            for i, chunk in enumerate(chunks):
                if self._is_placeholder(chunk):
                    continue
                else:
                    translate_indices.append(i)
                    translate_chunks.append(chunk)

            if self.glossary_agent and translate_chunks:
                self.glossary_dict_gen = await self.glossary_agent.send_segments_async(translate_chunks,
                                                                                       self.chunk_size)
                if self.translate_agent:
                    self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

            self.logger.info(f"markdown分为{len(chunks)}块 (其中需翻译{len(translate_chunks)}块)")

            if self.translate_agent and translate_chunks:
                translated_sub_results: list[str] = await self.translate_agent.send_chunks_async(translate_chunks)

                # 将翻译结果回填到对应位置
                for idx, translated_text in zip(translate_indices, translated_sub_results):
                    final_result[idx] = translated_text

            def run():
                content = join_markdown_texts(final_result)
                # 做一些加强鲁棒性的操作
                content = content.replace(r'\（', r'\(')
                content = content.replace(r'\）', r'\)')
                document.content = content.encode()

            await asyncio.to_thread(run)
        self.logger.info("翻译完成")
        return self