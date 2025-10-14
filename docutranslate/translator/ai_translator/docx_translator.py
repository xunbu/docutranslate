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

    [v6.1 - 笔误修复版]
    - 修复了 qn() 函数调用中的一个笔误 ('w:w:fldCharType')，该错误会导致程序崩溃。
    - 实现了基于“有效视觉样式”的智能分段逻辑。
    - 修复了对域代码（Fields）结果文本的错误跳过问题。
    - 新增了对结构化文档标签（SDT）的递归解析。
    - 修复了因页眉/页脚对象共享导致文本被重复提取和翻译的问题。
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

    def _get_run_style_signature(self, run: Run) -> tuple:
        """
        获取 Run 的“有效视觉样式”签名。
        通过比较 python-docx 计算后的最终属性（如字体、大小、颜色等），
        可以正确处理样式继承，比直接比较 XML 更健壮。
        """
        f = run.font
        return (
            f.name,
            f.size,
            f.bold,
            f.italic,
            f.underline,
            f.strike,
            f.all_caps,
            f.small_caps,
            f.color.rgb if f.color and f.color.rgb is not None else None,
            f.highlight_color,
        )

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
                # 【笔误修复】: 修正了 'w:w:fldCharType' 为 'w:fldCharType'
                fld_type = field_char_element.get(qn('w:fldCharType'))
                if fld_type == 'begin':
                    state['field_depth'] += 1
                elif fld_type == 'end':
                    state['field_depth'] = max(0, state['field_depth'] - 1)
                continue

            if isinstance(child, CT_R):
                if child.find(qn('w:instrText')) is not None:
                    continue

                run = Run(child, None)

                if is_image_run(run):
                    flush_segment()
                    continue

                if not run.text:
                    continue

                current_run_style_sig = self._get_run_style_signature(run)

                if not current_runs:
                    current_runs.append(run)
                else:
                    last_run_style_sig = self._get_run_style_signature(current_runs[-1])
                    if current_run_style_sig == last_run_style_sig:
                        current_runs.append(run)
                    else:
                        flush_segment()
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

    def _process_body_elements(self, parent_element, container, elements: List[Dict[str, Any]], texts: List[str]):
        """ 遍历一个容器内的所有顶级元素（段落、表格、内容控件等） """
        for child_element in parent_element:
            if child_element.tag.endswith('p'):
                self._process_paragraph(Paragraph(child_element, container), elements, texts)
            elif child_element.tag.endswith('tbl'):
                table = Table(child_element, container)
                for row in table.rows:
                    for cell in row.cells:
                        self._traverse_container(cell, elements, texts)
            elif child_element.tag.endswith('sdt'):
                sdt_content = child_element.find(qn('w:sdtContent'))
                if sdt_content is not None:
                    self._process_body_elements(sdt_content, container, elements, texts)

    def _traverse_container(self, container, elements: List[Dict[str, Any]], texts: List[str]):
        """
        [核心导航员] 健壮地遍历任何文本容器 (Document, _Cell, _Header, etc.)。
        """
        if container is None:
            return

        parent_element = None
        if hasattr(container, 'element') and hasattr(container.element, 'body'):
            parent_element = container.element.body
        elif hasattr(container, '_element'):
            parent_element = container._element

        if parent_element is not None:
            self._process_body_elements(parent_element, container, elements, texts)

    def _pre_translate(self, document: Document) -> Tuple[DocumentObject, List[Dict[str, Any]], List[str]]:
        doc = docx.Document(BytesIO(document.content))
        elements, texts = [], []
        processed_container_ids = set()

        def process_once(container):
            """一个辅助函数，确保每个容器只被处理一次"""
            if container is None or id(container) in processed_container_ids:
                return
            processed_container_ids.add(id(container))
            self._traverse_container(container, elements, texts)

        # 1. 处理主文档内容
        process_once(doc)

        # 2. 处理所有节的页眉和页脚
        for section in doc.sections:
            process_once(section.header)
            process_once(section.first_page_header)
            process_once(section.even_page_header)
            process_once(section.footer)
            process_once(section.first_page_footer)
            process_once(section.even_page_footer)

        # 3. 处理脚注和尾注
        if hasattr(doc.part, 'footnotes_part') and doc.part.footnotes_part is not None:
            process_once(doc.part.footnotes_part)
        if hasattr(doc.part, 'endnotes_part') and doc.part.endnotes_part is not None:
            process_once(doc.part.endnotes_part)

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