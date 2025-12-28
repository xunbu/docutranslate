# --- 新增: 通用 Workflow 工厂函数 ---

import logging

from docutranslate.agents.glossary_agent import GlossaryAgentConfig
from docutranslate.core.schemas import TranslatePayload, MarkdownWorkflowParams, TextWorkflowParams, JsonWorkflowParams, \
    XlsxWorkflowParams, DocxWorkflowParams, SrtWorkflowParams, EpubWorkflowParams, HtmlWorkflowParams, \
    AssWorkflowParams, PPTXWorkflowParams
from docutranslate.converter.x2md.converter_docling import ConverterDoclingConfig
from docutranslate.converter.x2md.converter_mineru import ConverterMineruConfig
from docutranslate.converter.x2md.converter_mineru_deploy import ConverterMineruDeployConfig
from docutranslate.exporter.ass.ass2html_exporter import Ass2HTMLExporterConfig
from docutranslate.exporter.docx.docx2html_exporter import Docx2HTMLExporterConfig
from docutranslate.exporter.epub.epub2html_exporter import Epub2HTMLExporterConfig
from docutranslate.exporter.js.json2html_exporter import Json2HTMLExporterConfig
from docutranslate.exporter.md.md2html_exporter import MD2HTMLExporterConfig
from docutranslate.exporter.pptx.pptx2html_exporter import PPTX2HTMLExporterConfig
from docutranslate.exporter.srt.srt2html_exporter import Srt2HTMLExporterConfig
from docutranslate.exporter.txt.txt2html_exporter import TXT2HTMLExporterConfig
from docutranslate.exporter.xlsx.xlsx2html_exporter import Xlsx2HTMLExporterConfig
from docutranslate.global_values.conditional_import import DOCLING_EXIST
from docutranslate.translator.ai_translator.ass_translator import AssTranslatorConfig
from docutranslate.translator.ai_translator.docx_translator import DocxTranslatorConfig
from docutranslate.translator.ai_translator.epub_translator import EpubTranslatorConfig
from docutranslate.translator.ai_translator.html_translator import HtmlTranslatorConfig
from docutranslate.translator.ai_translator.json_translator import JsonTranslatorConfig
from docutranslate.translator.ai_translator.md_translator import MDTranslatorConfig
from docutranslate.translator.ai_translator.pptx_translator import PPTXTranslatorConfig
from docutranslate.translator.ai_translator.srt_translator import SrtTranslatorConfig
from docutranslate.translator.ai_translator.txt_translator import TXTTranslatorConfig
from docutranslate.translator.ai_translator.xlsx_translator import XlsxTranslatorConfig
from docutranslate.workflow.ass_workflow import AssWorkflowConfig, AssWorkflow
from docutranslate.workflow.base import Workflow
from docutranslate.workflow.docx_workflow import DocxWorkflowConfig, DocxWorkflow
from docutranslate.workflow.epub_workflow import EpubWorkflowConfig, EpubWorkflow
from docutranslate.workflow.html_workflow import HtmlWorkflowConfig, HtmlWorkflow
from docutranslate.workflow.json_workflow import JsonWorkflowConfig, JsonWorkflow
from docutranslate.workflow.md_based_workflow import MarkdownBasedWorkflowConfig, MarkdownBasedWorkflow
from docutranslate.workflow.pptx_workflow import PPTXWorkflowConfig, PPTXWorkflow
from docutranslate.workflow.srt_workflow import SrtWorkflowConfig, SrtWorkflow
from docutranslate.workflow.txt_workflow import TXTWorkflowConfig, TXTWorkflow
from docutranslate.workflow.xlsx_workflow import XlsxWorkflowConfig, XlsxWorkflow


def create_workflow_from_payload(payload: TranslatePayload, logger: logging.Logger = None) -> Workflow:
    """
    根据扁平化的 Payload 配置对象，构建并返回对应的 Workflow 实例。
    """
    if logger is None:
        logger = logging.getLogger("docutranslate.factory")

    # 辅助函数：构建术语表生成配置
    def build_glossary_agent_config():
        if payload.glossary_generate_enable and payload.glossary_agent_config:
            return GlossaryAgentConfig(logger=logger, **payload.glossary_agent_config.model_dump())
        return None

    # 1. Markdown Based Workflow
    if isinstance(payload, MarkdownWorkflowParams):
        translator_args = payload.model_dump(
            include={"skip_translate", "base_url", "api_key", "model_id", "to_lang", "custom_prompt",
                     "temperature", "thinking", "chunk_size", "concurrent", "glossary_dict", "timeout",
                     "retry", "system_proxy_enable", "force_json", "rpm", "tpm", "provider"},
            exclude_none=True,
        )
        translator_args["glossary_generate_enable"] = payload.glossary_generate_enable
        translator_args["glossary_agent_config"] = build_glossary_agent_config()
        translator_config = MDTranslatorConfig(**translator_args)

        converter_config = None
        if payload.convert_engine == "mineru":
            converter_config = ConverterMineruConfig(logger=logger, mineru_token=payload.mineru_token,
                                                     formula_ocr=payload.formula_ocr,
                                                     model_version=payload.model_version)
        elif payload.convert_engine == "mineru_deploy":
            converter_config = ConverterMineruDeployConfig(base_url=payload.mineru_deploy_base_url,
                                                           backend=payload.mineru_deploy_backend,
                                                           formula_enable=payload.mineru_deploy_formula_enable,
                                                           start_page_id=payload.mineru_deploy_start_page_id,
                                                           end_page_id=payload.mineru_deploy_end_page_id,
                                                           lang_list=payload.mineru_deploy_lang_list,
                                                           server_url=payload.mineru_deploy_server_url)
        elif payload.convert_engine == "docling" and DOCLING_EXIST:
            converter_config = ConverterDoclingConfig(logger=logger, code_ocr=payload.code_ocr,
                                                      formula_ocr=payload.formula_ocr)

        # 默认 CDN 开启，如果是 Python 调用可能需要允许用户覆盖，这里暂定 True
        html_exporter_config = MD2HTMLExporterConfig(cdn=True)

        workflow_config = MarkdownBasedWorkflowConfig(
            convert_engine=payload.convert_engine,
            converter_config=converter_config,
            translator_config=translator_config,
            html_exporter_config=html_exporter_config,
            logger=logger,
        )
        return MarkdownBasedWorkflow(config=workflow_config)

    # 2. Text/Json/Docx/Etc... (使用通用模式简化代码)
    # 定义映射关系：Payload类型 -> (TranslatorConfig类, WorkflowConfig类, Workflow类, ExporterConfig类)
    mapping = {
        TextWorkflowParams: (TXTTranslatorConfig, TXTWorkflowConfig, TXTWorkflow, TXT2HTMLExporterConfig),
        JsonWorkflowParams: (JsonTranslatorConfig, JsonWorkflowConfig, JsonWorkflow, Json2HTMLExporterConfig),
        XlsxWorkflowParams: (XlsxTranslatorConfig, XlsxWorkflowConfig, XlsxWorkflow, Xlsx2HTMLExporterConfig),
        DocxWorkflowParams: (DocxTranslatorConfig, DocxWorkflowConfig, DocxWorkflow, Docx2HTMLExporterConfig),
        SrtWorkflowParams: (SrtTranslatorConfig, SrtWorkflowConfig, SrtWorkflow, Srt2HTMLExporterConfig),
        EpubWorkflowParams: (EpubTranslatorConfig, EpubWorkflowConfig, EpubWorkflow, Epub2HTMLExporterConfig),
        HtmlWorkflowParams: (HtmlTranslatorConfig, HtmlWorkflowConfig, HtmlWorkflow, None),  # Html通常不需要导出配置或特殊处理
        AssWorkflowParams: (AssTranslatorConfig, AssWorkflowConfig, AssWorkflow, Ass2HTMLExporterConfig),
        PPTXWorkflowParams: (PPTXTranslatorConfig, PPTXWorkflowConfig, PPTXWorkflow, PPTX2HTMLExporterConfig),
    }

    for param_type, (TransConf, WorkConf, WorkClass, ExpConf) in mapping.items():
        if isinstance(payload, param_type):
            # 提取通用 Translator 参数
            dump_exclude = {"workflow_type"}
            # 特定类型的特殊参数需要保留，例如 json_paths, insert_mode 等
            # model_dump 会自动包含定义在 param_type 中的所有字段
            translator_args = payload.model_dump(exclude=dump_exclude, exclude_none=True)

            # 手动注入复杂对象
            translator_args["glossary_generate_enable"] = payload.glossary_generate_enable
            translator_args["glossary_agent_config"] = build_glossary_agent_config()

            # 实例化 Translator Config
            translator_config = TransConf(**translator_args)

            # 实例化 Exporter Config
            html_exporter_config = ExpConf(cdn=True) if ExpConf else None

            # 实例化 Workflow Config
            # 注意：不同的 WorkflowConfig 构造函数参数可能略有不同，这里做一个简单的适配
            if WorkClass == HtmlWorkflow:
                workflow_config = WorkConf(translator_config=translator_config, logger=logger)
            else:
                workflow_config = WorkConf(translator_config=translator_config,
                                           html_exporter_config=html_exporter_config, logger=logger)

            return WorkClass(config=workflow_config)

    raise ValueError(f"未知的 Payload 类型: {type(payload)}")