# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Self, Tuple, Type

from docutranslate.cacher import md_based_convert_cacher
from docutranslate.converter.x2md.converter_mineru_deploy import ConverterMineruDeploy, ConverterMineruDeployConfig
from docutranslate.exporter.base import ExporterConfig
from docutranslate.global_values.conditional_import import DOCLING_EXIST
from docutranslate.glossary.glossary import Glossary
from docutranslate.ir.document import Document
from docutranslate.ir.markdown_document import MarkdownDocument
from docutranslate.utils.markdown_utils import embed_inline_image_from_zip

if DOCLING_EXIST:
    from docutranslate.converter.x2md.converter_docling import ConverterDoclingConfig, ConverterDocling
from docutranslate.converter.converter_identity import ConverterIdentity
from docutranslate.converter.x2md.converter_mineru import ConverterMineruConfig, ConverterMineru
from docutranslate.converter.x2md.base import X2MarkdownConverterConfig, X2MarkdownConverter
from docutranslate.exporter.md.md2html_exporter import MD2HTMLExporterConfig, MD2HTMLExporter
from docutranslate.exporter.md.md2md_exporter import MD2MDExporter
from docutranslate.exporter.md.md2mdzip_exporter import MD2MDZipExporter
from docutranslate.exporter.md.md2docx_exporter import MD2DocxExporterConfig, MD2DocxExporter
from docutranslate.exporter.md.types import ConvertEngineType
from docutranslate.workflow.base import Workflow, WorkflowConfig
from docutranslate.workflow.interfaces import MDFormatsExportable, HTMLExportable, DocxExportable
from docutranslate.translator.ai_translator.md_translator import MDTranslatorConfig, MDTranslator


@dataclass(kw_only=True)
class MarkdownBasedWorkflowConfig(WorkflowConfig):
    convert_engine: ConvertEngineType
    converter_config: X2MarkdownConverterConfig | None
    translator_config: MDTranslatorConfig
    html_exporter_config: MD2HTMLExporterConfig
    md2docx_exporter_config: MD2DocxExporterConfig | None


class MarkdownBasedWorkflow(Workflow[MarkdownBasedWorkflowConfig, Document, MarkdownDocument],
                            HTMLExportable[MD2HTMLExporterConfig],
                            MDFormatsExportable[ExporterConfig],
                            DocxExportable[MD2DocxExporterConfig]):
    _converter_factory: dict[
        ConvertEngineType, Tuple[Type[X2MarkdownConverter | ConverterIdentity], Type[
            X2MarkdownConverterConfig]] | None] = {
        "mineru": (ConverterMineru, ConverterMineruConfig),
        "identity": (ConverterIdentity, None),
        "mineru_deploy": (ConverterMineruDeploy, ConverterMineruDeployConfig)
    }

    if DOCLING_EXIST:
        _converter_factory["docling"] = (ConverterDocling, ConverterDoclingConfig)

    def __init__(self, config: MarkdownBasedWorkflowConfig):
        super().__init__(config=config)
        self.convert_engine = config.convert_engine
        if config.logger:
            for sub_config in [self.config.converter_config, self.config.translator_config,
                               self.config.html_exporter_config, self.config.md2docx_exporter_config]:
                if sub_config:
                    sub_config.logger = config.logger

    def _get_document_md(self, convert_engin: ConvertEngineType, convert_config: X2MarkdownConverterConfig):
        if self.document_original is None:
            raise RuntimeError("File has not been read yet. Call read_path or read_bytes first.")

        if self.document_original.suffix.lower() == ".zip":
            self.document_original = self._get_md_from_zip(self.document_original)
        # 获取缓存的解析后文件
        document_cached = md_based_convert_cacher.get_cached_result(self.document_original, convert_engin,
                                                                    convert_config)
        if document_cached:
            self.attachment.add_document("md_cached", document_cached.copy())
            return document_cached

        # 未缓存则解析文件
        if convert_engin in self._converter_factory:
            converter_class, config_class = self._converter_factory[convert_engin]
            if config_class and not isinstance(convert_config, config_class):
                raise TypeError(
                    f"The correct convert_config was not passed. It should be of type {config_class.__name__}, but it is currently of type {type(convert_config).__name__}.")
            converter = converter_class(convert_config)
        else:
            raise ValueError(f"不存在{convert_engin}解析引擎")
        document_md: Document = converter.convert(self.document_original)
        if hasattr(converter, "attachments"):
            for attachment in converter.attachments:
                self.attachment.add_attachment(attachment)
        # 缓存解析后文件
        md_based_convert_cacher.cache_result(document_md, self.document_original, convert_engin, convert_config)

        return document_md

    def _get_md_from_zip(self, document: Document) -> Document:
        assert document.suffix.lower() == ".zip"
        self.logger.info("传入zip文件，正在自动组合markdown文本与图片")
        content_byte = embed_inline_image_from_zip(document.content).encode()
        return document.from_bytes(content_byte, suffix=".md", stem=document.stem)

    def _pre_translate(self, document: Document):
        convert_engine: ConvertEngineType = "identity" if document.suffix.lower() in [".md", ".markdown",
                                                                                      ".zip"] else self.convert_engine
        convert_config = self.config.converter_config
        translator_config = self.config.translator_config
        translator = MDTranslator(translator_config)
        return convert_engine, convert_config, translator_config, translator

    def translate(self) -> Self:
        # 解析文档阶段
        self.progress_tracker.update(percent=10, message="正在解析文档...")
        convert_engine, convert_config, translator_config, translator = self._pre_translate(self.document_original)
        document_md = self._get_document_md(convert_engine, convert_config)

        # 翻译阶段
        translator.translate(document_md)

        # 保存术语表阶段
        if translator.glossary.glossary_dict:
            self.progress_tracker.update(percent=95, message="正在保存术语表...")
            self.attachment.add_document("glossary", Glossary.glossary_dict2csv(translator.glossary.glossary_dict))

        self.progress_tracker.update(percent=100, message="翻译完成")
        self.document_translated = document_md
        return self

    async def translate_async(self) -> Self:
        # 解析文档阶段
        self.progress_tracker.update(percent=10, message="正在解析文档...")
        convert_engine, convert_config, translator_config, translator = self._pre_translate(self.document_original)
        document_md = await asyncio.to_thread(self._get_document_md, convert_engine, convert_config)

        # 翻译阶段 - 由 agent 更新细粒度进度
        await translator.translate_async(document_md)

        # 保存术语表阶段
        if translator.glossary.glossary_dict:
            self.progress_tracker.update(percent=95, message="正在保存术语表...")
            self.attachment.add_document("glossary", Glossary.glossary_dict2csv(translator.glossary.glossary_dict))

        self.progress_tracker.update(percent=100, message="翻译完成")
        self.document_translated = document_md
        return self

    def export_to_html(self, config: MD2HTMLExporterConfig | None = None) -> str:
        config = config or self.config.html_exporter_config
        docu = self._export(MD2HTMLExporter(config))
        return docu.content.decode()

    def export_to_markdown(self, config: ExporterConfig | None = None) -> str:
        docu = self._export(MD2MDExporter())
        return docu.content.decode()

    def export_to_markdown_zip(self, config: ExporterConfig | None = None) -> bytes:
        docu = self._export(MD2MDZipExporter())
        return docu.content

    def save_as_html(self, name: str = None, output_dir: Path | str = "./output",
                     config: MD2HTMLExporterConfig | None = None) -> Self:
        config = config or self.config.html_exporter_config
        self._save(exporter=MD2HTMLExporter(config=config), name=name, output_dir=output_dir)
        return self

    def save_as_markdown(self, name: str = None, output_dir: Path | str = "./output",
                         _: ExporterConfig | None = None) -> Self:

        self._save(exporter=MD2MDExporter(), name=name, output_dir=output_dir)
        return self

    def save_as_markdown_zip(self, name: str = None, output_dir: Path | str = "./output",
                             _: ExporterConfig | None = None) -> Self:

        self._save(exporter=MD2MDZipExporter(), name=name, output_dir=output_dir)
        return self

    def export_to_docx(self, config: MD2DocxExporterConfig | None = None) -> bytes:
        config = config or self.config.md2docx_exporter_config
        if config is None:
            raise ValueError("md2docx_engine is set to None, docx export is disabled")
        docu = self._export(MD2DocxExporter(config))
        return docu.content

    def save_as_docx(self, name: str = None, output_dir: Path | str = "./output",
                     config: MD2DocxExporterConfig | None = None) -> Self:
        config = config or self.config.md2docx_exporter_config
        if config is None:
            raise ValueError("md2docx_engine is set to None, docx export is disabled")
        self._save(exporter=MD2DocxExporter(config), name=name, output_dir=output_dir)
        return self
