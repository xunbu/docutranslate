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


def is_tab_run(run: Run) -> bool:
    """
    检查一个 Run 是否主要代表一个制表符，应被视作格式边界。
    """
    if run.text.strip():
        return False
    xml = getattr(run.element, 'xml', '')
    return '<w:tab' in xml or '<w:ptab' in xml


def is_instr_text_run(run: Run) -> bool:
    """
    检查一个 Run 是否包含域指令文本 (w:instrText)。
    目录(TOC)、页码、超链接等功能的指令代码存储在此标签中。
    必须跳过这些 Run，否则写入 text 会破坏域结构。
    """
    return run.element.find(qn('w:instrText')) is not None


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
        glossary_dict = self.glossary.glossary_dict if self.glossary else None
        if not self.skip_translate:
            agent_config = SegmentsTranslateAgentConfig(
                custom_prompt=config.custom_prompt, to_lang=config.to_lang, base_url=config.base_url,
                api_key=config.api_key, model_id=config.model_id, temperature=config.temperature,
                thinking=config.thinking, concurrent=config.concurrent, timeout=config.timeout,
                logger=self.logger, glossary_dict=glossary_dict, retry=config.retry,
                system_proxy_enable=config.system_proxy_enable, force_json=config.force_json,
                rpm=config.rpm,
                tpm=config.tpm,
                provider=config.provider,
                extra_body=config.extra_body,
            )
            self.translate_agent = SegmentsTranslateAgent(agent_config)
        self.insert_mode = config.insert_mode
        self.separator = config.separator

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

    def _process_element_children(self, element, parent_paragraph: Paragraph, elements: List[Dict[str, Any]],
                                  texts: List[str],
                                  state: Dict[str, Any],
                                  top_level_para: Paragraph):

        def flush_segment():
            current_runs = state['current_runs']
            if not current_runs:
                return
            full_text = "".join(r.text for r in current_runs)
            if full_text.strip():
                # 在 elements 中增加对父段落和顶级段落的引用
                elements.append({
                    "type": "text_runs",
                    "runs": list(current_runs),
                    "paragraph": parent_paragraph,
                    "top_level_paragraph": top_level_para
                })
                texts.append(full_text)
            state['current_runs'].clear()

        for child in element:
            if child.tag in self.IGNORED_TAGS:
                continue

            if child.tag in self.RECURSIVE_CONTAINER_TAGS:
                flush_segment()
                self._process_element_children(child, parent_paragraph, elements, texts, state, top_level_para)
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

                if '<w:drawing' in run.element.xml or '<w:pict' in run.element.xml:
                    text_boxes = list(run.element.iter(qn('w:txbxContent')))
                    if text_boxes:
                        flush_segment()  # 包含文本的形状是一个边界，刷新前面的文本
                        for txbx_content in text_boxes:
                            for p_element in txbx_content.findall(qn('w:p')):
                                shape_para = Paragraph(p_element, parent_paragraph)
                                self._process_paragraph(shape_para, elements, texts, top_level_para=top_level_para)
                        continue

                # 增加对 instrText 的检查，防止提取出 TOC 指令作为原文
                if is_image_run(run) or is_formatting_only_run(run) or is_tab_run(run) or is_instr_text_run(run):
                    flush_segment()
                    continue

                # 保留原有逻辑: 基于格式变化进行切分
                last_run_in_segment = state['current_runs'][-1] if state['current_runs'] else None
                if last_run_in_segment and not self._have_same_significant_styles(last_run_in_segment, run):
                    flush_segment()

                state['current_runs'].append(run)
            else:
                flush_segment()

    def _process_paragraph(self, para: Paragraph, elements: List[Dict[str, Any]], texts: List[str],
                           top_level_para: Paragraph = None):
        if top_level_para is None:
            top_level_para = para

        state = {
            'current_runs': [],
        }
        self._process_element_children(para._p, para, elements, texts, state, top_level_para)

        current_runs = state['current_runs']
        if current_runs:
            full_text = "".join(r.text for r in current_runs)
            if full_text.strip():
                elements.append({
                    "type": "text_runs",
                    "runs": list(current_runs),
                    "paragraph": para,
                    "top_level_paragraph": top_level_para
                })
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
                    run._parent = element_info["paragraph"]
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

    def _prune_unwanted_elements_from_copy(self, p_element: OxmlElement):
        """
        从复制的段落元素中移除图片、页码字段以及TOC域指令。
        这可以防止在“append”模式下出现重复的图片、错误的页码或裸露的域代码。
        """
        runs_to_remove = []
        runs = p_element.findall(qn('w:r'))

        i = 0
        while i < len(runs):
            run_element = runs[i]

            # 1. 检查图片
            if run_element.find(qn('w:drawing')) is not None or run_element.find(qn('w:pict')) is not None:
                runs_to_remove.append(run_element)
                i += 1
                continue

            # 2. 检查域开始字符 (处理 PAGE, NUMPAGES, TOC 等)
            fldChar = run_element.find(qn('w:fldChar'))
            if fldChar is not None and fldChar.get(qn('w:fldCharType')) == 'begin':
                is_target_field = False
                field_end_index = -1
                is_toc_field = False

                # 向前查找指令文本
                for j in range(i + 1, len(runs)):
                    next_run = runs[j]

                    # 检查指令文本
                    instrText = next_run.find(qn('w:instrText'))
                    if instrText is not None and instrText.text is not None:
                        text = instrText.text.strip().upper()
                        # 检测页码
                        if 'PAGE' in text or 'NUMPAGES' in text:
                            is_target_field = True
                            break
                        # [FIX] 检测 TOC 目录生成指令
                        # 如果是 TOC 指令，我们必须移除它，否则译文段落会再次尝试生成目录，或显示乱码。
                        if text.startswith('TOC'):
                            is_target_field = True
                            is_toc_field = True
                            break

                    # 如果遇到嵌套的 begin，或者 unexpected end，停止搜索
                    next_fldChar = next_run.find(qn('w:fldChar'))
                    if next_fldChar is not None:
                        if next_fldChar.get(qn('w:fldCharType')) == 'begin':
                            break  # 嵌套开始，放弃当前层匹配（简化处理）
                        if next_fldChar.get(qn('w:fldCharType')) == 'end':
                            # 到了结束还没找到指令，说明不是我们要找的字段
                            break

                if is_target_field:
                    # 找到要移除的字段了。
                    # 对于 PAGE 字段，我们通常移除整个字段（因为译文段落的页码可能不准确，或者避免重复）。
                    # 对于 TOC 字段，我们必须"解包"：移除 Begin, Instr, Separate，但保留结果文本(Hyperlink/Text)。
                    # 但在这里，简单的策略是：移除 Begin 到 Separate (或 End) 之间的指令部分。

                    if is_toc_field:
                        # 特殊处理 TOC：我们希望保留后面的文字（如 "研究背景..."），只删掉域的定义部分。
                        # TOC 结构通常是: Begin -> Instr(TOC) -> Separate -> Result(Text) -> End
                        # 我们移除 Begin -> ... -> Separate。保留 Result -> End。
                        runs_to_remove.append(run_element)  # 移除 Begin

                        found_separate = False
                        for j in range(i + 1, len(runs)):
                            field_run = runs[j]

                            # 总是移除中间的 run (包含 instrText)
                            runs_to_remove.append(field_run)

                            end_fldChar = field_run.find(qn('w:fldChar'))
                            if end_fldChar is not None:
                                fld_type = end_fldChar.get(qn('w:fldCharType'))
                                if fld_type == 'separate':
                                    found_separate = True
                                    i = j + 1  # 跳过 Separate，继续处理后面的 Result Run
                                    break
                                if fld_type == 'end':
                                    # 如果没有 separate 直接 end，那就全删了
                                    i = j + 1
                                    break
                        if found_separate:
                            continue  # 继续外层循环

                    else:
                        # 普通字段 (PAGE 等)，移除整个字段 (Begin ... End)
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
            for i, info in enumerate(elements):
                top_level_paragraph = info["top_level_paragraph"]
                paragraph_segments[id(top_level_paragraph._p)].append({
                    "index": i,
                    "translation": translated[i],
                    "paragraph_obj": top_level_paragraph
                })

            for para_id, segments_for_this_para in paragraph_segments.items():
                top_level_paragraph_orig = segments_for_this_para[0]["paragraph_obj"]
                p_element_orig = top_level_paragraph_orig._p

                translated_p_element = deepcopy(p_element_orig)

                # ================= 核心修复：先映射 =================
                top_level_paragraph_copy = Paragraph(translated_p_element, top_level_paragraph_orig._parent)
                para_map = {id(p_element_orig): top_level_paragraph_copy}
                orig_nested_ps = p_element_orig.iter(qn('w:p'))
                copy_nested_ps = translated_p_element.iter(qn('w:p'))
                for o, c in zip(orig_nested_ps, copy_nested_ps):
                    para_map[id(o)] = Paragraph(c, top_level_paragraph_copy)

                # 建立 Run 映射
                run_element_map = {
                    id(orig_r): copied_r
                    for orig_r, copied_r in zip(p_element_orig.iter(qn('w:r')), translated_p_element.iter(qn('w:r')))
                }

                # ================= 核心修复：后清理 =================
                # 移除 TOC 指令等干扰元素，确保译文纯净
                self._prune_unwanted_elements_from_copy(translated_p_element)

                # ================= 新增逻辑：判断是否需要使用软回车 =================
                use_soft_break = False
                pPr = p_element_orig.find(qn('w:pPr'))

                if pPr is not None:
                    # 1. 判断是否列表项
                    if pPr.find(qn('w:numPr')) is not None:
                        use_soft_break = True

                    # 2. 判断是否目录项 (样式通常为 TOC1, TOC2...)
                    pStyle = pPr.find(qn('w:pStyle'))
                    if pStyle is not None:
                        style_val = pStyle.get(qn('w:val'), "")
                        # 检查样式名称是否以 TOC 开头 (忽略大小写)
                        if style_val and style_val.upper().startswith("TOC"):
                            use_soft_break = True

                # 如果不是软回车模式，才需要在副本中清理列表属性（避免两个圆点）
                if not use_soft_break:
                    pPr_copy = translated_p_element.find(qn('w:pPr'))
                    if pPr_copy is not None:
                        numPr = pPr_copy.find(qn('w:numPr'))
                        if numPr is not None:
                            pPr_copy.remove(numPr)

                # 应用翻译到副本 (使用前面建立的 map)
                for seg_info in segments_for_this_para:
                    element_index = seg_info["index"]
                    translation = seg_info["translation"]
                    original_element_info = elements[element_index]

                    original_para_id = id(original_element_info["paragraph"]._p)
                    translated_paragraph_obj = para_map.get(original_para_id)

                    if not translated_paragraph_obj: continue

                    runs_from_copy = []
                    for r in original_element_info["runs"]:
                        copied_r_element = run_element_map.get(id(r.element))
                        # 只有当该 Run 在副本中未被 prune 删除时，才进行翻译替换
                        if copied_r_element is not None and copied_r_element.getparent() is not None:
                            new_run = Run(copied_r_element, translated_paragraph_obj)
                            runs_from_copy.append(new_run)

                    if runs_from_copy:
                        self._apply_translation({
                            "type": "text_runs", "runs": runs_from_copy, "paragraph": translated_paragraph_obj
                        }, translation)

                # ================= 插入逻辑分支 =================
                if use_soft_break:
                    # 列表项或目录项：使用软回车 (<w:br>) 连接，忽略 separator
                    separator_run = OxmlElement('w:r')
                    separator_run.append(OxmlElement('w:br'))

                    translated_runs = list(translated_p_element.iter(qn('w:r')))

                    if self.insert_mode == "append":
                        p_element_orig.append(separator_run)
                        for tr in translated_runs:
                            p_element_orig.append(tr)

                    elif self.insert_mode == "prepend":
                        # 如果有属性节点(pPr)，插入到它后面
                        insert_index = 0
                        if p_element_orig.find(qn('w:pPr')) is not None:
                            insert_index = 1

                        # 先插入分隔符
                        p_element_orig.insert(insert_index, separator_run)
                        # 倒序插入译文 runs，确保顺序正确
                        for tr in reversed(translated_runs):
                            p_element_orig.insert(insert_index, tr)

                else:
                    # 普通段落：使用新段落 (<w:p>) 插入，并使用 separator
                    separator_p_element = None
                    if self.separator:
                        separator_p_element = OxmlElement('w:p')
                        # 尝试复制原段落样式到分隔符段落，保持间距一致（可选）
                        if pPr is not None:
                            separator_p_element.append(deepcopy(pPr))
                            # 但要去掉列表属性和边框等，防止分隔符也带列表头
                            sep_pPr = separator_p_element.find(qn('w:pPr'))
                            if sep_pPr is not None:
                                numPr = sep_pPr.find(qn('w:numPr'))
                                if numPr is not None: sep_pPr.remove(numPr)

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
                        current_element = p_element_orig
                        if separator_p_element is not None:
                            current_element.addnext(separator_p_element)
                            current_element = separator_p_element
                        current_element.addnext(translated_p_element)
                    elif self.insert_mode == "prepend":
                        p_element_orig.addprevious(translated_p_element)
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
            glossary_dict_gen = self.glossary_agent.send_segments(originals, self.chunk_size)
            if self.glossary:
                self.glossary.update(glossary_dict_gen)
            if self.translate_agent and self.glossary:
                self.translate_agent.update_glossary_dict(self.glossary.glossary_dict)

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
            glossary_dict_gen = await self.glossary_agent.send_segments_async(originals, self.chunk_size)
            if self.glossary:
                self.glossary.update(glossary_dict_gen)
            if self.translate_agent and self.glossary:
                self.translate_agent.update_glossary_dict(self.glossary.glossary_dict)

        translated = await self.translate_agent.send_segments_async(originals,
                                                                    self.chunk_size) if self.translate_agent else originals
        document.content = await asyncio.to_thread(self._after_translate, doc, elements, translated, originals)
        return self