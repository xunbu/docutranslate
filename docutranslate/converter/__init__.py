from .converter import Document,Converter
from .converter_mineru import ConverterMineru

from docutranslate.global_values import  conditional_import
if conditional_import("docling"):
    from .converter_docling import ConverterDocling

# 打包docling时取消下面一行注释
# from .converter_docling import ConverterDocling
