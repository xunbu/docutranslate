# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

from docutranslate.exporter.epub.base import EpubExporter
from docutranslate.ir.document import Document


class Epub2EpubExporter(EpubExporter):
    def export(self, document: Document) -> Document:
        return document.copy()
