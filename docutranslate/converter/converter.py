from typing import Protocol
from pathlib import Path


class Document:
    def __init__(self,path:Path|str=None,filename:str=None,filebytes:bytes=None):
        if path is None and (filename is None or filebytes is None):
            raise Exception("Document的路径或filename、filebytes不能同时为空")
        self.filebytes = filebytes
        self.filename = filename
        self.path = path
        if path:
            if isinstance(path,str):
                path=Path(path)
            self.path=path
            self.filename=path.name
            self.filebytes=path.read_bytes()

class Converter(Protocol):
    #转换为markdown
    def convert(self,document:Document)->str:
        ...

    async def convert_async(self,document:Document)->str:
        ...

    def set_config(self,cofig:dict):
        ...

    def get_config_list(self)->list[str]|None:
        ...