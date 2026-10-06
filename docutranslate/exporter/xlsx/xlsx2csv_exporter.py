# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from io import BytesIO, StringIO

import openpyxl
import csv
from docutranslate.exporter.xlsx.base import XlsxExporter
from docutranslate.ir.document import Document


class Xlsx2CsvExporter(XlsxExporter):

    def export(self, document: Document) -> Document:
        workbook = openpyxl.load_workbook(BytesIO(document.content))
        try:
            sheet = workbook.active

            # 2. 使用 StringIO 作为文本缓冲区
            text_buffer = StringIO()

            # 3. 直接将缓冲区传递给 csv.writer
            writer = csv.writer(text_buffer)

            # 遍历工作表中的每一行
            for row in sheet.rows:
                writer.writerow([cell.value for cell in row])

            # 4. 编码为 bytes；带 BOM 以便 Excel 正确识别非 ASCII 单元格
            output_bytes = text_buffer.getvalue().encode('utf-8-sig')
        finally:
            workbook.close()

        # 5. 返回一个后缀为 .csv 的 Document
        return Document.from_bytes(content=output_bytes, suffix=".csv", stem=document.stem)




