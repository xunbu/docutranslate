# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from docutranslate.exporter.base import Exporter
from docutranslate.ir.document import Document

#TODO:看情况是否需要为TXT单独写一个document类型
class AssExporter(Exporter[Document]):

    def export(self,document:Document)->Document:
        ...