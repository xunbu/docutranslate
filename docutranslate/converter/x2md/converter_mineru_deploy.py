# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
from dataclasses import dataclass
from typing import Literal, Hashable, List

import httpx

from docutranslate.converter.x2md.base import X2MarkdownConverter, X2MarkdownConverterConfig
from docutranslate.ir.attachment_manager import AttachMent
from docutranslate.ir.document import Document
from docutranslate.ir.markdown_document import MarkdownDocument
from docutranslate.utils.markdown_utils import embed_inline_image_from_zip


@dataclass(kw_only=True)
class ConverterMineruDeployConfig(X2MarkdownConverterConfig):
    base_url: str = "http://127.0.0.1:8000"
    output_dir: str = "./output"
    # 支持的语言列表 (来自 MinerU API)
    lang_list: List[str] | None = None  # 默认值在 API 侧处理，这里 None 即可

    # 后端引擎选项 (更新适配最新的 MinerU API)
    backend: Literal[
        "pipeline",
        "vlm-auto-engine",
        "vlm-http-client",
        "hybrid-auto-engine",
        "hybrid-http-client"
    ] = "hybrid-auto-engine"

    parse_method: Literal["auto", "txt", "ocr"] = "auto"
    formula_enable: bool = True
    table_enable: bool = True

    # 用于 vlm-http-client 或 hybrid-http-client 后端
    server_url: str | None = None

    # 返回选项
    return_md: bool = True
    return_middle_json: bool = False
    return_model_output: bool = False
    return_content_list: bool = False
    return_images: bool = True
    response_format_zip: bool = True

    # 页面范围
    start_page_id: int = 0
    end_page_id: int = 99999

    def gethash(self) -> Hashable:
        return (self.backend, self.formula_enable, self.table_enable,
                self.parse_method, self.start_page_id, self.end_page_id)


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

    def _build_form_data(self) -> dict:
        # httpx 在处理 data 参数时，如果值为 list，会自动展开为多个同名 key (例如 lang_list=ch&lang_list=en)
        # 这符合 FastAPI/Starlette 对 List 字段的解析要求
        data = {
            "output_dir": self.config.output_dir,
            "backend": self.config.backend,
            "parse_method": self.config.parse_method,
            # bool 类型在 multipart/form-data 中通常需要转为字符串 'true'/'false'，但 httpx 会处理 python bool
            "formula_enable": str(self.config.formula_enable).lower(),
            "table_enable": str(self.config.table_enable).lower(),
            "return_md": str(self.config.return_md).lower(),
            "return_middle_json": str(self.config.return_middle_json).lower(),
            "return_model_output": str(self.config.return_model_output).lower(),
            "return_content_list": str(self.config.return_content_list).lower(),
            "return_images": str(self.config.return_images).lower(),
            "response_format_zip": str(self.config.response_format_zip).lower(),
            "start_page_id": self.config.start_page_id,
            "end_page_id": self.config.end_page_id
        }

        if self.config.lang_list:
            data["lang_list"] = self.config.lang_list
        else:
            data["lang_list"] = ["ch"]  # 默认值

        if self.config.server_url:
            data["server_url"] = self.config.server_url

        return data

    def convert(self, d: Document) -> MarkdownDocument:
        self.logger.info("开始解析文件")
        files = [("files", (d.name, d.content, "application/octet-stream"))]
        response = client.post(
            self._api_url,
            files=files,
            data=self._build_form_data(),
            timeout=2000,
        )

        response.raise_for_status()  # 检查是否有错误
        # Mineru API 返回 zip 时包含图片和 md
        md = embed_inline_image_from_zip(response.content, None)
        self.logger.info("已转化为markdown")
        return MarkdownDocument.from_bytes(md.encode(), suffix=".md", stem=d.stem)

    async def convert_async(self, d: Document) -> MarkdownDocument:
        self.logger.info("开始解析文件")
        files = [("files", (d.name, d.content, "application/octet-stream"))]
        response = await client_async.post(
            self._api_url,
            files=files,
            data=self._build_form_data(),
            timeout=2000,
        )

        response.raise_for_status()
        md = await asyncio.to_thread(embed_inline_image_from_zip, response.content, None)
        self.logger.info("已转化为markdown")
        return MarkdownDocument.from_bytes(md.encode(), suffix=".md", stem=d.stem)

    def support_format(self) -> list[str]:
        return [".pdf", ".doc", ".docx", ".ppt", ".pptx", ".png", ".jpg", ".jpeg"]