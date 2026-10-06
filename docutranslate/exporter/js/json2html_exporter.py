# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import json
from dataclasses import dataclass

import jinja2

from docutranslate.exporter.base import ExporterConfig
from docutranslate.exporter.js.base import JsonExporter
from docutranslate.ir.document import Document
from docutranslate.utils.resource_utils import resource_path


@dataclass
class Json2HTMLExporterConfig(ExporterConfig):
    cdn: bool = True


class Json2HTMLExporter(JsonExporter):
    def __init__(self, config: Json2HTMLExporterConfig = None):
        config = config or Json2HTMLExporterConfig()
        super().__init__(config=config)
        self.cdn = config.cdn

    def export(self, document: Document) -> Document:
        cdn = self.cdn
        html_template = resource_path("template/json.html").read_text(encoding="utf-8")

        # language=html
        pico = f'<style>{resource_path("static/pico.css").read_text(encoding="utf-8")}</style>' if not cdn else r'<link rel="stylesheet" href="https://s4.zstatic.net/ajax/libs/picocss/2.1.1/pico.min.css" integrity="sha512-+4kjFgVD0n6H3xt19Ox84B56MoS7srFn60tgdWFuO4hemtjhySKyW4LnftYZn46k3THUEiTTsbVjrHai+0MOFw==" crossorigin="anonymous" referrerpolicy="no-referrer" />'
        # JSON 会被内联进 <script>：必须转义 <、>、& 以及 U+2028/2029，
        # 否则文档里的 </script> 会提前结束脚本。
        json_data = (
            document.content.decode("utf-8-sig")
            .replace("&", "\\u0026")
            .replace("<", "\\u003c")
            .replace(">", "\\u003e")
            .replace("\u2028", "\\u2028")
            .replace("\u2029", "\\u2029")
        )
        render = jinja2.Template(html_template).render(
            title=document.stem,
            pico=pico,
            jsonData=json_data,
        )
        return Document.from_bytes(content=render.encode("utf-8"), suffix=".html", stem=document.stem)
