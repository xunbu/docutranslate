# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from docutranslate.exporter.js.base import JsonExporter
from docutranslate.ir.document import Document


class Json2JsonExporter(JsonExporter):
    def export(self, document: Document) -> Document:
        return document.copy()
