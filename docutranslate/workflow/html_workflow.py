# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from docutranslate.exporter.base import ExporterConfig
from docutranslate.exporter.html.html2html_exporter import Html2HtmlExporter
from docutranslate.glossary.glossary import Glossary

from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.html_translator import HtmlTranslatorConfig, HtmlTranslator
from docutranslate.workflow.base import Workflow, WorkflowConfig
from docutranslate.workflow.interfaces import HTMLExportable


@dataclass(kw_only=True)
class HtmlWorkflowConfig(WorkflowConfig):
    translator_config: HtmlTranslatorConfig



class HtmlWorkflow(Workflow[HtmlWorkflowConfig, Document, Document], HTMLExportable):
    def __init__(self, config: HtmlWorkflowConfig):
        super().__init__(config=config)
        if config.logger:
            for sub_config in [self.config.translator_config]:
                if sub_config:
                    sub_config.logger = config.logger

    def _pre_translate(self, document_original: Document):
        document = document_original.copy()
        translate_config = self.config.translator_config
        translator = HtmlTranslator(translate_config)
        return document, translator

    def translate(self) -> Self:
        # 准备阶段
        self.progress_tracker.update(percent=10, message="正在准备翻译...")
        document, translator = self._pre_translate(self.document_original)

        # 翻译阶段
        translator.translate(document)

        # 保存术语表阶段
        if translator.glossary.glossary_dict:
            self.progress_tracker.update(percent=95, message="正在保存术语表...")
            self.attachment.add_document("glossary", Glossary.glossary_dict2csv(translator.glossary.glossary_dict))

        self.progress_tracker.update(percent=100, message="翻译完成")
        self.document_translated = document
        return self

    async def translate_async(self) -> Self:
        # 准备阶段
        self.progress_tracker.update(percent=10, message="正在准备翻译...")
        document, translator = self._pre_translate(self.document_original)

        # 翻译阶段 - 由 agent 更新细粒度进度
        await translator.translate_async(document)

        # 保存术语表阶段
        if translator.glossary.glossary_dict:
            self.progress_tracker.update(percent=95, message="正在保存术语表...")
            self.attachment.add_document("glossary", Glossary.glossary_dict2csv(translator.glossary.glossary_dict))

        self.progress_tracker.update(percent=100, message="翻译完成")
        self.document_translated = document
        return self

    def export_to_html(self, _: ExporterConfig = None) -> str:

        docu = self._export(Html2HtmlExporter())
        return docu.content.decode()


    def save_as_html(self, name: str = None, output_dir: Path | str = "./output",
                     _: ExporterConfig | None = None) -> Self:
        self._save(exporter=Html2HtmlExporter(), name=name, output_dir=output_dir)
        return self
