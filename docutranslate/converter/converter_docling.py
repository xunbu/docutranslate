import os
import time
from io import BytesIO
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import DocumentStream
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.settings import settings
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import ImageRefMode
from huggingface_hub.errors import LocalEntryNotFoundError

from docutranslate.logger import translater_logger

from docutranslate.converter import Converter, Document

import asyncio

IMAGE_RESOLUTION_SCALE = 4


def file2markdown_embed_images(file_path: Path | str | DocumentStream, formula=False, code=False,
                               artifacts_path: Path | str | None = None) -> str:
    pipeline_options = PdfPipelineOptions(artifacts_path=artifacts_path)
    pipeline_options.do_ocr = False
    pipeline_options.images_scale = IMAGE_RESOLUTION_SCALE
    pipeline_options.generate_picture_images = True
    # pipeline_options.table_structure_options.mode = TableFormerMode.FAST
    pipeline_options.table_structure_options.do_cell_matching = False
    if formula:
        pipeline_options.do_formula_enrichment = True
    if code:
        pipeline_options.do_code_enrichment = True
    # pipeline_options.accelerator_options= AcceleratorOptions(
    #     num_threads=4, device=AcceleratorDevice.AUTO
    # )
    # 打印时间
    settings.debug.profile_pipeline_timings = True
    converter = DocumentConverter(format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)

    })
    try:
        conversion_result = converter.convert(file_path)
        result = conversion_result.document.export_to_markdown(image_mode=ImageRefMode.EMBEDDED)
    except LocalEntryNotFoundError:
        translater_logger.info(f"无法连接huggingface，正在尝试换源")
        os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
        conversion_result = converter.convert(file_path)
        result = conversion_result.document.export_to_markdown(image_mode=ImageRefMode.EMBEDDED)
        # translater_logger.info(f"docling转换耗时: {conversion_result.timings["pipeline_total"].times}")
    return result


class ConverterDocling(Converter):
    def __init__(self, code=True, formula=True, artifact=None):
        self.code = code
        self.formula = formula
        self.artifact = artifact

    def convert(self, document):
        assert isinstance(document.filename, str)
        translater_logger.info(f"正在将文档转换为markdown")
        time1 = time.time()
        document_stream = DocumentStream(name=document.filename, stream=BytesIO(document.filebytes))
        result = file2markdown_embed_images(document_stream, formula=self.formula, code=self.code,
                                            artifacts_path=self.artifact)
        translater_logger.info(f"已转换为markdown，耗时{time.time() - time1}秒")
        return result

    async def convert_async(self, document: Document) -> str:
        return await asyncio.to_thread(
            self.convert,
            document
        )


if __name__ == '__main__':
    pass
