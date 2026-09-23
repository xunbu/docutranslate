# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
import hashlib
import time
from dataclasses import dataclass
from typing import Literal, Hashable, List
from urllib.parse import urljoin

import httpx

from docutranslate.config import (
    MINERU_DEPLOY_CONNECT_TIMEOUT,
    MINERU_DEPLOY_API_KEY,
    MINERU_DEPLOY_POOL_TIMEOUT,
    MINERU_DEPLOY_POLL_INTERVAL,
    MINERU_DEPLOY_READ_TIMEOUT,
    MINERU_DEPLOY_TASK_TIMEOUT,
    MINERU_DEPLOY_UPLOAD_CONNECT_TIMEOUT,
    MINERU_DEPLOY_UPLOAD_POOL_TIMEOUT,
    MINERU_DEPLOY_UPLOAD_READ_TIMEOUT,
    MINERU_DEPLOY_UPLOAD_WRITE_TIMEOUT,
    MINERU_DEPLOY_WRITE_TIMEOUT,
)

from docutranslate.converter.x2md.base import X2MarkdownConverter, X2MarkdownConverterConfig
from docutranslate.converter.x2md.mineru_v1 import MineruV1, TIERS, _origin
from docutranslate.ir.attachment_manager import AttachMent
from docutranslate.ir.document import Document
from docutranslate.ir.markdown_document import MarkdownDocument
from docutranslate.utils.markdown_utils import embed_inline_image_from_zip


MineruDeployBackend = Literal[
    "flash", "basic", "standard", "advanced",
    "pipeline",
    "vlm-engine",
    "vlm-http-client",
    "hybrid-engine",
    "hybrid-http-client",
    # MinerU 3.x 仍接受这些旧别名，保留以兼容历史配置。
    "vlm-auto-engine",
    "hybrid-auto-engine",
]
MineruDeployEffort = Literal["medium", "high"]

LEGACY_BACKEND_ALIASES = {
    "vlm-auto-engine": "vlm-engine",
    "hybrid-auto-engine": "hybrid-engine",
}
LEGACY_BACKEND_NAMES = {
    "vlm-engine": "vlm-auto-engine",
    "hybrid-engine": "hybrid-auto-engine",
}


@dataclass(kw_only=True)
class ConverterMineruDeployConfig(X2MarkdownConverterConfig):
    base_url: str = "http://127.0.0.1:8000"
    output_dir: str = "./output"
    api_key: str = MINERU_DEPLOY_API_KEY
    # 支持的语言列表 (来自 MinerU API)
    lang_list: List[str] | None = None  # 默认值在 API 侧处理，这里 None 即可

    # MinerU 3.x 公共 API 后端名称。
    backend: MineruDeployBackend = "hybrid-engine"
    effort: MineruDeployEffort = "medium"

    parse_method: Literal["auto", "txt", "ocr"] = "auto"
    formula_enable: bool = True
    table_enable: bool = True
    image_analysis: bool = True

    # 用于 vlm-http-client 或 hybrid-http-client 后端
    server_url: str | None = None

    # 返回选项
    return_md: bool = True
    return_middle_json: bool = False
    return_model_output: bool = False
    return_content_list: bool = False
    return_images: bool = True
    response_format_zip: bool = True
    return_original_file: bool = False
    client_side_output_generation: bool = False

    # 页面范围
    start_page_id: int = 0
    end_page_id: int = 99999

    def gethash(self) -> Hashable:
        return (
            self.base_url.rstrip('/'),
            hashlib.sha256(self.api_key.encode()).hexdigest(),
            self.backend,
            self.effort,
            self.formula_enable,
            self.table_enable,
            self.image_analysis,
            self.parse_method,
            self.server_url,
            self.return_md,
            self.return_middle_json,
            self.return_model_output,
            self.return_content_list,
            self.return_images,
            self.response_format_zip,
            self.return_original_file,
            self.client_side_output_generation,
            self.start_page_id,
            self.end_page_id,
            tuple(self.lang_list) if self.lang_list else None,
        )


# 配置HTTP客户端
timeout = httpx.Timeout(
    connect=MINERU_DEPLOY_CONNECT_TIMEOUT,
    read=MINERU_DEPLOY_READ_TIMEOUT,  # 本地部署可能处理时间较长，增加读取超时
    write=MINERU_DEPLOY_WRITE_TIMEOUT,
    pool=MINERU_DEPLOY_POOL_TIMEOUT
)

upload_timeout = httpx.Timeout(
    connect=MINERU_DEPLOY_UPLOAD_CONNECT_TIMEOUT,
    read=MINERU_DEPLOY_UPLOAD_READ_TIMEOUT,
    write=MINERU_DEPLOY_UPLOAD_WRITE_TIMEOUT,
    pool=MINERU_DEPLOY_UPLOAD_POOL_TIMEOUT,
)

limits = httpx.Limits(max_connections=500, max_keepalive_connections=20)
client = httpx.Client(
    limits=limits,
    trust_env=False,
    timeout=timeout,
    proxy=None,
    verify=False,
    follow_redirects=True,
)
client_async = httpx.AsyncClient(
    limits=limits,
    trust_env=False,
    timeout=timeout,
    proxy=None,
    verify=False,
    follow_redirects=True,
)


class ConverterMineruDeploy(X2MarkdownConverter):
    def __init__(self, config: ConverterMineruDeployConfig):
        super().__init__(config=config)
        self.base_url = config.base_url.rstrip('/')
        self.config = config
        self.attachments: list[AttachMent] = []
        self.task_timeout = max(MINERU_DEPLOY_TASK_TIMEOUT, 0.1)
        self.poll_interval = max(MINERU_DEPLOY_POLL_INTERVAL, 0.1)
        self._tasks_url = f"{self.base_url}/tasks"
        self._legacy_api_url = f"{self.base_url}/file_parse"

        canonical_backend = self._canonical_backend(config.backend)
        if canonical_backend.endswith("-http-client") and not config.server_url:
            raise ValueError(
                f"MinerU backend={canonical_backend} 时必须配置 server_url"
            )

    @staticmethod
    def _canonical_backend(backend: str) -> str:
        return LEGACY_BACKEND_ALIASES.get(backend, backend)

    def _build_form_data(self, *, legacy: bool = False) -> dict:
        """构造 MinerU 公共 API 的 multipart 表单。"""
        backend = self._canonical_backend(self.config.backend)
        if backend in TIERS:
            backend = "pipeline" if backend in {"flash", "basic"} else "hybrid-engine"
        if legacy:
            backend = LEGACY_BACKEND_NAMES.get(backend, backend)

        data = {
            "backend": backend,
            "parse_method": self.config.parse_method,
            "formula_enable": str(self.config.formula_enable).lower(),
            "table_enable": str(self.config.table_enable).lower(),
            "return_md": str(self.config.return_md).lower(),
            "return_middle_json": str(self.config.return_middle_json).lower(),
            "return_model_output": str(self.config.return_model_output).lower(),
            "return_content_list": str(self.config.return_content_list).lower(),
            "return_images": str(self.config.return_images).lower(),
            "response_format_zip": str(self.config.response_format_zip).lower(),
            "start_page_id": str(self.config.start_page_id),
            "end_page_id": str(self.config.end_page_id),
        }

        if not legacy:
            # MinerU 3.x 新增字段。2.7.x 的 /file_parse 不声明这些参数，
            # 回退时不发送，避免旧版或严格代理拒绝未知表单字段。
            data.update(
                {
                    "effort": "high" if self.config.backend == "advanced" else self.config.effort,
                    "image_analysis": str(self.config.image_analysis).lower(),
                    "return_original_file": str(
                        self.config.return_original_file
                    ).lower(),
                    "client_side_output_generation": str(
                        self.config.client_side_output_generation
                    ).lower(),
                }
            )

        data["lang_list"] = self.config.lang_list or ["ch"]

        if self.config.server_url:
            data["server_url"] = self.config.server_url

        # MinerU 2.7.x 的 /file_parse 接受 output_dir；3.x 新接口由服务端管理输出目录。
        if legacy:
            data["output_dir"] = self.config.output_dir

        return data

    @staticmethod
    def _files(d: Document):
        return [("files", (d.name, d.content, "application/octet-stream"))]

    @staticmethod
    def _response_detail(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except Exception:
            return response.text.strip() or response.reason_phrase
        if isinstance(payload, dict):
            for key in ("detail", "error", "message", "err_msg"):
                value = payload.get(key)
                if value:
                    return str(value)
        return str(payload)

    def _raise_for_status(self, response: httpx.Response, context: str) -> None:
        if response.is_success:
            return
        detail = self._response_detail(response)
        raise RuntimeError(
            f"MinerU Deploy {context}失败: HTTP {response.status_code}: {detail}"
        )

    def _resolve_task_url(self, value: object, fallback: str) -> str:
        if not isinstance(value, str) or not value:
            return fallback
        return urljoin(f"{self.base_url}/", value)

    def _auth_kwargs(self, url: str) -> dict:
        if self.config.api_key and _origin(url) == _origin(self.base_url):
            return {"headers": {"Authorization": f"Bearer {self.config.api_key}"}}
        return {}

    def _task_urls(self, payload: object) -> tuple[str, str, str]:
        if not isinstance(payload, dict):
            raise RuntimeError("MinerU Deploy 返回了无效的任务提交结果")
        task_id = payload.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise RuntimeError("MinerU Deploy 任务提交结果缺少 task_id")
        status_url = self._resolve_task_url(
            payload.get("status_url"), f"{self._tasks_url}/{task_id}"
        )
        result_url = self._resolve_task_url(
            payload.get("result_url"), f"{self._tasks_url}/{task_id}/result"
        )
        return task_id, status_url, result_url

    def _result_bytes(self, response: httpx.Response) -> bytes:
        self._raise_for_status(response, "获取结果")
        content_type = response.headers.get("content-type", "").lower()
        if "json" in content_type:
            raise RuntimeError(
                f"MinerU Deploy 未返回 ZIP: {self._response_detail(response)}"
            )
        return response.content

    def _submit_task(self, d: Document) -> tuple[str, str, str] | None:
        response = client.post(
            self._tasks_url,
            files=self._files(d),
            data=self._build_form_data(),
            **self._auth_kwargs(self._tasks_url),
            timeout=upload_timeout,
        )
        if response.status_code in {404, 405}:
            return None
        self._raise_for_status(response, "提交任务")
        if response.status_code != 202:
            raise RuntimeError(
                f"MinerU Deploy 任务提交返回了意外状态码 {response.status_code}"
            )
        return self._task_urls(response.json())

    async def _submit_task_async(self, d: Document) -> tuple[str, str, str] | None:
        response = await client_async.post(
            self._tasks_url,
            files=self._files(d),
            data=self._build_form_data(),
            **self._auth_kwargs(self._tasks_url),
            timeout=upload_timeout,
        )
        if response.status_code in {404, 405}:
            return None
        self._raise_for_status(response, "提交任务")
        if response.status_code != 202:
            raise RuntimeError(
                f"MinerU Deploy 任务提交返回了意外状态码 {response.status_code}"
            )
        return self._task_urls(response.json())

    def _wait_for_task(self, task: tuple[str, str, str]) -> bytes:
        task_id, status_url, result_url = task
        deadline = time.monotonic() + self.task_timeout
        while time.monotonic() < deadline:
            response = client.get(status_url, **self._auth_kwargs(status_url))
            self._raise_for_status(response, "查询任务状态")
            payload = response.json()
            status = payload.get("status") if isinstance(payload, dict) else None
            if status in {"pending", "processing"}:
                time.sleep(self.poll_interval)
                continue
            if status == "completed":
                return self._result_bytes(
                    client.get(result_url, timeout=upload_timeout, **self._auth_kwargs(result_url))
                )
            detail = self._response_detail(response)
            raise RuntimeError(
                f"MinerU Deploy 任务 {task_id} 失败，状态={status}: {detail}"
            )
        raise TimeoutError(
            f"MinerU Deploy 任务 {task_id} 超过总等待时间 {self.task_timeout} 秒"
        )

    async def _wait_for_task_async(self, task: tuple[str, str, str]) -> bytes:
        task_id, status_url, result_url = task
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.task_timeout
        while loop.time() < deadline:
            response = await client_async.get(status_url, **self._auth_kwargs(status_url))
            self._raise_for_status(response, "查询任务状态")
            payload = response.json()
            status = payload.get("status") if isinstance(payload, dict) else None
            if status in {"pending", "processing"}:
                await asyncio.sleep(self.poll_interval)
                continue
            if status == "completed":
                result_response = await client_async.get(
                    result_url, timeout=upload_timeout, **self._auth_kwargs(result_url)
                )
                return self._result_bytes(result_response)
            detail = self._response_detail(response)
            raise RuntimeError(
                f"MinerU Deploy 任务 {task_id} 失败，状态={status}: {detail}"
            )
        raise TimeoutError(
            f"MinerU Deploy 任务 {task_id} 超过总等待时间 {self.task_timeout} 秒"
        )

    def _v1_adapter(self):
        return MineruV1(self.base_url, self.config, task_timeout=self.task_timeout,
                        poll_interval=self.poll_interval, transfer_timeout=upload_timeout, logger=self.logger)

    def _legacy_request(self, d: Document) -> bytes:
        result = self._v1_adapter().run(client, d)
        if result is not None:
            return result
        self.logger.warning("MinerU 服务不支持 /tasks，回退到兼容接口 /file_parse")
        response = client.post(
            self._legacy_api_url,
            files=self._files(d),
            data=self._build_form_data(legacy=True),
            **self._auth_kwargs(self._legacy_api_url),
            timeout=upload_timeout,
        )
        return self._result_bytes(response)

    async def _legacy_request_async(self, d: Document) -> bytes:
        result = await self._v1_adapter().run_async(client_async, d)
        if result is not None:
            return result
        self.logger.warning("MinerU 服务不支持 /tasks，回退到兼容接口 /file_parse")
        response = await client_async.post(
            self._legacy_api_url,
            files=self._files(d),
            data=self._build_form_data(legacy=True),
            **self._auth_kwargs(self._legacy_api_url),
            timeout=upload_timeout,
        )
        return self._result_bytes(response)

    def _build_result(self, d: Document, content: bytes, md: str) -> MarkdownDocument:
        self.attachments.append(
            AttachMent(
                "mineru_deploy",
                Document.from_bytes(
                    content=content,
                    suffix=".zip",
                    stem="mineru_deploy",
                ),
            )
        )
        self.logger.info("已转化为markdown")
        return MarkdownDocument.from_bytes(md.encode(), suffix=".md", stem=d.stem)

    def convert(self, d: Document) -> MarkdownDocument:
        self.logger.info("开始解析文件")
        task = self._submit_task(d)
        content = self._legacy_request(d) if task is None else self._wait_for_task(task)
        md = embed_inline_image_from_zip(content, None)
        if md is None:
            raise Exception("无法从 MinerU Deploy 返回的 ZIP 中提取 Markdown 文件")
        return self._build_result(d, content, md)

    async def convert_async(self, d: Document) -> MarkdownDocument:
        self.logger.info("开始解析文件")
        task = await self._submit_task_async(d)
        content = (
            await self._legacy_request_async(d)
            if task is None
            else await self._wait_for_task_async(task)
        )
        md = await asyncio.to_thread(embed_inline_image_from_zip, content, None)
        if md is None:
            raise Exception("无法从 MinerU Deploy 返回的 ZIP 中提取 Markdown 文件")
        return self._build_result(d, content, md)

    def support_format(self) -> list[str]:
        return [".pdf", ".doc", ".docx", ".ppt", ".pptx", ".png", ".jpg", ".jpeg", ".jp2", ".webp", ".gif", ".bmp",
                ".xls", ".xlsx", ".rtf", ".odt", ".ods", ".odp", ".epub", ".ofd",
                ".html", ".htm", ".csv", ".tsv"]
