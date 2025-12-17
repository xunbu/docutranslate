# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
import os
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from io import BytesIO
from typing import Self, Literal, List, Dict, Any

from bs4 import BeautifulSoup, Tag, NavigableString

from docutranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator


@dataclass
class EpubTranslatorConfig(AiTranslatorConfig):
    insert_mode: Literal["replace", "append", "prepend"] = "replace"
    # 建议使用 \n，代码会将其转换为 <br /> 或 <span> 换行，更灵活
    separator: str = "\n"


class EpubTranslator(AiTranslator):
    """
    一个用于翻译 EPUB 文件中内容的翻译器。
    【高级版】此版本直接翻译HTML内容，以保留内联格式，并支持表格翻译。
    【结构化修改版 v3】
    1. 修复了 BeautifulSoup 自动添加 <html><body> 导致嵌套错误的问题。
    2. 对 li, div, td, th 采用内部追加模式，保护文档结构。
    3. 复制标签时自动移除 ID 属性，防止锚点冲突。
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
                force_json=config.force_json,
                rpm=config.rpm,
                tpm=config.tpm
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

        # 读取 Zip 内容
        with zipfile.ZipFile(BytesIO(document.content), 'r') as zf:
            for filename in zf.namelist():
                all_files[filename] = zf.read(filename)

        # 解析 container.xml 寻找 OPF
        container_xml = all_files.get('META-INF/container.xml')
        if not container_xml:
            raise ValueError("无效的 EPUB：找不到 META-INF/container.xml")
        root = ET.fromstring(container_xml)
        ns = {'cn': 'urn:oasis:names:tc:opendocument:xmlns:container'}
        opf_path = root.find('cn:rootfiles/cn:rootfile', ns).get('full-path')
        opf_dir = os.path.dirname(opf_path)

        # 解析 OPF 获取文件清单
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

        # 定义需要翻译的标签
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
                    soups[file_path] = BeautifulSoup(content_bytes, "lxml")

                soup = soups[file_path]

                all_potential_tags = soup.find_all(TAGS_TO_TRANSLATE)
                all_potential_tags_set = set(all_potential_tags)

                tags_to_process = []
                for tag in all_potential_tags:
                    # 仅处理叶子节点块（不包含其他待翻译块的块）
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

            # --- 核心修复：解析并剥离 HTML/BODY 外壳 ---
            # BeautifulSoup(html, 'lxml') 会自动补全 <html><body>，必须剥离
            new_content_soup = BeautifulSoup(translated_html, 'lxml')

            content_nodes = []
            if new_content_soup.body:
                content_nodes = list(new_content_soup.body.contents)
            elif new_content_soup.html:
                content_nodes = list(new_content_soup.html.contents)
            else:
                content_nodes = list(new_content_soup.contents)

            # 策略 A: 替换模式（Replace）
            if self.insert_mode == "replace":
                original_tag.clear()
                for node in content_nodes:
                    original_tag.append(node.extract())
                continue

            # 策略 B: 容器型元素 (td, th, li, div) -> 在内部追加
            # 这样可以保护 ul/ol 结构不被打断，div 布局不被破坏
            is_container_node = original_tag.name in ['td', 'th', 'li', 'div']

            if is_container_node:
                original_tag.clear()

                # 解析原文 (注意防范原文被解析出多余标签)
                orig_soup = BeautifulSoup(original_html, 'lxml')
                original_nodes = list(orig_soup.body.contents) if orig_soup.body else list(orig_soup.contents)

                # 译文节点使用上面剥离好的 content_nodes
                translated_nodes = content_nodes

                # 构建分隔符 (容器内部使用 span/br，不使用 p/div 以防破坏行内流)
                separator_nodes = []
                if self.separator:
                    lines = self.separator.split('\n')
                    for j, line in enumerate(lines):
                        if line:
                            sep_span = soup.new_tag('span', attrs={'class': 'translate-separator'})
                            sep_span.string = line
                            separator_nodes.append(sep_span)
                        if j < len(lines) - 1:
                            separator_nodes.append(soup.new_tag('br'))
                    # 额外加一个换行区分原文和译文
                    separator_nodes.append(soup.new_tag('br'))

                # 组装内容
                if self.insert_mode == "append":
                    nodes_order = [original_nodes, separator_nodes, translated_nodes]
                else:  # prepend
                    nodes_order = [translated_nodes, separator_nodes, original_nodes]

                for node_list in nodes_order:
                    for node in node_list:
                        if node:
                            original_tag.append(node.extract() if isinstance(node, Tag) else node)

            # 策略 C: 独立文本块 (p, h1-h6) -> 创建兄弟标签
            else:
                # 复制属性，但必须删除 ID 以防冲突
                new_attrs = dict(original_tag.attrs)
                if 'id' in new_attrs:
                    del new_attrs['id']

                translated_tag = soup.new_tag(original_tag.name, attrs=new_attrs)

                # 填充译文
                for node in content_nodes:
                    # 额外检查：防止 <p> 里面套 <p>
                    # 如果译文被识别为 <p>翻译</p>，而外层容器也是 <p>，则只取内部文本
                    if isinstance(node, Tag) and node.name == original_tag.name and node.name == 'p':
                        for inner_child in list(node.contents):
                            translated_tag.append(inner_child.extract())
                    else:
                        translated_tag.append(node.extract())

                # 创建块级分隔符
                separator_tag = None
                if self.separator:
                    separator_tag = soup.new_tag('div', attrs={'class': 'translate-separator'})
                    lines = self.separator.split('\n')
                    for j, line in enumerate(lines):
                        if line:
                            separator_tag.append(NavigableString(line))
                        if j < len(lines) - 1:
                            separator_tag.append(soup.new_tag('br'))

                if self.insert_mode == "append":
                    # 插入顺序：原文 -> 分隔符 -> 译文
                    current_node = original_tag
                    if separator_tag:
                        current_node.insert_after(separator_tag)
                        current_node = separator_tag
                    current_node.insert_after(translated_tag)
                elif self.insert_mode == "prepend":
                    # 插入顺序：译文 -> 分隔符 -> 原文
                    original_tag.insert_before(translated_tag)
                    if separator_tag:
                        translated_tag.insert_after(separator_tag)

        # 重新打包 EPUB
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