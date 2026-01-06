# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from dataclasses import dataclass
import jinja2
import markdown
from docutranslate.exporter.md.base import MDExporter, MDExporterConfig
from docutranslate.ir.document import Document
from docutranslate.ir.markdown_document import MarkdownDocument
from docutranslate.utils.resource_utils import resource_path


@dataclass
class MD2HTMLExporterConfig(MDExporterConfig):
    cdn: bool = True


# 预读取本地静态文件（加速）
_LOCAL_CACHE = {}


def _get_local_content(path: str) -> str:
    """从本地读取文件内容，使用缓存加速"""
    if path not in _LOCAL_CACHE:
        _LOCAL_CACHE[path] = resource_path(path).read_text(encoding="utf-8")
    return _LOCAL_CACHE[path]


class MD2HTMLExporter(MDExporter):
    def __init__(self, config: MD2HTMLExporterConfig = None):
        config = config or MD2HTMLExporterConfig()
        super().__init__(config=config)
        self.cdn = config.cdn

    def export(self, document: MarkdownDocument) -> Document:
        html_template = resource_path("template/markdown.html").read_text(encoding="utf-8")

        cdn_base = "https://s4.zstatic.net/ajax/libs"

        # 检测 CDN 是否可用
        def can_access_cdn(url: str) -> bool:
            try:
                import httpx
                response = httpx.get(url, timeout=2.0)
                return response.status_code == 200
            except:
                return False

        # CDN 可用时直接用链接
        if self.cdn and can_access_cdn(f"{cdn_base}/KaTeX/0.16.9/katex.min.js"):
            pico = r'<link rel="stylesheet" href="https://s4.zstatic.net/ajax/libs/picocss/2.1.1/pico.min.css" />'
            katex_css = r'<link rel="stylesheet" href="https://s4.zstatic.net/ajax/libs/KaTeX/0.16.9/katex.min.css" />'
            katex_js = r'<script src="https://s4.zstatic.net/ajax/libs/KaTeX/0.16.9/katex.min.js"></script>'
            copy_tex_css = r'<link rel="stylesheet" href="https://s4.zstatic.net/ajax/libs/KaTeX/0.16.9/contrib/copy-tex.min.css" />'
            copy_tex_js = r'<script src="https://s4.zstatic.net/ajax/libs/KaTeX/0.16.9/contrib/copy-tex.min.js"></script>'
            auto_render = r'<script src="https://s4.zstatic.net/ajax/libs/KaTeX/0.16.9/contrib/auto-render.min.js"></script>'
            mermaid = r'<script src="https://s4.zstatic.net/ajax/libs/mermaid/10.6.1/mermaid.min.js"></script>'
        else:
            # CDN 不可用时，嵌入本地文件
            pico = f'<style>{_get_local_content("static/pico.css")}</style>'
            katex_css = f'<style>{_get_local_content("static/katex/katex.css")}</style>'
            katex_js = f'<script>{_get_local_content("static/katex/katex.js")}</script>'
            copy_tex_css = f'<style>{_get_local_content("static/katex/copy-tex.min.css")}</style>'
            copy_tex_js = f'<script>{_get_local_content("static/katex/copy-tex.min.js")}</script>'
            auto_render = f'<script>{_get_local_content("static/autoRender.js")}</script>'
            mermaid = f'<script>{_get_local_content("static/mermaid.js")}</script>'

        render_math_in_element = r"""
        <script>
            document.addEventListener("DOMContentLoaded", function () {
                renderMathInElement(document.body, {
                    delimiters: [
                        {left: '\\[', right: '\\]', display: true},
                        {left: '\\(', right: '\\)', display: false}
                    ],
                    throwOnError: false,
                    errorColor: '#F5CF27',
                    macros: { "\\f": "#1f(#2)" },
                    trust: true,
                    strict: false
                })
            });
        </script>"""

        extensions = [
            'markdown.extensions.tables',
            'pymdownx.arithmatex',
            'pymdownx.superfences'
        ]

        extension_configs = {
            'pymdownx.arithmatex': {
                'generic': True,
                'block_tag': 'div',
                'inline_tag': 'span',
                'block_syntax': ['dollar', 'square'],
                'inline_syntax': ['dollar', 'round'],
                'tex_inline_wrap': ['\\(', '\\)'],
                'tex_block_wrap': ['\\[', '\\]'],
                'smart_dollar': True
            },
            'pymdownx.superfences': {
                'custom_fences': [
                    {
                        'name': 'mermaid',
                        'class': 'mermaid',
                        'format': lambda source, language, css_class, options, md,
                                         **kwargs: f'<pre class="{css_class}">{source}</pre>'
                    }
                ]
            }
        }

        content = document.content.decode()

        html_content = markdown.markdown(
            content,
            extensions=extensions,
            extension_configs=extension_configs
        )

        render = jinja2.Template(html_template).render(
            title=document.stem,
            pico=pico,
            katexCss=katex_css,
            katexJs=katex_js,
            copyTexCss=copy_tex_css,
            copyTexJs=copy_tex_js,
            autoRender=auto_render,
            markdown=html_content,
            renderMathInElement=render_math_in_element,
            mermaid=mermaid,
        )
        return Document.from_bytes(content=render.encode("utf-8"), suffix=".html", stem=document.stem)

if __name__ == '__main__':
    from pathlib import Path
    d = Document.from_path(r"C:\Users\jxgm\Desktop\full_translated.md")
    exporter = MD2HTMLExporter()
    d1 = exporter.export(d)
    path = Path(r"C:\Users\jxgm\Desktop\a.html")
    path.write_bytes(d1.content)
