# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
from dataclasses import dataclass
from io import BytesIO
from typing import Self, Literal, List, Optional
import zipfile
import xml.etree.ElementTree as ET

import openpyxl
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
                system_proxy_enable=config.system_proxy_enable
            )
            self.translate_agent = SegmentsTranslateAgent(agent_config)
        self.insert_mode = config.insert_mode
        self.separator = config.separator
        self.translate_regions = config.translate_regions

    def _get_texts_to_translate(self, document: Document) -> List[str]:
        """使用 openpyxl 识别指定区域内需要翻译的文本。"""
        texts_to_translate = set()
        try:
            # 使用 data_only=True 来获取单元格的计算值，而不是公式
            workbook = openpyxl.load_workbook(BytesIO(document.content), data_only=True)
            # 如果未指定区域，则翻译所有文本
            if not self.translate_regions:
                for sheet in workbook.worksheets:
                    for row in sheet.iter_rows():
                        for cell in row:
                            # 仅处理共享字符串类型，这是最常见的文本存储方式
                            if isinstance(cell.value, str) and cell.data_type == "s":
                                texts_to_translate.add(cell.value)
                # 同时也要检查表格的标题
                for sheet in workbook.worksheets:
                    for table in sheet._tables:
                        for column in table.tableColumns:
                            if column.name:
                                texts_to_translate.add(column.name)

            # 如果指定了区域
            else:
                processed_coordinates = set()
                regions_by_sheet = {}
                all_sheet_regions = []
                for region in self.translate_regions:
                    if '!' in region:
                        sheet_name, cell_range = region.split('!', 1)
                        # 支持带引号的工作表名称
                        sheet_name = sheet_name.strip("'")
                        if sheet_name not in regions_by_sheet:
                            regions_by_sheet[sheet_name] = []
                        regions_by_sheet[sheet_name].append(cell_range)
                    else:
                        all_sheet_regions.append(region)

                for sheet in workbook.worksheets:
                    sheet_specific_ranges = regions_by_sheet.get(sheet.title, [])
                    total_ranges_for_this_sheet = sheet_specific_ranges + all_sheet_regions

                    if not total_ranges_for_this_sheet:
                        continue

                    # 检查此区域内的表格标题
                    for table in sheet._tables:
                        # openpyxl 没有提供简单的方法来检查表格是否与区域相交
                        # 为简单起见，我们假设如果指定了工作表，则翻译该工作表上的所有表格标题
                        for column in table.tableColumns:
                            if column.name:
                                texts_to_translate.add(column.name)

                    for cell_range in total_ranges_for_this_sheet:
                        try:
                            cells_in_range = sheet[cell_range]
                            flat_cells = []
                            if isinstance(cells_in_range, Cell):
                                flat_cells.append(cells_in_range)
                            elif isinstance(cells_in_range, tuple):
                                for item in cells_in_range:
                                    if isinstance(item, Cell):
                                        flat_cells.append(item)
                                    elif isinstance(item, tuple):
                                        flat_cells.extend(item)

                            for cell in flat_cells:
                                if isinstance(cell.value, str) and cell.data_type == "s":
                                    texts_to_translate.add(cell.value)
                        except Exception as e:
                            self.logger.warning(f"跳过无效的区域 '{cell_range}' 在工作表 '{sheet.title}'. 错误: {e}")
            workbook.close()
        except Exception as e:
            self.logger.error(f"使用 openpyxl 预处理文件失败: {e}")

        return list(texts_to_translate)

    def _rebuild_xlsx_with_translated_content(self, original_content_bytes: bytes, translation_map: dict) -> bytes:
        """
        通过替换 sharedStrings.xml 和 tableX.xml 中的文本内容来重构 XLSX 文件。
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
            print("\n在指定区域中没有找到需要翻译的纯文本内容。")
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
            print("\n在指定区域中没有找到需要翻译的纯文本内容。")
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