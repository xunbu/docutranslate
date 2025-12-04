# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
# from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
import pathlib

import docling.utils.model_downloader
def get_docling_artifacts(output_dir=None):
    # path = StandardPdfPipeline.download_models_hf()
    path=docling.utils.model_downloader.download_models(output_dir)
    print(f"docling模型包已经下载到{path.resolve()}")
    return path
#
if __name__ == '__main__':
    get_docling_artifacts(output_dir=pathlib.Path(r"C:\Users\jxgm\Desktop\translate\docutranslate\dist\models"))

