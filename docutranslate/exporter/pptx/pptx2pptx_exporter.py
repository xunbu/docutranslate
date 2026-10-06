# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

from docutranslate.exporter.pptx.base import PPTXExporter
from docutranslate.ir.document import Document


class PPTX2PPTXExporter(PPTXExporter):
    def export(self, document: Document) -> Document:
        return document.copy()
