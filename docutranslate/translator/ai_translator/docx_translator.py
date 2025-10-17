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

# 注意：根据最终方案，lxml 不再需要，已移除
# from lxml import etree

from docutranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator


# ---------------- 辅助函数 ----------------
def is_image_run(run: Run) -> bool:
    """检查一个 Run 是否包含图片。"""
    xml = getattr(run.element, 'xml', '')
    return '<w:drawing' in xml or '<w:pict' in xml


# ==================== MODIFICATION START ====================
#  对 is_formatting_only_run 函数进行了修改
#  旧的实现无法识别仅包含颜色等 rPr 属性的空 Run，导致其与后续文本 Run 错误合并。
# #  新的实现通过一个更简单的标准来判断：只要一个 Run 的文本内容为空，
# #  它就被认为是纯格式化的，从而解决了交叉引用文本消失的问题。
# ==========================================================
def is_formatting_only_run(run: Run) -> bool:
    """
    检查一个 Run 是否仅用于格式化，不包含任何应被渲染的文本。
    这仅适用于其 .text 属性为 "" 的情况。
    """
    return run.text == ""


# ===================== MODIFICATION END =====================


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

    [v5.3 - 语义切分修复版]
    - 修复了 v5.2 方案中因过度切分格式变化文本（如 H₂O）导致翻译上下文丢失的问题。
    - 废弃了基于 <w:rPr> 比较的切分逻辑，转而采用更稳健的语义边界切分。
    - 核心改动：在处理完一个域（Field）的结束标记（fldCharType="end"）后强制刷新文本段，
      这既能正确分离引用标记（如[1]）与后续文本，防止格式污染，又能保持化学式等
      含格式变化的连续文本的完整性。

    [v5.1 - 遍历修复版]
    - 重构了核心遍历函数 _traverse_container，使其能稳健处理所有类型的文本容器，
      包括页眉 (header)、页脚 (footer)、脚注 (footnote) 和尾注 (endnote)。

    [v5.0 - 增强版]
    - 引入了智能域处理状态机，精确识别并跳过 PAGEREF (页码) 和 SEQ (序号) 等不应翻译的动态域内容。
    - 优化了文本切分逻辑，解决了目录(TOC)和图表目录(TOF)条目被错误拆分为“标题”和“页码”两部分的问题。
    - 根除了因复杂域处理不当导致的目录项重复翻译问题，确保每个条目只被提取和翻译一次。
    """
    IGNORED_TAGS = {
        qn('w:proofErr'), qn('w:lastRenderedPageBreak'), qn('w:bookmarkStart'),
        qn('w:bookmarkEnd'), qn('w:commentRangeStart'), qn('w:commentRangeEnd'),
        qn('w:del'), qn('w:ins'), qn('w:moveFrom'), qn('w:moveTo'),
    }
    RECURSIVE_CONTAINER_TAGS = {
        qn('w:smartTag'), qn('w:sdtContent'), qn('w:hyperlink'),
    }
    # [v5.0] 定义不应翻译其结果的域指令
    SKIPPABLE_FIELD_INSTRUCTIONS = {'PAGEREF', 'SEQ', 'PAGE', 'NUMPAGES', 'DATE', 'TIME', 'SECTION'}

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

            # --- [v5.3] 智能域处理逻辑 ---
            instr_text_element = child.find(qn('w:instrText')) if isinstance(child, CT_R) else None
            if instr_text_element is not None:
                instr_text = instr_text_element.text.strip()
                if any(keyword in instr_text for keyword in self.SKIPPABLE_FIELD_INSTRUCTIONS):
                    state['is_in_skippable_field'] = True
                continue

            field_char_element = child.find(qn('w:fldChar')) if isinstance(child, CT_R) else (
                child if child.tag == qn('w:fldChar') else None)
            if field_char_element is not None:
                fld_type = field_char_element.get(qn('w:fldCharType'))
                if fld_type == 'begin':
                    flush_segment()
                    state['is_in_skippable_field'] = False
                    state['is_skipping_result'] = False
                elif fld_type == 'separate':
                    if state.get('is_in_skippable_field'):
                        flush_segment()
                        state['is_skipping_result'] = True
                elif fld_type == 'end':
                    # ===== [v5.3] 关键改动 =====
                    # 在域结束后强制刷新，确保域结果（如[1]）和后面的文本分开。
                    # 这就是我们需要的语义边界。
                    flush_segment()
                    state['is_in_skippable_field'] = False
                    state['is_skipping_result'] = False
                continue

            if state.get('is_skipping_result'):
                continue
            # --- 域处理逻辑结束 ---

            if isinstance(child, CT_R):
                run = Run(child, None)
                if is_image_run(run) or is_formatting_only_run(run):
                    flush_segment()
                else:
                    # [v5.3] 移除了 v5.2 的 rPr 比较逻辑，允许 H₂O 合并
                    state['current_runs'].append(run)
            else:
                flush_segment()

    def _process_paragraph(self, para: Paragraph, elements: List[Dict[str, Any]], texts: List[str]):
        if not para.text.strip():
            return
        state = {
            'current_runs': [],
            'is_in_skippable_field': False,
            'is_skipping_result': False
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
        # 首先获取包含内容的顶层 XML 元素
        if isinstance(container, (DocumentObject, Part)):
            # 对于 Document 和 Part 对象 (如 FootnotesPart)，使用 .element
            parent_element = container.element.body if hasattr(container.element, 'body') else container.element
        elif isinstance(container, (_Cell, _Header, _Footer)):
            # 对于内部块容器，使用 ._element
            parent_element = container._element
        else:
            # 如果遇到未知类型，记录警告并返回
            self.logger.warning(f"跳过未知类型的容器: {type(container)}")
            return

        # 检查是否是需要特殊处理的嵌套结构 (如脚注/尾注)
        if parent_element is not None and parent_element.tag in [qn('w:footnotes'), qn('w:endnotes')]:
            # 遍历每个 <w:footnote> 或 <w:endnote> 元素
            for note_element in parent_element:
                # 在每个注释元素内部处理其包含的段落和表格
                self._process_body_elements(note_element, container, elements, texts)
        elif parent_element is not None:
            # 对于其他所有容器 (body, tc, hdr, ftr)，直接处理其子元素
            self._process_body_elements(parent_element, container, elements, texts)

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

            first_real_run_index = -1
            for i, run in enumerate(runs):
                # 确保run仍然在文档树中
                if run.element.getparent() is not None:
                    # 找到第一个可以写入文本的run
                    run.text = final_text
                    first_real_run_index = i
                    break

            if first_real_run_index == -1:
                self.logger.warning(f"无法应用翻译 '{final_text}'，因为找不到有效的run。")
                return

            # 从第一个有效的run之后开始，删除所有多余的run
            for i in range(first_real_run_index + 1, len(runs)):
                run = runs[i]
                parent_element = run.element.getparent()
                if parent_element is not None:
                    try:
                        parent_element.remove(run.element)
                    except ValueError:
                        # 如果元素已经被其他操作移除，这里会抛出ValueError，可以安全地忽略
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