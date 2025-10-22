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
    # 建议使用 <br />，它在 XHTML (EPUB标准) 中更规范
    separator: str = "<br />"


class EpubTranslator(AiTranslator):
    """
    一个用于翻译 EPUB 文件中内容的翻译器。
    【高级版】此版本直接翻译HTML内容，以保留内联格式，并支持表格翻译。
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
                system_proxy_enable=config.system_proxy_enable
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

        # ==================== 代码修改 1: 添加表格相关的标签 ====================
        TAGS_TO_TRANSLATE = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'div', 'td', 'th']
        # 定义一个正则表达式，用于按 <br> 和 <img> 标签分割内容
        split_pattern = re.compile(r'(<br\s*/?>|<img[^>]*>)', re.IGNORECASE)

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
                    # 采用“Bottom-Up”逻辑，只选择不包含其他可翻译块级标签的“叶子”标签。
                    contains_other_block = tag.find(
                        lambda child_tag: child_tag in all_potential_tags_set and child_tag is not tag
                    )
                    if not contains_other_block:
                        tags_to_process.append(tag)
                # ==================== 修改结束 ====================

                for tag in tags_to_process:
                    inner_html = tag.decode_contents()
                    if not inner_html or inner_html.isspace():
                        continue

                    # ==================== 代码修改 2: 增加对表格标签的特殊处理 ====================
                    # 对于表格单元格（td, th），我们希望直接翻译其内容，并替换。
                    # 这样做可以避免在单元格内部错误地插入 <br> 导致表格布局破坏。
                    # 其他标签（如 p, div）则可以继续使用分割逻辑，以支持段内换行。
                    is_table_cell = tag.name in ['td', 'th']
                    # ==================== 修改结束 ====================

                    html_parts = split_pattern.split(inner_html)

                    # 如果不是表格单元格，且存在 <br> 或 <img>，则按片段处理
                    is_split = len(html_parts) > 1 and not is_table_cell

                    if is_split:
                        # 逻辑保持不变：处理被 <br> 或 <img> 分割的段落
                        for part in html_parts:
                            part_stripped = part.strip()
                            if not part_stripped:
                                continue

                            is_separator_tag = split_pattern.fullmatch(part_stripped)
                            plain_text = BeautifulSoup(part, 'html.parser').get_text(strip=True)

                            if not is_separator_tag and plain_text:
                                item_info = {
                                    "file_path": file_path,
                                    "tag": tag,
                                    "original_html": part,
                                    "original_full_html": inner_html,
                                    "is_split": True
                                }
                                items_to_translate.append(item_info)
                                original_texts.append(part)
                    else:
                        # 对于完整的标签内容（或表格单元格），我们整体处理
                        plain_text = tag.get_text(strip=True)
                        if plain_text:
                            item_info = {
                                "file_path": file_path,
                                "tag": tag,
                                "original_html": inner_html,
                                "is_split": False
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

        # ==================== 代码修改 3: 重构 _after_translate 逻辑 ====================
        # 使用一个更清晰的 defaultdict 来处理内容的重构
        # key 是每个独立 tag 对象的 id，value 是待处理的信息
        tag_reconstruction_map = defaultdict(
            lambda: {'chunks': [], 'is_split': False, 'original_full_html': None, 'tag_obj': None})

        for i, item_info in enumerate(items_to_translate):
            tag = item_info["tag"]
            tag_id = id(tag)

            tag_reconstruction_map[tag_id]['is_split'] = item_info['is_split']
            tag_reconstruction_map[tag_id]['tag_obj'] = tag
            if item_info['is_split']:
                tag_reconstruction_map[tag_id]['original_full_html'] = item_info['original_full_html']

            tag_reconstruction_map[tag_id]['chunks'].append({
                'original': original_texts[i],
                'translated': translated_texts[i]
            })

        for tag_id, data in tag_reconstruction_map.items():
            tag: Tag = data['tag_obj']
            final_html = ""

            if data['is_split']:
                # 如果是分割的段落，我们需要重组它
                reconstructed_html = data['original_full_html']
                for chunk in data['chunks']:
                    original_chunk = chunk['original']
                    translated_chunk = chunk['translated']

                    if self.insert_mode == "replace":
                        final_chunk = translated_chunk
                    elif self.insert_mode == "append":
                        final_chunk = original_chunk + self.separator + translated_chunk
                    else:  # prepend
                        final_chunk = translated_chunk + self.separator + original_chunk

                    # 使用带计数的替换，确保只替换第一个匹配项
                    reconstructed_html = reconstructed_html.replace(original_chunk, final_chunk, 1)

                final_html = reconstructed_html
            else:
                # 如果是完整的标签内容（包括表格单元格），则直接处理
                chunk = data['chunks'][0]
                original_chunk = chunk['original']
                translated_chunk = chunk['translated']

                if self.insert_mode == "replace":
                    final_html = translated_chunk
                elif self.insert_mode == "append":
                    # 对于表格，即使是 append 模式，直接拼接也可能破坏格式。
                    # 因此，对于 td/th，我们强制在内部用 separator 分隔，而不是在标签外。
                    if tag.name in ['td', 'th']:
                        final_html = f"{original_chunk}{self.separator}{translated_chunk}"
                    else:
                        final_html = original_chunk + self.separator + translated_chunk
                else:  # prepend
                    if tag.name in ['td', 'th']:
                        final_html = f"{translated_chunk}{self.separator}{original_chunk}"
                    else:
                        final_html = translated_chunk + self.separator + original_chunk

            # 清空旧内容并插入新内容
            tag.clear()
            # 使用 BeautifulSoup 解析最终的 HTML 片段，以正确处理嵌套标签
            new_content_soup = BeautifulSoup(final_html, 'html.parser')

            # new_content_soup.body 可能不存在，如果 final_html 不含 body 标签。
            # 我们需要从 soup 的顶层子节点开始插入。
            nodes_to_insert = list(new_content_soup.children)
            if len(nodes_to_insert) == 1 and nodes_to_insert[0].name == 'html':
                nodes_to_insert = list(nodes_to_insert[0].body.children)

            for node in nodes_to_insert:
                # .extract() 会将节点从原文档树中移除，这样可以直接 append 到新位置
                tag.append(node.extract())
        # ==================== 修改结束 ====================

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