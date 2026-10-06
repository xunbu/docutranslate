# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import charset_normalizer

from docutranslate.ir.markdown_document import MarkdownDocument
from docutranslate.logger import global_logger
from docutranslate.utils.markdown_utils import MaskDict, uris2placeholder, placeholder2uris

_UTF8_BOM = "\ufeff"


class MDMaskUrisContext:
    """Mask image/URI payloads before translation and restore them afterwards.

    The document content is decoded with the encoding detected by
    ``charset_normalizer`` (the same detector used by the Markdown translator)
    instead of assuming UTF-8: GBK/Big5/CP949 Markdown used to raise
    ``UnicodeDecodeError`` here, *before* the translator's own charset detection
    could run. The masked content is normalised to UTF-8 for the rest of the
    pipeline.
    """

    def __init__(self, document: MarkdownDocument, encoding: str | None = None):
        self.document = document
        self.mask_dict = MaskDict()
        self.encoding = encoding or self._detect_encoding(document.content)

    @staticmethod
    def _detect_encoding(content: bytes) -> str:
        if not isinstance(content, (bytes, bytearray)):
            return "utf-8"
        candidate = None
        result = charset_normalizer.from_bytes(content).best()
        if result is not None and result.encoding:
            candidate = result.encoding
            try:
                content.decode(candidate)
                return candidate
            except (UnicodeDecodeError, LookupError):
                pass
        try:
            content.decode("utf-8")
            return "utf-8"
        except UnicodeDecodeError:
            if candidate:
                global_logger.warning(
                    "Markdown 内容无法用检测到的编码 %s 或 utf-8 完整解码，将替换非法字节", candidate
                )
            return "utf-8"

    def _decode(self) -> str:
        try:
            text = self.document.content.decode(self.encoding)
        except UnicodeDecodeError:
            text = self.document.content.decode("utf-8", errors="replace")
        # A leading BOM (or a doubly-encoded BOM) would otherwise hide the first
        # Markdown block from the parsers, so drop every leading BOM character.
        return text.lstrip(_UTF8_BOM)

    def __enter__(self):
        masked = uris2placeholder(self._decode(), self.mask_dict)
        self.document.content = masked.encode("utf-8")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        unmasked = placeholder2uris(self.document.content.decode("utf-8"), self.mask_dict)
        self.document.content = unmasked.encode("utf-8")
