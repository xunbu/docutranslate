# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import asyncio
import csv
from dataclasses import dataclass
from io import BytesIO, StringIO
from typing import Hashable

import charset_normalizer
import openpyxl

from docutranslate.converter.x2xlsx.base import X2XlsxConverter, X2XlsxConverterConfig
from docutranslate.ir.document import Document


# 配置一个基本的日志记录器（如果您的项目尚未配置）
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
@dataclass(kw_only=True)
class ConverterCsv2XlsxConfig(X2XlsxConverterConfig):

    def gethash(self) -> Hashable:
        return "1"


class ConverterCsv2Xlsx(X2XlsxConverter):
    """
    一个经过改进的、健壮的 CSV 到 XLSX 转换器。

    特性:
    - 内存高效：使用流式写入模式处理大型文件。
    - 自动编码检测：避免乱码问题。
    - 自动 CSV 格式识别：支持不同的分隔符。
    - 完善的错误处理和日志记录。
    """

    def __init__(self, config: ConverterCsv2XlsxConfig):
        super().__init__(config=config)

    def convert(self, document: Document) -> Document:
        """
        将 CSV Document 对象同步转换为 XLSX Document 对象。
        """
        self.logger.info(f"开始转换文件 {document.name} (大小: {len(document.content)} bytes)")

        try:
            # --- 1. 自动检测文件编码 ---
            # 为提高性能，只取文件头部一部分进行检测
            detection_result = charset_normalizer.detect(document.content[:4096])
            encoding = detection_result['encoding'] or 'utf-8'  # 提供一个默认值
            confidence = detection_result['confidence']
            self.logger.info(f"检测到文件编码为: {encoding} (置信度: {confidence:.2%})")

            # --- 2. 解码并创建文本流 ---
            try:
                decoded_content = document.content.decode(encoding)
            except UnicodeDecodeError:
                self.logger.warning(f"使用检测到的编码 '{encoding}' 解码失败，尝试使用 'utf-8'。")
                decoded_content = document.content.decode('utf-8', errors='replace')

            csv_text_stream = StringIO(decoded_content)

            # --- 3. 自动识别CSV方言（如分隔符） ---
            try:
                # Sniffer需要一些数据来嗅探，如果文件太小可能失败
                dialect = csv.Sniffer().sniff(csv_text_stream.read(2048))
                csv_text_stream.seek(0)  # 将流指针重置回文件开头
                self.logger.info(f"检测到CSV分隔符为: '{dialect.delimiter}'")
            except csv.Error:
                self.logger.warning("无法自动识别CSV方言，将使用默认的逗号分隔符。")
                dialect = 'excel'  # 使用默认方言
                csv_text_stream.seek(0)

            csv_reader = csv.reader(csv_text_stream, dialect)

            # --- 4. 使用内存优化的`write_only`模式创建XLSX ---
            wb = openpyxl.Workbook(write_only=True)
            ws = wb.create_sheet()

            # --- 5. 逐行读取CSV并写入XLSX ---
            row_count = 0
            for row_data in csv_reader:
                ws.append(row_data)  # append() 是 write_only 模式下的高效写入方法
                row_count += 1

            self.logger.info(f"共处理 {row_count} 行数据。")

            # --- 6. 将生成的XLSX保存到内存中的字节流 ---
            output_buffer = BytesIO()
            wb.save(output_buffer)
            output_buffer.seek(0)  # 将指针移到开头，以便getvalue()读取完整内容

            self.logger.info(f"文件 {document.name} 已成功转换为 XLSX 格式。")

            return Document.from_bytes(
                content=output_buffer.getvalue(),
                suffix=".xlsx",
                stem=document.stem
            )

        except Exception as e:
            self.logger.error(f"转换文件 {document.name} 时发生严重错误: {e}", exc_info=True)
            # 根据您的业务逻辑，这里可以抛出异常或返回一个表示失败的特定对象
            raise

    async def convert_async(self, document: Document) -> Document:
        """
        异步执行转换操作。
        由于核心转换逻辑是CPU密集型和阻塞IO，使用 to_thread 是正确的选择，
        它可以防止阻塞asyncio事件循环。
        """
        self.logger.info(f"为文件 {document.name} 的转换任务创建新线程。")
        # 我们已经优化了 `convert` 方法，所以 `to_thread` 的方式非常适合
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.convert, document)

    def support_format(self) -> list[str]:
        """
        声明此转换器支持的源文件格式。
        """
        return [".csv"]
