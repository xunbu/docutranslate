# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
from dataclasses import dataclass
from typing import Self, List

from docutranslate.agents import MDTranslateAgent
from docutranslate.agents.markdown_agent import MDTranslateAgentConfig
from docutranslate.context.md_mask_context import MDMaskUrisContext
from docutranslate.ir.markdown_document import MarkdownDocument
from docutranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator
# 引入新的布局分割和拼接函数
from docutranslate.utils.markdown_splitter import (
    split_markdown_with_layout,
    join_markdown_with_layout,
    is_placeholder
)


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
                                                  system_proxy_enable=config.system_proxy_enable,
                                                  rpm=config.rpm,
                                                  tpm=config.tpm,
                                                  provider=config.provider,
                                                  )
            self.translate_agent = MDTranslateAgent(agent_config)

    def translate(self, document: MarkdownDocument) -> Self:
        self.logger.info("正在翻译markdown")
        with MDMaskUrisContext(document):
            # 使用新接口，获取 chunks 和对应的 separators
            chunks, separators = split_markdown_with_layout(document.content.decode(), self.chunk_size)

            translate_indices: List[int] = []
            translate_chunks: List[str] = []
            final_result: List[str] = list(chunks)  # 浅拷贝，用于回填翻译结果

            for i, chunk in enumerate(chunks):
                # 占位符不翻译
                if is_placeholder(chunk):
                    continue
                else:
                    translate_indices.append(i)
                    translate_chunks.append(chunk)

            if self.glossary_agent and translate_chunks:
                self.glossary_dict_gen = self.glossary_agent.send_segments(translate_chunks, self.chunk_size)
                if self.translate_agent:
                    self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

            self.logger.info(f"markdown分为{len(chunks)}块 (其中需翻译{len(translate_chunks)}块)")

            if self.translate_agent and translate_chunks:
                translated_sub_results: list[str] = self.translate_agent.send_chunks(translate_chunks)
                for idx, translated_text in zip(translate_indices, translated_sub_results):
                    final_result[idx] = translated_text

            # 使用记录的 separators 进行还原，完美保留布局
            content = join_markdown_with_layout(final_result, separators)

            content = content.replace(r'\（', r'\(')
            content = content.replace(r'\）', r'\)')

            document.content = content.encode()
        self.logger.info("翻译完成")
        return self

    async def translate_async(self, document: MarkdownDocument) -> Self:
        self.logger.info("正在翻译markdown")
        with MDMaskUrisContext(document):
            # 异步方法同样更新
            chunks, separators = split_markdown_with_layout(document.content.decode(), self.chunk_size)

            translate_indices: List[int] = []
            translate_chunks: List[str] = []
            final_result: List[str] = list(chunks)

            for i, chunk in enumerate(chunks):
                if is_placeholder(chunk):
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
                for idx, translated_text in zip(translate_indices, translated_sub_results):
                    final_result[idx] = translated_text

            def run():
                content = join_markdown_with_layout(final_result, separators)
                content = content.replace(r'\（', r'\(')
                content = content.replace(r'\）', r'\)')
                document.content = content.encode()

            await asyncio.to_thread(run)
        self.logger.info("翻译完成")
        return self