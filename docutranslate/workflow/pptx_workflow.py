# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from docutranslate.exporter.base import ExporterConfig
from docutranslate.exporter.pptx.pptx2html_exporter import PPTX2HTMLExporterConfig, PPTX2HTMLExporter
from docutranslate.exporter.pptx.pptx2pptx_exporter import PPTX2PPTXExporter
from docutranslate.glossary.glossary import Glossary
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.pptx_translator import PPTXTranslatorConfig, PPTXTranslator
from docutranslate.workflow.base import WorkflowConfig, Workflow
from docutranslate.workflow.interfaces import HTMLExportable, PPTXExportable


@dataclass(kw_only=True)
class PPTXWorkflowConfig(WorkflowConfig):
    translator_config: PPTXTranslatorConfig
    html_exporter_config: PPTX2HTMLExporterConfig


class PPTXWorkflow(Workflow[PPTXWorkflowConfig, Document, Document], HTMLExportable[PPTX2HTMLExporterConfig],
                   PPTXExportable[ExporterConfig]):
    def __init__(self, config: PPTXWorkflowConfig):
        super().__init__(config=config)
        if config.logger:
            for sub_config in [self.config.translator_config]:
                if sub_config:
                    sub_config.logger = config.logger

    def _pre_translate(self, document_original: Document):
        suffix = document_original.suffix.lower() if document_original.suffix else ""
        if suffix != ".pptx":
            raise ValueError(f"该工作流不支持{suffix}格式，请转为.pptx格式")
        document = document_original.copy()
        translate_config = self.config.translator_config
        translator = PPTXTranslator(translate_config)
        return document, translator

    def translate(self) -> Self:
        document, translator = self._pre_translate(self.document_original)
        translator.translate(document)
        if translator.glossary_dict_gen:
            self.attachment.add_document("glossary", Glossary.glossary_dict2csv(translator.glossary_dict_gen))
        self.document_translated = document
        return self

    async def translate_async(self) -> Self:
        document, translator = self._pre_translate(self.document_original)
        await translator.translate_async(document)
        if translator.glossary_dict_gen:
            self.attachment.add_document("glossary", Glossary.glossary_dict2csv(translator.glossary_dict_gen))
        self.document_translated = document
        return self

    def export_to_html(self, config: PPTX2HTMLExporterConfig = None) -> str:
        config = config or self.config.html_exporter_config
        docu = self._export(PPTX2HTMLExporter(config))
        return docu.content.decode()

    def export_to_pptx(self, _: ExporterConfig | None = None) -> bytes:
        docu = self._export(PPTX2PPTXExporter())
        return docu.content

    def save_as_html(self, name: str = None, output_dir: Path | str = "./output",
                     config: PPTX2HTMLExporter | None = None) -> Self:
        config = config or self.config.html_exporter_config
        self._save(exporter=PPTX2HTMLExporter(config), name=name, output_dir=output_dir)
        return self

    def save_as_pptx(self, name: str = None, output_dir: Path | str = "./output",
                     _: ExporterConfig | None = None) -> Self:
        self._save(exporter=PPTX2PPTXExporter(), name=name, output_dir=output_dir)
        return self
