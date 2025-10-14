# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
from dataclasses import dataclass
from io import BytesIO
from typing import Self, Literal, List, Dict, Any, Tuple

import docx
from docx.document import Document as DocumentObject
from docx.oxml.ns import qn
from docx.oxml.text.run import CT_R
from docx.text.paragraph import Paragraph
from docx.text.run import Run
from docx.table import _Cell, Table

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
    检查一个 Run 是否主要用于格式化，例如一个空的粗体/斜体/下划线 Run。
    """
    text = run.text
    if not text.strip():
        if run.underline or run.bold or run.italic or run.font.strike or run.font.subscript or run.font.superscript:
            return True
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
    一个基于高级结构化解析的 .docx 文件翻译器。
    它能高精度保留样式，并正确处理正文、表格、页眉/脚、脚注/尾注、超链接和目录(TOC)等复杂元素。

    [v4.1 - 稳定版重构]
    - 移除所有对 python-docx 内部类的脆弱导入和猴子补丁。
    - 实现了一个健壮的、基于鸭子类型的 _traverse_container 函数来统一处理所有文本容器。
    """
    IGNORED_TAGS = {
        qn('w:proofErr'), qn('w:lastRenderedPageBreak'), qn('w:bookmarkStart'),
        qn('w:bookmarkEnd'), qn('w:commentRangeStart'), qn('w:commentRangeEnd'),
        qn('w:del'), qn('w:ins'), qn('w:moveFrom'), qn('w:moveTo'),
    }
    RECURSIVE_CONTAINER_TAGS = {
        qn('w:smartTag'), qn('w:sdtContent'), qn('w:hyperlink'),
    }

    def __init__(self, config: DocxTranslatorConfig):
        super().__init__(config=config)
        self.chunk_size = config.chunk_size
        self.translate_agent = None
        if not self.skip_translate:
            agent_config = SegmentsTranslateAgentConfig(
                custom_prompt=config.custom_prompt, to_lang=config.to_lang, base_url=config.base_url,
                api_key=config.api_key, model_id=config.model_id, temperature=config.temperature,
                thinking=config.thinking, concurrent=config.concurrent, timeout=config.timeout,
                logger=self.logger, glossary_dict=config.glossary_dict, retry=config.retry,
                system_proxy_enable=config.system_proxy_enable
            )
            self.translate_agent = SegmentsTranslateAgent(agent_config)
        self.insert_mode = config.insert_mode
        self.separator = config.separator

    def _process_element_children(self, element, elements: List[Dict[str, Any]], texts: List[str],
                                  state: Dict[str, Any]):
        current_runs = state['current_runs']

        def flush_segment():
            nonlocal current_runs
            if not current_runs: return
            full_text = "".join(r.text for r in current_runs)
            if full_text.strip():
                elements.append({"type": "text_runs", "runs": current_runs})
                texts.append(full_text)
            current_runs = []
            state['current_runs'] = current_runs

        for child in element:
            if child.tag in self.IGNORED_TAGS:
                continue
            if child.tag in self.RECURSIVE_CONTAINER_TAGS:
                self._process_element_children(child, elements, texts, state)
                continue
            field_char_element = child.find(qn('w:fldChar')) if isinstance(child, CT_R) else (
                child if child.tag == qn('w:fldChar') else None)
            if field_char_element is not None:
                flush_segment()
                fld_type = field_char_element.get(qn('w:fldCharType'))
                if fld_type == 'begin':
                    state['field_depth'] += 1
                elif fld_type == 'end':
                    state['field_depth'] = max(0, state['field_depth'] - 1)
                continue
            if isinstance(child, CT_R):
                # 只跳过包含域指令的 Run
                if child.find(qn('w:instrText')) is not None:
                    continue

                # 删除了 'if state['field_depth'] > 0: continue' 这一行

                run = Run(child, None)
                if is_image_run(run) or is_formatting_only_run(run):
                    flush_segment()
                else:
                    current_runs.append(run)
            else:
                flush_segment()
        state['current_runs'] = current_runs

    def _process_paragraph(self, para: Paragraph, elements: List[Dict[str, Any]], texts: List[str]):
        if not para.text.strip():
            return
        state = {'current_runs': [], 'field_depth': 0}
        self._process_element_children(para._p, elements, texts, state)
        current_runs = state['current_runs']
        if current_runs:
            full_text = "".join(r.text for r in current_runs)
            if full_text.strip():
                elements.append({"type": "text_runs", "runs": current_runs})
                texts.append(full_text)

    def _traverse_container(self, container, elements: List[Dict[str, Any]], texts: List[str]):
        """
        [核心导航员] 健壮地遍历任何文本容器 (Document, _Cell, _Header, etc.)。
        """
        if container is None:
            return

        # --- 关键修复 ---
        # 通过检查属性来确定如何获取子元素，而不是依赖于对象的具体类型。
        # 这种方法对所有类型的容器都有效。
        parent_element = None
        if hasattr(container, 'element') and hasattr(container.element, 'body'):
            parent_element = container.element.body  # For Document
        elif hasattr(container, '_element'):
            parent_element = container._element  # For _Cell, _Header, _Footer, NotesParts

        if parent_element is None:
            return

        for child_element in parent_element:
            if child_element.tag.endswith('p'):
                self._process_paragraph(Paragraph(child_element, container), elements, texts)
            elif child_element.tag.endswith('tbl'):
                table = Table(child_element, container)
                for row in table.rows:
                    for cell in row.cells:
                        self._traverse_container(cell, elements, texts)

    def _pre_translate(self, document: Document) -> Tuple[DocumentObject, List[Dict[str, Any]], List[str]]:
        doc = docx.Document(BytesIO(document.content))
        elements, texts = [], []

        # 1. 处理主文档内容
        self._traverse_container(doc, elements, texts)

        # 2. 处理所有节的页眉和页脚
        for section in doc.sections:
            self._traverse_container(section.header, elements, texts)
            self._traverse_container(section.first_page_header, elements, texts)
            self._traverse_container(section.even_page_header, elements, texts)
            self._traverse_container(section.footer, elements, texts)
            self._traverse_container(section.first_page_footer, elements, texts)
            self._traverse_container(section.even_page_footer, elements, texts)

        # 3. 处理脚注和尾注
        if hasattr(doc.part, 'footnotes_part') and doc.part.footnotes_part is not None:
            self._traverse_container(doc.part.footnotes_part, elements, texts)
        if hasattr(doc.part, 'endnotes_part') and doc.part.endnotes_part is not None:
            self._traverse_container(doc.part.endnotes_part, elements, texts)

        return doc, elements, texts

    def _apply_translation(self, element_info: Dict[str, Any], final_text: str):
        if element_info["type"] == "text_runs":
            runs = element_info["runs"]
            if not runs: return
            runs[0].text = final_text
            for run in runs[1:]:
                parent_element = run.element.getparent()
                if parent_element is not None:
                    try:
                        parent_element.remove(run.element)
                    except ValueError:
                        pass

    def _after_translate(self, doc: DocumentObject, elements: List[Dict[str, Any]], translated: List[str],
                         originals: List[str]) -> bytes:
        if len(elements) != len(translated):
            self.logger.error(
                f"翻译数量不匹配！原文: {len(originals)}, 译文: {len(translated)}. 将只处理公共部分。")
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
            self.logger.info("\n文档中未找到可翻译的文本内容。")
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
            self.logger.info("\n文档中未找到可翻译的文本内容。")
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