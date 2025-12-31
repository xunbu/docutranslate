# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from docutranslate.converter.base import ConverterConfig
from docutranslate.converter.converter_identity import ConverterIdentity
from docutranslate.converter.x2xlsx.base import X2XlsxConverter
from docutranslate.converter.x2xlsx.converter_csv2xlsx import ConverterCsv2Xlsx, ConverterCsv2XlsxConfig
from docutranslate.exporter.base import ExporterConfig
from docutranslate.exporter.xlsx.xlsx2csv_exporter import Xlsx2CsvExporter
from docutranslate.exporter.xlsx.xlsx2html_exporter import Xlsx2HTMLExporterConfig, Xlsx2HTMLExporter
from docutranslate.exporter.xlsx.xlsx2xlsx_exporter import Xlsx2XlsxExporter
from docutranslate.glossary.glossary import Glossary
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.xlsx_translator import XlsxTranslatorConfig, XlsxTranslator
from docutranslate.workflow.base import Workflow, WorkflowConfig
from docutranslate.workflow.interfaces import HTMLExportable, XlsxExportable, CsvExportable


@dataclass(kw_only=True)
class XlsxWorkflowConfig(WorkflowConfig):
    translator_config: XlsxTranslatorConfig
    html_exporter_config: Xlsx2HTMLExporterConfig


class XlsxWorkflow(Workflow[XlsxWorkflowConfig, Document, Document], HTMLExportable[Xlsx2HTMLExporterConfig],
                   XlsxExportable[ExporterConfig], CsvExportable[ExporterConfig]):

    def __init__(self, config: XlsxWorkflowConfig):
        super().__init__(config=config)
        if config.logger:
            for sub_config in [self.config.translator_config]:
                if sub_config:
                    sub_config.logger = config.logger
        self._converter_factory: dict[
            str, tuple[
                type[X2XlsxConverter | ConverterIdentity], ConverterConfig|None]] = {
            ".csv": (ConverterCsv2Xlsx, ConverterCsv2XlsxConfig(logger=self.logger)),
            ".xlsx": (ConverterIdentity,None)
        }

    def _get_document_xlsx(self, document: Document) -> Document:
        suffix = document.suffix
        converter_types = self._converter_factory.get(suffix.lower())
        if converter_types is None:
            raise ValueError(f"该工作流不支持{suffix}格式，请转为xlsx或csv格式")
        converter_type, converter_config = converter_types
        converter = converter_type(converter_config)

        return converter.convert(document)

    def _pre_translate(self, document_pre_translate: Document):
        document = document_pre_translate.copy()
        translate_config = self.config.translator_config
        translator = XlsxTranslator(translate_config)
        return document, translator

    def translate(self) -> Self:
        document_xlsx = self._get_document_xlsx(self.document_original)
        document, translator = self._pre_translate(document_xlsx)
        translator.translate(document)
        if translator.glossary_dict_gen:
            self.attachment.add_document("glossary", Glossary.glossary_dict2csv(translator.glossary_dict_gen))
        self.document_translated = document
        return self

    async def translate_async(self) -> Self:
        document_xlsx = await asyncio.to_thread(self._get_document_xlsx, self.document_original)
        document, translator = self._pre_translate(document_xlsx)
        await translator.translate_async(document)
        if translator.glossary_dict_gen:
            self.attachment.add_document("glossary", Glossary.glossary_dict2csv(translator.glossary_dict_gen))
        self.document_translated = document
        return self

    def export_to_html(self, config: Xlsx2HTMLExporterConfig = None) -> str:
        config = config or self.config.html_exporter_config
        docu = self._export(Xlsx2HTMLExporter(config))
        return docu.content.decode()

    def export_to_xlsx(self, _: ExporterConfig | None = None) -> bytes:
        docu = self._export(Xlsx2XlsxExporter())
        return docu.content

    def export_to_csv(self, _: ExporterConfig | None = None) -> bytes:
        docu = self._export(Xlsx2CsvExporter())
        return docu.content

    def save_as_html(self, name: str = None, output_dir: Path | str = "./output",
                     config: Xlsx2HTMLExporterConfig | None = None) -> Self:
        config = config or self.config.html_exporter_config
        self._save(exporter=Xlsx2HTMLExporter(config), name=name, output_dir=output_dir)
        return self

    def save_as_xlsx(self, name: str = None, output_dir: Path | str = "./output",
                     _: ExporterConfig | None = None) -> Self:
        self._save(exporter=Xlsx2XlsxExporter(), name=name, output_dir=output_dir)
        return self

    def save_as_csv(self, name: str = None, output_dir: Path | str = "./output",
                    _: ExporterConfig | None = None) -> Self:
        self._save(exporter=Xlsx2CsvExporter(), name=name, output_dir=output_dir)
        return self
