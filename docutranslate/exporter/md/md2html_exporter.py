# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import re  # <--- 步骤 1: 导入 re 模块
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


class MD2HTMLExporter(MDExporter):
    def __init__(self, config: MD2HTMLExporterConfig = None):
        config = config or MD2HTMLExporterConfig()
        super().__init__(config=config)
        self.cdn = config.cdn

    def export(self, document: MarkdownDocument) -> Document:
        cdn = self.cdn
        html_template = resource_path("template/markdown.html").read_text(encoding="utf-8")

        # CDN 基础 URL
        cdn_base = "https://s4.zstatic.net/ajax/libs"

        def fetch_text(url_or_path: str) -> str:
            """从 URL 或本地文件获取文本内容"""
            try:
                if url_or_path.startswith("http"):
                    import httpx
                    response = httpx.get(url_or_path, timeout=10.0)
                    response.raise_for_status()
                    return response.text
                else:
                    return resource_path(url_or_path).read_text(encoding="utf-8")
            except Exception as e:
                print(f"Warning: Failed to fetch {url_or_path}: {e}")
                return ""

        # 辅助函数：将 CSS 中的字体 URL 替换为 CDN 链接
        def replace_font_urls(css_content: str) -> str:
            """将 CSS 中的 url(fonts/xxx) 替换为 CDN URL"""
            def replace(match):
                url_path = match.group(1)
                if 'fonts/' in url_path:
                    font_filename = url_path.split('/')[-1]
                    return f'url({cdn_base}/KaTeX/0.16.9/fonts/{font_filename})'
                return match.group(0)
            return re.sub(r'url\(([^)]*fonts/[^)]*)\)', replace, css_content)

        # 辅助函数：包装为 style/script 标签
        def tag(content: str, tag_type: str) -> str:
            if tag_type == "style":
                return f"<style>\n{content}\n</style>"
            return f"<script>\n{content}\n</script>"

        # Pico CSS
        pico_url = f"{cdn_base}/picocss/2.1.1/pico.min.css"
        pico = tag(fetch_text(pico_url), "style")

        # KaTeX CSS (字体使用 CDN)
        katex_css_url = f"{cdn_base}/KaTeX/0.16.9/katex.min.css"
        katex_css_content = fetch_text(katex_css_url)
        katex_css_content = replace_font_urls(katex_css_content)
        katex_css = tag(katex_css_content, "style")

        # KaTeX JS
        katex_js_url = f"{cdn_base}/KaTeX/0.16.9/katex.min.js"
        katex_js = tag(fetch_text(katex_js_url), "script")

        # copy-tex CSS
        copy_tex_css_url = f"{cdn_base}/KaTeX/0.16.9/contrib/copy-tex.min.css"
        copy_tex_css = tag(fetch_text(copy_tex_css_url), "style")

        # copy-tex JS
        copy_tex_js_url = f"{cdn_base}/KaTeX/0.16.9/contrib/copy-tex.min.js"
        copy_tex_js = tag(fetch_text(copy_tex_js_url), "script")

        # auto-render JS
        auto_render_url = f"{cdn_base}/KaTeX/0.16.9/contrib/auto-render.min.js"
        auto_render = tag(fetch_text(auto_render_url), "script")

        # renderMathInElement 配置
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
                    macros: {
                        "\\f": "#1f(#2)"
                    },
                    trust: true,
                    strict: false
                })
            });
        </script>"""

        # mermaid JS
        mermaid_url = f"{cdn_base}/mermaid/10.6.1/mermaid.min.js"
        mermaid = tag(fetch_text(mermaid_url), "script")

        # 扩展配置
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
