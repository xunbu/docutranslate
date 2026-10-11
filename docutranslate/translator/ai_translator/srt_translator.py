# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
from dataclasses import dataclass
from datetime import timedelta
from typing import Self, Literal

import charset_normalizer
import srt  # 导入srt库来处理字幕文件

from docutranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from docutranslate.ir.document import Document
from docutranslate.logger import global_logger
from docutranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator


@dataclass
class SrtTranslatorConfig(AiTranslatorConfig):
    insert_mode: Literal["replace", "append", "prepend"] = "replace"
    separator: str = "\n"


# 注意：这里刻意**不**为 SRT 写死「逐条翻译、不得合并、不得留空」这类规则。
#
# 用 deepseek-chat 在英译中语料上实测（74 条真实字幕 × 5 轮，独立评审盲评）：
# 真实字幕（句子自然跨条）本来就不会产出空译文，加不加这类规则盲评排序打平；
# 它只在「逐词断句」这类畸形输入上把空译文率从 25% 降到 1%，代价是整句习语被
# 拆到多条时退化成直译（kicked the bucket -> 他踢了/那个/桶）。
# 而「空译文 = 失败」这个前提本身也不成立：它常常表示该段文字被并入了邻条的
# 译文，属合法输出。因此合并与否交给模型判断，空的就如实写回空（时间窗照旧保留），
# 有特殊需要时由调用方通过 custom_prompt 自行追加策略。


def _srt_structural_skip_reason(subtitle: srt.Subtitle) -> str | None:
    """返回该条目时间轴无法写入 SRT 的原因；可以写入时返回 ``None``。

    只有**时间轴本身无法表示**时才判定不写入。内容为空不是丢条理由：它通常是
    模型合并相邻段落的合法结果，条目与时间窗都必须保留。

    ``srt.compose`` 默认以 ``reindex=True`` 调用 ``sort_and_reindex(skip=True)``，
    那个函数会额外丢弃「内容为空/只有空白」「起始时间为负」「起始时间不早于结束
    时间」的条目并重排其余编号，丢条因此既不报错也不留痕。这里把判定收回自己手里，
    是为了让「哪些条目被移除」由本模块显式决定并逐条报告。
    """
    if subtitle.start < timedelta(0):
        return "起始时间为负"
    if subtitle.start >= subtitle.end:
        return "起始时间不早于结束时间"
    return None


def _summarize_cue_indices(indices: list[int], limit: int = 10) -> str:
    """把可能很长的条目编号列表压缩成一行日志。"""
    shown = ", ".join(f"#{index}" for index in indices[:limit])
    if len(indices) > limit:
        shown += f" ...（共 {len(indices)} 条）"
    return shown


class SrtTranslator(AiTranslator):
    """
    一个用于翻译 SRT (.srt) 字幕文件的翻译器。
    它会提取每个字幕块的文本内容，进行翻译，然后根据配置将译文写回。
    """

    def __init__(self, config: SrtTranslatorConfig):
        super().__init__(config=config)
        self.chunk_size = config.chunk_size
        self.translate_agent = None
        self.total_chunks = 0
        glossary_dict = self.glossary.glossary_dict if self.glossary else None
        if not self.skip_translate:
            # 创建进度回调函数
            def progress_callback(current: int, total: int):
                self.total_chunks = total
                if self.progress_tracker:
                    # 计算进度百分比 (30% - 90% 区间)
                    percent = 30 + int((current / total) * 60)
                    self.progress_tracker.update(
                        percent=percent,
                        message=f"正在翻译 ({current}/{total})"
                    )

            agent_config = SegmentsTranslateAgentConfig(
                custom_prompt=config.custom_prompt,
                to_lang=config.to_lang,
                base_url=config.base_url,
                api_key=config.api_key,
                model_id=config.model_id,
                temperature=config.temperature,
                top_p=config.top_p,
                thinking=config.thinking,
                concurrent=config.concurrent,
                timeout=config.timeout,
                connect_timeout=config.connect_timeout,
                read_timeout=config.read_timeout,
                write_timeout=config.write_timeout,
                pool_timeout=config.pool_timeout,
                streaming=config.streaming,
                stream_idle_timeout=config.stream_idle_timeout,
                non_stream_timeout=config.non_stream_timeout,
                logger=self.logger,
                glossary_dict=glossary_dict,
                retry=config.retry,
                system_proxy_enable=config.system_proxy_enable,
                force_json=config.force_json,
                rpm=config.rpm,
                tpm=config.tpm,
                provider=config.provider,
                extra_body=config.extra_body,
                progress_callback=progress_callback,
            )
            self.translate_agent = SegmentsTranslateAgent(agent_config)
        self.insert_mode = config.insert_mode
        self.separator = config.separator

    def _pre_translate(self, document: Document):
        """
        预处理步骤：解析SRT文件，提取所有字幕文本。

        Returns:
            tuple: (解析后的字幕对象列表, 待翻译的原文文本列表)
        """
        # 使用 charset_normalizer 自动检测编码
        result = charset_normalizer.from_bytes(document.content).best()
        if result is None:
            self.logger.error("无法检测SRT文件编码")
            return [], []
        detected_encoding = result.encoding
        try:
            srt_content = document.content.decode(detected_encoding)
        except (UnicodeDecodeError, AttributeError) as e:
            self.logger.error(f"无法使用检测到的编码 {detected_encoding} 解码文件: {e}")
            return [], []

        # 使用 srt 库解析内容
        try:
            subtitles = list(srt.parse(srt_content))
        except srt.SRTParseError as e:
            self.logger.error(f"解析SRT文件失败: {e}")
            return [], []

        # 提取所有原文文本，准备进行批量翻译
        original_texts = [sub.content for sub in subtitles]

        return subtitles, original_texts

    def _after_translate(self, subtitles: list[srt.Subtitle], translated_texts: list[str],
                         original_texts: list[str]) -> bytes:
        """
        翻译后处理步骤：将译文根据配置模式写回字幕对象，并生成新的SRT文件内容。

        两条原则：

        1. **不伪造内容。** 空译文不是翻译失败的证据：模型按提示词约定合并相邻
           段落时，译文会落在其中一条上，相邻那条就是空的。这里原样写回空内容，
           不拿源文顶替（那会把「已翻译、只是并入了邻条」显示成「没有翻译」），
           也不去猜它被并入了哪一条。
        2. **不静默丢条。** ``srt.compose`` 默认经 ``sort_and_reindex(skip=True)``
           丢弃空内容条目并重排编号，所以这里自己排序、自己重编号，再以
           ``compose(reindex=False)`` 序列化。只有时间轴本身无法表示的条目才会被
           移除，而且逐条报告。

        保证的是**条目与时间窗完整**，不是文本逐字保真——``srt.compose(strict=True)``
        仍会按库规则整理内容里的空行。

        Returns:
            bytes: 新的SRT文件内容的字节流。
        """
        # 后处理只依赖 insert_mode/separator，允许在未走 __init__ 的实例上调用
        logger = getattr(self, "logger", None) or global_logger

        cue_count = len(subtitles)
        if len(translated_texts) != cue_count:
            logger.error(
                "译文条目数与字幕条目数不一致（译文 %d 条 / 字幕 %d 条），缺少译文的条目按空内容保留。",
                len(translated_texts), cue_count,
            )

        insert_mode = self.insert_mode
        if insert_mode not in ("replace", "append", "prepend"):
            logger.error(f"不正确的SrtTranslatorConfig参数: insert_mode='{insert_mode}'")
            # 默认回退到替换模式，避免程序中断
            insert_mode = "replace"

        output_subtitles: list[srt.Subtitle] = []
        untranslated_indices: list[int] = []
        dropped: list[tuple[int, str]] = []

        for i, sub in enumerate(subtitles):
            original_text = original_texts[i] if i < len(original_texts) else sub.content
            original_text = "" if original_text is None else str(original_text)
            translated_text = translated_texts[i] if i < len(translated_texts) else ""
            translated_text = "" if translated_text is None else str(translated_text)
            cue_number = sub.index if sub.index is not None else i + 1

            # 根据插入模式计算该条目的最终内容；空译文原样保留，不做替换
            if insert_mode == "replace":
                content = translated_text
            elif insert_mode == "append":
                # strip() 避免在原文和译文间产生多余的空白；空译文不留悬空分隔符
                content = original_text.strip() + self.separator + translated_text.strip() \
                    if translated_text.strip() else original_text
            else:
                content = translated_text.strip() + self.separator + original_text.strip() \
                    if translated_text.strip() else original_text

            if not translated_text.strip():
                untranslated_indices.append(cue_number)

            reason = _srt_structural_skip_reason(sub)
            if reason is not None:
                dropped.append((cue_number, reason))
                continue

            sub.content = content
            output_subtitles.append(sub)

        if untranslated_indices:
            logger.warning(
                "以下字幕段落译文为空（相邻段落被合并翻译时会出现），已按空内容保留其时间窗（%d 条）：%s",
                len(untranslated_indices), _summarize_cue_indices(untranslated_indices),
            )
        if dropped:
            detail = "; ".join(f"#{index}（{reason}）" for index, reason in dropped[:10])
            if len(dropped) > 10:
                detail += f" ...（共 {len(dropped)} 条）"
            logger.warning(
                "以下字幕条目时间轴无效，无法写入SRT（%d 条）：%s",
                len(dropped), detail,
            )

        # 自己排序并重编号，再以 reindex=False 序列化：绕开 srt.compose 默认的
        # sort_and_reindex(skip=True)（它会丢掉空内容条目并重排编号）。按时间排序
        # 同时避开了库内以 (start, index) 比较时 index=None 抛出的 TypeError。
        ordered = sorted(output_subtitles, key=lambda item: (item.start, item.end))
        composed_subtitles = [srt.Subtitle(**vars(item)) for item in ordered]
        for position, item in enumerate(composed_subtitles, start=1):
            item.index = position

        new_srt_content_str = srt.compose(composed_subtitles, reindex=False)

        # 导出后核对：逐条比对回读出来的时间窗，而不只是比条数——只比条数会被
        # 「丢一条 + 译文里注入一条」相互抵消。回读只是诊断，译文里可能出现超长
        # 数字（CPython int 转换上限）等库边界，任何异常都不能反过来让已经完成
        # 的翻译整体失败。
        try:
            reparsed = list(srt.parse(new_srt_content_str)) if new_srt_content_str else []
        except Exception as e:  # noqa: BLE001 - 诊断步骤，不应中断导出
            logger.error("SRT 导出结果无法回读校验，文件可能不符合SRT规范: %s", e)
        else:
            written = sorted((sub.start, sub.end) for sub in composed_subtitles)
            read_back = sorted((sub.start, sub.end) for sub in reparsed)
            if read_back != written:
                logger.error(
                    "SRT 导出结果与预期时间窗不一致：预期写入 %d 条，回读 %d 条。",
                    len(written), len(read_back),
                )
            elif len(written) != cue_count:
                logger.error(
                    "SRT 导出结果不完整：原始 %d 条，实际写入 %d 条。",
                    cue_count, len(written),
                )

        # 返回UTF-8编码的字节流
        return new_srt_content_str.encode('utf-8')

    def translate(self, document: Document) -> Self:
        """
        同步翻译SRT文档。
        """
        subtitles, original_texts = self._pre_translate(document)

        if not original_texts:
            self.logger.info("\n文件中没有找到需要翻译的字幕内容。")
            return self
        if self.glossary_agent:
            # 1. 获取增量
            glossary_dict_gen = self.glossary_agent.send_segments(original_texts, self.chunk_size)

            # 2. 在 Translator 层统一合并 (SSOT)
            if self.glossary:
                self.glossary.update(glossary_dict_gen)

            # 3. 将合并后的【完整字典】传给 Agent
            if self.translate_agent and self.glossary:
                self.translate_agent.update_glossary_dict(self.glossary.glossary_dict)
        # --- 步骤 2: 调用翻译Agent ---
        if self.translate_agent:
            translated_texts = self.translate_agent.send_segments(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts
        # --- 步骤 3: 后处理并更新文档内容 ---
        document.content = self._after_translate(subtitles, translated_texts, original_texts)
        return self

    async def translate_async(self, document: Document) -> Self:
        """
        异步翻译SRT文档。
        """
        # I/O密集型操作在线程中运行
        subtitles, original_texts = await asyncio.to_thread(self._pre_translate, document)

        if not original_texts:
            self.logger.info("\n文件中没有找到需要翻译的字幕内容。")
            return self

        if self.glossary_agent:
            # 1. 获取增量
            glossary_dict_gen = await self.glossary_agent.send_segments_async(original_texts, self.chunk_size)

            # 2. 在 Translator 层统一合并 (SSOT)
            if self.glossary:
                self.glossary.update(glossary_dict_gen)

            # 3. 将合并后的【完整字典】传给 Agent
            if self.translate_agent and self.glossary:
                self.translate_agent.update_glossary_dict(self.glossary.glossary_dict)

        # --- 步骤 2: 调用翻译Agent (异步) ---
        if self.translate_agent:
            translated_texts = await self.translate_agent.send_segments_async(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts
        # --- 步骤 3: 后处理并更新文档内容 (I/O密集型) ---
        document.content = await asyncio.to_thread(
            self._after_translate, subtitles, translated_texts, original_texts
        )
        return self
