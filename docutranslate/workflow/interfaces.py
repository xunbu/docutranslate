# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from pathlib import Path
from typing import Protocol, Self, TypeVar, runtime_checkable

from docutranslate.exporter.base import ExporterConfig

T_ExporterConfig = TypeVar("T_ExporterConfig", bound=ExporterConfig)


@runtime_checkable
class HTMLExportable(Protocol[T_ExporterConfig]):
    def export_to_html(self, config: T_ExporterConfig | None = None) -> str:
        ...

    def save_as_html(self, name: str, output_dir: Path | str, config: T_ExporterConfig | None = None) -> Self:
        ...


@runtime_checkable
class MDExportable(Protocol[T_ExporterConfig]):

    def export_to_markdown(self, config: T_ExporterConfig | None = None) -> str:
        ...

    def save_as_markdown(self, name: str, output_dir: Path | str, config: T_ExporterConfig | None = None) -> Self:
        ...


@runtime_checkable
class MDZIPExportable(Protocol[T_ExporterConfig]):

    def export_to_markdown_zip(self, config: T_ExporterConfig | None = None) -> bytes:
        ...

    def save_as_markdown_zip(self, name: str, output_dir: Path | str, config: T_ExporterConfig | None = None) -> Self:
        ...


@runtime_checkable
class MDFormatsExportable(MDZIPExportable[T_ExporterConfig], MDExportable[T_ExporterConfig], Protocol):
    ...


@runtime_checkable
class TXTExportable(Protocol[T_ExporterConfig]):
    def export_to_txt(self, config: T_ExporterConfig | None = None) -> str:
        ...

    def save_as_txt(self, name: str, output_dir: Path | str, config: T_ExporterConfig | None = None) -> Self:
        ...


@runtime_checkable
class JsonExportable(Protocol[T_ExporterConfig]):
    def export_to_json(self, config: T_ExporterConfig | None = None) -> str:
        ...

    def save_as_json(self, name: str, output_dir: Path | str, config: T_ExporterConfig | None = None) -> Self:
        ...


@runtime_checkable
class XlsxExportable(Protocol[T_ExporterConfig]):
    def export_to_xlsx(self, config: T_ExporterConfig | None = None) -> bytes:
        ...

    def save_as_xlsx(self, name: str, output_dir: Path | str, config: T_ExporterConfig | None = None) -> Self:
        ...


@runtime_checkable
class CsvExportable(Protocol[T_ExporterConfig]):
    def export_to_csv(self, config: T_ExporterConfig | None = None) -> bytes:
        ...

    def save_as_csv(self, name: str, output_dir: Path | str, config: T_ExporterConfig | None = None) -> Self:
        ...


@runtime_checkable
class DocxExportable(Protocol[T_ExporterConfig]):
    def export_to_docx(self, config: T_ExporterConfig | None = None) -> bytes:
        ...

    def save_as_docx(self, name: str, output_dir: Path | str, config: T_ExporterConfig | None = None) -> Self:
        ...


@runtime_checkable
class SrtExportable(Protocol[T_ExporterConfig]):
    def export_to_srt(self, config: T_ExporterConfig | None = None) -> str:
        ...

    def save_as_srt(self, name: str, output_dir: Path | str, config: T_ExporterConfig | None = None) -> Self:
        ...


@runtime_checkable
class EpubExportable(Protocol[T_ExporterConfig]):
    def export_to_epub(self, config: T_ExporterConfig | None = None) -> bytes:
        ...

    def save_as_epub(self, name: str, output_dir: Path | str, config: T_ExporterConfig | None = None) -> Self:
        ...

@runtime_checkable
class AssExportable(Protocol[T_ExporterConfig]):
    def export_to_ass(self, config: T_ExporterConfig | None = None) -> str:
        ...

    def save_as_ass(self, name: str, output_dir: Path | str, config: T_ExporterConfig | None = None) -> Self:
        ...
