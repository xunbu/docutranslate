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
