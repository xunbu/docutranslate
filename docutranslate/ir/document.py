# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import copy
import dataclasses
from pathlib import Path

class Document:
    def __init__(self,suffix:str,content:bytes,stem:str|None=None,path:Path=None):
        self.suffix=suffix
        self.content=content
        self._stem=stem
        self.path=path


    @property
    def stem(self)->str|None:
        if not self._stem:
            return None
        if len(self._stem)>50:
            return self._stem[:50]
        return self._stem

    @property
    def name(self)->str|None:
        if not self.stem:
            return None
        return self.stem+self.suffix

    @classmethod
    def from_path(cls,path:Path|str):
        if isinstance(path,str):
            path=Path(path)
        return cls(suffix=path.suffix,content=path.read_bytes(),stem=path.stem,path=path)

    @classmethod
    def from_bytes(cls,content:bytes,suffix:str,stem:str|None):
        return cls(content=content,suffix=suffix,stem=stem)

    def copy(self):
        return copy.copy(self)
