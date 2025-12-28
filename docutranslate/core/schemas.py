# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
# docutranslate.core.schemas.py

import json
from typing import (
    List,
    Dict,
    Optional,
    Literal,
    Union,
    Annotated,
)

from pydantic import (
    BaseModel,
    Field,
    model_validator,
    field_validator,
    AliasChoices,
    ConfigDict,
)

from docutranslate.agents.agent import ThinkingMode
from docutranslate.agents.thinking.thinking_factory import ProviderType
from docutranslate.translator import default_params


class GlossaryAgentConfigPayload(BaseModel):
    base_url: str = Field(
        ...,
        validation_alias=AliasChoices("base_url", "baseurl"),
        description="用于术语表生成的Agent的LLM API基础URL。",
        examples=["https://api.openai.com/v1"],
    )
    api_key: str = Field(
        default="xx",
        validation_alias=AliasChoices("api_key", "key"),
        description="用于术语表生成的Agent的LLM API密钥（默认为xx）。",
        examples=["sk-agent-api-key"],
    )

    @field_validator("api_key")
    @classmethod
    def set_default_glossary_api_key(cls, v: str) -> str:
        return v if v and v.strip() else "xx"

    model_id: str = Field(
        ..., description="用于术语表生成的Agent的模型ID。", examples=["gpt-4-turbo"]
    )
    to_lang: str = Field(
        ..., description="术语表生成的目标语言。", examples=["简体中文", "English"]
    )
    temperature: float = Field(
        default=0.7, description="用于术语表生成的Agent的温度参数。"
    )
    concurrent: int = Field(default=30, description="Agent的最大并发请求数。")
    timeout: int = Field(
        default=default_params["timeout"], description="等待API回复的时间（秒）。"
    )
    thinking: ThinkingMode = Field(default="default", description="Agent的思考模式。")
    retry: int = Field(
        default=default_params["retry"], description="分块失败后的最大重试次数。"
    )
    system_proxy_enable: bool = Field(
        default=default_params["system_proxy_enable"],
        description="是否使用系统代理",
        examples=[True, False],
    )
    # 修改: 默认值改为 "" 以避免 Swagger 显示 "string"
    custom_prompt: Optional[str] = Field(
        default="", description="生成术语表的用户自定义提示词"
    )
    force_json: bool = Field(
        default=False, description="强制Agent输出JSON格式的术语表。"
    )
    # 修改: 增加 examples=[None]
    rpm: Optional[int] = Field(
        default=None, description="RPM限制 (Requests Per Minute)", examples=[None]
    )
    tpm: Optional[int] = Field(
        default=None, description="TPM限制 (Tokens Per Minute)", examples=[None]
    )
    provider: Optional[ProviderType] = Field(
        default=None, description="LLM供应商标识", examples=[None]
    )


# 1. 定义所有工作流共享的基础参数
class BaseWorkflowParams(BaseModel):
    skip_translate: bool = Field(
        default=False,
        description="是否跳过翻译步骤。如果为True，则仅执行文档解析和格式转换。",
    )
    # 修改: 默认值改为 ""
    base_url: Optional[str] = Field(
        default="",
        validation_alias=AliasChoices("base_url", "baseurl"),
        description="LLM API的基础URL。当 `skip_translate` 为 `False` 时必填。",
        examples=["https://api.openai.com/v1"],
    )
    api_key: str = Field(
        default="xx",
        validation_alias=AliasChoices("api_key", "key"),
        description="LLM API的密钥（可选，默认为xx）。",
        examples=["sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
    )

    @field_validator("api_key")
    @classmethod
    def set_default_api_key(cls, v: str) -> str:
        return v if v and v.strip() else "xx"

    # 修改: 默认值改为 ""
    model_id: Optional[str] = Field(
        default="",
        description="要使用的LLM模型ID。当 `skip_translate` 为 `False` 时必填。",
        examples=["gpt-4o"],
    )
    to_lang: str = Field(
        default="中文", description="目标翻译语言。", examples=["简体中文", "English"]
    )
    chunk_size: int = Field(
        default=default_params["chunk_size"], description="文本分割的块大小（字符）。"
    )
    concurrent: int = Field(
        default=default_params["concurrent"], description="并发请求数。"
    )
    temperature: float = Field(
        default=default_params["temperature"], description="LLM温度参数。"
    )
    timeout: int = Field(
        default=default_params["timeout"], description="等待API回复的时间（秒）。"
    )
    thinking: ThinkingMode = Field(
        default=default_params["thinking"],
        description="Agent的思考模式。",
        examples=["default", "enable", "disable"],
    )
    retry: int = Field(
        default=default_params["retry"],
        description="某个分块翻译失败后的最大重试次数。",
    )
    system_proxy_enable: bool = Field(
        default=default_params["system_proxy_enable"],
        description="是否使用系统代理",
        examples=[True, False],
    )
    # 修改: 默认值改为 ""
    custom_prompt: Optional[str] = Field(
        default="", description="用户自定义的翻译Prompt。", alias="custom_prompt"
    )
    glossary_dict: Optional[Dict[str, str]] = Field(
        None, description="术语表字典，key为原文，value为译文。", examples=[None]
    )
    glossary_generate_enable: bool = Field(
        default=False, description="是否开启术语表自动生成。"
    )
    glossary_agent_config: Optional[GlossaryAgentConfigPayload] = Field(
        None,
        description="用于术语表生成的Agent的配置。如果 `glossary_generate_enable` 为 `True`，此项必填。",
        examples=[None],
    )
    force_json: bool = Field(
        default=False, description="应输出json格式时强制ai输出json"
    )
    rpm: Optional[int] = Field(
        default=None, description="RPM限制 (Requests Per Minute)", examples=[None]
    )
    tpm: Optional[int] = Field(
        default=None, description="TPM限制 (Tokens Per Minute)", examples=[None]
    )
    provider: Optional[ProviderType] = Field(
        default=None, description="LLM供应商标识", examples=[None]
    )

    @model_validator(mode="before")
    @classmethod
    def check_translation_fields(cls, values):
        # 修复: 当使用 FastAPI Form + Json 时，Pydantic V2 mode='before' 验证器可能会接收到 JSON 字符串
        if isinstance(values, str):
            try:
                values = json.loads(values)
            except ValueError:
                pass

        if isinstance(values, dict):
            if not values.get("skip_translate"):
                # 如果是空字符串 "" (即默认值)，not "" 为 True，会触发错误，符合预期
                if not (values.get("base_url") or values.get("baseurl")):
                    # Auto 模式在校验前不强制要求 base_url
                    if values.get("workflow_type") != "auto":
                        raise ValueError(
                            "当 `skip_translate` 为 `False` 时, `base_url` 或 `baseurl` 字段是必须的。"
                        )
                if not values.get("model_id"):
                    if values.get("workflow_type") != "auto":
                        raise ValueError(
                            "当 `skip_translate` 为 `False` 时, `model_id` 字段是必须的。"
                        )
        return values


# 2. 为每个工作流创建独立的参数模型
class AutoWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal["auto"] = Field(..., description="根据文件后缀自动选择工作流。")
    model_config = ConfigDict(extra="allow")


class MarkdownWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal["markdown_based"] = Field(
        ..., description="指定使用基于Markdown的翻译工作流。"
    )
    convert_engine: Literal[
        "identity", "mineru", "docling", "mineru_deploy"
    ] = Field(
        "identity",
        description="选择将文件解析为markdown的引擎。'mineru_deploy' 适用于本地部署的 MinerU 服务。如果输入文件是.md，此项可为`identity`或不传。",
        examples=["identity", "mineru", "docling", "mineru_deploy"],
    )

    # --- Engine-Specific Parameters ---

    # -- For "mineru" (Cloud API) --
    # 修改: 默认值改为 ""
    mineru_token: Optional[str] = Field(
        default="",
        description="[仅当 convert_engine='mineru'] 必填的API令牌。",
    )
    model_version: Literal["pipeline", "vlm"] = Field(
        "vlm", description="[仅当 convert_engine='mineru'] Mineru Cloud模型的版本。"
    )
    formula_ocr: bool = Field(
        True,
        description="[仅当 convert_engine='mineru' 或 'docling'] 是否对公式进行OCR识别。",
    )

    # -- For "docling" --
    code_ocr: bool = Field(
        True, description="[仅当 convert_engine='docling'] 是否对代码块进行OCR识别。"
    )

    # -- For "mineru_deploy" (Local Deployment) --
    mineru_deploy_base_url: Optional[str] = Field(
        "http://127.0.0.1:8000",
        description="[仅当 convert_engine='mineru_deploy'] 本地部署的 MinerU 服务地址。",
    )
    mineru_deploy_backend: Literal[
        "pipeline",
        "vlm-transformers",
        "vlm-mlx-engine",
        "vlm-vllm-async-engine",
        "vlm-lmdeploy-engine",
        "vlm-http-client",
    ] = Field(
        "pipeline",
        description="[仅当 convert_engine='mineru_deploy'] 本地部署的 MinerU 服务使用的后端。",
    )
    mineru_deploy_formula_enable: bool = Field(
        True,
        description="[仅当 convert_engine='mineru_deploy'] 本地部署的服务是否启用公式解析。",
    )
    mineru_deploy_start_page_id: int = Field(
        0, description="[仅当 convert_engine='mineru_deploy'] 起始解析页面。"
    )
    mineru_deploy_end_page_id: int = Field(
        99999, description="[仅当 convert_engine='mineru_deploy'] 结束解析页面。"
    )
    mineru_deploy_lang_list: Optional[List[str]] = Field(
        None,
        description="[仅当 convert_engine='mineru_deploy' 且 backend='pipeline'] 语言列表。",
        examples=[None],
    )
    # 修改: 默认值改为 ""
    mineru_deploy_server_url: Optional[str] = Field(
        default="",
        description="[仅当 convert_engine='mineru_deploy' 且 backend='vlm-http-client'] Server URL.",
    )

    @model_validator(mode="after")
    def check_engine_params(self):
        if self.convert_engine == "mineru" and not self.mineru_token:
            raise ValueError(
                "当 `convert_engine` 为 'mineru' 时，`mineru_token` 字段是必须的。"
            )
        if (
            self.convert_engine == "mineru_deploy"
            and not self.mineru_deploy_base_url
        ):
            raise ValueError(
                "当 `convert_engine` 为 'mineru_deploy' 时，`mineru_deploy_base_url` 字段是必须的。"
            )
        return self


class TextWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal["txt"] = Field(
        ..., description="指定使用纯文本的翻译工作流。"
    )
    insert_mode: Literal["replace", "append", "prepend"] = Field(
        "replace",
        description="翻译文本的插入模式。'replace'：替换原文，'append'：附加到原文后，'prepend'：附加到原文前。",
    )
    separator: str = Field(
        "\n",
        description="当 insert_mode 为 'append' 或 'prepend' 时，用于分隔原文和译文的分隔符。",
    )
    segment_mode: Literal["line", "paragraph", "none"] = Field(
        "line",
        description="分段模式。'line'：按行分段（每行独立翻译），'paragraph'：按段落分段（连续非空行合并为段落），'none'：不分段（全文视为一个段落）。",
    )


class JsonWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal["json"] = Field(
        ..., description="指定使用JSON的翻译工作流。"
    )
    json_paths: List[str] = Field(
        ...,
        description="一个jsonpath-ng表达式列表，用于指定需要翻译的JSON字段。",
        examples=[["$.product.name", "$.product.description", "$.features[*]"]],
    )


class XlsxWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal["xlsx"] = Field(
        ..., description="指定使用XLSX的翻译工作流。"
    )
    insert_mode: Literal["replace", "append", "prepend"] = Field(
        "replace",
        description="翻译文本的插入模式。'replace'：替换原文，'append'：附加到原文后，'prepend'：附加到原文前。",
    )
    separator: str = Field(
        "\n",
        description="当 insert_mode 为 'append' 或 'prepend' 时，用于分隔原文和译文的分隔符。",
    )
    translate_regions: Optional[List[str]] = Field(
        None,
        description="指定翻译区域列表。示例: ['Sheet1!A1:B10', 'C:D', 'E5']。如果不指定表名 (如 'C:D')，则应用于所有表。如果为 None，则翻译整个文件中的所有文本。",
        examples=[None],
    )


class DocxWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal["docx"] = Field(
        ..., description="指定使用DOCX的翻译工作流。"
    )
    insert_mode: Literal["replace", "append", "prepend"] = Field(
        "replace",
        description="翻译文本的插入模式。'replace'：替换原文，'append'：附加到原文后，'prepend'：附加到原文前。",
    )
    separator: str = Field(
        "\n",
        description="当 insert_mode 为 'append' 或 'prepend' 时，用于分隔原文和译文的分隔符。",
    )


class SrtWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal["srt"] = Field(
        ..., description="指定使用SRT字幕的翻译工作流。"
    )
    insert_mode: Literal["replace", "append", "prepend"] = Field(
        "replace",
        description="翻译文本的插入模式。'replace'：替换原文，'append'：附加到原文后，'prepend'：附加到原文前。",
    )
    separator: str = Field(
        "\n",
        description="当 insert_mode 为 'append' 或 'prepend' 时，用于分隔原文和译文的分隔符。",
    )


class EpubWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal["epub"] = Field(
        ..., description="指定使用EPUB的翻译工作流。"
    )
    insert_mode: Literal["replace", "append", "prepend"] = Field(
        "replace",
        description="翻译文本的插入模式。'replace'：替换原文，'append'：附加到原文后，'prepend'：附加到原文前。",
    )
    separator: str = Field(
        "\n",
        description="当 insert_mode 为 'append' 或 'prepend' 时，用于分隔原文和译文的分隔符。",
    )


# --- HTML WORKFLOW PARAMS START ---
class HtmlWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal["html"] = Field(
        ..., description="指定使用HTML的翻译工作流。"
    )
    insert_mode: Literal["replace", "append", "prepend"] = Field(
        "replace",
        description="翻译文本的插入模式。'replace'：替换原文，'append' :附加到原文后，'prepend'：附加到原文前。",
    )
    separator: str = Field(
        " ",
        description="当 insert_mode 为 'append' 或 'prepend' 时，用于分隔原文和译文的分隔符。",
    )


# --- HTML WORKFLOW PARAMS END ---


# --- ASS WORKFLOW PARAMS START ---
class AssWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal["ass"] = Field(
        ..., description="指定使用ASS字幕的翻译工作流。"
    )
    insert_mode: Literal["replace", "append", "prepend"] = Field(
        "replace",
        description="翻译文本的插入模式。'replace'：替换原文，'append'：附加到原文后，'prepend'：附加到原文前。",
    )
    separator: str = Field(
        "\\N",
        description="当 insert_mode 为 'append' 或 'prepend' 时，用于分隔原文和译文的分隔符。ASS格式通常使用 \\N 作为换行符。",
    )


# --- ASS WORKFLOW PARAMS END ---


# --- PPTX WORKFLOW PARAMS START ---
class PPTXWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal["pptx"] = Field(
        ..., description="指定使用PPTX的翻译工作流。"
    )
    insert_mode: Literal["replace", "append", "prepend"] = Field(
        "replace",
        description="翻译文本的插入模式。'replace'：替换原文，'append'：附加到原文后，'prepend'：附加到原文前。",
    )
    separator: str = Field(
        "\n",
        description="当 insert_mode 为 'append' 或 'prepend' 时，用于分隔原文和译文的分隔符。",
    )
    # target_cjk_font removed as per request


# --- PPTX WORKFLOW PARAMS END ---


TranslatePayload = Annotated[
    Union[
        AutoWorkflowParams,
        MarkdownWorkflowParams,
        TextWorkflowParams,
        JsonWorkflowParams,
        XlsxWorkflowParams,
        DocxWorkflowParams,
        SrtWorkflowParams,
        EpubWorkflowParams,
        HtmlWorkflowParams,
        AssWorkflowParams,
        PPTXWorkflowParams,
    ],
    Field(discriminator="workflow_type"),
]