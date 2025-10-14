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
        # Handles empty runs with formatting
        if run.underline or run.bold or run.italic or run.font.strike or run.font.subscript or run.font.superscript:
            return True
        # Handles runs that are just whitespace but have formatting that might be visually significant
        if text and run.underline:
            return True
        # A simple tab run is also considered formatting-only for our purpose
        if text == '\t':
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

    [v4.2 - 修复版]
    - 修复了对域代码（Fields）结果文本的错误跳过问题，确保目录条目可被翻译。
    - 新增了对结构化文档标签（Structured Document Tags, SDT）的递归解析，
      确保由内容控件（如自动目录）包裹的内容可以被正确处理。

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
    SKIPPABLE_FIELD_INSTRUCTIONS = {'PAGEREF', 'SEQ'}

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
                # [v5.0] 递归前刷新，确保容器前的内容已保存
                flush_segment()
                self._process_element_children(child, elements, texts, state)
                continue

            # --- [v5.0] 智能域处理逻辑 ---
            # 检查是否为域指令文本 (instrText)
            instr_text_element = child.find(qn('w:instrText')) if isinstance(child, CT_R) else None
            if instr_text_element is not None:
                instr_text = instr_text_element.text.strip()
                # 检查指令是否属于需要跳过的类型
                if any(keyword in instr_text for keyword in self.SKIPPABLE_FIELD_INSTRUCTIONS):
                    state['is_in_skippable_field'] = True
                continue  # 无论如何都跳过指令文本本身的处理

            # 检查是否为域字符 (fldChar)
            field_char_element = child.find(qn('w:fldChar')) if isinstance(child, CT_R) else (
                child if child.tag == qn('w:fldChar') else None)
            if field_char_element is not None:
                fld_type = field_char_element.get(qn('w:fldCharType'))

                if fld_type == 'begin':
                    flush_segment()
                    # 重置子域的状态
                    state['is_in_skippable_field'] = False
                    state['is_skipping_result'] = False
                elif fld_type == 'separate':
                    # 如果这是一个我们标记为要跳过的域，现在开始跳过其结果
                    if state.get('is_in_skippable_field'):
                        flush_segment()  # 刷新域之前的所有文本 (如目录标题)
                        state['is_skipping_result'] = True
                elif fld_type == 'end':
                    # 域结束，恢复正常处理
                    state['is_in_skippable_field'] = False
                    state['is_skipping_result'] = False
                continue

            # 如果当前状态是跳过域结果，则忽略这个子元素
            if state.get('is_skipping_result'):
                continue
            # --- 域处理逻辑结束 ---

            if isinstance(child, CT_R):
                run = Run(child, None)
                if is_image_run(run) or is_formatting_only_run(run):
                    flush_segment()
                else:
                    state['current_runs'].append(run)
            else:
                flush_segment()

        # 在元素处理结束后，确保最后一部分也被刷新
        # [v5.0] 此处的刷新由调用者 (_process_paragraph) 控制，以避免递归中过早刷新

    def _process_paragraph(self, para: Paragraph, elements: List[Dict[str, Any]], texts: List[str]):
        if not para.text.strip():
            return

        # [v5.0] 为每个段落初始化独立的状态
        state = {
            'current_runs': [],
            'is_in_skippable_field': False,  # 是否在PAGEREF等域的指令部分
            'is_skipping_result': False  # 是否正在跳过PAGEREF等域的结果部分
        }

        self._process_element_children(para._p, elements, texts, state)

        # [v5.0] 处理完一个段落的所有子元素后，刷新剩余的runs
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

            # [v5.0] 改进合并逻辑，更稳健地处理空runs
            first_real_run_index = -1
            # 将翻译文本赋给第一个有效的run
            for i, run in enumerate(runs):
                if run.element.getparent() is not None:
                    run.text = final_text
                    first_real_run_index = i
                    break

            if first_real_run_index == -1:
                self.logger.warning(f"无法应用翻译 '{final_text}'，因为找不到有效的run。")
                return

            # 删除其余的runs
            for i in range(first_real_run_index + 1, len(runs)):
                run = runs[i]
                parent_element = run.element.getparent()
                if parent_element is not None:
                    try:
                        parent_element.remove(run.element)
                    except ValueError:
                        # 在某些复杂情况下，元素可能已被其父元素的其他操作移除
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
        # print(f"【测试】originals\n:{originals}")  # 保持您的测试输出
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