# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from docutranslate.exporter.ass.base import AssExporter
from docutranslate.ir.document import Document


class Ass2AssExporter(AssExporter):
    def export(self, document: Document) -> Document:
        return document.copy()
