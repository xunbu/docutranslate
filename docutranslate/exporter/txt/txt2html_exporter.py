# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from dataclasses import dataclass

import jinja2

from docutranslate.exporter.base import ExporterConfig
from docutranslate.exporter.txt.base import TXTExporter
from docutranslate.ir.document import Document
from docutranslate.utils.resource_utils import resource_path


@dataclass
class TXT2HTMLExporterConfig(ExporterConfig):
    cdn: bool = True


class TXT2HTMLExporter(TXTExporter):
    def __init__(self, config: TXT2HTMLExporterConfig = None):
        config = config or TXT2HTMLExporterConfig()
        super().__init__(config=config)
        self.cdn = config.cdn

    def export(self, document: Document) -> Document:
        cdn = self.cdn
        html_template = resource_path("template/txt.html").read_text(encoding="utf-8")

        # language=html
        body=document.content.decode()
        render = jinja2.Template(html_template).render(
            title=document.stem,
            body=body,
        )
        return Document.from_bytes(content=render.encode("utf-8"), suffix=".html", stem=document.stem)
