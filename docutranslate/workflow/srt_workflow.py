# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from docutranslate.exporter.base import ExporterConfig
from docutranslate.exporter.srt.srt2html_exporter import Srt2HTMLExporterConfig, Srt2HTMLExporter
from docutranslate.exporter.srt.srt2srt_exporter import Srt2SrtExporter
from docutranslate.glossary.glossary import Glossary
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.srt_translator import SrtTranslatorConfig, SrtTranslator
from docutranslate.workflow.base import Workflow, WorkflowConfig
from docutranslate.workflow.interfaces import HTMLExportable, SrtExportable


@dataclass(kw_only=True)
class SrtWorkflowConfig(WorkflowConfig):
    translator_config: SrtTranslatorConfig
    html_exporter_config: Srt2HTMLExporterConfig


class SrtWorkflow(Workflow[SrtWorkflowConfig, Document, Document], HTMLExportable[Srt2HTMLExporterConfig],
                  SrtExportable[ExporterConfig]):
    def __init__(self, config: SrtWorkflowConfig):
        super().__init__(config=config)
        if config.logger:
            for sub_config in [self.config.translator_config]:
                if sub_config:
                    sub_config.logger = config.logger

    def _pre_translate(self,document_original:Document):
        document = document_original.copy()
        translate_config = self.config.translator_config
        translator = SrtTranslator(translate_config)
        return document,translator


    def translate(self) -> Self:
        document, translator=self._pre_translate(self.document_original)
        translator.translate(document)
        # 使用合并后的术语表（用户上传 + 自动生成）
        merged_glossary = getattr(translator.translate_agent, 'glossary_dict', None) or translator.glossary_dict_gen
        if merged_glossary:
            self.attachment.add_document("glossary", Glossary.glossary_dict2csv(merged_glossary))
        self.document_translated = document
        return self

    async def translate_async(self) -> Self:
        document, translator = self._pre_translate(self.document_original)
        await translator.translate_async(document)
        # 使用合并后的术语表（用户上传 + 自动生成）
        merged_glossary = getattr(translator.translate_agent, 'glossary_dict', None) or translator.glossary_dict_gen
        if merged_glossary:
            self.attachment.add_document("glossary", Glossary.glossary_dict2csv(merged_glossary))
        self.document_translated = document
        return self

    def export_to_html(self, config: Srt2HTMLExporterConfig = None) -> str:
        config = config or self.config.html_exporter_config
        docu = self._export(Srt2HTMLExporter(config))
        return docu.content.decode()

    def export_to_srt(self, _: ExporterConfig | None = None) -> str:
        docu = self._export(Srt2SrtExporter())
        return docu.content.decode()

    def save_as_html(self, name: str = None, output_dir: Path | str = "./output",
                     config: Srt2HTMLExporterConfig | None = None) -> Self:
        config = config or self.config.html_exporter_config
        self._save(exporter=Srt2HTMLExporter(config), name=name, output_dir=output_dir)
        return self

    def save_as_srt(self, name: str = None, output_dir: Path | str = "./output",
                    _: ExporterConfig | None = None) -> Self:
        self._save(exporter=Srt2SrtExporter(), name=name, output_dir=output_dir)
        return self
