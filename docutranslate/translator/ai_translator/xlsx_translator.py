# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
from dataclasses import dataclass
from io import BytesIO
from typing import Self, Literal, List, Optional
import zipfile
import xml.etree.ElementTree as ET

import openpyxl  # openpyxl 仍然保留，以备将来可能需要混合模式或用于其他目的
from openpyxl.cell import Cell

from docutranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator


@dataclass
class XlsxTranslatorConfig(AiTranslatorConfig):
    insert_mode: Literal["replace", "append", "prepend"] = "replace"
    separator: str = "\n"
    # 指定翻译区域列表。
    # 示例: ["Sheet1!A1:B10", "C:D", "E5"]
    # 如果不指定表名 (如 "C:D")，则应用于所有表。
    # 如果为 None 或空列表，则翻译整个文件中的所有文本。
    translate_regions: Optional[List[str]] = None


class XlsxTranslator(AiTranslator):
    def __init__(self, config: XlsxTranslatorConfig):
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
        self.translate_regions = config.translate_regions

    def _get_texts_to_translate(self, document: Document) -> List[str]:
        """
        【已修改】通过直接解析内部XML文件来识别需要翻译的文本。
        这种方法可以正确处理包含富文本的单元格，并确保与重建逻辑一致，但不支持按区域翻译。
        """
        if self.translate_regions:
            self.logger.warning("当前文本提取方法直接解析XML，不支持 'translate_regions'。将翻译文件中的所有文本内容。")

        texts_to_translate = set()
        ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

        try:
            with zipfile.ZipFile(BytesIO(document.content), 'r') as original_zip:
                # --- 1. 处理共享字符串 (sharedStrings.xml) ---
                # 这是所有文本（包括富文本片段）的主要存储位置。
                if "xl/sharedStrings.xml" in original_zip.namelist():
                    with original_zip.open("xl/sharedStrings.xml") as f:
                        root = ET.fromstring(f.read())
                        # 查找所有 <t> 元素，无论它们在哪个层级，这能正确捕获富文本片段
                        text_nodes = root.findall('.//main:t', ns)
                        for node in text_nodes:
                            # 确保节点有文本内容且不是纯粹的空白
                            if node.text and node.text.strip():
                                texts_to_translate.add(node.text)

                # --- 2. 处理表格标题 (tableX.xml) ---
                # 表格的列名不存储在 sharedStrings.xml 中，需要单独处理。
                for item in original_zip.infolist():
                    if item.filename.startswith("xl/tables/table"):
                        with original_zip.open(item.filename) as f:
                            root = ET.fromstring(f.read())
                            table_columns = root.findall('.//main:tableColumn', ns)
                            for col in table_columns:
                                original_name = col.get('name')
                                if original_name and original_name.strip():
                                    texts_to_translate.add(original_name)

        except Exception as e:
            self.logger.error(f"直接解析XLSX的XML文件失败: {e}")

        return list(texts_to_translate)

    def _rebuild_xlsx_with_translated_content(self, original_content_bytes: bytes, translation_map: dict) -> bytes:
        """
        【无需修改】通过替换 sharedStrings.xml 和 tableX.xml 中的文本内容来重构 XLSX 文件。
        此函数的逻辑与新的读取逻辑完全匹配。
        """
        # 注册命名空间以正确解析和生成XML
        ns = {
            'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        }
        ET.register_namespace('', ns['main'])

        original_zip_io = BytesIO(original_content_bytes)
        output_zip_io = BytesIO()

        try:
            with zipfile.ZipFile(original_zip_io, 'r') as original_zip:
                with zipfile.ZipFile(output_zip_io, 'w', zipfile.ZIP_DEFLATED) as output_zip:
                    for item in original_zip.infolist():
                        file_content = original_zip.read(item.filename)

                        # --- 1. 处理共享字符串文件 ---
                        if item.filename == "xl/sharedStrings.xml":
                            root = ET.fromstring(file_content)
                            text_nodes = root.findall('.//main:t', ns)
                            for node in text_nodes:
                                original_text = node.text
                                if original_text in translation_map:
                                    translated_text = translation_map[original_text]
                                    if self.insert_mode == "replace":
                                        node.text = translated_text
                                    elif self.insert_mode == "append":
                                        node.text = original_text + self.separator + translated_text
                                    elif self.insert_mode == "prepend":
                                        node.text = translated_text + self.separator + original_text
                            file_content = ET.tostring(root, encoding='utf-8', xml_declaration=True)

                        # --- 2. 处理表格定义文件 ---
                        elif item.filename.startswith("xl/tables/table"):
                            root = ET.fromstring(file_content)
                            table_columns = root.findall('.//main:tableColumn', ns)
                            for col in table_columns:
                                original_name = col.get('name')
                                if original_name in translation_map:
                                    translated_name = translation_map[original_name]
                                    if self.insert_mode == "replace":
                                        col.set('name', translated_name)
                                    elif self.insert_mode == "append":
                                        col.set('name', original_name + self.separator + translated_name)
                                    elif self.insert_mode == "prepend":
                                        col.set('name', translated_name + self.separator + original_name)
                            file_content = ET.tostring(root, encoding='utf-8', xml_declaration=True)

                        output_zip.writestr(item, file_content)

            return output_zip_io.getvalue()

        except (zipfile.BadZipFile, ET.ParseError) as e:
            self.logger.error(f"处理XLSX文件失败: {e}. 返回原始文件。")
            return original_content_bytes

    def translate(self, document: Document) -> Self:
        original_texts = self._get_texts_to_translate(document)

        if not original_texts:
            print("\n在文件中没有找到需要翻译的文本内容。")
            return self

        if self.glossary_agent:
            self.glossary_dict_gen = self.glossary_agent.send_segments(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

        if self.translate_agent:
            translated_texts = self.translate_agent.send_segments(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts

        translation_map = dict(zip(original_texts, translated_texts))

        document.content = self._rebuild_xlsx_with_translated_content(document.content, translation_map)

        return self

    async def translate_async(self, document: Document) -> Self:
        original_texts = await asyncio.to_thread(self._get_texts_to_translate, document)

        if not original_texts:
            print("\n在文件中没有找到需要翻译的文本内容。")
            return self

        if self.glossary_agent:
            self.glossary_dict_gen = await self.glossary_agent.send_segments_async(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

        if self.translate_agent:
            translated_texts = await self.translate_agent.send_segments_async(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts

        translation_map = dict(zip(original_texts, translated_texts))

        document.content = await asyncio.to_thread(self._rebuild_xlsx_with_translated_content, document.content,
                                                   translation_map)

        return self