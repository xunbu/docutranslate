# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
from dataclasses import dataclass
from io import BytesIO
from typing import Self, Literal, List, Dict, Any, Tuple

import docx
from docx.document import Document as DocumentObject
from docx.opc.part import Part
from docx.oxml.ns import qn
from docx.oxml.text.run import CT_R
from docx.section import _Header, _Footer
from docx.text.paragraph import Paragraph
from docx.text.run import Run
from docx.table import _Cell, Table

from docutranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator


# ---------------- 辅助函数 ----------------

# [v6.2] 定义一组具有显著视觉效果的格式标签。
# 我们只在 Run 包含这些格式时才将其视为空白格式边界。
# 这避免了因字体、字号等微小变化导致的过度文本切分。
SIGNIFICANT_STYLES = frozenset([
    qn('w:u'),  # 下划线
    qn('w:strike'),  # 删除线
    qn('w:dstrike'),  # 双删除线
    qn('w:shd'),  # 底纹/背景色
    qn('w:highlight'),  # 荧光笔高亮
    qn('w:bdr'),  # 边框
    qn('w:effectLst'),  # 文本效果 (如发光、阴影)
    qn('w:em'),  # 强调标记 (着重号)
])


def is_image_run(run: Run) -> bool:
    """检查一个 Run 是否包含图片。"""
    xml = getattr(run.element, 'xml', '')
    return '<w:drawing' in xml or '<w:pict' in xml


def is_formatting_only_run(run: Run) -> bool:
    """
    检查一个 Run 是否仅用于格式化，不包含任何应被渲染的文本。
    这仅适用于其 .text 属性为 "" 的情况。
    """
    return run.text == ""


def is_styled_whitespace_run(run: Run) -> bool:
    """
    [v6.2] 检查一个 Run 是否只包含空白字符，但应用了应保留的“显著”格式。
    这些 Run 应被视为翻译段的边界并保持不变。
    """
    if not (run.text and run.text.isspace()):
        return False

    rPr = run.element.rPr
    if rPr is None:
        return False

    # 仅当 Run 的属性中包含我们定义的“显著”样式之一时，才返回 True。
    return any(child.tag in SIGNIFICANT_STYLES for child in rPr)


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

    [v6.2 - 精确格式保留]
    - 根据用户反馈，精确定义了构成“重要格式”的样式范围。
    - 现在仅在空白 Run 包含下划线、背景色、边框等显著视觉样式时才将其视为边界。
    - 忽略了加粗、倾斜、字体/字号变化等对空格本身无视觉效果或不重要的样式，
      避免了因此对翻译句子造成不必要的切分，提升了翻译质量。

    [v6.1 - 格式保留修复版]
    - 修复了因合并 Run 导致下划线等格式在翻译后丢失的问题。
    - 通过引入 is_styled_whitespace_run 检查，将仅包含空格但带有样式的 Run（如下划线空格）
      视为与图片类似的不可翻译边界。

    [v6.0 - 语义切分重构版]
    - 重构核心逻辑，不再跳过域结果，而是将其作为语义边界来切分文本，增强了鲁棒性。
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

        def flush_segment():
            current_runs = state['current_runs']
            if not current_runs:
                return
            full_text = "".join(r.text for r in current_runs)
            if full_text.strip():
                elements.append({"type": "text_runs", "runs": list(current_runs)})
                texts.append(full_text)
            state['current_runs'].clear()

        for child in element:
            if child.tag in self.IGNORED_TAGS:
                continue

            if child.tag in self.RECURSIVE_CONTAINER_TAGS:
                flush_segment()
                self._process_element_children(child, elements, texts, state)
                continue

            field_char_element = child.find(qn('w:fldChar')) if isinstance(child, CT_R) else None
            if field_char_element is not None:
                fld_type = field_char_element.get(qn('w:fldCharType'))
                if fld_type == 'begin' or fld_type == 'end':
                    flush_segment()
                continue

            if isinstance(child, CT_R):
                run = Run(child, None)
                # [v6.2] 使用更精确的检查来识别作为边界的 Run。
                if is_image_run(run) or is_formatting_only_run(run) or is_styled_whitespace_run(run):
                    flush_segment()
                else:
                    state['current_runs'].append(run)
            else:
                flush_segment()

    def _process_paragraph(self, para: Paragraph, elements: List[Dict[str, Any]], texts: List[str]):
        # [v6.2] 此处无需检查 para.text.strip()，因为一个段落可能只包含一个带样式的空白 Run，
        # 这种 Run 我们需要保留，而 .text.strip() 会将其视为空。
        # 具体的文本提取逻辑在 _process_element_children 中处理。
        state = {
            'current_runs': [],
        }
        self._process_element_children(para._p, elements, texts, state)

        current_runs = state['current_runs']
        if current_runs:
            full_text = "".join(r.text for r in current_runs)
            if full_text.strip():
                elements.append({"type": "text_runs", "runs": list(current_runs)})
                texts.append(full_text)
            current_runs.clear()

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

    def _traverse_container(self, container: Any, elements: List[Dict[str, Any]], texts: List[str]):
        """
        [核心导航员 v2.0 - 增强版] 健壮地遍历任何文本容器，
        特别为具有额外嵌套层的 Part (如脚注/尾注) 提供了专门处理逻辑。
        """
        if container is None:
            return

        parent_element = None
        if isinstance(container, (DocumentObject, Part)):
            parent_element = container.element.body if hasattr(container.element, 'body') else container.element
        elif isinstance(container, (_Cell, _Header, _Footer)):
            parent_element = container._element
        else:
            self.logger.warning(f"跳过未知类型的容器: {type(container)}")
            return

        if parent_element is not None and parent_element.tag in [qn('w:footnotes'), qn('w:endnotes')]:
            for note_element in parent_element:
                self._process_body_elements(note_element, container, elements, texts)
        elif parent_element is not None:
            self._process_body_elements(parent_element, container, elements, texts)

    def _pre_translate(self, document: Document) -> Tuple[DocumentObject, List[Dict[str, Any]], List[str]]:
        doc = docx.Document(BytesIO(document.content))
        elements, texts = [], []

        self._traverse_container(doc, elements, texts)

        for section in doc.sections:
            self._traverse_container(section.header, elements, texts)
            self._traverse_container(section.first_page_header, elements, texts)
            self._traverse_container(section.even_page_header, elements, texts)
            self._traverse_container(section.footer, elements, texts)
            self._traverse_container(section.first_page_footer, elements, texts)
            self._traverse_container(section.even_page_footer, elements, texts)

        if hasattr(doc.part, 'footnotes_part') and doc.part.footnotes_part is not None:
            self._traverse_container(doc.part.footnotes_part, elements, texts)
        if hasattr(doc.part, 'endnotes_part') and doc.part.endnotes_part is not None:
            self._traverse_container(doc.part.endnotes_part, elements, texts)

        return doc, elements, texts

    def _apply_translation(self, element_info: Dict[str, Any], final_text: str):
        if element_info["type"] == "text_runs":
            runs = element_info["runs"]
            if not runs: return

            first_real_run_index = -1
            for i, run in enumerate(runs):
                if run.element.getparent() is not None:
                    run.text = final_text
                    first_real_run_index = i
                    break

            if first_real_run_index == -1:
                self.logger.warning(f"无法应用翻译 '{final_text}'，因为找不到有效的run。")
                return

            for i in range(first_real_run_index + 1, len(runs)):
                run = runs[i]
                parent_element = run.element.getparent()
                if parent_element is not None:
                    try:
                        parent_element.remove(run.element)
                    except ValueError:
                        self.logger.debug(f"尝试删除一个不存在的run元素。这通常是安全的。")
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