# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
"""CAD file translation workflow.

Supports DWG/DXF files with automatic text extraction, LLM translation,
and write-back. Requires ``ezdxf`` (install with ``pip install docutranslate[cad]``).
DWG conversion requires an external tool (LibreDWG, HaoChen, AutoCAD, or ODA).
"""
from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Self

from docutranslate.cad.dwg_converter import DwgConverter
from docutranslate.cad.text_extractor import CadTextExtractor
from docutranslate.cad.text_applier import CadTextApplier
from docutranslate.glossary.glossary import Glossary
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.txt_translator import TXTTranslatorConfig, TXTTranslator
from docutranslate.workflow.base import Workflow, WorkflowConfig


@dataclass(kw_only=True)
class CadWorkflowConfig(WorkflowConfig):
    translator_config: TXTTranslatorConfig
    cad_converter_backend: str = "auto"
    insert_mode: str = "replace"
    font_name: str = "Times New Roman"
    font_size_reduction: int = 2


class CadWorkflow(Workflow[CadWorkflowConfig, Document, Document]):
    """Translate CAD files (DWG/DXF).

    Pipeline:
    1. If DWG, convert to DXF using available backend
    2. Extract text entities from DXF
    3. Translate extracted text via LLM
    4. Write translated text back to DXF
    """

    def __init__(self, config: CadWorkflowConfig):
        super().__init__(config=config)
        self._translator: TXTTranslator | None = None
        self._dxf_path: Path | None = None
        self._extraction_result = None
        if config.logger:
            config.translator_config.logger = config.logger

    def _ensure_dxf(self, file_path: str) -> Path:
        """Convert DWG→DXF if needed, or return DXF path directly."""
        src = Path(file_path)
        if src.suffix.lower() == ".dxf":
            return src

        converter = DwgConverter(backend=self.config.cad_converter_backend)
        tmp_dir = Path(tempfile.mkdtemp(prefix="docutranslate_cad_"))
        result = converter.dwg_to_dxf(str(src), str(tmp_dir))
        if not result.success:
            raise RuntimeError(f"DWG conversion failed: {result.message}")
        return Path(result.output_path)

    def read_path(self, path: Path | str) -> Self:
        """Read CAD file (DWG or DXF). Converts DWG→DXF if needed."""
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        self._dxf_path = self._ensure_dxf(str(file_path))

        # Extract text from DXF
        extractor = CadTextExtractor()
        self._extraction_result = extractor.extract(str(self._dxf_path))
        if not self._extraction_result.success:
            raise RuntimeError(f"Text extraction failed: {self._extraction_result.message}")

        if not self._extraction_result.entities:
            raise RuntimeError("No translatable text found in CAD file")

        # Build a text document from extracted entities for translation
        texts = [e.text for e in self._extraction_result.entities]
        content = "\n".join(texts).encode("utf-8")
        self.document_original = Document.from_bytes(content=content, suffix=".txt", stem="cad_texts")
        return self

    def translate(self) -> Self:
        """Translate extracted CAD text via LLM."""
        self.progress_tracker.update(percent=10, message="Extracting text...")
        self.progress_tracker.update(percent=30, message="Translating...")

        translator_config = TXTTranslatorConfig(
            base_url=self.config.translator_config.base_url,
            api_key=self.config.translator_config.api_key,
            model_id=self.config.translator_config.model_id,
            to_lang=self.config.translator_config.to_lang,
            concurrent=self.config.translator_config.concurrent,
            timeout=self.config.translator_config.timeout,
            retry=self.config.translator_config.retry,
            thinking=self.config.translator_config.thinking,
            custom_prompt=self.config.translator_config.custom_prompt,
            system_proxy_enable=self.config.translator_config.system_proxy_enable,
            chunk_size=self.config.translator_config.chunk_size,
            temperature=self.config.translator_config.temperature,
            top_p=self.config.translator_config.top_p,
        )
        translator = TXTTranslator(translator_config)
        self._translator = translator

        doc = self.document_original.copy()
        translator.translate(doc)
        self.document_translated = doc

        # Save glossary
        if translator.glossary.glossary_dict:
            self.progress_tracker.update(percent=95, message="Saving glossary...")
            self.attachment.add_document("glossary", Glossary.glossary_dict2csv(translator.glossary.glossary_dict))

        self.progress_tracker.update(percent=100, message="Translation complete")
        return self

    async def translate_async(self) -> Self:
        """Async version of translate."""
        self.progress_tracker.update(percent=10, message="Extracting text...")
        self.progress_tracker.update(percent=30, message="Translating...")

        translator_config = TXTTranslatorConfig(
            base_url=self.config.translator_config.base_url,
            api_key=self.config.translator_config.api_key,
            model_id=self.config.translator_config.model_id,
            to_lang=self.config.translator_config.to_lang,
            concurrent=self.config.translator_config.concurrent,
            timeout=self.config.translator_config.timeout,
            retry=self.config.translator_config.retry,
            thinking=self.config.translator_config.thinking,
            custom_prompt=self.config.translator_config.custom_prompt,
            system_proxy_enable=self.config.translator_config.system_proxy_enable,
            chunk_size=self.config.translator_config.chunk_size,
            temperature=self.config.translator_config.temperature,
            top_p=self.config.translator_config.top_p,
        )
        translator = TXTTranslator(translator_config)
        self._translator = translator

        doc = self.document_original.copy()
        await translator.translate_async(doc)
        self.document_translated = doc

        if translator.glossary.glossary_dict:
            self.progress_tracker.update(percent=95, message="Saving glossary...")
            self.attachment.add_document("glossary", Glossary.glossary_dict2csv(translator.glossary.glossary_dict))

        self.progress_tracker.update(percent=100, message="Translation complete")
        return self

    def apply_translations_to_dxf(
        self,
        output_path: str,
        mode: str = "",
        font_name: str = "",
        font_size_reduction: int = 0,
    ) -> Self:
        """Apply translated text back to DXF file."""
        if not self._extraction_result or not self._dxf_path:
            raise RuntimeError("No CAD file loaded. Call read_path() first.")

        if not self.document_translated:
            raise RuntimeError("No translation available. Call translate() first.")

        # Build translation map from original entities and translated text
        translated_text = self.document_translated.content.decode("utf-8")
        translated_lines = translated_text.split("\n")

        translation_map: dict[str, str] = {}
        for i, entity in enumerate(self._extraction_result.entities):
            if i < len(translated_lines):
                translated = translated_lines[i].strip()
                if translated:
                    translation_map[entity.text] = translated

        if not translation_map:
            raise RuntimeError("No translations generated")

        applier = CadTextApplier()
        result = applier.apply(
            dxf_path=str(self._dxf_path),
            output_path=output_path,
            translation_map=translation_map,
            mode=mode or self.config.insert_mode,
            font_name=font_name or self.config.font_name,
            font_size_reduction=font_size_reduction or self.config.font_size_reduction,
        )

        if not result.success:
            raise RuntimeError(f"Apply failed: {result.message}")

        self.document_translated = Document.from_path(output_path)
        return self

    def get_statistics(self) -> dict:
        if self._translator:
            return self._translator.get_statistics()
        return {}
