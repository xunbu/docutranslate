# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
from dataclasses import dataclass
from typing import Self, Literal, Set, Dict, List, Tuple

from bs4 import BeautifulSoup, NavigableString, Comment

from docutranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator

# --- 规则定义 ---

# 1. 不可翻译标签（黑名单）
# 这些标签及其内容在任何情况下都不应被翻译，因为它们通常包含代码、样式或元数据。
# 在预处理阶段，这些标签及其所有子元素将被直接从文档中移除，以确保它们不会被意外修改。
NON_TRANSLATABLE_TAGS: Set[str] = {
    'script',  # JavaScript代码
    'style',  # CSS样式
    'pre',  # 预格式化文本，通常用于代码块
    'code',  # 行内代码
    'kbd',  # 键盘输入
    'samp',  # 示例输出
    'var',  # 变量
    'noscript',  # script未启用时的内容
    'meta',  # 元数据
    'link',  # 外部资源链接
    'head',  # 文档头部，通常不包含可见的可翻译内容
}

# 2. 可翻译标签（白名单）
# 定义一组被认为是“安全”的HTML标签，这些标签中的直接文本内容适合被翻译。
# 这种白名单策略与上面的黑名单结合，提供了双重保障。
SAFE_TAGS: Set[str] = {
    'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'li', 'blockquote', 'q', 'caption',
    'span', 'a', 'strong', 'em', 'b', 'i', 'u',
    'td', 'th',
    'button', 'label', 'legend', 'option',
    'figcaption', 'summary', 'details',
    'div',  # div 比较通用，但我们的逻辑只提取其顶层文本节点，相对安全
}

# 3. 可翻译属性（白名单）
# 定义一组“安全”的属性，这些属性的值通常是给用户看的可读文本。
# 格式为: { 'tag_name': ['attr1', 'attr2'], ... }
SAFE_ATTRIBUTES: Dict[str, List[str]] = {
    'img': ['alt', 'title'],
    'a': ['title'],
    'input': ['placeholder', 'title'],
    'textarea': ['placeholder', 'title'],
    'abbr': ['title'],
    'area': ['alt'],
    # 对于所有标签，title属性通常是可翻译的
    '*': ['title']
}


@dataclass
class HtmlTranslatorConfig(AiTranslatorConfig):
    """
    HTML翻译器的配置类。

    Attributes:
        insert_mode (Literal["replace", "append", "prepend"]):
            指定如何插入翻译文本。
            - "replace": 用译文替换原文。
            - "append": 在原文后追加译文。
            - "prepend": 在原文前追加译文。
        separator (str): 在 "append" 或 "prepend" 模式下，用于分隔原文和译文的字符串。
    """
    insert_mode: Literal["replace", "append", "prepend"] = "replace"
    separator: str = " "  # HTML中用空格作为默认分隔符可能更合适


class HtmlTranslator(AiTranslator):
    """
    一个用于翻译 HTML 文件内容的翻译器。
    它采用黑白名单结合的策略，以最大程度地保留页面样式和功能：
    1. 黑名单：首先，完全移除 script, style, code 等明确不可翻译的标签及其内容。
    2. 白名单：然后，在剩余的HTML中，只提取和翻译指定安全标签和属性中的文本内容。
    3. 注释保护：显式地跳过HTML注释，确保它们不被翻译。
    这种方法能有效避免破坏页面结构、脚本、样式和注释。
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
                system_proxy_enable=config.system_proxy_enable
            )
            self.translate_agent = SegmentsTranslateAgent(agent_config)
        self.insert_mode = config.insert_mode
        self.separator = config.separator

    def _pre_translate(self, document: Document) -> Tuple[BeautifulSoup, List[Dict], List[str]]:
        """
        解析HTML文档，根据规则提取所有需要翻译的文本节点和属性。
        步骤:
        1. 使用黑名单移除所有不可翻译的标签，从根本上防止它们被处理。
        2. 遍历剩余的HTML元素，根据白名单提取可翻译的文本和属性值，同时跳过注释。
        """
        soup = BeautifulSoup(document.content, 'lxml')

        # 步骤 1: 移除所有不可翻译的标签及其内容
        for tag in soup.find_all(NON_TRANSLATABLE_TAGS):
            tag.decompose()

        translatable_items = []
        original_texts = []

        # 步骤 2: 遍历所有剩余标签，提取可翻译内容
        for tag in soup.find_all(True):
            # --- 2a. 翻译安全标签内的文本节点 ---
            if tag.name in SAFE_TAGS:
                # 只处理标签的直接子节点中的文本，这是保留样式的关键。
                for child in list(tag.children):
                    # 【关键修改】确保处理的是纯文本节点，而不是注释（Comment是NavigableString的子类）
                    if isinstance(child, NavigableString) and not isinstance(child, Comment) and child.strip():
                        text = str(child)
                        translatable_items.append({'type': 'node', 'object': child})
                        original_texts.append(text)

            # --- 2b. 翻译安全标签内的安全属性 ---
            attributes_to_check = SAFE_ATTRIBUTES.get(tag.name, []) + SAFE_ATTRIBUTES.get('*', [])
            for attr in set(attributes_to_check):  # 使用set去重
                if tag.has_attr(attr) and tag[attr].strip():
                    value = tag[attr]
                    translatable_items.append({'type': 'attribute', 'tag': tag, 'attribute': attr})
                    original_texts.append(value)

        return soup, translatable_items, original_texts

    def _after_translate(self, soup: BeautifulSoup, translatable_items: list,
                         translated_texts: list[str], original_texts: list[str]) -> bytes:
        """
        将翻译后的文本写回到BeautifulSoup对象中对应的节点或属性，并返回最终的HTML字节流。
        """
        if len(translatable_items) != len(translated_texts):
            self.logger.error("翻译前后的文本片段数量不匹配 (%d vs %d)，跳过写入操作以防损坏文件。",
                              len(translatable_items), len(translated_texts))
            return soup.encode('utf-8')

        for i, item in enumerate(translatable_items):
            translated_text = translated_texts[i]
            original_text = original_texts[i]

            new_content = ""
            if self.insert_mode == "replace":
                if item['type'] == 'node':
                    # 对于文本节点，保留原文前后的空白字符，这对维持内联元素的间距至关重要。
                    leading_space = original_text[:len(original_text) - len(original_text.lstrip())]
                    trailing_space = original_text[len(original_text.rstrip()):]
                    new_content = leading_space + translated_text + trailing_space
                else:  # 属性
                    new_content = translated_text

            elif self.insert_mode == "append":
                new_content = original_text + self.separator + translated_text
            elif self.insert_mode == "prepend":
                new_content = translated_text + self.separator + original_text
            else:
                self.logger.error(f"不正确的HtmlTranslatorConfig参数: insert_mode='{self.insert_mode}'")
                new_content = original_text  # 出错时恢复原文

            # 根据类型将内容写回
            if item['type'] == 'node':
                node = item['object']
                # 检查节点是否仍然在解析树中，以防在处理过程中被移动或删除
                if node.parent:
                    node.replace_with(NavigableString(new_content))
            elif item['type'] == 'attribute':
                tag = item['tag']
                attr = item['attribute']
                tag[attr] = new_content

        # 将修改后的BeautifulSoup对象编码为utf-8字节流
        return soup.encode('utf-8')

    def translate(self, document: Document) -> Self:
        """
        同步翻译HTML文档。
        """
        soup, translatable_items, original_texts = self._pre_translate(document)
        if not translatable_items:
            self.logger.info("\nHTML文件中没有找到符合安全规则的可翻译内容。")
            # 即使没有翻译内容，也返回经过清理（移除非翻译标签）的文档内容
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
        """
        异步翻译HTML文档。
        """
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
