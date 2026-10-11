import json
import re

import pytest

from docutranslate.agents.agent import AgentResultError, PartialAgentResultError
from docutranslate.agents.segments_agent import (
    SegmentsTranslateAgent,
    SegmentsTranslateAgentConfig,
    _build_system_prompt,
    generate_prompt,
)


def test_few_shot_examples_in_system_prompt_are_valid_json():
    """提示词里的示例 JSON 必须能解析——引号没转义会教坏模型（回归）。"""
    prompt = _build_system_prompt("简体中文")
    blocks = re.findall(r"Output:\s*```json\s*(.*?)\s*```", prompt, re.DOTALL)
    assert blocks, "系统提示词里应当有示例输出"
    for block in blocks:
        parsed = json.loads(block)
        assert isinstance(parsed, list) and parsed
        for item in parsed:
            assert isinstance(item.get("id"), str)
            assert isinstance(item.get("t"), str)


@pytest.fixture
def agent():
    return SegmentsTranslateAgent(SegmentsTranslateAgentConfig(
        base_url="https://example.invalid/v1", model_id="test", to_lang="zh",
    ))


@pytest.mark.parametrize("response", [
    [{"id": "1", "t": "译文一"}, {"id": 0, "t": "译文零"}],
    [{"id": 1, "t": "译文一"}, {"id": 0, "t": "译文零"}],
    [[{"id": "1", "t": "译文一"}], [{"id": 0, "t": "译文零"}]],
    {"1": "译文一", "0": "译文零"},
])
def test_response_ids_match_original_string_keys(agent, response):
    prompt = generate_prompt(json.dumps({"0": "zero", "1": "one"}), "zh")

    result = agent._result_handler(json.dumps(response), prompt, agent.logger)

    assert result == {"0": "译文零", "1": "译文一"}


def test_numeric_ids_still_detect_untranslated_response(agent):
    prompt = generate_prompt(json.dumps({"0": "zero", "1": "one"}), "zh")
    response = [{"id": "1", "t": "one"}, {"id": 0, "t": "zero"}]

    with pytest.raises(AgentResultError, match="翻译结果与原文完全相同"):
        agent._result_handler(json.dumps(response), prompt, agent.logger)


def test_missing_id_preserves_successful_numeric_id_translation(agent):
    prompt = generate_prompt(json.dumps({"0": "zero", "1": "one"}), "zh")

    with pytest.raises(PartialAgentResultError) as exc_info:
        agent._result_handler('[{"id": 0, "t": "译文零"}]', prompt, agent.logger)

    assert exc_info.value.partial_result == {"0": "译文零", "1": "one"}


@pytest.mark.parametrize("first_id, repeated_id", [(0, "0"), ("0", 0)])
def test_continuation_deduplicates_numeric_and_string_ids(agent, first_id, repeated_id):
    accumulated = [{"id": first_id, "t": "保留的译文"}]
    additional = [{"id": repeated_id, "t": "重复译文"}, {"id": 1, "t": "新译文"}]

    merged = json.loads(agent.merge_continue_result(
        json.dumps(accumulated), json.dumps(additional),
    ))

    assert [item["t"] for item in merged] == ["保留的译文", "新译文"]
