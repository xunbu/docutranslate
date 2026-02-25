# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from abc import ABC, abstractmethod
from dataclasses import dataclass
from logging import Logger
from typing import TypeVar, Generic, Optional

from docutranslate.ir.document import Document
from docutranslate.logger import global_logger
from docutranslate.progress import ProgressTracker


@dataclass(kw_only=True)
class TranslatorConfig:
    logger: Logger = global_logger
    progress_tracker: Optional[ProgressTracker] = None


T = TypeVar('T', bound=Document)


class Translator(ABC, Generic[T]):
    """
    翻译中间文本（原地替换），Translator不做格式转换
    """

    def __init__(self, config: TranslatorConfig | None = None):
        self.config = config
        self.logger = config.logger or global_logger
        self.progress_tracker = config.progress_tracker if config else None

    @abstractmethod
    def translate(self, document: T) -> Document:
        ...

    @abstractmethod
    async def translate_async(self, document: T) -> Document:
        ...
