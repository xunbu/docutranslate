# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import TypeVar, Dict, Any, Optional

from docutranslate.agents.agent import AgentConfig
from docutranslate.agents.glossary_agent import GlossaryAgentConfig, GlossaryAgent
from docutranslate.glossary.glossary import Glossary
from docutranslate.ir.document import Document
from docutranslate.translator.base import Translator, TranslatorConfig


@dataclass(kw_only=True)
class AiTranslatorConfig(TranslatorConfig, AgentConfig):
    base_url: str | None = field(
        default=None,
        metadata={"description": "OpenAI兼容地址，当skip_translate为False时为必填项"},
    )
    model_id: str | None = field(
        default=None, metadata={"description": "当skip_translate为False时为必填项"}
    )
    to_lang: str = "简体中文"
    custom_prompt: str | None = None
    chunk_size: int = 3000
    glossary: Glossary | None = None
    glossary_dict: Dict[str, str] | None = None
    glossary_generate_enable: bool = False
    glossary_agent_config: GlossaryAgentConfig | None = None
    skip_translate: bool = False  # 当skip_translate为False时base_url、model_id为必填项


T = TypeVar("T", bound=Document)


class AiTranslator(Translator[T]):
    """
    翻译中间文本（原地替换），Translator不做格式转换
    """

    def __init__(self, config: AiTranslatorConfig):
        super().__init__(config=config)
        self.skip_translate = config.skip_translate


        if config.glossary:
            self.glossary = config.glossary
        elif config.glossary_dict:
            self.glossary = Glossary(glossary_dict=config.glossary_dict)
        else:
            self.glossary = Glossary()

        self.glossary_agent = None
        if not self.skip_translate and (
                config.base_url is None or config.api_key is None or config.model_id is None
        ):
            raise ValueError("skip_translate不为false时，base_url、api_key、model_id为必填项")

        if config.glossary_generate_enable:
            # 创建术语表进度回调 (20% - 30%)
            def glossary_progress_callback(current: int, total: int):
                if self.progress_tracker:
                    # 映射到 20% - 30% 区间
                    percent = 20 + int((current / total) * 10)
                    self.progress_tracker.update(
                        percent=percent,
                        message=f"正在提取术语表 ({current}/{total})"
                    )

            if config.glossary_agent_config:
                # 如果有预配置，确保传入 progress_callback
                config.glossary_agent_config.progress_callback = glossary_progress_callback
                self.glossary_agent = GlossaryAgent(config.glossary_agent_config)
            else:
                glossary_agent_config = GlossaryAgentConfig(
                    to_lang=config.to_lang,
                    base_url=config.base_url,
                    api_key=config.api_key,
                    model_id=config.model_id,
                    temperature=config.temperature,
                    top_p=config.top_p,
                    thinking=config.thinking,
                    concurrent=config.concurrent,
                    timeout=config.timeout,
                    logger=self.logger,
                    retry=config.retry,
                    system_proxy_enable=config.system_proxy_enable,
                    force_json=config.force_json,
                    rpm=config.rpm,
                    tpm=config.tpm,
                    provider=config.provider,
                    extra_body=config.extra_body,
                    progress_callback=glossary_progress_callback,
                )
                self.glossary_agent = GlossaryAgent(glossary_agent_config)

    def get_statistics(self) -> Dict[str, Any]:
        """
        收集所有agent的统计信息，包括术语表生成和翻译两个阶段的统计。

        Returns:
            Dict[str, Any]: 包含glossary、translation和total三个部分的统计信息
        """
        glossary_stats: Optional[Dict[str, Any]] = None
        translation_stats: Optional[Dict[str, Any]] = None

        if self.glossary_agent:
            glossary_stats = self.glossary_agent.get_full_stats()

        if hasattr(self, 'translate_agent') and self.translate_agent:
            translation_stats = self.translate_agent.get_full_stats()

        # 计算汇总统计
        total_stats = self._calculate_total_stats(glossary_stats, translation_stats)

        return {
            "glossary": glossary_stats,
            "translation": translation_stats,
            "total": total_stats
        }

    def _calculate_total_stats(
        self,
        glossary_stats: Optional[Dict[str, Any]],
        translation_stats: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        计算汇总统计信息。

        Args:
            glossary_stats: 术语表生成阶段的统计
            translation_stats: 翻译阶段的统计

        Returns:
            Dict[str, Any]: 汇总后的统计信息
        """
        total_input = 0
        total_cached = 0
        total_output = 0
        total_reasoning = 0
        total_tokens = 0
        total_requests = 0
        total_unresolved = 0

        if glossary_stats:
            total_input += glossary_stats.get("input_tokens", 0)
            total_cached += glossary_stats.get("cached_tokens", 0)
            total_output += glossary_stats.get("output_tokens", 0)
            total_reasoning += glossary_stats.get("reasoning_tokens", 0)
            total_tokens += glossary_stats.get("total_tokens", 0)
            total_requests += glossary_stats.get("request_count", 0)
            total_unresolved += glossary_stats.get("unresolved_errors", 0)

        if translation_stats:
            total_input += translation_stats.get("input_tokens", 0)
            total_cached += translation_stats.get("cached_tokens", 0)
            total_output += translation_stats.get("output_tokens", 0)
            total_reasoning += translation_stats.get("reasoning_tokens", 0)
            total_tokens += translation_stats.get("total_tokens", 0)
            total_requests += translation_stats.get("request_count", 0)
            total_unresolved += translation_stats.get("unresolved_errors", 0)

        total_error_rate = total_unresolved / total_requests if total_requests > 0 else 0.0

        return {
            "input_tokens": total_input,
            "cached_tokens": total_cached,
            "output_tokens": total_output,
            "reasoning_tokens": total_reasoning,
            "total_tokens": total_tokens,
            "request_count": total_requests,
            "unresolved_errors": total_unresolved,
            "unresolved_error_rate": total_error_rate
        }

    @abstractmethod
    def translate(self, document: T) -> Document:
        ...

    @abstractmethod
    async def translate_async(self, document: T) -> Document:
        ...