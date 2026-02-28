# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
# docutranslate/sdk.py

import asyncio
import base64
import os
from pathlib import Path
from typing import Optional, Literal, Dict, Any, List, Union

from pydantic import TypeAdapter

from docutranslate.agents.agent import ThinkingMode
from docutranslate.agents.provider import ProviderType

from docutranslate.core.schemas import TranslatePayload, GlossaryAgentConfigPayload, WorkflowType, InsertMode
from docutranslate.core.factory import create_workflow_from_payload
from docutranslate.translator import default_params
from docutranslate.global_values.conditional_import import DOCLING_EXIST

# --- 映射配置 ---
# 格式说明: {workflow_type: {save_type: (method_name, default_suffix)}}
# 注意: 第一个格式为默认格式
_WORKFLOW_MAPPINGS = {
    "markdown_based": {
        "markdown": ("save_as_markdown", "md"),  # 默认格式: 内嵌 base64 图片
        "markdown_zip": ("save_as_markdown_zip", "zip"),  # 非内嵌图片，分离存储
        "html": ("save_as_html", "html"),
    },
    "docx": {"docx": ("save_as_docx", "docx")},
    "xlsx": {"xlsx": ("save_as_xlsx", "xlsx")},
    "pptx": {"pptx": ("save_as_pptx", "pptx")},
    "epub": {"epub": ("save_as_epub", "epub")},
    "txt": {"txt": ("save_as_txt", "txt")},
    "json": {"json": ("save_as_json", "json")},
    "srt": {"srt": ("save_as_srt", "srt")},
    "ass": {"ass": ("save_as_ass", "ass")},
    "html": {"html": ("save_as_html", "html")},
}

# 每种工作流支持的输出格式列表
_WORKFLOW_SUPPORTED_FORMATS = {
    wf: list(formats.keys()) for wf, formats in _WORKFLOW_MAPPINGS.items()
}


class TranslationResult:
    """
    封装翻译结果，负责后续的保存或导出操作。
    """

    def __init__(self, workflow: Any, workflow_type: str, original_filename: str):
        self._workflow = workflow
        self._workflow_type = workflow_type
        self._original_filename = original_filename
        self._mapping = _WORKFLOW_MAPPINGS.get(workflow_type)
        self._supported_formats = _WORKFLOW_SUPPORTED_FORMATS.get(workflow_type, [])

    @property
    def supported_formats(self) -> List[str]:
        """获取当前工作流支持的输出格式"""
        return self._supported_formats

    def save(
            self,
            output_dir: str = "./output",
            name: Optional[str] = None,
            fmt: Optional[str] = None
    ) -> str:
        """
        保存结果到文件系统。

        :param output_dir: 输出目录。
        :param name: 文件名 (如 'result.html')。若为 None，使用原文件名 + 对应后缀。
        :param fmt: 输出格式 (如 'html', 'markdown', 'markdown_zip')。
                    若为 None，使用工作流默认格式。
        :return: 保存文件的完整路径 (仅供参考)。
        """
        if not self._mapping:
            raise ValueError(f"工作流 {self._workflow_type} 不支持自动保存")

        # 确定使用的格式
        if fmt:
            if fmt not in self._mapping:
                raise ValueError(
                    f"格式 '{fmt}' 不支持。可用格式: {self._supported_formats}"
                )
            method_name, default_suffix = self._mapping[fmt]
        else:
            # 使用默认第一个格式
            fmt = self._supported_formats[0]
            method_name, default_suffix = self._mapping[fmt]

        # 生成文件名
        if not name:
            base_name = os.path.splitext(self._original_filename)[0]
            name = f"{base_name}.{default_suffix}"

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        method = getattr(self._workflow, method_name, None)
        if method:
            method(name=name, output_dir=output_dir)
            return str(Path(output_dir) / name)
        raise AttributeError(f"Workflow 缺少方法 {method_name}")

    def export(self, fmt: Optional[str] = None) -> str:
        """
        导出为 Base64 编码的字符串 (用于 API 传输或无需落盘的场景)。

        :param fmt: 输出格式。若为 None，使用工作流默认格式。
        :return: Base64 编码的结果。
        """
        if not self._mapping:
            raise ValueError(f"工作流 {self._workflow_type} 不支持导出")

        # 确定使用的格式
        if fmt:
            if fmt not in self._mapping:
                raise ValueError(
                    f"格式 '{fmt}' 不支持。可用格式: {self._supported_formats}"
                )
            export_key = fmt
        else:
            # 使用默认第一个格式
            fmt = self._supported_formats[0]
            export_key = fmt

        # 构建方法名
        if export_key == "markdown_zip":
            method_name = "export_to_markdown_zip"
        else:
            method_name = f"export_to_{export_key}"

        method = getattr(self._workflow, method_name, None)
        if method:
            content = method()
            if isinstance(content, str):
                content = content.encode('utf-8')
            return base64.b64encode(content).decode('utf-8')
        raise AttributeError(f"Workflow 缺少方法 {method_name}")

    @property
    def workflow(self):
        """获取底层 Workflow 实例以访问高级功能 (如附件)"""
        return self._workflow


class Client:
    """
    DocuTranslate SDK。
    """

    def __init__(
            self,
            api_key: Optional[str] = None,
            base_url: Optional[str] = None,
            model_id: Optional[str] = None,
            to_lang: str = "中文",
            concurrent: int = default_params["concurrent"],
            timeout: int = default_params["timeout"],
            retry: int = default_params["retry"],
            thinking: ThinkingMode = default_params["thinking"],
            system_proxy_enable: bool = default_params["system_proxy_enable"],
            convert_engine: Literal["identity", "mineru", "docling", "mineru_deploy"] = "identity",
            mineru_token: str = "",
            extra_body: Optional[str] = None,
            **kwargs
    ):
        """
        初始化 SDK 实例。
        此处设置的参数将作为全局默认值，可在调用 translate 时被覆盖。
        """
        self.defaults = {
            "api_key": api_key, "base_url": base_url, "model_id": model_id,
            "to_lang": to_lang, "concurrent": concurrent, "timeout": timeout,
            "retry": retry, "thinking": thinking,
            "system_proxy_enable": system_proxy_enable,
            "convert_engine": convert_engine, "mineru_token": mineru_token,
            "extra_body": extra_body,
            **kwargs
        }
        self.defaults = {k: v for k, v in self.defaults.items() if v is not None}

    def translate(
            self,
            file_path: str,
            *,
            # --- 为了获得 IDE 提示，必须在这里显式列出所有参数 ---
            api_key: Optional[str] = None,
            base_url: Optional[str] = None,
            model_id: Optional[str] = None,
            to_lang: Optional[str] = None,
            workflow_type: WorkflowType = "auto",
            skip_translate: bool = False,
            concurrent: Optional[int] = None,
            chunk_size: Optional[int] = None,
            temperature: Optional[float] = None,
            timeout: Optional[int] = None,
            retry: Optional[int] = None,
            thinking: Optional[ThinkingMode] = None,
            custom_prompt: Optional[str] = None,
            system_proxy_enable: Optional[bool] = None,
            force_json: Optional[bool] = None,
            rpm: Optional[int] = None,
            tpm: Optional[int] = None,
            provider: Optional[Union[ProviderType, str]] = None,
            extra_body: Optional[str] = None,
            insert_mode: Literal["replace", "append", "prepend"] = "replace",
            separator: str = "\n",
            segment_mode: Literal["line", "paragraph", "none"] = "line",
            translate_regions: Optional[List[str]] = None,
            convert_engine: Literal["identity", "mineru", "docling", "mineru_deploy"] = "identity",
            mineru_token: str = "",
            md2docx_engine: Literal["python", "pandoc", "auto"] | None = "auto",
            model_version: Literal["pipeline", "vlm"] = "vlm",
            formula_ocr: bool = True,
            code_ocr: bool = True,
            mineru_deploy_base_url: str = "http://127.0.0.1:8000",
            mineru_deploy_backend: Literal["pipeline", "vlm-auto-engine", "vlm-http-client", "hybrid-auto-engine", "hybrid-http-client"] = "hybrid-auto-engine",
            mineru_deploy_parse_method: Literal["auto", "txt", "ocr"] = "auto",
            mineru_deploy_formula_enable: bool = True,
            mineru_deploy_table_enable: bool = True,
            mineru_deploy_start_page_id: int = 0,
            mineru_deploy_end_page_id: int = 99999,
            mineru_deploy_lang_list: Optional[List[str]] = None,
            mineru_deploy_server_url: str = "",
            json_paths: Optional[List[str]] = None,
            glossary_generate_enable: Optional[bool] = None,
            glossary_dict: Optional[Dict[str, str]] = None,
            glossary_agent_config: Optional[Union[GlossaryAgentConfigPayload, Dict[str, Any]]] = None,
            **kwargs
    ) -> TranslationResult:
        """
        同步执行翻译。参数说明请参考 translate_async。
        """
        # 获取当前函数的所有参数（这包含了你传入的 api_key, model_id 等）
        # 排除掉 self，剩下的就是传给 async 函数的参数
        args = locals()
        call_params = {k: v for k, v in args.items() if k != 'self'}

        # 剔除 kwargs 避免双重传递 (因为 call_params 已经包含了 kwargs 的内容)
        if 'kwargs' in call_params:
            extra = call_params.pop('kwargs')
            call_params.update(extra)

        return asyncio.run(self.translate_async(**call_params))

    async def translate_async(
            self,
            file_path: str,
            *,
            # --- 核心覆盖参数 ---
            api_key: Optional[str] = None,
            base_url: Optional[str] = None,
            model_id: Optional[str] = None,
            to_lang: Optional[str] = None,

            # --- 流程控制 ---
            workflow_type: WorkflowType = "auto",
            skip_translate: bool = False,

            # --- LLM 参数 ---
            concurrent: Optional[int] = None,
            chunk_size: Optional[int] = None,
            temperature: Optional[float] = None,
            timeout: Optional[int] = None,
            retry: Optional[int] = None,
            thinking: Optional[ThinkingMode] = None,
            custom_prompt: Optional[str] = None,
            system_proxy_enable: Optional[bool] = None,
            force_json: Optional[bool] = None,
            rpm: Optional[int] = None,
            tpm: Optional[int] = None,
            provider: Optional[Union[ProviderType, str]] = None,
            extra_body: Optional[str] = None,

            # --- 格式参数 (Docx/Excel/Txt) ---
            insert_mode: Literal["replace", "append", "prepend"] = "replace",
            separator: str = "\n",
            segment_mode: Literal["line", "paragraph", "none"] = "line",
            translate_regions: Optional[List[str]] = None,

            # --- 解析引擎 (PDF/OCR) ---
            convert_engine: Literal["identity", "mineru", "docling", "mineru_deploy"] = "identity",
            mineru_token: str = "",
            md2docx_engine: Literal["python", "pandoc", "auto"] | None = "auto",
            model_version: Literal["pipeline", "vlm"] = "vlm",
            formula_ocr: bool = True,
            code_ocr: bool = True,

            # --- Mineru 本地部署参数 ---
            mineru_deploy_base_url: str = "http://127.0.0.1:8000",
            mineru_deploy_backend: Literal["pipeline", "vlm-auto-engine", "vlm-http-client", "hybrid-auto-engine", "hybrid-http-client"] = "hybrid-auto-engine",
            mineru_deploy_parse_method: Literal["auto", "txt", "ocr"] = "auto",
            mineru_deploy_formula_enable: bool = True,
            mineru_deploy_table_enable: bool = True,
            mineru_deploy_start_page_id: int = 0,
            mineru_deploy_end_page_id: int = 99999,
            mineru_deploy_lang_list: Optional[List[str]] = None,
            mineru_deploy_server_url: str = "",

            # --- JSON / 术语表 ---
            json_paths: Optional[List[str]] = None,
            glossary_generate_enable: Optional[bool] = None,
            glossary_dict: Optional[Dict[str, str]] = None,
            glossary_agent_config: Optional[Union[GlossaryAgentConfigPayload, Dict[str, Any]]] = None,

            **kwargs
    ) -> TranslationResult:
        """
        异步执行翻译任务。

        :param file_path: 输入文件路径 (必需)。
        :param workflow_type: 工作流类型 (auto, docx, markdown_based, xlsx, json, txt)。
        :param skip_translate: 若为 True，仅进行解析/OCR，不调用 LLM 翻译。
        :param concurrent: LLM 请求并发数。
        :param json_paths: [Json专用] JsonPath 列表 (如 '$.data.*')。
        :param translate_regions: [Excel专用] 翻译区域 (如 'Sheet1!A1:B10')。
        :param insert_mode: [Docx/Xlsx/Txt] 译文插入模式 (replace, append, prepend)。
        :param convert_engine: [PDF/OCR] 解析引擎 (mineru, docling)。
        :param mineru_token: [Mineru Cloud] API Token。
        :param mineru_deploy_base_url: [Mineru Local] 本地服务地址。
        """

        # 1. 获取所有参数
        current_args = locals()
        call_params = {
            k: v for k, v in current_args.items()
            if k not in ['self', 'file_path', 'kwargs'] and v is not None
        }
        call_params.update({k: v for k, v in kwargs.items() if v is not None})

        # 2. 参数层级合并
        final_params = {**default_params, **self.defaults, **call_params}

        # 3. 文件校验
        path_obj = Path(file_path)
        if not path_obj.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 4. 自动检测 Workflow 类型
        if final_params.get("workflow_type", "auto") == "auto":
            final_params["workflow_type"] = self._detect_workflow(path_obj)

        # 5. 智能补全
        self._patch_defaults(final_params, path_obj)

        # 6. Pydantic 校验
        try:
            payload = TypeAdapter(TranslatePayload).validate_python(final_params)
        except Exception as e:
            raise ValueError(f"参数配置校验失败: {e}")

        # 7. 创建 Workflow
        workflow = create_workflow_from_payload(payload)

        # 8. 执行逻辑
        workflow.read_path(str(path_obj))

        # 仅当 skip_translate 为 False 时才执行翻译
        if not payload.skip_translate:
            await workflow.translate_async()

        return TranslationResult(workflow, final_params["workflow_type"], path_obj.name)

    def _detect_workflow(self, path: Path) -> str:
        ext = path.suffix.lower().lstrip(".")
        if ext in ["md", "pdf", "png", "jpg"]: return "markdown_based"
        if ext in ["xlsx", "csv", "xls"]: return "xlsx"
        if ext in ["docx", "doc"]: return "docx"
        if ext in ["html", "htm"]: return "html"
        if ext in ["pptx", "ppt"]: return "pptx"
        if ext in ["txt", "json", "srt", "epub", "ass"]: return ext
        return "txt"

    def _patch_defaults(self, params: Dict[str, Any], path: Path):
        wf = params.get("workflow_type")
        if wf == "json" and not params.get("json_paths"):
            params["json_paths"] = ["$..*"]
        if wf == "markdown_based" and "convert_engine" not in params:
            ext = path.suffix.lower()
            if ext == ".pdf":
                params["convert_engine"] = "mineru" if not DOCLING_EXIST else "docling"
            else:
                params["convert_engine"] = "identity"

