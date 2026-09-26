import asyncio
import json
import zipfile
from io import BytesIO

import httpx
import pytest
from bs4 import BeautifulSoup

from docutranslate.agents.segments_agent import get_original_segments
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.epub_translator import (
    EpubTranslator,
    EpubTranslatorConfig,
)


@pytest.mark.parametrize("use_async", [False, True])
def test_epub_translation_with_mixed_response_id_types(monkeypatch, use_async):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip")
        archive.writestr("META-INF/container.xml", """
            <container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
              <rootfiles><rootfile full-path="OEBPS/content.opf"/></rootfiles>
            </container>
        """)
        archive.writestr("OEBPS/content.opf", """
            <package xmlns="http://www.idpf.org/2007/opf">
              <manifest><item id="chapter" href="chapter.xhtml"
                media-type="application/xhtml+xml"/></manifest>
              <spine><itemref idref="chapter"/></spine>
            </package>
        """)
        archive.writestr("OEBPS/chapter.xhtml", """
            <html><body><p id="first">Hello <em>world</em></p>
            <p id="second">Goodbye</p></body></html>
        """)
        archive.writestr("OEBPS/style.css", "p { color: black; }")
    document = Document(suffix=".epub", content=buffer.getvalue(), stem="book")
    requests = []

    async def handler(request):
        payload = json.loads(request.content)
        requests.append(payload)
        originals = json.loads(get_original_segments(payload["messages"][-1]["content"]))
        assert originals == {"0": "Hello <em>world</em>", "1": "Goodbye"}
        return httpx.Response(200, json={
            "choices": [{"message": {"content": json.dumps([
                {"id": "1", "t": "再见"},
                {"id": 0, "t": "你好<em>世界</em>"},
            ])}, "finish_reason": "stop"}],
        })

    async_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: async_client(
        **{**kwargs, "transport": httpx.MockTransport(handler)},
    ))
    translator = EpubTranslator(EpubTranslatorConfig(
        base_url="https://example.invalid/v1", api_key="test", model_id="test",
        streaming=False, retry=0,
    ))

    if use_async:
        asyncio.run(translator.translate_async(document))
    else:
        translator.translate(document)

    assert len(requests) == 1
    with zipfile.ZipFile(BytesIO(document.content)) as archive:
        assert archive.testzip() is None
        assert archive.infolist()[0].filename == "mimetype"
        assert archive.getinfo("mimetype").compress_type == zipfile.ZIP_STORED
        assert archive.read("OEBPS/style.css") == b"p { color: black; }"
        soup = BeautifulSoup(archive.read("OEBPS/chapter.xhtml").decode("utf-8"), "lxml")
        assert soup.find(id="first").decode_contents() == "你好<em>世界</em>"
        assert soup.find(id="second").get_text() == "再见"


def _build_epub_with_chapter(chapter_html: str) -> Document:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip")
        archive.writestr("META-INF/container.xml", """
            <container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
              <rootfiles><rootfile full-path="OEBPS/content.opf"/></rootfiles>
            </container>
        """)
        archive.writestr("OEBPS/content.opf", """
            <package xmlns="http://www.idpf.org/2007/opf">
              <manifest><item id="chapter" href="chapter.xhtml"
                media-type="application/xhtml+xml"/></manifest>
              <spine><itemref idref="chapter"/></spine>
            </package>
        """)
        archive.writestr("OEBPS/chapter.xhtml",
                         f"<html><body>{chapter_html}</body></html>")
    return Document(suffix=".epub", content=buffer.getvalue(), stem="book")


def _structure_after_identity_translation(chapter_html: str) -> BeautifulSoup:
    """skip_translate=True：译文即原文，只考察回填后的 DOM 结构。"""
    document = _build_epub_with_chapter(chapter_html)
    EpubTranslator(EpubTranslatorConfig(skip_translate=True)).translate(document)
    with zipfile.ZipFile(BytesIO(document.content)) as archive:
        raw = archive.read("OEBPS/chapter.xhtml").decode("utf-8")
    # html.parser 不会自动闭合嵌套 <p>，便于检测非法结构
    return BeautifulSoup(raw, "html.parser")


def _assert_no_nested_paragraphs(soup: BeautifulSoup):
    nested = [p for p in soup.find_all("p") if p.find("p") is not None]
    assert nested == [], f"出现嵌套 <p>: {nested}"


def test_container_bare_text_is_wrapped_without_swallowing_blocks():
    """容器内裸文本 + 已有段落的混排必须各自成段，不能被吞进同一个 <p>。"""
    soup = _structure_after_identity_translation(
        '<div class="chapter"><span id="pagestart"></span>'
        "Bare text before.<p>Real paragraph one.</p>Trailing bare text.</div>"
    )
    _assert_no_nested_paragraphs(soup)
    div = soup.find("div", class_="chapter")
    paragraphs = div.find_all("p", recursive=False)
    assert [p.get_text(strip=True) for p in paragraphs] == [
        "Bare text before.", "Real paragraph one.", "Trailing bare text.",
    ]
    # 结尾的结构标记必须保留在容器开头
    assert div.contents[0].name == "span" and div.contents[0].get("id") == "pagestart"


def test_inline_image_keeps_sentence_together():
    """行内 <img> 不应被拆成块级、也不应把句子劈成两段。"""
    soup = _structure_after_identity_translation(
        '<div class="para">Text before <img src="i.png" alt=""/> text after.</div>'
    )
    _assert_no_nested_paragraphs(soup)
    paragraphs = soup.find("div", class_="para").find_all("p", recursive=False)
    assert len(paragraphs) == 1, soup
    assert paragraphs[0].find("img") is not None, "行内图片被移出段落"
    assert paragraphs[0].get_text(" ", strip=True) == "Text before text after."


def test_line_breaks_stay_inside_one_paragraph():
    """<br/> 换行不应被转换成段落（会改变行距、影响诗歌/地址排版）。"""
    soup = _structure_after_identity_translation(
        '<div class="verse">line one<br/>line two<br/>line three</div>'
    )
    _assert_no_nested_paragraphs(soup)
    paragraphs = soup.find("div", class_="verse").find_all("p", recursive=False)
    assert len(paragraphs) == 1, soup
    assert len(paragraphs[0].find_all("br")) == 2, "换行被丢弃或转成了段落"
    assert paragraphs[0].get_text(" ", strip=True) == "line one line two line three"


def test_existing_blocks_and_breaks_are_preserved():
    """已有 <p> 之间不应被插入空段落，<br/> 也不应被删除。"""
    soup = _structure_after_identity_translation(
        '<div class="outer"><p>alpha</p><br/><p>beta</p></div>'
    )
    _assert_no_nested_paragraphs(soup)
    div = soup.find("div", class_="outer")
    assert [p.get_text(strip=True) for p in div.find_all("p", recursive=False)] == [
        "alpha", "beta",
    ]
    assert len(div.find_all("br")) == 1, "分隔用的 <br/> 被删除"


def test_bare_text_in_container_is_actually_translated(monkeypatch):
    """回归保护：1.7.8 的包裹逻辑核心目标是让容器内裸文本进入翻译分片。"""
    document = _build_epub_with_chapter('<div class="c">Bare text<p>Para</p></div>')
    seen = []

    async def handler(request):
        payload = json.loads(request.content)
        originals = json.loads(get_original_segments(payload["messages"][-1]["content"]))
        seen.append(originals)
        return httpx.Response(200, json={
            "choices": [{"message": {"content": json.dumps([
                {"id": "0", "t": "裸文本"},
                {"id": "1", "t": "段落"},
            ])}, "finish_reason": "stop"}],
        })

    async_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: async_client(
        **{**kwargs, "transport": httpx.MockTransport(handler)},
    ))
    translator = EpubTranslator(EpubTranslatorConfig(
        base_url="https://example.invalid/v1", api_key="test", model_id="test",
        streaming=False, retry=0,
    ))
    translator.translate(document)

    assert seen == [{"0": "Bare text", "1": "Para"}], seen
    with zipfile.ZipFile(BytesIO(document.content)) as archive:
        raw = archive.read("OEBPS/chapter.xhtml").decode("utf-8")
    soup = BeautifulSoup(raw, "html.parser")
    _assert_no_nested_paragraphs(soup)
    assert [p.get_text(strip=True) for p in soup.find_all("p")] == ["裸文本", "段落"]

