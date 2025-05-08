from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling_core.types.doc import ImageRefMode
from pathlib import Path
from docling.document_converter import DocumentConverter, PdfFormatOption

IMAGE_RESOLUTION_SCALE = 4


def pdf2markdown_embed_images(pdf: Path | str, formula=False, code=False) -> str:
    pipeline_options = PdfPipelineOptions()
    pipeline_options.images_scale = IMAGE_RESOLUTION_SCALE
    pipeline_options.generate_picture_images = True
    if formula:
        pipeline_options.do_formula_enrichment=True
    if code:
        pipeline_options.do_code_enrichment=True
    converter = DocumentConverter(format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    })
    result = converter.convert(pdf).document.export_to_markdown( image_mode=ImageRefMode.EMBEDDED)
    return result

if __name__ == '__main__':
    pass