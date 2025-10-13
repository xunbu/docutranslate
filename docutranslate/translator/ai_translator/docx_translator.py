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


# ---------------- 辅助函数 ----------------
def is_image_run(run: Run) -> bool:
    """检查一个 Run 是否包含图片。"""
    xml = getattr(run.element, 'xml', '')
    return '<w:drawing' in xml or '<w:pict' in xml


def is_formatting_only_run(run: Run) -> bool:
    """
    检查一个 Run 是否主要用于格式化，例如：
    - 一个空的粗体/斜体/下划线 Run。
    - 一个只包含空格但有下划线的 Run (用于画线)。
    """
    text = run.text
    # 如果文本为空或只包含空格
    if not text.strip():
        # 并且它带有任何一种常见的格式，就认为它是一个格式化标记
        if run.underline or run.bold or run.italic or run.font.strike or run.font.subscript or run.font.superscript:
            return True
        # 特别处理：如果文本是空格且有下划线，这几乎总是为了画线
        if text and run.underline:
            return True
    return False


# ---------------- 配置类 ----------------
@dataclass
class DocxTranslatorConfig(AiTranslatorConfig):
    insert_mode: Literal["replace", "append", "prepend"] = "replace"
    separator: str = "\n"


# ---------------- 主类 ----------------
class DocxTranslator(AiTranslator):
    """
    用于翻译 .docx 文件的高级翻译器，能够高精度保留样式、处理超链接、
    域代码（如图注），并支持翻译脚注、尾注等。
    [v3.1 - 采纳新规则：将带格式的空文本视为分割点]
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

    @staticmethod
    def _extract_hyperlink_text(hyperlink_element) -> str:
        """从超链接 OXML 元素中提取所有显示文本。"""
        return ''.join(
            t.text for t in hyperlink_element.findall('.//w:t', namespaces=hyperlink_element.nsmap) if t.text
        )

    def _is_seq_field(self, child) -> bool:
        """判断一个 OXML 元素是否为 SEQ 域的一部分（如图、表编号）。"""
        try:
            if child.tag == qn('w:fldSimple'):
                instr = child.get(qn('w:instr'), '')
                if 'SEQ' in instr: return True
            if child.tag == qn('w:r'):
                for instr_text in child.findall('.//w:instrText', namespaces=child.nsmap):
                    if instr_text.text and 'SEQ' in instr_text.text:
                        return True
        except Exception:
            pass
        return False

    def _process_paragraph(self, para: Paragraph, elements: List[Dict[str, Any]], texts: List[str]):
        """
        使用状态机处理段落，将连续的文本Run合并为一个翻译单元，
        同时将图片、超链接、带格式的空文本等视为分割点。
        """
        if not para.text.strip():
            return

        current_runs = []
        is_inside_field = False

        def flush_segment():
            nonlocal current_runs
            if not current_runs:
                return
            full_text = "".join(r.text for r in current_runs)
            if full_text.strip():
                elements.append({"type": "text_runs", "runs": current_runs})
                texts.append(full_text)
            current_runs = []

        for child in para._p:
            if self._is_seq_field(child):
                flush_segment()
                continue

            if child.tag == qn('w:fldChar'):
                fld_type = child.get(qn('w:fldCharType'))
                if fld_type == 'begin':
                    flush_segment()
                    is_inside_field = True
                elif fld_type == 'end':
                    is_inside_field = False
                continue

            if is_inside_field:
                continue

            if isinstance(child, CT_R):
                run = Run(child, para)
                # 如果是图片、制表符，或者【带格式的空文本】，则视为分割点
                if is_image_run(run) or run.element.find(qn('w:tab')) is not None or is_formatting_only_run(run):
                    flush_segment()
                    # 这个 run 本身被保留，不参与翻译
                else:
                    # 否则，它是一个普通的文本 Run，收集起来
                    current_runs.append(run)
            elif child.tag == qn('w:hyperlink'):
                flush_segment()
                hyperlink_text = self._extract_hyperlink_text(child)
                if hyperlink_text.strip():
                    elements.append({"type": "hyperlink", "element": child})
                    texts.append(hyperlink_text)
            else:
                flush_segment()

        flush_segment()

    def _process_container(self, container, elements: List[Dict[str, Any]], texts: List[str]):
        """递归处理包含段落和表格的容器（如文档、单元格、页眉）。"""
        if not container: return
        for para in getattr(container, 'paragraphs', []):
            self._process_paragraph(para, elements, texts)
        for table in getattr(container, 'tables', []):
            for row in table.rows:
                for cell in row.cells:
                    self._process_container(cell, elements, texts)

    def _process_part(self, doc_part, elements: List[Dict[str, Any]], texts: List[str]):
        """处理文档的非主内容部分，如脚注、尾注。"""
        if not doc_part: return
        for para_element in doc_part.element.findall('.//w:p', namespaces=doc_part.element.nsmap):
            try:
                self._process_paragraph(Paragraph(para_element, doc_part), elements, texts)
            except Exception as e:
                self.logger.warning(f"处理文档部件段落时出错: {e}")

    def _pre_translate(self, document: Document) -> Tuple[DocumentObject, List[Dict[str, Any]], List[str]]:
        doc = docx.Document(BytesIO(document.content))
        elements, texts = [], []

        # 1. 处理主文档内容
        self._process_container(doc, elements, texts)

        # 2. 处理所有类型的页眉和页脚
        for section in doc.sections:
            self._process_container(section.header, elements, texts)
            self._process_container(section.first_page_header, elements, texts)
            self._process_container(section.even_page_header, elements, texts)
            self._process_container(section.footer, elements, texts)
            self._process_container(section.first_page_footer, elements, texts)
            self._process_container(section.even_page_footer, elements, texts)

        # 3. 处理脚注、尾注
        if part := getattr(doc.part, 'footnotes_part', None): self._process_part(part, elements, texts)
        if part := getattr(doc.part, 'endnotes_part', None): self._process_part(part, elements, texts)

        return doc, elements, texts

    def _apply_translation(self, element_info: Dict[str, Any], final_text: str):
        """将翻译后的文本写回对应的 OXML 元素。对于多Run的文本段，写入第一个Run并清空其余。"""
        el_type = element_info["type"]
        if el_type == "text_runs":
            runs = element_info["runs"]
            if runs:
                runs[0].text = final_text
                for run in runs[1:]:
                    run.text = ""
        elif el_type == "hyperlink":
            hyperlink = element_info["element"]
            r_elements = hyperlink.findall(f'.//{qn("w:r")}')
            if r_elements:
                first_r = r_elements[0]
                for t in first_r.findall(f'.//{qn("w:t")}'):
                    first_r.remove(t)
                new_t = OxmlElement('w:t')
                new_t.text = final_text
                new_t.set(qn('xml:space'), 'preserve')
                first_r.append(new_t)
                for other_r in r_elements[1:]:
                    if (parent := other_r.getparent()) is not None:
                        parent.remove(other_r)

    def _after_translate(self, doc: DocumentObject, elements: List[Dict[str, Any]], translated: List[str],
                         originals: List[str]) -> bytes:
        if len(elements) != len(translated):
            self.logger.error(f"Translation count mismatch! Originals: {len(originals)}, Translated: {len(translated)}. Processing common part only.")
            min_len = min(len(elements), len(translated), len(originals))
            elements, translated, originals = elements[:min_len], translated[:min_len], originals[:min_len]

        for info, orig, trans in zip(elements, originals, translated):
            if self.insert_mode == "replace":
                final_text = trans
            elif self.insert_mode == "append":
                final_text = orig + self.separator + trans
            elif self.insert_mode == "prepend":
                final_text = trans + self.separator + orig
            else:
                final_text = trans
            self._apply_translation(info, final_text)

        doc_output_stream = BytesIO()
        doc.save(doc_output_stream)
        return doc_output_stream.getvalue()

    def translate(self, document: Document) -> Self:
        doc, elements, originals = self._pre_translate(document)
        if not originals:
            self.logger.info("\nNo translatable text content found in the document.")
            document.content = self._after_translate(doc, elements, [], [])
            return self

        if self.glossary_agent:
            self.glossary_dict_gen = self.glossary_agent.send_segments(originals, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

        translated = self.translate_agent.send_segments(originals,
                                                        self.chunk_size) if self.translate_agent else originals

        document.content = self._after_translate(doc, elements, translated, originals)
        return self

    async def translate_async(self, document: Document) -> Self:
        doc, elements, originals = await asyncio.to_thread(self._pre_translate, document)
        if not originals:
            self.logger.info("\nNo translatable text content found in the document.")
            document.content = await asyncio.to_thread(self._after_translate, doc, elements, [], [])
            return self

        if self.glossary_agent:
            self.glossary_dict_gen = await self.glossary_agent.send_segments_async(originals, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

        translated = await self.translate_agent.send_segments_async(originals,
                                                                    self.chunk_size) if self.translate_agent else originals

        document.content = await asyncio.to_thread(self._after_translate, doc, elements, translated, originals)
        return self