# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
from dataclasses import dataclass
from io import BytesIO
from typing import Self, Literal, List, Optional, Dict, Tuple, Set
import zipfile
import re  # 引入正则用于解析简写
import xml.etree.ElementTree as ET

# 仅导入 openpyxl 的工具函数用于坐标计算，不加载 workbook 对象
from openpyxl.utils.cell import coordinate_to_tuple, range_boundaries

from docutranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator


@dataclass
class XlsxTranslatorConfig(AiTranslatorConfig):
    insert_mode: Literal["replace", "append", "prepend"] = "replace"
    separator: str = "\n"
    # 指定翻译区域列表。
    # 示例: ["Sheet1!A1:B10", "C", "3"] (支持简写: C代表C列, 3代表第3行)
    # 如果不指定表名 (如 "C")，则应用于所有表。
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

        # 命名空间定义
        self.ns = {
            'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
            'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
        }
        ET.register_namespace('', self.ns['main'])

    # =========================================================================
    # 辅助方法：无需加载 Workbook 即可解析结构
    # =========================================================================

    def _get_shared_strings(self, zf: zipfile.ZipFile) -> List[str]:
        """解析共享字符串表，返回字符串列表。"""
        if "xl/sharedStrings.xml" not in zf.namelist():
            return []

        shared_strings = []
        with zf.open("xl/sharedStrings.xml") as f:
            context = ET.iterparse(f, events=("end",))
            for event, elem in context:
                if elem.tag.endswith('}si'):  # shared item
                    texts = [t.text for t in elem.findall('.//main:t', self.ns) if t.text]
                    shared_strings.append("".join(texts))
                    elem.clear()
        return shared_strings

    def _get_sheet_mapping(self, zf: zipfile.ZipFile) -> Dict[str, str]:
        """
        获取 Sheet 名称到文件路径的映射。
        例如: {'Sheet1': 'xl/worksheets/sheet1.xml'}
        """
        sheet_name_to_rid = {}
        try:
            with zf.open("xl/workbook.xml") as f:
                root = ET.fromstring(f.read())
                for sheet in root.findall(".//main:sheet", self.ns):
                    name = sheet.get("name")
                    rid = sheet.get(f"{{{self.ns['r']}}}id")
                    if name and rid:
                        sheet_name_to_rid[name] = rid
        except Exception:
            return {}

        rid_to_target = {}
        try:
            with zf.open("xl/_rels/workbook.xml.rels") as f:
                tree = ET.parse(f)
                root = tree.getroot()
                for child in root:
                    rid = child.get("Id")
                    target = child.get("Target")
                    if rid and target:
                        if not target.startswith("/"):
                            target = "xl/" + target
                        rid_to_target[rid] = target
        except Exception:
            return {}

        mapping = {}
        for name, rid in sheet_name_to_rid.items():
            if rid in rid_to_target:
                mapping[name] = rid_to_target[rid]

        return mapping

    def _normalize_range(self, range_str: str) -> str:
        """
        将用户输入的简写转换为标准范围格式。
        "C" -> "C:C"
        "3" -> "3:3"
        "A1" -> "A1:A1" (openpyxl range_boundaries 实际上支持 A1，但这里统一处理更安全)
        """
        # 纯字母 (例如 "C", "AA") -> 整列
        if re.match(r"^[A-Za-z]+$", range_str):
            return f"{range_str}:{range_str}"
        # 纯数字 (例如 "3", "10") -> 整行
        if re.match(r"^\d+$", range_str):
            return f"{range_str}:{range_str}"
        return range_str

    def _parse_region_boundaries(self, sheet_mapping: Dict[str, str]) -> Dict[str, List[Tuple]]:
        """
        解析配置的 translate_regions。
        返回: { 'xl/worksheets/sheet1.xml': [(min_col, min_row, max_col, max_row), ...], ... }
        """
        if not self.translate_regions:
            return {}

        region_map = {}  # filename -> list of boundaries
        global_regions = []  # list of boundaries for all sheets

        for region in self.translate_regions:
            sheet_name = None
            raw_range = region.strip()

            if "!" in raw_range:
                parts = raw_range.split("!", 1)
                sheet_name = parts[0].strip("'")
                range_part = self._normalize_range(parts[1])
            else:
                range_part = self._normalize_range(raw_range)

            try:
                # boundaries: (min_col, min_row, max_col, max_row)
                boundaries = range_boundaries(range_part)

                if sheet_name:
                    filename = sheet_mapping.get(sheet_name)
                    if filename:
                        if filename not in region_map:
                            region_map[filename] = []
                        region_map[filename].append(boundaries)
                else:
                    global_regions.append(boundaries)
            except Exception as e:
                self.logger.warning(f"无法解析区域 '{region}': {e}")

        # 将全局区域添加到所有已知 Sheet
        if global_regions:
            all_files = set(sheet_mapping.values())
            for f in all_files:
                if f not in region_map:
                    region_map[f] = []
                region_map[f].extend(global_regions)

        return region_map

    def _is_in_boundaries(self, col: int, row: int, boundaries_list: List[Tuple]) -> bool:
        """检查坐标 (col, row) 是否在给定的边界列表中。"""
        for (min_col, min_row, max_col, max_row) in boundaries_list:
            if min_col is not None and col < min_col: continue
            if min_row is not None and row < min_row: continue
            if max_col is not None and col > max_col: continue
            if max_row is not None and row > max_row: continue
            return True
        return False

    # =========================================================================
    # 高效 XML 区域提取与重构
    # =========================================================================

    def _get_texts_xml_regions(self, document: Document) -> List[str]:
        """使用纯 XML 解析（结合 SharedStrings）提取指定区域文本。"""
        texts_to_translate = set()

        with zipfile.ZipFile(BytesIO(document.content), 'r') as zf:
            shared_strings = self._get_shared_strings(zf)
            if not shared_strings:
                return []

            sheet_mapping = self._get_sheet_mapping(zf)
            boundaries_map = self._parse_region_boundaries(sheet_mapping)

            for filename, boundaries in boundaries_map.items():
                if filename not in zf.namelist():
                    continue

                with zf.open(filename) as f:
                    context = ET.iterparse(f, events=("end",))
                    for event, elem in context:
                        if elem.tag.endswith('}c'):  # Cell
                            r_attr = elem.get('r')  # e.g. "C5"
                            t_attr = elem.get('t')  # e.g. "s"

                            if r_attr and t_attr == 's':
                                try:
                                    # 【修正】coordinate_to_tuple 返回 (row, col)
                                    row, col = coordinate_to_tuple(r_attr)
                                    if self._is_in_boundaries(col, row, boundaries):
                                        v_node = elem.find('main:v', self.ns)
                                        if v_node is not None and v_node.text:
                                            idx = int(v_node.text)
                                            if 0 <= idx < len(shared_strings):
                                                texts_to_translate.add(shared_strings[idx])
                                except Exception:
                                    pass
                            elem.clear()

        return list(texts_to_translate)

    def _rebuild_xml_regions(self, original_content_bytes: bytes, translation_map: dict) -> bytes:
        """使用纯 XML 重构，修正了坐标解包顺序。"""
        output_zip_io = BytesIO()

        with zipfile.ZipFile(BytesIO(original_content_bytes), 'r') as zf_in:
            with zipfile.ZipFile(output_zip_io, 'w', zipfile.ZIP_DEFLATED) as zf_out:

                shared_strings = self._get_shared_strings(zf_in)
                sheet_mapping = self._get_sheet_mapping(zf_in)
                boundaries_map = self._parse_region_boundaries(sheet_mapping)

                for item in zf_in.infolist():
                    if item.filename in boundaries_map:
                        boundaries = boundaries_map[item.filename]

                        with zf_in.open(item.filename) as f:
                            tree = ET.parse(f)
                            root = tree.getroot()

                            cells_modified = False
                            for cell in root.findall(".//main:c", self.ns):
                                r_attr = cell.get('r')
                                t_attr = cell.get('t')

                                if r_attr and t_attr == 's':
                                    try:
                                        # 【修正】coordinate_to_tuple 返回 (row, col)
                                        row, col = coordinate_to_tuple(r_attr)

                                        if self._is_in_boundaries(col, row, boundaries):
                                            v_node = cell.find('main:v', self.ns)
                                            if v_node is not None and v_node.text:
                                                idx = int(v_node.text)
                                                if 0 <= idx < len(shared_strings):
                                                    original_text = shared_strings[idx]

                                                    if original_text in translation_map:
                                                        translated_text = translation_map[original_text]

                                                        final_text = translated_text
                                                        if self.insert_mode == "append":
                                                            final_text = original_text + self.separator + translated_text
                                                        elif self.insert_mode == "prepend":
                                                            final_text = translated_text + self.separator + original_text

                                                        # 转换为 inlineStr
                                                        cell.set('t', 'inlineStr')
                                                        cell.remove(v_node)
                                                        is_node = ET.Element(f"{{{self.ns['main']}}}is")
                                                        t_node = ET.SubElement(is_node, f"{{{self.ns['main']}}}t")
                                                        t_node.text = final_text
                                                        cell.append(is_node)

                                                        cells_modified = True
                                    except Exception:
                                        pass

                            if cells_modified:
                                xml_str = ET.tostring(root, encoding='utf-8', xml_declaration=True)
                                zf_out.writestr(item, xml_str)
                            else:
                                zf_out.writestr(item, zf_in.read(item.filename))
                    else:
                        zf_out.writestr(item, zf_in.read(item.filename))

        return output_zip_io.getvalue()

    # =========================================================================
    # 原有全文档逻辑 (针对全文档翻译保持极致速度)
    # =========================================================================

    def _get_texts_xml_all(self, document: Document) -> List[str]:
        texts_to_translate = set()
        try:
            with zipfile.ZipFile(BytesIO(document.content), 'r') as zf:
                if "xl/sharedStrings.xml" in zf.namelist():
                    with zf.open("xl/sharedStrings.xml") as f:
                        root = ET.fromstring(f.read())
                        for node in root.findall('.//main:t', self.ns):
                            if node.text and node.text.strip():
                                texts_to_translate.add(node.text)

                for item in zf.infolist():
                    if item.filename.startswith("xl/tables/table"):
                        with zf.open(item.filename) as f:
                            root = ET.fromstring(f.read())
                            for col in root.findall('.//main:tableColumn', self.ns):
                                if col.get('name'):
                                    texts_to_translate.add(col.get('name'))
        except Exception as e:
            self.logger.error(f"XML解析失败: {e}")
        return list(texts_to_translate)

    def _rebuild_xml_all(self, original_content_bytes: bytes, translation_map: dict) -> bytes:
        output_zip_io = BytesIO()
        try:
            with zipfile.ZipFile(BytesIO(original_content_bytes), 'r') as zf_in:
                with zipfile.ZipFile(output_zip_io, 'w', zipfile.ZIP_DEFLATED) as zf_out:
                    for item in zf_in.infolist():
                        content = zf_in.read(item.filename)

                        if item.filename == "xl/sharedStrings.xml":
                            root = ET.fromstring(content)
                            for node in root.findall('.//main:t', self.ns):
                                if node.text in translation_map:
                                    trans = translation_map[node.text]
                                    if self.insert_mode == "append":
                                        node.text = node.text + self.separator + trans
                                    elif self.insert_mode == "prepend":
                                        node.text = trans + self.separator + node.text
                                    else:
                                        node.text = trans
                            content = ET.tostring(root, encoding='utf-8', xml_declaration=True)

                        elif item.filename.startswith("xl/tables/table"):
                            root = ET.fromstring(content)
                            for col in root.findall('.//main:tableColumn', self.ns):
                                orig = col.get('name')
                                if orig in translation_map:
                                    trans = translation_map[orig]
                                    if self.insert_mode == "append":
                                        col.set('name', orig + self.separator + trans)
                                    elif self.insert_mode == "prepend":
                                        col.set('name', trans + self.separator + orig)
                                    else:
                                        col.set('name', trans)
                            content = ET.tostring(root, encoding='utf-8', xml_declaration=True)

                        zf_out.writestr(item, content)
            return output_zip_io.getvalue()
        except Exception as e:
            self.logger.error(f"XML重构失败: {e}")
            return original_content_bytes

    # =========================================================================
    # 主入口
    # =========================================================================

    def translate(self, document: Document) -> Self:
        if self.translate_regions:
            original_texts = self._get_texts_xml_regions(document)
        else:
            original_texts = self._get_texts_xml_all(document)

        if not original_texts:
            print(f"\n未找到需要翻译的文本 (模式: {'区域' if self.translate_regions else '全文档'}).")
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

        if self.translate_regions:
            document.content = self._rebuild_xml_regions(document.content, translation_map)
        else:
            document.content = self._rebuild_xml_all(document.content, translation_map)

        return self

    async def translate_async(self, document: Document) -> Self:
        if self.translate_regions:
            original_texts = await asyncio.to_thread(self._get_texts_xml_regions, document)
        else:
            original_texts = await asyncio.to_thread(self._get_texts_xml_all, document)

        if not original_texts:
            print(f"\n未找到需要翻译的文本 (模式: {'区域' if self.translate_regions else '全文档'}).")
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

        if self.translate_regions:
            document.content = await asyncio.to_thread(self._rebuild_xml_regions, document.content, translation_map)
        else:
            document.content = await asyncio.to_thread(self._rebuild_xml_all, document.content, translation_map)

        return self