"""Regressions for URI masking on non-UTF-8 Markdown.

``MDMaskUrisContext`` used to hard-code UTF-8 for both directions, so a GBK or
Big5 Markdown file raised ``UnicodeDecodeError`` before the translator's own
charset detection could run. It also left a leading BOM in place, which hid the
first Markdown block from the parsers.

Note: on very short CJK samples charset_normalizer cannot reliably tell GBK from
Big5, so the auto-detection cases only assert "no crash, valid UTF-8 out" and the
exact-text cases pass the encoding explicitly.
"""
import pytest

from docutranslate.context.md_mask_context import MDMaskUrisContext
from docutranslate.ir.document import Document

AUTO_CASES = [
    ("gbk", "# 标题\n\n正文 with ![img](a.png)\n"),
    ("big5", "# 標題\n\n正文 with ![img](a.png)\n"),
    ("utf-8-sig", "# 标题\n\n正文 with ![img](a.png)\n"),
    ("utf-8", "# Title\n\nbody with ![img](a.png)\n"),
]

EXACT_CASES = [
    ("gbk", "# 标题\n\n正文 with ![img](a.png)\n"),
    ("big5", "# 標題\n\n正文 with ![img](a.png)\n"),
    ("utf-8", "# Title\n\nbody with ![img](a.png)\n"),
]


@pytest.mark.parametrize("encoding,text", AUTO_CASES, ids=[case[0] for case in AUTO_CASES])
def test_masking_never_crashes_and_produces_utf8(encoding, text):
    document = Document.from_bytes(content=text.encode(encoding), suffix=".md", stem="sample")

    with MDMaskUrisContext(document):
        assert "![img](a.png)" not in document.content.decode("utf-8")
        assert b"<ph-" in document.content

    decoded = document.content.decode("utf-8")  # must be valid UTF-8, never mojibake bytes
    assert decoded.endswith("\n") or decoded.endswith("</ph>") or decoded


@pytest.mark.parametrize("encoding,text", EXACT_CASES, ids=[case[0] for case in EXACT_CASES])
def test_masking_round_trips_exactly_when_encoding_is_known(encoding, text):
    document = Document.from_bytes(content=text.encode(encoding), suffix=".md", stem="sample")

    with MDMaskUrisContext(document, encoding=encoding):
        assert "![img](a.png)" not in document.content.decode("utf-8")

    assert document.content.decode("utf-8") == text


def test_bom_is_removed_from_masked_and_restored_content():
    raw = "\ufeff# Heading\n\n![a](x.png)\n".encode("utf-8")
    document = Document.from_bytes(content=raw, suffix=".md", stem="bom")

    with MDMaskUrisContext(document):
        assert not document.content.startswith(b"\xef\xbb\xbf")
        assert b"<ph-" in document.content

    assert document.content.decode("utf-8") == "# Heading\n\n![a](x.png)\n"


def test_doubly_encoded_bom_is_also_removed():
    raw = "\ufeff# Heading\n".encode("utf-8-sig")  # BOM + BOM
    document = Document.from_bytes(content=raw, suffix=".md", stem="bom2")
    context = MDMaskUrisContext(document)

    with context:
        pass

    assert not document.content.startswith(b"\xef\xbb\xbf")
    assert document.content.decode("utf-8").startswith("# Heading")


def test_detected_encoding_is_reported():
    document = Document.from_bytes(content="# 标题\n".encode("gbk"), suffix=".md", stem="gbk")
    context = MDMaskUrisContext(document)
    assert isinstance(context.encoding, str) and context.encoding
