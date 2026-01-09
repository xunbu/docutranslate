# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
from dataclasses import dataclass
from io import BytesIO
from typing import Self, Literal, List, Optional, Dict, Tuple, Set
import zipfile
import re
import xml.etree.ElementTree as ET

from openpyxl.utils.cell import coordinate_to_tuple, range_boundaries

from docutranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator


@dataclass
class XlsxTranslatorConfig(AiTranslatorConfig):
    insert_mode: Literal["replace", "append", "prepend"] = "replace"
    separator: str = "\n"
    # 指定翻译区域列表。
    translate_regions: Optional[List[str]] = None


class XlsxTranslator(AiTranslator):
    def __init__(self, config: XlsxTranslatorConfig):
        super().__init__(config=config)
        self.chunk_size = config.chunk_size
        self.translate_agent = None
        glossary_dict = self.glossary.glossary_dict if self.glossary else None
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
                glossary_dict=glossary_dict,
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
        self.translate_regions = config.translate_regions

        # 我们虽然不依赖它查找，但写入新节点时最好还是带上标准命名空间
        self.NS_MAIN = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        ET.register_namespace('', self.NS_MAIN)

    # =========================================================================
    # 核心辅助方法：忽略命名空间查找
    # =========================================================================

    def _tag_is(self, elem: ET.Element, tag_name: str) -> bool:
        """判断元素的标签名是否匹配（忽略命名空间）。"""
        return elem.tag.endswith(f"}}{tag_name}") or elem.tag == tag_name

    def _find_child(self, parent: ET.Element, tag_name: str) -> Optional[ET.Element]:
        """在直接子节点中查找指定标签（忽略命名空间）。"""
        for child in parent:
            if self._tag_is(child, tag_name):
                return child
        return None

    def _find_all_children(self, parent: ET.Element, tag_name: str) -> List[ET.Element]:
        """查找所有匹配的直接子节点（忽略命名空间）。"""
        return [child for child in parent if self._tag_is(child, tag_name)]

    def _get_child_text(self, parent: ET.Element, tag_name: str) -> Optional[str]:
        """获取子节点的文本内容（忽略命名空间）。"""
        child = self._find_child(parent, tag_name)
        return child.text if child is not None else None

    # =========================================================================
    # 辅助逻辑
    # =========================================================================

    def _get_shared_strings(self, zf: zipfile.ZipFile) -> List[str]:
        if "xl/sharedStrings.xml" not in zf.namelist():
            return []
        shared_strings = []
        with zf.open("xl/sharedStrings.xml") as f:
            context = ET.iterparse(f, events=("end",))
            for event, elem in context:
                # 匹配 <si>
                if self._tag_is(elem, "si"):
                    # 查找所有 <t>
                    # 注意：xml.etree 的 findall 只能简单的路径查找，
                    # 既然我们要忽略命名空间，最好手动遍历子树，但 si 结构简单，
                    # 这里简化处理：直接遍历 iter 出来的 t 元素（如果在 si 内部）
                    pass
                    # 由于 iterparse 是扁平流，很难直接关联 si 和 t。
                    # 更稳妥的方式是：当 elem 是 si 时，遍历 elem 的 children
                    texts = []
                    for child in elem.iter():
                        if self._tag_is(child, "t") and child.text:
                            texts.append(child.text)
                    shared_strings.append("".join(texts))
                    elem.clear()
        return shared_strings

    def _get_sheet_mapping(self, zf: zipfile.ZipFile) -> Dict[str, str]:
        """建立 SheetName -> ZipFilename 的映射（稳健版）"""
        sheet_name_to_rid = {}
        try:
            with zf.open("xl/workbook.xml") as f:
                root = ET.fromstring(f.read())
                # 查找所有 sheet 标签
                # 需递归查找，因为 sheet 通常在 sheets 节点下
                for sheet in root.iter():
                    if self._tag_is(sheet, "sheet"):
                        name = sheet.get("name")
                        # id 的属性名通常带有 r: 前缀，这很难忽略命名空间，
                        # 但 openpyxl 规范里 id 属性几乎总是依赖 relationships 命名空间
                        # 这里我们尝试遍历属性找到 key 包含 id 的
                        rid = None
                        for k, v in sheet.attrib.items():
                            if k.endswith("id"):  # 匹配 r:id
                                rid = v
                                break
                        if name and rid:
                            sheet_name_to_rid[name] = rid
        except Exception:
            return {}

        rid_to_target = {}
        try:
            with zf.open("xl/_rels/workbook.xml.rels") as f:
                root = ET.fromstring(f.read())
                for child in root:
                    # Relationships 里的 tag 也是 Relationship
                    rid = child.get("Id")
                    target = child.get("Target")
                    if rid and target:
                        target = target.replace("\\", "/")
                        if target.startswith("/"):
                            target = target.lstrip("/")
                        else:
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
        if re.match(r"^[A-Za-z]+$", range_str):
            return f"{range_str}:{range_str}"
        if re.match(r"^\d+$", range_str):
            return f"{range_str}:{range_str}"
        return range_str

    def _parse_region_boundaries(self, sheet_mapping: Dict[str, str]) -> Dict[str, List[Tuple]]:
        if not self.translate_regions:
            return {}
        region_map = {}
        global_regions = []

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

        if global_regions:
            target_files = set(sheet_mapping.values())
            for f in target_files:
                if f not in region_map:
                    region_map[f] = []
                region_map[f].extend(global_regions)
        return region_map

    def _is_in_boundaries(self, col: int, row: int, boundaries_list: List[Tuple]) -> bool:
        for (min_col, min_row, max_col, max_row) in boundaries_list:
            if min_col is not None and col < min_col: continue
            if min_row is not None and row < min_row: continue
            if max_col is not None and col > max_col: continue
            if max_row is not None and row > max_row: continue
            return True
        return False

    def _apply_insert_mode(self, original: str, translated: str) -> str:
        if self.insert_mode == "append":
            return f"{original}{self.separator}{translated}"
        elif self.insert_mode == "prepend":
            return f"{translated}{self.separator}{original}"
        else:
            return translated

    # =========================================================================
    # 区域处理 (使用 Helper 方法，完全解耦命名空间)
    # =========================================================================

    def _get_texts_xml_regions(self, document: Document) -> List[str]:
        texts_to_translate = set()

        with zipfile.ZipFile(BytesIO(document.content), 'r') as zf:
            shared_strings = self._get_shared_strings(zf)
            sheet_mapping = self._get_sheet_mapping(zf)

            if not sheet_mapping:
                all_sheets = [n for n in zf.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")]
                for s in all_sheets:
                    sheet_mapping[f"Unknown_{s}"] = s

            boundaries_map = self._parse_region_boundaries(sheet_mapping)

            for filename, boundaries in boundaries_map.items():
                if filename not in zf.namelist():
                    continue

                with zf.open(filename) as f:
                    context = ET.iterparse(f, events=("end",))
                    for event, elem in context:
                        # 匹配 <c>
                        if self._tag_is(elem, "c"):
                            r_attr = elem.get('r')
                            t_attr = elem.get('t')

                            if r_attr:
                                try:
                                    row, col = coordinate_to_tuple(r_attr)
                                    if self._is_in_boundaries(col, row, boundaries):
                                        text_found = None

                                        # Shared String
                                        if t_attr == 's':
                                            v_text = self._get_child_text(elem, "v")
                                            if v_text:
                                                idx = int(v_text)
                                                if 0 <= idx < len(shared_strings):
                                                    text_found = shared_strings[idx]

                                        # Inline String
                                        elif t_attr == 'inlineStr':
                                            is_node = self._find_child(elem, "is")
                                            if is_node is not None:
                                                t_text = self._get_child_text(is_node, "t")
                                                if t_text:
                                                    text_found = t_text

                                        if text_found:
                                            texts_to_translate.add(text_found)
                                except Exception:
                                    pass
                            elem.clear()
                        elif self._tag_is(elem, "row"):
                            elem.clear()

        return list(texts_to_translate)

    def _rebuild_xml_regions(self, original_content_bytes: bytes, translation_map: dict) -> bytes:
        output_zip_io = BytesIO()
        with zipfile.ZipFile(BytesIO(original_content_bytes), 'r') as zf_in:
            with zipfile.ZipFile(output_zip_io, 'w', zipfile.ZIP_DEFLATED) as zf_out:
                shared_strings = self._get_shared_strings(zf_in)
                sheet_mapping = self._get_sheet_mapping(zf_in)

                if not sheet_mapping:
                    all_sheets = [n for n in zf_in.namelist() if
                                  n.startswith("xl/worksheets/sheet") and n.endswith(".xml")]
                    for s in all_sheets:
                        sheet_mapping[f"Unknown_{s}"] = s

                boundaries_map = self._parse_region_boundaries(sheet_mapping)

                for item in zf_in.infolist():
                    if item.filename in boundaries_map:
                        boundaries = boundaries_map[item.filename]
                        with zf_in.open(item.filename) as f:
                            tree = ET.parse(f)
                            root = tree.getroot()
                            cells_modified = False

                            # 查找所有 <c>
                            # 因为 findall 不支持复杂的 tag.endswith，这里我们遍历所有节点
                            # 对于 parse 加载的树，iter() 是高效的
                            for cell in root.iter():
                                if not self._tag_is(cell, "c"):
                                    continue

                                r_attr = cell.get('r')
                                t_attr = cell.get('t')
                                if r_attr:
                                    try:
                                        row, col = coordinate_to_tuple(r_attr)
                                        if self._is_in_boundaries(col, row, boundaries):
                                            original_text = None

                                            if t_attr == 's':
                                                v_text = self._get_child_text(cell, "v")
                                                if v_text:
                                                    idx = int(v_text)
                                                    if 0 <= idx < len(shared_strings):
                                                        original_text = shared_strings[idx]
                                            elif t_attr == 'inlineStr':
                                                is_node = self._find_child(cell, "is")
                                                if is_node is not None:
                                                    original_text = self._get_child_text(is_node, "t")

                                            if original_text and original_text in translation_map:
                                                final_text = self._apply_insert_mode(original_text,
                                                                                     translation_map[original_text])

                                                # 清空旧内容
                                                for child in list(cell):
                                                    cell.remove(child)

                                                # 写入新内容 (这里必须使用带有命名空间的标签名，否则Excel不认)
                                                cell.set('t', 'inlineStr')
                                                # 注意：写入时使用 self.NS_MAIN 是必须的，因为这是标准
                                                is_node = ET.Element(f"{{{self.NS_MAIN}}}is")
                                                t_node = ET.SubElement(is_node, f"{{{self.NS_MAIN}}}t")
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
    # 全文档处理 (同样使用 Helper)
    # =========================================================================

    def _get_texts_xml_all(self, document: Document) -> List[str]:
        texts_to_translate = set()
        try:
            with zipfile.ZipFile(BytesIO(document.content), 'r') as zf:
                if "xl/sharedStrings.xml" in zf.namelist():
                    with zf.open("xl/sharedStrings.xml") as f:
                        context = ET.iterparse(f, events=("end",))
                        for event, elem in context:
                            if self._tag_is(elem, "t"):
                                if elem.text and elem.text.strip():
                                    texts_to_translate.add(elem.text)
                                elem.clear()

                sheet_files = [n for n in zf.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")]
                for sheet_file in sheet_files:
                    with zf.open(sheet_file) as f:
                        context = ET.iterparse(f, events=("end",))
                        for event, elem in context:
                            if self._tag_is(elem, "c"):
                                if elem.get('t') == 'inlineStr':
                                    is_node = self._find_child(elem, "is")
                                    if is_node is not None:
                                        t_text = self._get_child_text(is_node, "t")
                                        if t_text and t_text.strip():
                                            texts_to_translate.add(t_text)
                                elem.clear()
                            elif self._tag_is(elem, "row"):
                                elem.clear()

                for item in zf.infolist():
                    if item.filename.startswith("xl/tables/table"):
                        with zf.open(item.filename) as f:
                            root = ET.fromstring(f.read())
                            for col in root.iter():
                                if self._tag_is(col, "tableColumn"):
                                    if col.get('name'):
                                        texts_to_translate.add(col.get('name'))
        except Exception as e:
            self.logger.error(f"XML解析失败: {e}", exc_info=True)
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
                            modified = False
                            for node in root.iter():
                                if self._tag_is(node, "t"):
                                    if node.text in translation_map:
                                        node.text = self._apply_insert_mode(node.text, translation_map[node.text])
                                        modified = True
                            if modified:
                                zf_out.writestr(item, ET.tostring(root, encoding='utf-8', xml_declaration=True))
                            else:
                                zf_out.writestr(item, content)

                        elif item.filename.startswith("xl/worksheets/sheet") and item.filename.endswith(".xml"):
                            root = ET.fromstring(content)
                            modified = False
                            for cell in root.iter():
                                if self._tag_is(cell, "c") and cell.get('t') == 'inlineStr':
                                    is_node = self._find_child(cell, "is")
                                    if is_node is not None:
                                        t_node = self._find_child(is_node, "t")
                                        if t_node is not None and t_node.text in translation_map:
                                            t_node.text = self._apply_insert_mode(t_node.text,
                                                                                  translation_map[t_node.text])
                                            modified = True
                            if modified:
                                zf_out.writestr(item, ET.tostring(root, encoding='utf-8', xml_declaration=True))
                            else:
                                zf_out.writestr(item, content)

                        elif item.filename.startswith("xl/tables/table"):
                            root = ET.fromstring(content)
                            modified = False
                            for col in root.iter():
                                if self._tag_is(col, "tableColumn"):
                                    orig = col.get('name')
                                    if orig in translation_map:
                                        col.set('name', self._apply_insert_mode(orig, translation_map[orig]))
                                        modified = True
                            if modified:
                                zf_out.writestr(item, ET.tostring(root, encoding='utf-8', xml_declaration=True))
                            else:
                                zf_out.writestr(item, content)
                        else:
                            zf_out.writestr(item, content)
            return output_zip_io.getvalue()
        except Exception as e:
            self.logger.error(f"XML重构失败: {e}", exc_info=True)
            return original_content_bytes

    def translate(self, document: Document) -> Self:
        if self.translate_regions:
            original_texts = self._get_texts_xml_regions(document)
        else:
            original_texts = self._get_texts_xml_all(document)

        if not original_texts:
            print(f"\n未找到需要翻译的文本 (模式: {'区域' if self.translate_regions else '全文档'}).")
            return self

        if self.glossary_agent:
            glossary_dict_gen = self.glossary_agent.send_segments(original_texts, self.chunk_size)
            if self.glossary:
                self.glossary.update(glossary_dict_gen)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(glossary_dict_gen)

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
            glossary_dict_gen = await self.glossary_agent.send_segments_async(original_texts, self.chunk_size)
            if self.glossary:
                self.glossary.update(glossary_dict_gen)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(glossary_dict_gen)

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