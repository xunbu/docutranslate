# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
import os
import xml.etree.ElementTree as ET
import zipfile
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

        TAGS_TO_TRANSLATE = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'div']

        for item_id, item_data in manifest_items.items():
            media_type = item_data['media_type']
            if media_type in ['application/xhtml+xml', 'text/html']:
                file_path = item_data['href']
                content_bytes = all_files.get(file_path)
                if not content_bytes:
                    self.logger.warning(f"在 EPUB 中找不到文件: {file_path}")
                    continue

                # << [关键修改] 解析一次并存储
                if file_path not in soups:
                    soups[file_path] = BeautifulSoup(content_bytes, "html.parser")

                soup = soups[file_path]
                for tag in soup.find_all(TAGS_TO_TRANSLATE):
                    inner_html = tag.decode_contents()
                    if inner_html and not inner_html.isspace():
                        item_info = {
                            "file_path": file_path,
                            "tag": tag,  # 这个tag是soups[file_path]中的活引用
                            "original_html": inner_html,
                        }
                        items_to_translate.append(item_info)
                        original_texts.append(inner_html)

        return all_files, soups, items_to_translate, original_texts

    def _after_translate(
            self,
            all_files: Dict[str, bytes],
            soups: Dict[str, BeautifulSoup],  # << [关键修改] 接收解析好的BS对象
            items_to_translate: List[Dict[str, Any]],
            translated_texts: List[str],
            original_texts: List[str],
    ) -> bytes:
        for i, item_info in enumerate(items_to_translate):
            # << [关键修改] 直接使用 item_info 中的活引用 tag，它属于 soups 字典中的一个对象
            tag: Tag = item_info["tag"]
            translated_html = translated_texts[i]
            original_html = original_texts[i]

            if self.insert_mode == "replace":
                final_html = translated_html
            elif self.insert_mode == "append":
                final_html = original_html + self.separator + translated_html
            elif self.insert_mode == "prepend":
                final_html = translated_html + self.separator + original_html
            else:
                final_html = translated_html

            # 清空旧内容
            tag.clear()

            # 解析新的HTML片段
            new_content_soup = BeautifulSoup(final_html, 'html.parser')

            # << [关键修复] 将新片段的*内容*（而不是整个文档）移动到原始标签中
            # 使用 list() 创建副本以安全地迭代和修改
            if new_content_soup.body:
                nodes_to_insert = list(new_content_soup.body.children)
            else:
                nodes_to_insert = list(new_content_soup.children)

            for node in nodes_to_insert:
                tag.append(node.extract())  # .extract() 从旧树中移除并返回节点

        # << [关键修改] 从修改后的soups对象生成新的文件内容
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
        # << [关键修改] 传递 soups 对象
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
        # << [关键修改] 传递 soups 对象
        document.content = await asyncio.to_thread(
            self._after_translate, all_files, soups, items_to_translate, translated_texts, original_texts
        )
        return self