"""Fidelity regressions for Markdown helpers.

Covers:
* ``format_markdown_latex`` must not rewrite fenced code blocks or inline code
  (shell ``$$`` is a PID, not a formula) while still padding real display math.
* ``process_table_formulas`` must convert ``$$...$$`` before single ``$...$``.
* ``uris2placeholder`` must mask whole URIs that contain parentheses and nested
  images, leaving no fragment for the model to translate.
* ``embed_inline_image_from_zip`` must honour an explicitly requested encoding.
"""
import io
import zipfile

from docutranslate.utils.markdown_utils import (
    MaskDict,
    embed_inline_image_from_zip,
    format_markdown_latex,
    placeholder2uris,
    process_table_formulas,
    uris2placeholder,
)

PEP8_FENCE = "```python\ndef a():\n    pass\n\n\ndef b():\n    pass\n```"


class TestFormatMarkdownLatex:
    def test_inline_code_with_double_dollar_is_untouched(self):
        source = "Run `echo $$` to get the pid.\n"
        assert "`echo $$`" in format_markdown_latex(source)

    def test_fenced_code_block_is_untouched(self):
        source = "before\n\n```sh\necho $$\n```\n\nafter\n"
        result = format_markdown_latex(source)
        assert "```sh\necho $$\n```" in result

    def test_blank_lines_inside_fence_are_preserved(self):
        result = format_markdown_latex(PEP8_FENCE)
        assert result == PEP8_FENCE + "\n"
        assert "\n\n\n" in result

    def test_display_math_in_prose_is_padded(self):
        result = format_markdown_latex("text\n$$\nx=1\n$$\ntail\n")
        assert "\n\n$$\nx=1\n$$\n\n" in result

    def test_prose_blank_line_runs_are_collapsed(self):
        assert format_markdown_latex("a\n\n\n\nb") == "a\n\nb\n"


class TestTableFormulas:
    def test_display_math_is_not_destroyed(self):
        table = "<table><tr><td>$$E=mc^2$$</td></tr></table>"
        assert process_table_formulas_for(table) == "<table><tr><td>\\[E=mc^2\\]</td></tr></table>"

    def test_mixed_inline_and_display_math(self):
        table = "<table><tr><td>$x=1$ and $$y=2$$</td></tr></table>"
        assert process_table_formulas_for(table) == "<table><tr><td>\\(x=1\\) and \\[y=2\\]</td></tr></table>"

    def test_multiline_display_math(self):
        table = "<table><tr><td>$$\nx=1\n$$</td></tr></table>"
        assert "\\[" in process_table_formulas_for(table)


def process_table_formulas_for(table: str) -> str:
    import re

    return re.sub(r"<table[\s\S]*?</table>", process_table_formulas, table)


class TestUriMasking:
    def test_uri_with_parentheses_is_masked_whole(self):
        source = "![a](http://x.com/(y).png)"
        mask = MaskDict()
        masked = uris2placeholder(source, mask)
        assert masked.strip().startswith("<ph-")
        assert masked.strip().endswith(">")
        assert placeholder2uris(masked, mask) == source

    def test_nested_image_is_masked_whole(self):
        source = "![outer ![inner](i.png)](o.png)"
        mask = MaskDict()
        masked = uris2placeholder(source, mask)
        assert "](" not in masked
        assert placeholder2uris(masked, mask) == source

    def test_plain_uri_and_title_still_work(self):
        for source in ("![ok](http://x.com/a.png)", '![t](url "title")'):
            mask = MaskDict()
            assert placeholder2uris(uris2placeholder(source, mask), mask) == source


class TestZipMarkdownEncoding:
    def _zip_with(self, name: str, payload: bytes) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(name, payload)
        return buffer.getvalue()

    def test_explicit_encoding_wins_over_detection(self):
        gbk = "# 标题\n\n正文\n".encode("gbk")
        content = embed_inline_image_from_zip(self._zip_with("full.md", gbk), encoding="gbk")
        assert content == "# 标题\n\n正文\n"

    def test_utf8_without_encoding_still_works(self):
        utf8 = "# 标题\n\n正文\n".encode("utf-8")
        content = embed_inline_image_from_zip(self._zip_with("full.md", utf8))
        assert content == "# 标题\n\n正文\n"
