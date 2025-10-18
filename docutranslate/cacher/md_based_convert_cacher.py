# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import os
from collections import OrderedDict

from docutranslate.converter.base import ConverterConfig
from docutranslate.ir.document import Document
from docutranslate.ir.markdown_document import MarkdownDocument

CACHE_NUM = os.getenv("DOCUTRANSLATE_CACHE_NUM", default="10")


class MDBasedCovertCacher:
    def __init__(self):
        self.cache_dict = OrderedDict()

    @staticmethod
    def _get_hashcode(document: Document, convert_engin: str, convert_config: ConverterConfig | None) -> str:
        if convert_config:
            convert_config_hash = convert_config.gethash()
        else:
            convert_config_hash = None

        obj = (document.suffix, document.content, convert_engin, convert_config_hash)
        return str(hash(obj))

    def get_cached_result(self, document: Document, convert_engin: str,
                          convert_config: ConverterConfig) -> MarkdownDocument | None:
        d: MarkdownDocument | None = self.cache_dict.get(self._get_hashcode(document, convert_engin, convert_config))
        if d:
            return d.copy()
        else:
            return None

    def cache_result(self, convert_result: MarkdownDocument, document: Document, convert_engin: str,
                     convert_config: ConverterConfig) -> MarkdownDocument:
        hash_code = self._get_hashcode(document, convert_engin, convert_config)
        if len(self.cache_dict) > int(CACHE_NUM):
            self.cache_dict.popitem(last=False)
        self.cache_dict[hash_code] = convert_result.copy()
        return convert_result

    def clear(self):
        self.cache_dict.clear()


md_based_convert_cacher = MDBasedCovertCacher()
