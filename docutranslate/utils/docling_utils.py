from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline

def get_docling_artifacts():
    path = StandardPdfPipeline.download_models_hf()
    return path