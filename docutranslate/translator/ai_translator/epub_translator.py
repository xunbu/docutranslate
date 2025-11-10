# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
import os
import re
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from io import BytesIO
from typing import Self, Literal, List, Dict, Any, Tuple

from bs4 import BeautifulSoup, Tag, NavigableString

from docutranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator


@dataclass
class EpubTranslatorConfig(AiTranslatorConfig):
    insert_mode: Literal["replace", "append", "prepend"] = "replace"
    # 建议使用 \n，代码会将其转换为 <br />，更灵活
    separator: str = "\n"


class EpubTranslator(AiTranslator):
    """
    一个用于翻译 EPUB 文件中内容的翻译器。
    【高级版】此版本直接翻译HTML内容，以保留内联格式，并支持表格翻译。
    【结构化修改版 v2】借鉴 DocxTranslator 的实现，在 append/prepend 模式下，
    对常规块级元素创建新标签存放译文，对表格单元格则在内部追加内容，以保证文档结构的正确性。
    """

    def __init__(self, config: EpubTranslatorConfig):
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
                force_json=config.force_json
            )
            self.translate_agent = SegmentsTranslateAgent(agent_config)
        self.insert_mode = config.insert_mode
        self.separator = config.separator

    def _pre_translate(self, document: Document) -> tuple[
        Dict[str, bytes],
        Dict[str, BeautifulSoup],
        List[Dict[str, Any]],
        List[str]
    ]:
        all_files = {}
        soups = {}
        items_to_translate = []
        original_texts = []

        with zipfile.ZipFile(BytesIO(document.content), 'r') as zf:
            for filename in zf.namelist():
                all_files[filename] = zf.read(filename)

        container_xml = all_files.get('META-INF/container.xml')
        if not container_xml:
            raise ValueError("无效的 EPUB：找不到 META-INF/container.xml")
        root = ET.fromstring(container_xml)
        ns = {'cn': 'urn:oasis:names:tc:opendocument:xmlns:container'}
        opf_path = root.find('cn:rootfiles/cn:rootfile', ns).get('full-path')
        opf_dir = os.path.dirname(opf_path)

        opf_xml = all_files.get(opf_path)
        if not opf_xml:
            raise ValueError(f"无效的 EPUB：找不到 {opf_path}")
        opf_root = ET.fromstring(opf_xml)
        ns_opf = {'opf': 'http://www.idpf.org/2007/opf'}

        manifest_items = {}
        for item in opf_root.findall('opf:manifest/opf:item', ns_opf):
            item_id = item.get('id')
            href = item.get('href')
            full_href = os.path.join(opf_dir, href).replace('\\', '/')
            manifest_items[item_id] = {'href': full_href, 'media_type': item.get('media-type')}

        TAGS_TO_TRANSLATE = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'div', 'td', 'th']

        for item_id, item_data in manifest_items.items():
            media_type = item_data['media_type']
            if media_type in ['application/xhtml+xml', 'text/html']:
                file_path = item_data['href']
                content_bytes = all_files.get(file_path)
                if not content_bytes:
                    self.logger.warning(f"在 EPUB 中找不到文件: {file_path}")
                    continue

                if file_path not in soups:
                    soups[file_path] = BeautifulSoup(content_bytes, "html.parser")

                soup = soups[file_path]

                all_potential_tags = soup.find_all(TAGS_TO_TRANSLATE)
                all_potential_tags_set = set(all_potential_tags)

                tags_to_process = []
                for tag in all_potential_tags:
                    contains_other_block = tag.find(
                        lambda child_tag: child_tag in all_potential_tags_set and child_tag is not tag
                    )
                    if not contains_other_block:
                        tags_to_process.append(tag)

                for tag in tags_to_process:
                    inner_html = tag.decode_contents()
                    plain_text = tag.get_text(strip=True)

                    if plain_text:
                        item_info = {
                            "file_path": file_path,
                            "tag": tag,
                        }
                        items_to_translate.append(item_info)
                        original_texts.append(inner_html)

        return all_files, soups, items_to_translate, original_texts

    def _after_translate(
            self,
            all_files: Dict[str, bytes],
            soups: Dict[str, BeautifulSoup],
            items_to_translate: List[Dict[str, Any]],
            translated_texts: List[str],
            original_texts: List[str],
    ) -> bytes:

        for i, item_info in enumerate(items_to_translate):
            original_tag = item_info["tag"]
            soup = soups[item_info["file_path"]]
            original_html = original_texts[i]
            translated_html = translated_texts[i]

            # --- 关键逻辑：根据标签类型选择不同的处理策略 ---
            is_table_cell = original_tag.name in ['td', 'th']

            if self.insert_mode == "replace":
                original_tag.clear()
                new_content_soup = BeautifulSoup(translated_html, 'html.parser')
                for node in list(new_content_soup.children):
                    original_tag.append(node.extract())

            elif is_table_cell:
                # --- 表格单元格处理：在标签内部组合内容 ---
                original_tag.clear()

                # 解析HTML片段
                original_nodes = BeautifulSoup(original_html, 'html.parser').contents
                translated_nodes = BeautifulSoup(translated_html, 'html.parser').contents

                # 创建分隔符节点
                separator_nodes = []
                if self.separator:
                    lines = self.separator.split('\n')
                    for j, line in enumerate(lines):
                        if line:
                            separator_nodes.append(NavigableString(line))
                        if j < len(lines) - 1:
                            separator_nodes.append(soup.new_tag('br'))

                # 根据模式按顺序重新填充
                if self.insert_mode == "append":
                    nodes_order = [original_nodes, separator_nodes, translated_nodes]
                else:  # prepend
                    nodes_order = [translated_nodes, separator_nodes, original_nodes]

                for node_list in nodes_order:
                    for node in node_list:
                        original_tag.append(node.extract() if isinstance(node, Tag) else node)

            else:
                # --- 常规块级元素处理：创建新标签 ---
                translated_tag = soup.new_tag(original_tag.name, attrs=original_tag.attrs)
                new_content_soup = BeautifulSoup(translated_html, 'html.parser')
                for node in list(new_content_soup.children):
                    translated_tag.append(node.extract())

                separator_tag = None
                if self.separator:
                    separator_tag = soup.new_tag('p')
                    lines = self.separator.split('\n')
                    for j, line in enumerate(lines):
                        if line:
                            separator_tag.append(NavigableString(line))
                        if j < len(lines) - 1:
                            separator_tag.append(soup.new_tag('br'))

                if self.insert_mode == "append":
                    current_node = original_tag
                    if separator_tag:
                        current_node.insert_after(separator_tag)
                        current_node = separator_tag
                    current_node.insert_after(translated_tag)
                elif self.insert_mode == "prepend":
                    original_tag.insert_before(translated_tag)
                    if separator_tag:
                        translated_tag.insert_after(separator_tag)

        for file_path, soup in soups.items():
            all_files[file_path] = str(soup).encode('utf-8')

        output_buffer = BytesIO()
        with zipfile.ZipFile(output_buffer, 'w') as zf_out:
            if 'mimetype' in all_files:
                zf_out.writestr('mimetype', all_files['mimetype'], compress_type=zipfile.ZIP_STORED)
            for filename, content in all_files.items():
                if filename != 'mimetype':
                    zf_out.writestr(filename, content, compress_type=zipfile.ZIP_DEFLATED)
        return output_buffer.getvalue()

    def translate(self, document: Document) -> Self:
        all_files, soups, items_to_translate, original_texts = self._pre_translate(document)
        if not items_to_translate:
            self.logger.info("\n文件中没有找到需要翻译的内容。")
            document.content = self._after_translate(all_files, soups, [], [], [])
            return self

        if self.glossary_agent:
            self.glossary_dict_gen = self.glossary_agent.send_segments(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)
        if self.translate_agent:
            translated_texts = self.translate_agent.send_segments(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts
        document.content = self._after_translate(
            all_files, soups, items_to_translate, translated_texts, original_texts
        )
        return self

    async def translate_async(self, document: Document) -> Self:
        all_files, soups, items_to_translate, original_texts = await asyncio.to_thread(
            self._pre_translate, document
        )
        if not items_to_translate:
            self.logger.info("\n文件中没有找到需要翻译的内容。")
            document.content = await asyncio.to_thread(self._after_translate, all_files, soups, [], [], [])
            return self

        if self.glossary_agent:
            self.glossary_dict_gen = await self.glossary_agent.send_segments_async(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)
        if self.translate_agent:
            translated_texts = await self.translate_agent.send_segments_async(
                original_texts, self.chunk_size
            )
        else:
            translated_texts = original_texts
        document.content = await asyncio.to_thread(
            self._after_translate, all_files, soups, items_to_translate, translated_texts, original_texts
        )
        return self