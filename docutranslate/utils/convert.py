import asyncio
import os
from huggingface_hub.errors import LocalEntryNotFoundError
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, AcceleratorOptions, AcceleratorDevice
from docling_core.types.doc import ImageRefMode
from pathlib import Path
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.document import DocumentStream
from docling.datamodel.settings import settings
from docutranslate.logger import translater_logger
IMAGE_RESOLUTION_SCALE = 4


def file2markdown_embed_images(file_path: Path | str|DocumentStream, formula=False, code=False,artifacts_path:Path|str|None=None) -> str:
    translater_logger.info(f"正在将文档转换为markdown")
    pipeline_options = PdfPipelineOptions(artifacts_path=artifacts_path)
    pipeline_options.do_ocr=False
    pipeline_options.images_scale = IMAGE_RESOLUTION_SCALE
    pipeline_options.generate_picture_images = True
    if formula:
        pipeline_options.do_formula_enrichment=True
    if code:
        pipeline_options.do_code_enrichment=True
    # pipeline_options.accelerator_options= AcceleratorOptions(
    #     num_threads=4, device=AcceleratorDevice.AUTO
    # )
    #打印时间
    settings.debug.profile_pipeline_timings=True
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
        result=conversion_result.document.export_to_markdown(image_mode=ImageRefMode.EMBEDDED)
    translater_logger.info(f"已转换为markdown")
    translater_logger.info(f"pdf转换耗时: {conversion_result.timings["pipeline_total"].times}")
    return result

if __name__ == '__main__':
    pass