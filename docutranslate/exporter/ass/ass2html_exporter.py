# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from dataclasses import dataclass

import jinja2

from docutranslate.exporter.ass.base import AssExporter
from docutranslate.exporter.base import ExporterConfig

from docutranslate.ir.document import Document
from docutranslate.utils.resource_utils import resource_path


@dataclass
class Ass2HTMLExporterConfig(ExporterConfig):
    cdn: bool = True


class Ass2HTMLExporter(AssExporter):
    def __init__(self, config: Ass2HTMLExporterConfig = None):
        config = config or Ass2HTMLExporterConfig()
        super().__init__(config=config)
        self.cdn = config.cdn

    def export(self, document: Document) -> Document:
        cdn = self.cdn

        html_template = resource_path("template/ass.html").read_text(encoding="utf-8")

        render = jinja2.Template(html_template).render(
            ass_data=document.content.decode("utf-8")
        )
        return Document.from_bytes(content=render.encode("utf-8"), suffix=".html", stem=document.stem)


