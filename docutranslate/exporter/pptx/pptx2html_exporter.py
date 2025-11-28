# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import html
from dataclasses import dataclass
from io import BytesIO

from pptx import Presentation

from docutranslate.exporter.base import ExporterConfig
from docutranslate.exporter.pptx.base import PPTXExporter
from docutranslate.ir.document import Document


@dataclass
class PPTX2HTMLExporterConfig(ExporterConfig):
    cdn: bool = True
    include_hidden_slides: bool = False


class PPTX2HTMLExporter(PPTXExporter):
    def __init__(self, config: PPTX2HTMLExporterConfig = None):
        config = config or PPTX2HTMLExporterConfig()
        super().__init__(config=config)
        self.cdn = config.cdn
        self.include_hidden_slides = getattr(config, 'include_hidden_slides', False)

    def export(self, document: Document) -> Document:
        # 使用 python-pptx 加载二进制内容
        prs = Presentation(BytesIO(document.content))

        html_parts = []

        # 添加基础的 HTML 头部
        html_parts.append("<!DOCTYPE html><html><head><meta charset='utf-8'>")
        html_parts.append("<style>")
        html_parts.append(".slide { border: 1px solid #ccc; margin: 20px auto; padding: 20px; max-width: 800px; }")
        html_parts.append(".slide-title { font-size: 1.5em; font-weight: bold; margin-bottom: 10px; }")
        html_parts.append("</style>")
        html_parts.append("</head><body>")

        for i, slide in enumerate(prs.slides):
            # 处理隐藏幻灯片的逻辑
            # 注意: python-pptx 的 slide 对象可能没有 hidden 属性，取决于版本，
            # 若需要严格过滤需检查 slide.element.get('show') 等，这里做基础遍历。

            slide_html = []
            slide_html.append(f'<div class="slide" id="slide-{i + 1}">')

            # 1. 尝试提取并处理标题
            title = slide.shapes.title
            if title and title.has_text_frame and title.text.strip():
                escaped_title = html.escape(title.text)
                slide_html.append(f'<div class="slide-title">{escaped_title}</div>')

            # 2. 遍历其他形状提取文本
            for shape in slide.shapes:
                # 跳过已经处理过的标题
                if shape == title:
                    continue

                if hasattr(shape, "has_text_frame") and shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        text = paragraph.text.strip()
                        if text:
                            # 简单处理：将每个段落作为 p 标签
                            # 进阶处理可以根据 paragraph.level 处理列表缩进
                            escaped_text = html.escape(text)
                            slide_html.append(f'<p>{escaped_text}</p>')

                # 如果需要处理表格 (Table)
                if shape.has_table:
                    slide_html.append('<table border="1" style="border-collapse: collapse; width: 100%;">')
                    for row in shape.table.rows:
                        slide_html.append('<tr>')
                        for cell in row.cells:
                            cell_text = html.escape(cell.text_frame.text) if cell.text_frame else ""
                            slide_html.append(f'<td style="padding: 5px;">{cell_text}</td>')
                        slide_html.append('</tr>')
                    slide_html.append('</table>')

            slide_html.append('</div>')
            html_parts.append("".join(slide_html))

        html_parts.append("</body></html>")

        full_html = "\n".join(html_parts)

        return Document.from_bytes(
            content=full_html.encode("utf-8"),
            suffix=".html",
            stem=document.stem
        )