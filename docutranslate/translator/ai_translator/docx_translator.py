# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
from dataclasses import dataclass
from io import BytesIO
from typing import Self, Literal, List, Dict, Any, Tuple

import docx
from docx.document import Document as DocumentObject
from docx.oxml.ns import qn
from docx.oxml.shared import OxmlElement
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from docutranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator


def is_image_run(run: Run) -> bool:
    """检查一个 run 是否包含图片。"""
    # w:drawing 是嵌入式图片的标志, w:pict 是 VML 图片的标志
    return '<w:drawing' in run.element.xml or '<w:pict' in run.element.xml


@dataclass
class DocxTranslatorConfig(AiTranslatorConfig):
    """
    DocxTranslator 的配置类。
    """
    insert_mode: Literal["replace", "append", "prepend"] = "replace"
    separator: str = "\n"


class DocxTranslator(AiTranslator):
    """
    用于翻译 .docx 文件的翻译器。
    此版本经过优化，可以处理图文混排的段落而不会丢失图片。
    新增功能：自动设置文档，使其在 Word 中打开时提示更新目录（TOC）。
    """

    def __init__(self, config: DocxTranslatorConfig):
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

    def _pre_translate(self, document: Document) -> Tuple[DocumentObject, List[Dict[str, Any]], List[str]]:
        """
        [已重构] 预处理 .docx 文件，在 Run 级别上提取文本，以避免破坏图片。
        此版本增加了对页眉和页脚的翻译支持。
        :param document: 包含 .docx 文件内容的 Document 对象。
        :return: 一个元组，包含：
                 - docx.Document 对象
                 - 一个包含文本块信息的列表 (每个元素代表一组连续的文本 run)
                 - 一个包含所有待翻译原文的列表
        """
        doc = docx.Document(BytesIO(document.content))
        elements_to_translate = []
        original_texts = []

        def process_paragraph(para: Paragraph):
            nonlocal elements_to_translate, original_texts
            current_text_segment = ""
            current_runs = []

            for run in para.runs:
                if is_image_run(run):
                    # 遇到图片，将之前累积的文本作为一个翻译单元
                    if current_text_segment.strip():
                        elements_to_translate.append({"type": "text_runs", "runs": current_runs})
                        original_texts.append(current_text_segment)
                    # 重置累加器
                    current_text_segment = ""
                    current_runs = []
                else:
                    # 累积文本 run
                    current_runs.append(run)
                    current_text_segment += run.text

            # 处理段落末尾的最后一个文本块
            if current_text_segment.strip():
                elements_to_translate.append({"type": "text_runs", "runs": current_runs})
                original_texts.append(current_text_segment)

        def process_container(container):
            """处理给定容器（如文档、页眉、单元格）中的段落和表格。"""
            # 遍历容器中的所有段落
            for para in container.paragraphs:
                process_paragraph(para)
            # 遍历容器中的所有表格
            for table in container.tables:
                for row in table.rows:
                    for cell in row.cells:
                        # 单元格本身也是一个容器，我们直接处理其段落。
                        for cell_para in cell.paragraphs:
                            process_paragraph(cell_para)

        # 1. 翻译文档主体
        process_container(doc)

        # 2. 翻译所有节的页眉和页脚
        for section in doc.sections:
            # 每个节可以有多达三种不同的页眉和页脚（第一页、偶数页、默认页）
            for header in (section.header, section.first_page_header, section.even_page_header):
                process_container(header)
            for footer in (section.footer, section.first_page_footer, section.even_page_footer):
                process_container(footer)

        return doc, elements_to_translate, original_texts

    def _enable_update_fields_on_open(self, doc: DocumentObject):
        """
        设置 Word 文档在打开时自动更新域（如目录）。
        这通过在文档的 settings.xml 文件中添加 <w:updateFields w:val="true"/> 实现。
        这是更新目录（TOC）的最佳实践，因为 python-docx 无法直接重新计算页码和条目。
        :param doc: The docx.Document object.
        """
        # 获取 settings.xml 的根元素
        settings_element = doc.settings.element

        # 定义 <w:updateFields> 标签的 Clark notation，用于查找
        update_fields_tag_clark = qn('w:updateFields')

        # 查找现有的 <w:updateFields> 元素
        update_fields = settings_element.find(update_fields_tag_clark)

        # 如果不存在，则创建一个新的并添加到 settings 中
        # **【修复】** OxmlElement() 需要的是带前缀的标签名，而不是 Clark notation
        if update_fields is None:
            update_fields = OxmlElement('w:updateFields')
            settings_element.append(update_fields)

        # 设置 w:val="true" 属性以启用更新
        update_fields.set(qn('w:val'), 'true')

    def _after_translate(self, doc: DocumentObject, elements_to_translate: List[Dict[str, Any]],
                         translated_texts: List[str], original_texts: List[str]) -> bytes:
        """
        [已重构] 将翻译后的文本写回到对应的 text runs 中，保留图片和样式。
        同时，设置文档在打开时更新域，以便刷新目录（TOC）。
        """

        for i, element_info in enumerate(elements_to_translate):
            runs = element_info["runs"]
            original_text = original_texts[i]
            translated_text = translated_texts[i]

            # 根据插入模式确定最终文本
            if self.insert_mode == "replace":
                final_text = translated_text
            elif self.insert_mode == "append":
                final_text = original_text + self.separator + translated_text
            elif self.insert_mode == "prepend":
                final_text = translated_text + self.separator + original_text
            else:
                self.logger.error("不正确的DocxTranslatorConfig参数")
                final_text = translated_text

            if not runs:
                continue

            # --- 这是修改的核心部分 ---
            # 1. 将完整的翻译文本写入第一个 run
            first_run = runs[0]
            first_run.text = final_text

            # 2. 清空该文本块中其余 run 的内容，但保留 run 本身及其格式
            #    这可以防止重复文本，同时保留文档结构
            for run in runs[1:]:
                run.text = ""
            # --- 修改结束 ---

        # 启用“打开时更新域”功能，以便刷新目录
        self._enable_update_fields_on_open(doc)

        # 将修改后的文档保存到 BytesIO 流
        doc_output_stream = BytesIO()
        doc.save(doc_output_stream)
        return doc_output_stream.getvalue()

    def translate(self, document: Document) -> Self:
        """
        同步翻译 .docx 文件。
        """
        doc, elements_to_translate, original_texts = self._pre_translate(document)
        if not original_texts:
            print("\n文件中没有找到需要翻译的文本内容。")
            output_stream = BytesIO()
            doc.save(output_stream)
            document.content = output_stream.getvalue()
            return self

        if self.glossary_agent:
            self.glossary_dict_gen = self.glossary_agent.send_segments(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

        # 调用翻译 agent
        if self.translate_agent:
            translated_texts = self.translate_agent.send_segments(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts

        # 将翻译结果写回文档
        document.content = self._after_translate(doc, elements_to_translate, translated_texts, original_texts)
        return self

    async def translate_async(self, document: Document) -> Self:
        """
        异步翻译 .docx 文件。
        """
        doc, elements_to_translate, original_texts = await asyncio.to_thread(self._pre_translate, document)
        if not original_texts:
            print("\n文件中没有找到需要翻译的文本内容。")
            # 在异步环境中正确保存和返回
            output_stream = BytesIO()
            doc.save(output_stream)
            document.content = output_stream.getvalue()
            return self

        if self.glossary_agent:
            self.glossary_dict_gen = await self.glossary_agent.send_segments_async(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

        # 异步调用翻译 agent
        if self.translate_agent:
            translated_texts = await self.translate_agent.send_segments_async(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts
        # 将翻译结果写回文档
        document.content = await asyncio.to_thread(self._after_translate, doc, elements_to_translate, translated_texts,
                                                   original_texts)
        return self