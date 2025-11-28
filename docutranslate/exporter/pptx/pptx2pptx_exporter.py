# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

from docutranslate.exporter.docx.base import DocxExporter
from docutranslate.ir.document import Document


class PPTX2PPTXExporter(DocxExporter):
    def export(self, document: Document) -> Document:
        return document.copy()
