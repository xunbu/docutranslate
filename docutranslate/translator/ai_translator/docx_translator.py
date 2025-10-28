# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from io import BytesIO
from typing import Self, Literal, List, Dict, Any, Tuple

import docx
from docx.document import Document as DocumentObject
from docx.opc.part import Part
from docx.oxml import OxmlElement
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


# ---------- 新增修改部分 1: is_styled_whitespace_run 函数被移除 ----------
# 此函数不再需要，因为新的逻辑会根据格式变化来切分，而不是根据带格式的空格。
# ---------------------- 修改结束 ----------------------

def is_tab_run(run: Run) -> bool:
    """
    检查一个 Run 是否主要代表一个制表符，应被视作格式边界。
    仅当 Run 的文本内容为空或仅包含空白，且 XML 中存在 <w:tab/> 时，
    才将其视为纯格式化用途的 Run。
    """
    # .text 属性会将 <w:tab/> 转换成 '\t'
    # 如果 .text 在去除空白后仍有内容，说明这个 Run 不仅仅是个制表符。
    if run.text.strip():
        return False

    xml = getattr(run.element, 'xml', '')
    return '<w:tab' in xml or '<w:ptab' in xml


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

    [v6.4 - 形状文本翻译]
    - 新增对形状（Shapes）内文本的提取与翻译支持。现在可以正确翻译标注、流程图等图形元素中的文字。
    - 改进了核心遍历逻辑，使其能够深入 <w:drawing> 元素，解析内部的 <w:txbxContent>（文本框内容），
      同时保持对无文本的普通图片的原有处理方式，实现鲁棒性和兼容性。

    [v6.3 - 上下文感知格式切分]
    - 根本性地改进了文本切分逻辑，解决了因带格式的空格（如下划线空格）导致连续短语被错误拆分的问题。
    - 新逻辑不再将任何带格式的空格视为固定的边界，而是通过比较相邻文本片段的“显著格式”是否一致来决定是否合并。
    - 只要格式（如下划线、高亮等）保持不变，即使中间有空格，文本也会被视为一个连续的翻译单元，
      极大地提升了对标题、合同条款等格式化文本的翻译准确性和流畅性。

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

    # ---------- 新增修改部分 2: 增加用于比较格式的辅助函数 ----------
    def _get_significant_styles(self, run: Run) -> frozenset:
        """从一个 Run 中提取“显著”格式标签的集合。"""
        if run is None:
            return frozenset()
        rPr = run.element.rPr
        if rPr is None:
            return frozenset()
        return frozenset(child.tag for child in rPr if child.tag in SIGNIFICANT_STYLES)

    def _have_same_significant_styles(self, run1: Run, run2: Run) -> bool:
        """检查两个 Run 是否具有相同的“显著”格式集合。"""
        styles1 = self._get_significant_styles(run1)
        styles2 = self._get_significant_styles(run2)
        return styles1 == styles2

    # ---------------------- 修改结束 ----------------------

    # ---------- 代码修改部分 1: 形状翻译逻辑的核心实现 ----------
    def _process_element_children(self, element, parent_paragraph: Paragraph, elements: List[Dict[str, Any]],
                                  texts: List[str],
                                  state: Dict[str, Any]):

        def flush_segment():
            current_runs = state['current_runs']
            if not current_runs:
                return
            full_text = "".join(r.text for r in current_runs)
            if full_text.strip():
                # 在 elements 中增加对父段落的引用
                elements.append({"type": "text_runs", "runs": list(current_runs), "paragraph": parent_paragraph})
                texts.append(full_text)
            state['current_runs'].clear()

        for child in element:
            if child.tag in self.IGNORED_TAGS:
                continue

            if child.tag in self.RECURSIVE_CONTAINER_TAGS:
                flush_segment()
                self._process_element_children(child, parent_paragraph, elements, texts, state)
                flush_segment()  # 在递归容器后也刷新，确保其内容成为独立片段
                continue

            field_char_element = child.find(qn('w:fldChar')) if isinstance(child, CT_R) else None
            if field_char_element is not None:
                fld_type = field_char_element.get(qn('w:fldCharType'))
                if fld_type == 'begin' or fld_type == 'end':
                    flush_segment()
                continue

            if isinstance(child, CT_R):
                # 传入 parent_paragraph 以确保 Run 对象具有正确的上下文
                run = Run(child, parent_paragraph)

                # 新增逻辑：处理形状（drawing/pict）内的文本
                # 形状可以包含文本框，需要优先于图片处理逻辑进行解析
                if '<w:drawing' in run.element.xml or '<w:pict' in run.element.xml:
                    # 使用 list() 消耗迭代器，以便检查是否找到了文本框
                    text_boxes = list(run.element.iter(qn('w:txbxContent')))
                    if text_boxes:
                        flush_segment()  # 包含文本的形状是一个边界，刷新前面的文本
                        for txbx_content in text_boxes:
                            # 遍历文本框内的所有段落
                            for p_element in txbx_content.findall(qn('w:p')):
                                # 创建新的段落对象，并传入父级上下文
                                shape_para = Paragraph(p_element, parent_paragraph)
                                # 递归处理该段落
                                self._process_paragraph(shape_para, elements, texts)

                        # 如果处理了形状内的文本，则该 Run 的任务已完成
                        continue

                # 保留原有逻辑: 检查绝对边界（图片、制表符等）
                if is_image_run(run) or is_formatting_only_run(run) or is_tab_run(run):
                    flush_segment()
                    continue  # 这些 Run 本身不包含在任何文本片段中

                # 保留原有逻辑: 基于格式变化进行切分
                last_run_in_segment = state['current_runs'][-1] if state['current_runs'] else None
                if last_run_in_segment and not self._have_same_significant_styles(last_run_in_segment, run):
                    flush_segment()

                # 将当前 Run 添加到片段中
                state['current_runs'].append(run)
            else:
                # 遇到任何非 Run 的块级元素（如在单元格中嵌套的表格），都应结束当前文本片段。
                flush_segment()

    def _process_paragraph(self, para: Paragraph, elements: List[Dict[str, Any]], texts: List[str]):
        state = {
            'current_runs': [],
        }
        # 修改调用：传入 `para` 对象作为父级上下文
        self._process_element_children(para._p, para, elements, texts, state)

        # 确保在段落处理结束时，刷新所有剩余的 Run
        current_runs = state['current_runs']
        if current_runs:
            full_text = "".join(r.text for r in current_runs)
            if full_text.strip():
                elements.append({"type": "text_runs", "runs": list(current_runs), "paragraph": para})
                texts.append(full_text)
            current_runs.clear()

    # ---------------------- 修改结束 ----------------------

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
            # 找到第一个可以写入文本的run
            for i, run in enumerate(runs):
                if run.element.getparent() is not None:
                    # 如果 run 是副本的一部分，其 _parent 可能仍然指向原始文档的段落
                    # 但我们需要确保它与 element_info["paragraph"] 同步
                    run._parent = element_info["paragraph"]
                    run.text = final_text
                    first_real_run_index = i
                    break

            # 如果没有找到有效的run（例如，它们都已被删除），则记录警告
            if first_real_run_index == -1:
                self.logger.warning(f"无法应用翻译 '{final_text}'，因为找不到有效的run。")
                return

            # 删除所有后续的run，因为它们的文本已经被合并到第一个run中了
            for i in range(first_real_run_index + 1, len(runs)):
                run = runs[i]
                parent_element = run.element.getparent()
                if parent_element is not None:
                    try:
                        parent_element.remove(run.element)
                    except ValueError:
                        # 在某些复杂情况下，一个run可能已经被其父元素隐式删除
                        self.logger.debug(f"尝试删除一个不存在的run元素。这通常是安全的。")
                        pass

    # ---------- FIX START: 新增用于清理副本段落的辅助方法 ----------
    def _prune_unwanted_elements_from_copy(self, p_element: OxmlElement):
        """
        从复制的段落元素中移除包含图片或页码字段的 Run。
        这可以防止在“append”和“prepend”模式下出现重复。
        """
        runs_to_remove = []
        runs = p_element.findall(qn('w:r'))

        i = 0
        while i < len(runs):
            run_element = runs[i]

            # 检查图片
            if run_element.find(qn('w:drawing')) is not None or run_element.find(qn('w:pict')) is not None:
                runs_to_remove.append(run_element)
                i += 1
                continue

            # 检查页码字段
            fldChar = run_element.find(qn('w:fldChar'))
            if fldChar is not None and fldChar.get(qn('w:fldCharType')) == 'begin':
                is_page_field = False
                field_end_index = -1

                # 向前查找以确定是否是页码字段
                for j in range(i + 1, len(runs)):
                    next_run = runs[j]
                    instrText = next_run.find(qn('w:instrText'))
                    if instrText is not None and instrText.text is not None:
                        text = instrText.text.strip().upper()
                        if 'PAGE' in text or 'NUMPAGES' in text:
                            is_page_field = True
                        break

                    next_fldChar = next_run.find(qn('w:fldChar'))
                    if next_fldChar is not None and next_fldChar.get(qn('w:fldCharType')) == 'begin':
                        break

                if is_page_field:
                    # 如果是页码字段，则找到其结束标记并标记整个字段的 runs
                    field_runs_to_remove = [run_element]
                    end_found = False
                    for j in range(i + 1, len(runs)):
                        field_run = runs[j]
                        field_runs_to_remove.append(field_run)
                        end_fldChar = field_run.find(qn('w:fldChar'))
                        if end_fldChar is not None and end_fldChar.get(qn('w:fldCharType')) == 'end':
                            end_found = True
                            field_end_index = j
                            break

                    if end_found:
                        runs_to_remove.extend(field_runs_to_remove)
                        i = field_end_index + 1
                        continue
            i += 1

        # 从 XML 树中实际移除被标记的 runs
        for run_to_remove in runs_to_remove:
            if run_to_remove.getparent() is not None:
                p_element.remove(run_to_remove)

    # ---------- FIX END ----------

    def _after_translate(self, doc: DocumentObject, elements: List[Dict[str, Any]], translated: List[str],
                         originals: List[str]) -> bytes:
        if len(elements) != len(translated):
            self.logger.error(
                f"翻译数量不匹配！原文: {len(originals)}, 译文: {len(translated)}. 将只处理公共部分。")
            min_len = min(len(elements), len(translated), len(originals))
            elements, translated, originals = elements[:min_len], translated[:min_len], originals[:min_len]

        if self.insert_mode == "replace":
            for info, trans in zip(elements, translated):
                self._apply_translation(info, trans)
        else:
            paragraph_segments = defaultdict(list)
            # [结构优化] 预先按段落对所有片段进行分组
            for i, info in enumerate(elements):
                paragraph = info["paragraph"]
                paragraph_segments[id(paragraph._p)].append({
                    "index": i,
                    "translation": translated[i],
                    "paragraph_obj": paragraph
                })

            # [结构优化] 直接遍历按段落分组后的字典，每个段落只处理一次
            for para_id, segments_for_this_para in paragraph_segments.items():
                # 从该组的第一个片段中获取唯一的段落对象
                paragraph = segments_for_this_para[0]["paragraph_obj"]
                p_element = paragraph._p

                translated_p_element = deepcopy(p_element)

                # ---------- FIX: 在处理副本前调用新增的修剪逻辑 ----------
                self._prune_unwanted_elements_from_copy(translated_p_element)
                # -------------------------------------------------------------

                translated_paragraph_obj = Paragraph(translated_p_element, paragraph._parent)

                # [超链接修复] 使用 iter() 进行深度搜索，而不是 findall()
                original_r_elements = p_element.iter(qn('w:r'))
                copied_r_elements = translated_p_element.iter(qn('w:r'))
                element_map = {
                    id(orig_r): copied_r
                    for orig_r, copied_r in zip(original_r_elements, copied_r_elements)
                }

                for seg_info in segments_for_this_para:
                    element_index = seg_info["index"]
                    translation = seg_info["translation"]
                    original_element_info = elements[element_index]

                    runs_from_copy = []
                    for r in original_element_info["runs"]:
                        copied_r_element = element_map.get(id(r.element))
                        if copied_r_element is not None:
                            new_run = Run(copied_r_element, translated_paragraph_obj)
                            runs_from_copy.append(new_run)

                    if not runs_from_copy:
                        self.logger.warning("在副本段落中找不到对应的Runs，跳过翻译应用。")
                        continue

                    translated_element_info = {
                        "type": "text_runs",
                        "runs": runs_from_copy,
                        "paragraph": translated_paragraph_obj
                    }
                    self._apply_translation(translated_element_info, translation)

                # --- 分隔符和插入逻辑 (保持不变) ---
                separator_p_element = None
                if self.separator:
                    separator_p_element = OxmlElement('w:p')
                    run_element = OxmlElement('w:r')
                    lines = self.separator.split('\n')
                    for i, line in enumerate(lines):
                        text_element = OxmlElement('w:t')
                        text_element.set(qn('xml:space'), 'preserve')
                        text_element.text = line
                        run_element.append(text_element)
                        if i < len(lines) - 1:
                            run_element.append(OxmlElement('w:br'))
                    separator_p_element.append(run_element)

                if self.insert_mode == "append":
                    current_element = p_element
                    if separator_p_element is not None:
                        current_element.addnext(separator_p_element)
                        current_element = separator_p_element
                    current_element.addnext(translated_p_element)
                elif self.insert_mode == "prepend":
                    p_element.addprevious(translated_p_element)
                    if separator_p_element is not None:
                        translated_p_element.addnext(separator_p_element)

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