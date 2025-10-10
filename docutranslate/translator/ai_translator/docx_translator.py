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
from docx.oxml.text.run import CT_R
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from docutranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator


HEADING_STYLES = {f"Heading {i}" for i in range(1, 10)} | \
                 {f"heading {i}" for i in range(1, 10)} | \
                 {f"标题 {i}" for i in range(1, 10)}


def is_image_run(run: Run) -> bool:
    """检查一个 run 是否包含图片。"""
    return '<w:drawing' in run.element.xml or '<w:pict' in run.element.xml


def is_formatting_only_run(run: Run) -> bool:
    """检查一个 run 是否只包含格式（如下划线）而没有实际的、非空白的文本内容。"""
    if run.text.strip() == "":
        if run.underline:
            return True
    return False


@dataclass
class DocxTranslatorConfig(AiTranslatorConfig):
    """DocxTranslator 的配置类。"""
    insert_mode: Literal["replace", "append", "prepend"] = "replace"
    separator: str = "\n"


class DocxTranslator(AiTranslator):
    """
    用于翻译 .docx 文件的翻译器。
    [核心优化] 仅在检测到目录且相关标题被翻译时，才设置“更新域”标志。
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

        # [新增] 状态变量，用于智能判断
        self._has_toc_field = False
        self._translated_a_heading = False

    def _check_for_toc(self, doc: DocumentObject) -> bool:
        """[新增] 扫描文档，检查是否存在目录（TOC）域。"""
        # 目录的指令文本通常包含 'TOC'
        # 我们需要查找 <w:instrText> 元素
        for instr_text in doc.element.body.iter(qn('w:instrText')):
            if instr_text.text and 'TOC' in instr_text.text.strip():
                self.logger.info("在文档中检测到目录（TOC）。")
                return True
        return False

    def _pre_translate(self, document: Document) -> Tuple[DocumentObject, List[Dict[str, Any]], List[str]]:
        """
        预处理 .docx 文件，提取文本并检测是否需要更新域。
        """
        doc = docx.Document(BytesIO(document.content))
        elements_to_translate = []
        original_texts = []

        # [新增] 在开始时重置状态并进行检测
        self._has_toc_field = self._check_for_toc(doc)
        self._translated_a_heading = False

        def get_hyperlink_text(hyperlink_element) -> str:
            text = ""
            for t_element in hyperlink_element.findall('.//w:t', namespaces=hyperlink_element.nsmap):
                if t_element.text:
                    text += t_element.text
            return text

        def process_paragraph_children(para: Paragraph):
            nonlocal elements_to_translate, original_texts
            current_text_segment = ""
            current_runs = []

            # [新增] 检查当前段落是否为标题样式
            is_heading_para = para.style.name in HEADING_STYLES

            for child in para._p:
                if isinstance(child, CT_R):
                    run = Run(child, para)
                    if is_image_run(run) or is_formatting_only_run(run):
                        if current_text_segment.strip():
                            elements_to_translate.append({"type": "text_runs", "runs": current_runs})
                            original_texts.append(current_text_segment)
                            # [新增] 如果这个文本块来自标题段落，则标记
                            if is_heading_para:
                                self._translated_a_heading = True
                        current_text_segment = ""
                        current_runs = []
                    else:
                        current_runs.append(run)
                        current_text_segment += run.text

                elif child.tag == qn('w:hyperlink'):
                    # (省略超链接处理逻辑，与之前版本相同)
                    # ...
                    if current_text_segment.strip():
                        elements_to_translate.append({"type": "text_runs", "runs": current_runs})
                        original_texts.append(current_text_segment)
                        if is_heading_para:
                            self._translated_a_heading = True
                    current_text_segment = ""
                    current_runs = []

                    hyperlink_text = get_hyperlink_text(child)
                    if hyperlink_text.strip():
                        style_run = None
                        r_elements = child.findall(qn('w:r'))
                        if r_elements:
                            style_run = Run(r_elements[0], para)

                        elements_to_translate.append({
                            "type": "hyperlink",
                            "element": child,
                            "style_run": style_run
                        })
                        original_texts.append(hyperlink_text)
                        if is_heading_para:
                            self._translated_a_heading = True

            if current_text_segment.strip():
                elements_to_translate.append({"type": "text_runs", "runs": current_runs})
                original_texts.append(current_text_segment)
                # [新增] 如果这个文本块来自标题段落，则标记
                if is_heading_para:
                    self._translated_a_heading = True

        def process_container(container):
            if not container:
                return
            for para in container.paragraphs:
                process_paragraph_children(para)
            for table in container.tables:
                for row in table.rows:
                    for cell in row.cells:
                        process_container(cell)

        process_container(doc)
        for section in doc.sections:
            process_container(section.header)
            process_container(section.first_page_header)
            process_container(section.even_page_header)
            process_container(section.footer)
            process_container(section.first_page_footer)
            process_container(section.even_page_footer)

        return doc, elements_to_translate, original_texts

    def _enable_update_fields_on_open(self, doc: DocumentObject):
        settings_element = doc.settings.element
        update_fields_tag_clark = qn('w:updateFields')
        update_fields = settings_element.find(update_fields_tag_clark)
        if update_fields is None:
            update_fields = OxmlElement('w:updateFields')
            settings_element.append(update_fields)
        update_fields.set(qn('w:val'), 'true')

    def _after_translate(self, doc: DocumentObject, elements_to_translate: List[Dict[str, Any]],
                         translated_texts: List[str], original_texts: List[str]) -> bytes:
        # 回写翻译文本的逻辑保持不变...
        for i, element_info in enumerate(elements_to_translate):
            # ... (此处省略与前一版本完全相同的回写代码)
            original_text = original_texts[i]
            translated_text = translated_texts[i]

            if self.insert_mode == "replace":
                final_text = translated_text
            elif self.insert_mode == "append":
                final_text = original_text + self.separator + translated_text
            elif self.insert_mode == "prepend":
                final_text = translated_text + self.separator + original_text
            else:
                self.logger.error("不正确的DocxTranslatorConfig参数")
                final_text = translated_text

            element_type = element_info["type"]

            if element_type == "text_runs":
                runs = element_info["runs"]
                if not runs: continue
                runs[0].text = final_text
                for run in runs[1:]: run.text = ""

            elif element_type == "hyperlink":
                hyperlink_element = element_info["element"]
                style_run = element_info["style_run"]
                for run_element in hyperlink_element.findall(qn('w:r')):
                    hyperlink_element.remove(run_element)
                new_run_element = OxmlElement('w:r')
                if style_run and style_run.element.rPr is not None:
                    new_run_element.append(style_run.element.rPr)
                new_text_element = OxmlElement('w:t')
                new_text_element.text = final_text
                new_text_element.set(qn('xml:space'), 'preserve')
                new_run_element.append(new_text_element)
                hyperlink_element.append(new_run_element)

        # [核心修改] 智能决策：仅在需要时才启用“打开时更新域”
        if self._has_toc_field and self._translated_a_heading:
            self.logger.info("检测到目录且相关标题已被翻译，设置文档在打开时更新域。")
            self._enable_update_fields_on_open(doc)
        else:
            self.logger.info("未翻译标题或文档无目录，跳过设置更新域标志。")

        doc_output_stream = BytesIO()
        doc.save(doc_output_stream)
        return doc_output_stream.getvalue()

    # translate 和 translate_async 方法保持不变
    def translate(self, document: Document) -> Self:
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

        if self.translate_agent:
            translated_texts = self.translate_agent.send_segments(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts

        document.content = self._after_translate(doc, elements_to_translate, translated_texts, original_texts)
        return self

    async def translate_async(self, document: Document) -> Self:
        doc, elements_to_translate, original_texts = await asyncio.to_thread(self._pre_translate, document)
        if not original_texts:
            print("\n文件中没有找到需要翻译的文本内容。")
            output_stream = BytesIO()
            await asyncio.to_thread(doc.save, output_stream)
            document.content = output_stream.getvalue()
            return self

        if self.glossary_agent:
            self.glossary_dict_gen = await self.glossary_agent.send_segments_async(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

        if self.translate_agent:
            translated_texts = await self.translate_agent.send_segments_async(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts
        document.content = await asyncio.to_thread(self._after_translate, doc, elements_to_translate, translated_texts,
                                                   original_texts)
        return self