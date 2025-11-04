# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
from dataclasses import dataclass
from typing import Literal, Hashable

import httpx

from docutranslate.converter.x2md.base import X2MarkdownConverter, X2MarkdownConverterConfig
from docutranslate.ir.attachment_manager import AttachMent
from docutranslate.ir.document import Document
from docutranslate.ir.markdown_document import MarkdownDocument
from docutranslate.utils.markdown_utils import embed_inline_image_from_zip


@dataclass(kw_only=True)
class ConverterMineruDeployConfig(X2MarkdownConverterConfig):
    base_url: str = "http://127.0.0.1:8000"
    output_dir: str = "./output"  # 覆盖默认值 ./output
    # lang_list: list[str] | None = None
    backend: Literal["pipeline", "transformers", "mlx-engine", "vllm-engine", "vllm-async-engine"] = "pipeline"
    # parse_method: str = "auto"
    formula_enable: bool = True
    # table_enable: bool = True
    # server_url: str | None = None
    # return_md: bool = True
    # return_middle_json: bool = True
    # return_model_output: bool = False
    # return_content_list: bool = False
    # return_images: bool = True
    # response_format_zip: bool = True
    start_page_id: int = 0
    end_page_id: int = 99999

    def gethash(self) ->Hashable:
        return (self.backend,self.formula_enable,self.start_page_id,self.end_page_id)

# 配置HTTP客户端
timeout = httpx.Timeout(
    connect=5.0,
    read=1800.0,  # 本地部署可能处理时间较长，增加读取超时
    write=300.0,
    pool=1.0
)

limits = httpx.Limits(max_connections=500, max_keepalive_connections=20)
client = httpx.Client(limits=limits, trust_env=False, timeout=timeout, proxy=None, verify=False)
client_async = httpx.AsyncClient(limits=limits, trust_env=False, timeout=timeout, proxy=None, verify=False)


class ConverterMineruDeploy(X2MarkdownConverter):
    def __init__(self, config: ConverterMineruDeployConfig):
        super().__init__(config=config)
        self.base_url = config.base_url.rstrip('/')
        self.config = config
        self.attachments: list[AttachMent] = []

        self._api_url = f"{self.base_url}/file_parse"

    def _build_form_data(self)->dict:
        data = {
            "output_dir": self.config.output_dir,
            "backend": self.config.backend,
            "parse_method": "auto",
            "formula_enable": self.config.formula_enable,
            "table_enable": True,
            "server_url": None,
            "return_md": True,
            "return_middle_json": True,
            "return_model_output": False,
            "return_content_list": False,
            "return_images": True,
            "response_format_zip": True,
            "start_page_id": self.config.start_page_id,
            "end_page_id": self.config.end_page_id
        }
        return data


    def convert(self,d:Document)->MarkdownDocument:
        self.logger.info("开始解析文件")
        files = [("files", (d.name, d.content, "application/octet-stream"))]
        response = client.post(
            self._api_url,
            files=files,
            data=self._build_form_data(),
            timeout=2000,
        )

        response.raise_for_status()  # 检查是否有错误
        md=embed_inline_image_from_zip(response.content,None)
        self.logger.info("已转化为markdown")
        return MarkdownDocument.from_bytes(md.encode(),suffix=".md",stem=d.stem)


    async def convert_async(self, d: Document) -> MarkdownDocument:
        self.logger.info("开始解析文件")
        files = [("files", (d.name, d.content, "application/octet-stream"))]
        response =await client_async.post(
            self._api_url,
            files=files,
            data=self._build_form_data(),
            timeout=2000,
        )

        response.raise_for_status()
        md = await asyncio.to_thread(embed_inline_image_from_zip,response.content, None)
        self.logger.info("已转化为markdown")
        return MarkdownDocument.from_bytes(md.encode(), suffix=".md", stem=d.stem)

    def support_format(self) -> list[str]:
        return [".pdf", ".doc", ".docx", ".ppt", ".pptx", ".png", ".jpg", ".jpeg"]

if __name__ == '__main__':
    d = Document.from_path(r"C:\Users\jxgm\Desktop\testfiles\table.pdf")
    config=ConverterMineruDeployConfig()
    converter = ConverterMineruDeploy(config=config)
    converter.convert(d)
