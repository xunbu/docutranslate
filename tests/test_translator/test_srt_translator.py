"""SRT 翻译器的完整性回归测试。

背景（v1.7.9 起存在）：``SrtTranslator._after_translate`` 直接把译文写回
``sub.content`` 再调用 ``srt.compose(subtitles)``。``compose`` 默认经
``sort_and_reindex(skip=True)`` 丢弃内容为空的条目并重排其余编号，于是空译文
会让对应的字幕时间窗静默消失（3 条进、2 条出），既不报错也不留痕。
"""
import asyncio
import json
import logging
import sys
from datetime import timedelta

import httpx
import pytest
import srt

from docutranslate.agents.segments_agent import get_original_segments
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.srt_translator import (
    SrtTranslator,
    SrtTranslatorConfig,
)

LOGGER_NAME = "TranslaterLogger"


def _make_translator(insert_mode: str = "replace", separator: str = "\n") -> SrtTranslator:
    """只构造后处理所需状态，聚焦 _after_translate 的行为。"""
    translator = SrtTranslator.__new__(SrtTranslator)
    translator.insert_mode = insert_mode
    translator.separator = separator
    return translator


def _cues(count: int) -> list[srt.Subtitle]:
    return [
        srt.Subtitle(
            index=i,
            start=timedelta(seconds=2 * i),
            end=timedelta(seconds=2 * i + 1),
            content=f"English cue {i}",
        )
        for i in range(1, count + 1)
    ]


def _windows(cues) -> list[tuple[float, float]]:
    return [(c.start.total_seconds(), c.end.total_seconds()) for c in cues]


def _translate(insert_mode: str, translated: list[str], count: int = 3):
    translator = _make_translator(insert_mode)
    subtitles = _cues(count)
    original = [c.content for c in subtitles]
    output = translator._after_translate(subtitles, translated, original).decode("utf-8")
    return list(srt.parse(output))


def _srt_document(count: int = 3) -> Document:
    return Document(suffix=".srt", content=srt.compose(_cues(count)).encode("utf-8"), stem="subs")


# --------------------------------------------------------------------------
# 报告中的最小复现
# --------------------------------------------------------------------------

def test_empty_translation_does_not_drop_cue():
    """空译文不能静默丢条：原报告的 3 条进、2 条出。

    空译文按原样写回空内容——它通常意味着这段文字被并入了邻条的译文，
    不能拿源文顶替（那会把「已翻译」显示成「没翻译」）。
    """
    result = _translate("replace", ["字幕一", "", "字幕三"])

    assert len(result) == 3, "空译文导致字幕条目被丢弃"
    assert _windows(result) == [(2, 3), (4, 5), (6, 7)], "时间窗缺失或被重排"
    assert [sub.content for sub in result] == ["字幕一", "", "字幕三"]
    assert [sub.index for sub in result] == [1, 2, 3]


def test_whitespace_only_translation_does_not_drop_cue():
    """只有空白字符的译文同样不能丢条（srt 库按 strip() 判定空内容）。"""
    result = _translate("replace", ["字幕一", "   \n  ", "字幕三"])

    assert len(result) == 3
    assert _windows(result) == [(2, 3), (4, 5), (6, 7)]
    assert result[1].content.strip() == ""


def test_all_empty_translations_keep_every_window():
    result = _translate("replace", ["", "", ""])

    assert len(result) == 3
    assert _windows(result) == [(2, 3), (4, 5), (6, 7)]
    assert [sub.content for sub in result] == ["", "", ""]


def test_normal_translation_preserves_count_and_windows():
    """正常译文必须保留条数与时间窗。"""
    result = _translate("replace", ["字幕一", "字幕二", "字幕三"])

    assert len(result) == 3
    assert _windows(result) == [(2, 3), (4, 5), (6, 7)]
    assert [sub.content for sub in result] == ["字幕一", "字幕二", "字幕三"]


@pytest.mark.parametrize("insert_mode", ["append", "prepend"])
def test_append_and_prepend_keep_cue_count(insert_mode):
    result = _translate(insert_mode, ["字幕一", "", "字幕三"])

    assert len(result) == 3
    assert _windows(result) == [(2, 3), (4, 5), (6, 7)]
    # 空译文不应留下悬空分隔符
    assert result[1].content == "English cue 2"


def test_separator_is_not_left_dangling_in_append_mode():
    result = _translate("append", ["字幕一", "   ", "字幕三"])

    assert [sub.content for sub in result] == [
        "English cue 1\n字幕一", "English cue 2", "English cue 3\n字幕三",
    ]


# --------------------------------------------------------------------------
# 译文列表长度校验
# --------------------------------------------------------------------------

def test_short_translation_list_keeps_every_window(caplog):
    """译文条目少于字幕条目时不得抛裸 IndexError，缺译文的条目按空内容保留。"""
    with caplog.at_level(logging.ERROR, logger=LOGGER_NAME):
        result = _translate("replace", ["字幕一", "字幕二"])

    assert len(result) == 3
    assert [sub.content for sub in result] == ["字幕一", "字幕二", ""]
    assert "译文条目数与字幕条目数不一致" in caplog.text


def test_long_translation_list_is_reported(caplog):
    with caplog.at_level(logging.ERROR, logger=LOGGER_NAME):
        result = _translate("replace", ["字幕一", "字幕二", "字幕三", "多余"])

    assert len(result) == 3
    assert [sub.content for sub in result] == ["字幕一", "字幕二", "字幕三"]
    assert "译文条目数与字幕条目数不一致" in caplog.text


# --------------------------------------------------------------------------
# 可观测性：不再无声丢条
# --------------------------------------------------------------------------

def test_untranslated_cues_are_reported(caplog):
    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        _translate("replace", ["字幕一", "", "字幕三"])

    assert "译文为空" in caplog.text
    assert "已按空内容保留其时间窗" in caplog.text
    assert "#2" in caplog.text


def test_invalid_time_window_is_dropped_but_reported(caplog):
    """时间轴本身无效的条目仍无法写入，但必须留下明确记录。"""
    translator = _make_translator()
    subtitles = _cues(3)
    subtitles[1].end = subtitles[1].start  # start >= end
    original = [c.content for c in subtitles]

    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        output = translator._after_translate(
            subtitles, ["字幕一", "字幕二", "字幕三"], original
        ).decode("utf-8")

    result = list(srt.parse(output))
    assert len(result) == 2
    assert "时间轴无效" in caplog.text and "#2" in caplog.text
    # 与原始条目数核对后必须明确报告结果不完整
    assert "SRT 导出结果不完整：原始 3 条，实际写入 2 条" in caplog.text


def test_blank_source_cue_is_preserved_as_empty(caplog):
    """源文本来就没有文字时，条目与时间窗仍必须保留，只是内容为空。"""
    translator = _make_translator()
    subtitles = _cues(3)
    subtitles[1].content = ""
    original = [c.content for c in subtitles]

    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        output = translator._after_translate(
            subtitles, ["字幕一", "", "字幕三"], original
        ).decode("utf-8")

    result = list(srt.parse(output))
    assert len(result) == 3
    assert _windows(result) == [(2, 3), (4, 5), (6, 7)]
    assert [sub.content for sub in result] == ["字幕一", "", "字幕三"]
    assert "无法写入SRT" not in caplog.text
    assert "SRT 导出结果不完整" not in caplog.text


def test_complete_result_does_not_warn_about_incompleteness(caplog):
    """全部条目正常写入时不应误报结果不完整。"""
    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        result = _translate("replace", ["字幕一", "字幕二", "字幕三"])

    assert len(result) == 3
    # 断言真实日志文本，避免断言一个永远不会出现的字符串
    assert "SRT 导出结果不完整" not in caplog.text
    assert "SRT 导出结果与预期时间窗不一致" not in caplog.text
    assert "无法回读校验" not in caplog.text


# --------------------------------------------------------------------------
# 回读校验的对立面：既不能漏报，也不能误伤
# --------------------------------------------------------------------------

INJECTED_BLOCK = "中文A\n2\n00:00:09,000 --> 00:00:10,000\n中文B"


def test_compensating_errors_are_detected_by_window_comparison(caplog):
    """丢一条 + 译文注入一条时条数相同，只比条数会漏报，必须比时间窗。"""
    translator = _make_translator()
    subtitles = _cues(2)
    subtitles[1].end = subtitles[1].start  # 第二条时间轴无效 -> 被移除
    original = [c.content for c in subtitles]

    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        output = translator._after_translate(subtitles, [INJECTED_BLOCK, "乙"], original)

    reparsed = list(srt.parse(output.decode("utf-8")))
    # 写入 1 条、回读 2 条：4-5s 真窗口丢失，9-10s 是译文注入的伪条目
    assert len(reparsed) == 2
    assert [(p.start.total_seconds(), p.end.total_seconds()) for p in reparsed] == [(2, 3), (9, 10)]
    assert "SRT 导出结果与预期时间窗不一致" in caplog.text


def test_huge_digit_translation_does_not_break_export(caplog):
    """译文含超长数字时 srt.parse 会抛 ValueError（int 转换上限），校验不能中断导出。"""
    limit = sys.get_int_max_str_digits()
    if limit == 0:
        pytest.skip("解释器未限制整数/字符串转换位数")
    huge = "9" * (limit + 100)
    tricky = f"a\n{huge}\n00:00:01,000 --> 00:00:02,000"

    translator = _make_translator()
    subtitles = _cues(1)
    original = [c.content for c in subtitles]

    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        output = translator._after_translate(subtitles, [tricky], original)

    assert isinstance(output, bytes)
    assert huge in output.decode("utf-8")
    assert "无法回读校验" in caplog.text


# --------------------------------------------------------------------------
# 边界输入
# --------------------------------------------------------------------------

@pytest.mark.parametrize("separator", ["", "<br>", "\r\n"])
def test_custom_separator_is_respected(separator):
    translator = _make_translator("append", separator)
    subtitles = _cues(2)
    original = [c.content for c in subtitles]

    output = translator._after_translate(subtitles, ["一", "二"], original).decode("utf-8")
    result = list(srt.parse(output))

    assert len(result) == 2
    # srt.parse 读回时会把 CRLF 归一化为 LF
    assert result[0].content == f"English cue 1{separator}一".replace("\r\n", "\n")


def test_none_and_non_str_translations_are_coerced(caplog):
    """None/非字符串译文按空内容处理，不回填原文，也不崩溃。"""
    translator = _make_translator()
    subtitles = _cues(2)
    original = [c.content for c in subtitles]

    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        output = translator._after_translate(subtitles, [None, 123], original).decode("utf-8")

    result = list(srt.parse(output))
    assert len(result) == 2
    assert result[0].content == ""  # None 视为空译文
    assert result[1].content == "123"


def test_crlf_input_round_trips():
    content = srt.compose(_cues(3)).replace("\n", "\r\n").encode("utf-8")
    document = Document(suffix=".srt", content=content, stem="subs")

    SrtTranslator(SrtTranslatorConfig(skip_translate=True)).translate(document)

    result = list(srt.parse(document.content.decode("utf-8")))
    assert _windows(result) == [(2, 3), (4, 5), (6, 7)]


def test_unnumbered_blocks_are_renumbered():
    text = ("00:00:02,000 --> 00:00:03,000\n甲\n\n"
            "00:00:04,000 --> 00:00:05,000\n乙\n\n")
    subtitles = list(srt.parse(text))
    assert all(sub.index is None for sub in subtitles)
    original = [c.content for c in subtitles]

    output = _make_translator()._after_translate(subtitles, ["A", "B"], original)
    result = list(srt.parse(output.decode("utf-8")))

    assert [sub.index for sub in result] == [1, 2]
    assert [sub.content for sub in result] == ["A", "B"]


def test_invalid_insert_mode_falls_back_to_replace(caplog):
    with caplog.at_level(logging.ERROR, logger=LOGGER_NAME):
        result = _translate("bogus", ["字幕一", "字幕二", "字幕三"])

    assert [sub.content for sub in result] == ["字幕一", "字幕二", "字幕三"]
    assert caplog.text.count("不正确的SrtTranslatorConfig参数") == 1


# --------------------------------------------------------------------------
# SRT 专用提示词：只作用于 SRT、必须很短、不能顶掉用户自定义提示词
# --------------------------------------------------------------------------

def _agent_prompt(**config_kwargs) -> str:
    translator = SrtTranslator(SrtTranslatorConfig(
        base_url="https://example.invalid/v1", api_key="test", model_id="test",
        to_lang="简体中文", **config_kwargs,
    ))
    return translator.translate_agent.system_prompt


def test_srt_injects_no_extra_prompt_rules():
    """不给 SRT 写死「逐条翻译/不得合并」这类策略：合并与否交给模型。

    实测（真实字幕盲评）这类规则在正常字幕上买不到任何收益，却会让整句习语被
    拆到多条时退化成直译，所以只透传用户自己的 custom_prompt。
    """
    prompt = _agent_prompt(custom_prompt="术语：GPU 译为图形处理器")
    assert "术语：GPU 译为图形处理器" in prompt
    for banned in ("不得合并", "逐条翻译", "不许留空"):
        assert banned not in prompt


def test_user_custom_prompt_is_not_modified():
    assert "我的自定义规则" in _agent_prompt(custom_prompt="我的自定义规则")


def test_skip_translate_builds_no_agent():
    translator = SrtTranslator(SrtTranslatorConfig(skip_translate=True))
    assert translator.translate_agent is None


# --------------------------------------------------------------------------
# 端到端：模型按提示词约定返回空译文（真实 translate 链路）
# --------------------------------------------------------------------------

def _mock_response(request):
    payload = json.loads(request.content)
    originals = json.loads(get_original_segments(payload["messages"][-1]["content"]))
    assert originals == {"0": "English cue 1", "1": "English cue 2", "2": "English cue 3"}
    return httpx.Response(200, json={
        "choices": [{"message": {"content": json.dumps([
            {"id": "0", "t": "字幕一"},
            {"id": "1", "t": ""},  # 提示词允许：相邻段落合并后留空值
            {"id": "2", "t": "字幕三"},
        ])}, "finish_reason": "stop"}],
    })


@pytest.mark.parametrize("use_async", [False, True])
def test_translate_end_to_end_keeps_every_window(monkeypatch, use_async):
    document = _srt_document(3)

    async def handler(request):
        return _mock_response(request)

    async_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: async_client(
        **{**kwargs, "transport": httpx.MockTransport(handler)},
    ))
    translator = SrtTranslator(SrtTranslatorConfig(
        base_url="https://example.invalid/v1", api_key="test", model_id="test",
        streaming=False, retry=0,
    ))

    if use_async:
        asyncio.run(translator.translate_async(document))
    else:
        translator.translate(document)

    result = list(srt.parse(document.content.decode("utf-8")))
    assert len(result) == 3, "模型返回空译文时字幕条目被静默删除"
    assert _windows(result) == [(2, 3), (4, 5), (6, 7)]
    assert [sub.content for sub in result] == ["字幕一", "", "字幕三"]


# --------------------------------------------------------------------------
# 回读校验本身不能把已经完成的翻译变成失败
# --------------------------------------------------------------------------

TRICKY_TRANSLATION = "a\n1\n1:2:3"  # 合成后无法被 srt.parse 回读


def test_output_that_cannot_be_reparsed_does_not_raise(caplog):
    """译文含形如编号/时间戳的行时，条数核对不能抛出异常。"""
    translator = _make_translator()
    subtitles = _cues(1)
    original = [c.content for c in subtitles]

    with caplog.at_level(logging.ERROR, logger=LOGGER_NAME):
        output = translator._after_translate(subtitles, [TRICKY_TRANSLATION], original)

    assert isinstance(output, bytes)
    assert TRICKY_TRANSLATION in output.decode("utf-8")
    assert "无法回读校验" in caplog.text


@pytest.mark.parametrize("use_async", [False, True])
def test_translate_survives_output_that_breaks_reparse(monkeypatch, use_async):
    """回归：条数核对曾让这类模型输出导致整份文档翻译失败并丢弃结果。"""
    document = _srt_document(1)
    baseline = document.content

    async def handler(request):
        return httpx.Response(200, json={
            "choices": [{"message": {"content": json.dumps([
                {"id": "0", "t": TRICKY_TRANSLATION},
            ])}, "finish_reason": "stop"}],
        })

    async_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: async_client(
        **{**kwargs, "transport": httpx.MockTransport(handler)},
    ))
    translator = SrtTranslator(SrtTranslatorConfig(
        base_url="https://example.invalid/v1", api_key="test", model_id="test",
        streaming=False, retry=0,
    ))

    if use_async:
        asyncio.run(translator.translate_async(document))
    else:
        translator.translate(document)

    assert document.content != baseline, "翻译结果被丢弃"
    assert TRICKY_TRANSLATION in document.content.decode("utf-8")
