# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import os
from collections import OrderedDict
from threading import RLock

from docutranslate.converter.base import ConverterConfig
from docutranslate.ir.document import Document
from docutranslate.ir.markdown_document import MarkdownDocument

CACHE_NUM = os.getenv("DOCUTRANSLATE_CACHE_NUM", default="10")


class MDBasedCovertCacher:
    def __init__(self):
        self.cache_dict = OrderedDict()
        self._lock = RLock()

    @staticmethod
    def _get_hashcode(document: Document, convert_engin: str, convert_config: ConverterConfig | None) -> str:
        if convert_config:
            convert_config_hash = convert_config.gethash()
        else:
            convert_config_hash = None

        # MinerU output and exported filenames may depend on the input name.
        obj = (document.stem, document.suffix, document.content, convert_engin, convert_config_hash)
        return str(hash(obj))

    def get_cached_result(self, document: Document, convert_engin: str,
                          convert_config: ConverterConfig) -> MarkdownDocument | None:
        key = self._get_hashcode(document, convert_engin, convert_config)
        with self._lock:
            d = self.cache_dict.get(key)
            if d is not None:
                self.cache_dict.move_to_end(key)
                return d.copy()
            return None

    def cache_result(self, convert_result: MarkdownDocument, document: Document, convert_engin: str,
                     convert_config: ConverterConfig) -> MarkdownDocument:
        hash_code = self._get_hashcode(document, convert_engin, convert_config)
        limit = max(0, int(CACHE_NUM))
        with self._lock:
            if limit == 0:
                self.cache_dict.clear()
                return convert_result
            self.cache_dict[hash_code] = convert_result.copy()
            self.cache_dict.move_to_end(hash_code)
            while len(self.cache_dict) > limit:
                self.cache_dict.popitem(last=False)
        return convert_result

    def clear(self):
        with self._lock:
            self.cache_dict.clear()


md_based_convert_cacher = MDBasedCovertCacher()
