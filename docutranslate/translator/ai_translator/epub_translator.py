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

from bs4 import BeautifulSoup, Tag

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
    【高级版】此版本直接翻译HTML内容，以保留内联格式。
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
        Dict[str, bytes],  # all_files: 原始文件内容
        Dict[str, BeautifulSoup],  # soups: 解析后的HTML对象
        List[Dict[str, Any]],  # items_to_translate: 待翻译项
        List[str]  # original_texts: 原始HTML片段
    ]:
        all_files = {}
        soups = {}  # << [关键修改] 存储解析后的BS对象
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

        # TAGS_TO_TRANSLATE 定义了哪些块级标签的内容需要被翻译
        TAGS_TO_TRANSLATE = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'div']

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
                for tag in soup.find_all(TAGS_TO_TRANSLATE):
                    inner_html = tag.decode_contents()
                    if not inner_html or inner_html.isspace():
                        continue

                    # 使用正则表达式按 <br> 标签分割内容，同时保留 <br> 标签本身
                    html_parts = re.split(r'(<br\s*/?>)', inner_html, flags=re.IGNORECASE)

                    is_split = len(html_parts) > 1

                    for part in html_parts:
                        part_stripped = part.strip()
                        # 判断当前部分是否是 <br> 标签
                        is_br_tag = re.fullmatch(r'<br\s*/?>', part_stripped, flags=re.IGNORECASE)

                        # 我们只翻译那些不是 <br> 标签且有实际内容的片段
                        if not is_br_tag and part_stripped:
                            item_info = {
                                "file_path": file_path,
                                "tag": tag,  # 父标签的引用
                                "original_html": part,  # 这部分是需要翻译的原文
                                "original_full_html": inner_html if is_split else None  # 仅在分割时保存完整原文
                            }
                            items_to_translate.append(item_info)
                            original_texts.append(part)

        return all_files, soups, items_to_translate, original_texts

    def _after_translate(
            self,
            all_files: Dict[str, bytes],
            soups: Dict[str, BeautifulSoup],  # << [关键修改] 接收解析好的BS对象
            items_to_translate: List[Dict[str, Any]],
            translated_texts: List[str],
            original_texts: List[str],
    ) -> bytes:
        # 由于一个父标签可能被<br>分割成多个翻译块，我们需要重构替换逻辑
        # 按父标签（通过其对象id）对所有翻译块进行分组
        tag_reconstruction_map = defaultdict(lambda: {'new_html': None, 'chunks': []})

        # 1. 初始化每个父标签的重建信息
        for i, item_info in enumerate(items_to_translate):
            tag = item_info["tag"]
            tag_id = id(tag)
            if tag_reconstruction_map[tag_id]['new_html'] is None:
                # 如果有分割，使用保存的完整原文；否则，使用当前块的原文（因为就这一个块）
                original_full_html = item_info.get("original_full_html") or item_info["original_html"]
                tag_reconstruction_map[tag_id]['new_html'] = original_full_html
                tag_reconstruction_map[tag_id]['tag_obj'] = tag

        # 2. 为每个父标签准备好所有原始块和翻译块的对应关系
        for i, item_info in enumerate(items_to_translate):
            tag = item_info["tag"]
            tag_id = id(tag)
            original_chunk = original_texts[i]
            translated_chunk = translated_texts[i]

            if self.insert_mode == "replace":
                final_chunk = translated_chunk
            elif self.insert_mode == "append":
                final_chunk = original_chunk + self.separator + translated_chunk
            elif self.insert_mode == "prepend":
                final_chunk = translated_chunk + self.separator + original_chunk
            else:
                final_chunk = translated_chunk

            tag_reconstruction_map[tag_id]['chunks'].append({'original': original_chunk, 'final': final_chunk})

        # 3. 对每个父标签，用其所有的翻译块重建完整内容
        for tag_id, data in tag_reconstruction_map.items():
            tag: Tag = data['tag_obj']
            reconstructed_html = data['new_html']

            for chunk_info in data['chunks']:
                # 使用replace函数进行替换。为避免错误替换，处理原始文本中的特殊字符
                # 这个方法在原始文本块在父标签中重复出现时可能出错，但对于大多数情况是有效的
                reconstructed_html = reconstructed_html.replace(chunk_info['original'], chunk_info['final'], 1)

            # 4. 更新父标签的内容
            tag.clear()
            new_content_soup = BeautifulSoup(reconstructed_html, 'html.parser')

            if new_content_soup.body:
                nodes_to_insert = list(new_content_soup.body.children)
            else:
                nodes_to_insert = list(new_content_soup.children)

            for node in nodes_to_insert:
                tag.append(node.extract())

        # 从修改后的soups对象生成新的文件内容
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