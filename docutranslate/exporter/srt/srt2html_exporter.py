# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from dataclasses import dataclass

import html
import jinja2

import srt
from docutranslate.exporter.base import ExporterConfig
from docutranslate.exporter.srt.base import SrtExporter
from docutranslate.ir.document import Document
from docutranslate.utils.resource_utils import resource_path


@dataclass
class Srt2HTMLExporterConfig(ExporterConfig):
    cdn: bool = True


class Srt2HTMLExporter(SrtExporter):
    def __init__(self, config: Srt2HTMLExporterConfig = None):
        config = config or Srt2HTMLExporterConfig()
        super().__init__(config=config)
        self.cdn = config.cdn

    def export(self, document: Document) -> Document:
        cdn = self.cdn
        srt_string = document.content.decode("utf-8-sig")
        subs = list(srt.parse(srt_string))
        for sub in subs:
            # 先转义再插入 <br>：字幕文本里的 `<`/`&` 以前会被当成 HTML 解析。
            sub.content = html.escape(sub.content).replace('\n', '<br>')

        html_template = resource_path("template/srt.html").read_text(encoding="utf-8")

        # language=html
        pico = f'<style>{resource_path("static/pico.css").read_text(encoding="utf-8")}</style>' if not cdn else r'<link rel="stylesheet" href="https://s4.zstatic.net/ajax/libs/picocss/2.1.1/pico.min.css" integrity="sha512-+4kjFgVD0n6H3xt19Ox84B56MoS7srFn60tgdWFuO4hemtjhySKyW4LnftYZn46k3THUEiTTsbVjrHai+0MOFw==" crossorigin="anonymous" referrerpolicy="no-referrer" />'

        render = jinja2.Template(html_template).render(
            title=document.stem,
            pico=pico,
            subtitles=subs
        )
        return Document.from_bytes(content=render.encode("utf-8"), suffix=".html", stem=document.stem)
