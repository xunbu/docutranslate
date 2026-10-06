"""Exporter fidelity regressions.

* A UTF-8 BOM must not hide the first Markdown block (``# 标题`` lost its ``<h1>``).
* ``md2mdzip`` must not rewrite LF as CRLF on Windows.
* ``xlsx2csv`` must close the workbook and write a BOM so Excel shows non-ASCII.
* The CSV converter must honour an explicitly declared encoding.
"""
import io
import zipfile

import openpyxl
import pytest

from docutranslate.converter.x2xlsx.converter_csv2xlsx import (
    ConverterCsv2Xlsx,
    ConverterCsv2XlsxConfig,
)
from docutranslate.exporter.md.md2html_exporter import MD2HTMLExporter
from docutranslate.exporter.md.md2mdzip_exporter import MD2MDZipExporter
from docutranslate.exporter.xlsx.xlsx2csv_exporter import Xlsx2CsvExporter
from docutranslate.ir.document import Document


def test_bom_does_not_hide_first_heading():
    source = "\ufeff# Heading One\n\n## Sub Two\n".encode("utf-8")
    html = MD2HTMLExporter().export(
        Document.from_bytes(content=source, suffix=".md", stem="bom")
    ).content.decode("utf-8")

    assert "<h1>Heading One</h1>" in html
    assert "\ufeff" not in html


def test_markdown_zip_export_keeps_lf_newlines():
    markdown = "# T\n\npara **bold**\n"
    archive_bytes = MD2MDZipExporter().export(
        Document.from_bytes(content=markdown.encode("utf-8"), suffix=".md", stem="t")
    ).content

    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        member = next(name for name in archive.namelist() if name.endswith(".md"))
        inner = archive.read(member)

    assert b"\r\n" not in inner
    assert markdown.encode("utf-8") in inner


def test_xlsx_to_csv_writes_utf8_bom():
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["姓名", "城市"])
    buffer = io.BytesIO()
    workbook.save(buffer)

    exported = Xlsx2CsvExporter().export(
        Document.from_bytes(content=buffer.getvalue(), suffix=".xlsx", stem="x")
    )

    assert exported.content.startswith(b"\xef\xbb\xbf")
    assert "姓名" in exported.content.decode("utf-8-sig")


def _csv_to_xlsx(content: bytes, **config_kwargs):
    converter = ConverterCsv2Xlsx(ConverterCsv2XlsxConfig(**config_kwargs))
    result = converter.convert(Document.from_bytes(content=content, suffix=".csv", stem="data"))
    return openpyxl.load_workbook(io.BytesIO(result.content)).active


def test_csv_converter_reads_utf8_by_default():
    sheet = _csv_to_xlsx("姓名,年龄\n张三,20\n".encode("utf-8"))
    assert [cell.value for cell in sheet[1]] == ["姓名", "年龄"]
    assert [cell.value for cell in sheet[2]] == ["张三", "20"]


def test_csv_converter_honours_declared_encoding():
    sheet = _csv_to_xlsx("姓名,年龄\n张三,20\n".encode("gbk"), encoding="gbk")
    assert [cell.value for cell in sheet[1]] == ["姓名", "年龄"]
    assert [cell.value for cell in sheet[2]] == ["张三", "20"]


def test_csv_converter_rejects_unknown_declared_encoding():
    sheet = _csv_to_xlsx("姓名,年龄\n".encode("utf-8"), encoding="not-a-codec")
    assert [cell.value for cell in sheet[1]] == ["姓名", "年龄"]
