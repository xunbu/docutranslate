# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
from dataclasses import dataclass
from typing import Self, Literal, Set, Dict, List, Tuple

from bs4 import BeautifulSoup, NavigableString, Comment, Tag

from docutranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator

# --- 规则定义 ---

# 1. 不可翻译标签（黑名单）
NON_TRANSLATABLE_TAGS: Set[str] = {
    'script', 'style', 'pre', 'code', 'kbd', 'samp', 'var', 'noscript', 'meta', 'link', 'head',
}

# 2. 可作为独立翻译单元的块级标签（白名单）
# 这些标签将被视为一个整体进行翻译，并且在append/prepend模式下会触发结构化操作。
TRANSLATABLE_BLOCK_TAGS: Set[str] = {
    'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'blockquote', 'q', 'caption',
    'td', 'th', 'button', 'legend', 'figcaption', 'summary', 'details', 'div',
}

# 3. 可翻译属性（白名单）
SAFE_ATTRIBUTES: Dict[str, List[str]] = {
    'img': ['alt', 'title'],
    'a': ['title'],
    'input': ['placeholder', 'title'],
    'textarea': ['placeholder', 'title'],
    'abbr': ['title'],
    'area': ['alt'],
    '*': ['title']
}


@dataclass
class HtmlTranslatorConfig(AiTranslatorConfig):
    insert_mode: Literal["replace", "append", "prepend"] = "replace"
    separator: str = "\n"


class HtmlTranslator(AiTranslator):
    """
    一个用于翻译 HTML 文件内容的翻译器。
    【结构化修改版】: 借鉴 Docx/EpubTranslator 的实现，将块级元素作为整体翻译单元。
    在 append/prepend 模式下，对常规块级元素创建新标签存放译文，对表格单元格则在内部追加内容，
    以保证文档结构的清晰和样式的绝对一致性，同时保留了强大的黑白名单安全规则。
    """

    def __init__(self, config: HtmlTranslatorConfig):
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
                system_proxy_enable=config.system_proxy_enable,
                force_json=config.force_json,
                rpm=config.rpm,
                tpm=config.tpm,
                provider=config.provider,
            )
            self.translate_agent = SegmentsTranslateAgent(agent_config)
        self.insert_mode = config.insert_mode
        self.separator = config.separator

    def _pre_translate(self, document: Document) -> Tuple[BeautifulSoup, List[Dict], List[str]]:
        soup = BeautifulSoup(document.content, 'lxml')
        for tag in soup.find_all(NON_TRANSLATABLE_TAGS):
            tag.decompose()

        translatable_items = []
        original_texts = []

        # --- 1. 提取块级标签进行翻译 ---
        all_potential_blocks = soup.find_all(TRANSLATABLE_BLOCK_TAGS)
        all_potential_blocks_set = set(all_potential_blocks)

        tags_to_process = []
        for tag in all_potential_blocks:
            # 采用“Bottom-Up”逻辑，只选择不包含其他可翻译块级标签的“叶子”标签。
            contains_other_block = tag.find(
                lambda child_tag: child_tag in all_potential_blocks_set and child_tag is not tag
            )
            if not contains_other_block:
                tags_to_process.append(tag)

        for tag in tags_to_process:
            if tag.get_text(strip=True):
                translatable_items.append({'type': 'block_tag', 'tag': tag})
                original_texts.append(tag.decode_contents())

        # --- 2. 提取安全属性进行翻译 ---
        for tag in soup.find_all(True):
            attributes_to_check = SAFE_ATTRIBUTES.get(tag.name, []) + SAFE_ATTRIBUTES.get('*', [])
            for attr in set(attributes_to_check):
                if tag.has_attr(attr) and tag[attr].strip():
                    translatable_items.append({'type': 'attribute', 'tag': tag, 'attribute': attr})
                    original_texts.append(tag[attr])

        return soup, translatable_items, original_texts

    def _after_translate(self, soup: BeautifulSoup, translatable_items: list,
                         translated_texts: list[str], original_texts: list[str]) -> bytes:
        if len(translatable_items) != len(translated_texts):
            self.logger.error("翻译前后的文本片段数量不匹配 (%d vs %d)，跳过写入操作以防损坏文件。",
                              len(translatable_items), len(translated_texts))
            return soup.encode('utf-8')

        for i, item in enumerate(translatable_items):
            original_text = original_texts[i]
            translated_text = translated_texts[i]
            tag = item['tag']

            # --- 分类处理：属性 vs. 块级标签 ---
            if item['type'] == 'attribute':
                attr = item['attribute']
                separator_for_attr = self.separator.replace('\n', ' ').strip()
                new_attr_value = ""

                if self.insert_mode == "replace":
                    new_attr_value = translated_text
                elif self.insert_mode == "append":
                    new_attr_value = f"{original_text}{separator_for_attr}{translated_text}"
                elif self.insert_mode == "prepend":
                    new_attr_value = f"{translated_text}{separator_for_attr}{original_text}"

                tag[attr] = new_attr_value.strip()

            elif item['type'] == 'block_tag':
                is_table_cell = tag.name in ['td', 'th']

                if self.insert_mode == "replace":
                    tag.clear()
                    new_content_soup = BeautifulSoup(translated_text, 'html.parser')
                    for node in list(new_content_soup.children):
                        tag.append(node.extract())

                elif is_table_cell:
                    # 表格单元格：在内部组合内容
                    tag.clear()
                    original_nodes = BeautifulSoup(original_text, 'html.parser').contents
                    translated_nodes = BeautifulSoup(translated_text, 'html.parser').contents

                    separator_nodes = []
                    if self.separator:
                        lines = self.separator.split('\n')
                        for j, line in enumerate(lines):
                            if line: separator_nodes.append(NavigableString(line))
                            if j < len(lines) - 1: separator_nodes.append(soup.new_tag('br'))

                    order = [original_nodes, separator_nodes, translated_nodes] if self.insert_mode == "append" else [
                        translated_nodes, separator_nodes, original_nodes]
                    for node_list in order:
                        for node in node_list:
                            tag.append(node.extract() if isinstance(node, Tag) else node)

                else:
                    # 常规块级元素：创建新标签
                    translated_tag = soup.new_tag(tag.name, attrs=tag.attrs)
                    new_content_soup = BeautifulSoup(translated_text, 'html.parser')
                    for node in list(new_content_soup.children):
                        translated_tag.append(node.extract())

                    separator_tag = None
                    if self.separator:
                        separator_tag = soup.new_tag('p')
                        lines = self.separator.split('\n')
                        for j, line in enumerate(lines):
                            if line: separator_tag.append(NavigableString(line))
                            if j < len(lines) - 1: separator_tag.append(soup.new_tag('br'))

                    if self.insert_mode == "append":
                        current_node = tag
                        if separator_tag:
                            current_node.insert_after(separator_tag)
                            current_node = separator_tag
                        current_node.insert_after(translated_tag)
                    elif self.insert_mode == "prepend":
                        tag.insert_before(translated_tag)
                        if separator_tag:
                            translated_tag.insert_after(separator_tag)

        return soup.encode('utf-8')

    def translate(self, document: Document) -> Self:
        soup, translatable_items, original_texts = self._pre_translate(document)
        if not translatable_items:
            self.logger.info("\nHTML文件中没有找到符合安全规则的可翻译内容。")
            document.content = soup.encode('utf-8')
            return self

        if self.glossary_agent:
            self.glossary_dict_gen = self.glossary_agent.send_segments(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)
        if self.translate_agent:
            translated_texts = self.translate_agent.send_segments(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts
        document.content = self._after_translate(soup, translatable_items, translated_texts, original_texts)
        return self

    async def translate_async(self, document: Document) -> Self:
        soup, translatable_items, original_texts = await asyncio.to_thread(self._pre_translate, document)

        if not translatable_items:
            self.logger.info("\nHTML文件中没有找到符合安全规则的可翻译内容。")
            document.content = await asyncio.to_thread(soup.encode, 'utf-8')
            return self

        if self.glossary_agent:
            self.glossary_dict_gen = await self.glossary_agent.send_segments_async(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)
        if self.translate_agent:
            translated_texts = await self.translate_agent.send_segments_async(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts
        document.content = await asyncio.to_thread(
            self._after_translate, soup, translatable_items, translated_texts, original_texts
        )
        return self