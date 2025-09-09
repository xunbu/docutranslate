# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
import os
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from io import BytesIO
from typing import Self, Literal, List, Dict, Any

from bs4 import BeautifulSoup

from docutranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator


@dataclass
class EpubTranslatorConfig(AiTranslatorConfig):
    insert_mode: Literal["replace", "append", "prepend"] = "replace"
    separator: str = "\n"


class EpubTranslator(AiTranslator):
    """
    一个用于翻译 EPUB 文件中内容的翻译器。
    此版本使用内置的 `zipfile` 和 `xml` 库，不依赖 `ebooklib`。
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
                retry=config.retry
            )
            self.translate_agent = SegmentsTranslateAgent(agent_config)
        self.insert_mode = config.insert_mode
        self.separator = config.separator

    def _pre_translate(self, document: Document) -> tuple[
        Dict[str, bytes], List[Dict[str, Any]], List[str]
    ]:
        """
        预处理 EPUB 文件，提取所有需要翻译的文本。
        """
        all_files = {}
        items_to_translate = []
        original_texts = []

        # --- 步骤 1: 使用 zipfile 读取 EPUB 内容到内存 ---
        with zipfile.ZipFile(BytesIO(document.content), 'r') as zf:
            for filename in zf.namelist():
                all_files[filename] = zf.read(filename)

        # --- 步骤 2: 解析元数据以找到内容文件 ---
        # 2.1: 解析 container.xml 找到 .opf 文件的路径
        container_xml = all_files.get('META-INF/container.xml')
        if not container_xml:
            raise ValueError("无效的 EPUB：找不到 META-INF/container.xml")

        root = ET.fromstring(container_xml)
        # XML 命名空间，解析时必须使用
        ns = {'cn': 'urn:oasis:names:tc:opendocument:xmlns:container'}
        opf_path = root.find('cn:rootfiles/cn:rootfile', ns).get('full-path')
        opf_dir = os.path.dirname(opf_path)

        # 2.2: 解析 .opf 文件找到 manifest 和 spine
        opf_xml = all_files.get(opf_path)
        if not opf_xml:
            raise ValueError(f"无效的 EPUB：找不到 {opf_path}")

        opf_root = ET.fromstring(opf_xml)
        ns_opf = {'opf': 'http://www.idpf.org/2007/opf'}

        manifest_items = {}
        for item in opf_root.findall('opf:manifest/opf:item', ns_opf):
            item_id = item.get('id')
            href = item.get('href')
            # 路径需要相对于 .opf 文件的位置
            full_href = os.path.join(opf_dir, href).replace('\\', '/')
            manifest_items[item_id] = {'href': full_href, 'media_type': item.get('media-type')}

        spine_itemrefs = [item.get('idref') for item in opf_root.findall('opf:spine/opf:itemref', ns_opf)]

        # --- 步骤 3: 提取可翻译内容 ---
        # 我们这里简单地翻译 manifest 中所有的 xhtml/html 文件
        for item_id, item_data in manifest_items.items():
            media_type = item_data['media_type']
            if media_type in ['application/xhtml+xml', 'text/html']:
                file_path = item_data['href']
                content_bytes = all_files.get(file_path)
                if not content_bytes:
                    self.logger.warning(f"在 EPUB 中找不到文件: {file_path}")
                    continue

                soup = BeautifulSoup(content_bytes, "html.parser")
                for text_node in soup.find_all(string=True):
                    if (
                            text_node.parent.name not in ['style', 'script', 'head', 'title', 'meta', '[document]']
                            and not text_node.isspace()
                    ):
                        text = text_node.get_text(strip=True)
                        if text:
                            item_info = {
                                "file_path": file_path,
                                "text_node": text_node,
                                "original_text": text,
                            }
                            items_to_translate.append(item_info)
                            original_texts.append(text)

        return all_files, items_to_translate, original_texts

    def _after_translate(
            self,
            all_files: Dict[str, bytes],
            items_to_translate: List[Dict[str, Any]],
            translated_texts: List[str],
            original_texts: List[str],
    ) -> bytes:
        """
        将翻译后的文本写回，并重新打包成 EPUB 文件。
        """
        modified_soups = {}  # 缓存每个文件的 soup 对象

        for i, item_info in enumerate(items_to_translate):
            file_path = item_info["file_path"]
            text_node = item_info["text_node"]
            translated_text = translated_texts[i]
            original_text = original_texts[i]

            # 获取或创建该文件的 soup 对象
            if file_path not in modified_soups:
                # 找到该节点所属的根 soup 对象
                modified_soups[file_path] = text_node.find_parent('html')

            if self.insert_mode == "replace":
                new_text = translated_text
            elif self.insert_mode == "append":
                new_text = original_text + self.separator + translated_text
            elif self.insert_mode == "prepend":
                new_text = translated_text + self.separator + original_text
            else:
                new_text = translated_text

            text_node.replace_with(new_text)

        # 将修改后的 soup 对象转换回字节串
        for file_path, soup in modified_soups.items():
            all_files[file_path] = str(soup).encode('utf-8')

        # --- 步骤 4: 创建新的 EPUB (ZIP) 文件 ---
        output_buffer = BytesIO()
        with zipfile.ZipFile(output_buffer, 'w') as zf_out:
            # 关键：mimetype 必须是第一个文件且不能压缩
            if 'mimetype' in all_files:
                zf_out.writestr('mimetype', all_files['mimetype'], compress_type=zipfile.ZIP_STORED)

            # 写入其他所有文件
            for filename, content in all_files.items():
                if filename != 'mimetype':
                    zf_out.writestr(filename, content, compress_type=zipfile.ZIP_DEFLATED)

        return output_buffer.getvalue()

    def translate(self, document: Document) -> Self:
        """
        同步翻译 EPUB 文档。
        """
        all_files, items_to_translate, original_texts = self._pre_translate(document)
        if not items_to_translate:
            self.logger.info("\n文件中没有找到需要翻译的纯文本内容。")
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
            all_files, items_to_translate, translated_texts, original_texts
        )
        return self

    async def translate_async(self, document: Document) -> Self:
        """
        异步翻译 EPUB 文档。
        """
        all_files, items_to_translate, original_texts = await asyncio.to_thread(
            self._pre_translate, document
        )
        if not items_to_translate:
            self.logger.info("\n文件中没有找到需要翻译的纯文本内容。")
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
            self._after_translate, all_files, items_to_translate, translated_texts, original_texts
        )
        return self
