# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from docutranslate.exporter.base import ExporterConfig
from docutranslate.exporter.js.json2html_exporter import Json2HTMLExporterConfig, Json2HTMLExporter
from docutranslate.exporter.js.json2json_exporter import Json2JsonExporter
from docutranslate.glossary.glossary import Glossary
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.json_translator import JsonTranslatorConfig, JsonTranslator
from docutranslate.workflow.base import Workflow, WorkflowConfig
from docutranslate.workflow.interfaces import HTMLExportable, JsonExportable


@dataclass(kw_only=True)
class JsonWorkflowConfig(WorkflowConfig):
    translator_config: JsonTranslatorConfig
    html_exporter_config: Json2HTMLExporterConfig


class JsonWorkflow(Workflow[JsonWorkflowConfig, Document, Document], HTMLExportable[Json2HTMLExporterConfig],
                   JsonExportable[ExporterConfig]):
    def __init__(self, config: JsonWorkflowConfig):
        super().__init__(config=config)
        if config.logger:
            for sub_config in [self.config.translator_config]:
                if sub_config:
                    sub_config.logger = config.logger

    def _pre_translate(self, document_original: Document):
        document = document_original.copy()
        translate_config = self.config.translator_config
        translator = JsonTranslator(translate_config)
        return document, translator

    def translate(self) -> Self:
        document, translator = self._pre_translate(self.document_original)
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

    def export_to_html(self, config: Json2HTMLExporterConfig = None) -> str:
        config = config or self.config.html_exporter_config
        docu = self._export(Json2HTMLExporter(config))
        return docu.content.decode()

    def export_to_json(self, _: ExporterConfig | None = None) -> str:
        docu = self._export(Json2JsonExporter())
        return docu.content.decode()

    def save_as_html(self, name: str = None, output_dir: Path | str = "./output",
                     config: Json2HTMLExporterConfig | None = None) -> Self:
        config = config or self.config.html_exporter_config
        self._save(exporter=Json2HTMLExporter(config), name=name, output_dir=output_dir)
        return self

    def save_as_json(self, name: str = None, output_dir: Path | str = "./output",
                     _: ExporterConfig | None = None) -> Self:
        self._save(exporter=Json2JsonExporter(), name=name, output_dir=output_dir)
        return self
