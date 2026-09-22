import ast
import asyncio
import inspect
from pathlib import Path

import pytest
from pydantic import TypeAdapter

import docutranslate.sdk as sdk_module
from docutranslate.agents.agent import Agent, AgentConfig
from docutranslate.agents.glossary_agent import (
    GlossaryAgent,
    GlossaryAgentConfig,
    generate_prompt as generate_glossary_prompt,
)
from docutranslate.agents.markdown_agent import (
    MDTranslateAgent,
    MDTranslateAgentConfig,
    generate_prompt as generate_markdown_prompt,
)
from docutranslate.agents.segments_agent import (
    SegmentsTranslateAgent,
    SegmentsTranslateAgentConfig,
    generate_prompt as generate_segments_prompt,
)
from docutranslate.core.schemas import (
    BaseWorkflowParams,
    DocxWorkflowParams,
    TranslatePayload,
    XlsxWorkflowParams,
)
from docutranslate.sdk import Client
from docutranslate.server.core import TranslationService
from docutranslate.translator.ai_translator.txt_translator import (
    TXTTranslator,
    TXTTranslatorConfig,
)


SDK_INHERITED_DEFAULT_FIELDS = {
    "insert_mode",
    "separator",
    "segment_mode",
    "convert_engine",
    "mineru_token",
    "md2docx_engine",
    "model_version",
    "formula_ocr",
    "mineru_language",
    "mineru_deploy_base_url",
    "mineru_deploy_backend",
    "mineru_deploy_effort",
    "mineru_deploy_parse_method",
    "mineru_deploy_formula_enable",
    "mineru_deploy_table_enable",
    "mineru_deploy_image_analysis",
    "mineru_deploy_start_page_id",
    "mineru_deploy_end_page_id",
    "mineru_deploy_lang_list",
    "mineru_deploy_server_url",
}

STREAM_POLICY_FIELDS = {
    "streaming",
    "stream_idle_timeout",
    "non_stream_timeout",
}


@pytest.mark.parametrize("provider", ["mimo", "litellm"])
def test_new_providers_are_accepted_by_public_workflow_schema(provider):
    params = BaseWorkflowParams(skip_translate=True, provider=provider)

    assert params.provider == provider


def test_sdk_sync_and_async_signatures_inherit_workflow_defaults():
    sync_params = inspect.signature(Client.translate).parameters
    async_params = inspect.signature(Client.translate_async).parameters

    for field_name in SDK_INHERITED_DEFAULT_FIELDS:
        assert sync_params[field_name].default is None
        assert async_params[field_name].default is None


@pytest.mark.asyncio
async def test_sdk_constructor_values_are_not_overwritten_by_call_defaults(
    monkeypatch, tmp_path
):
    source = tmp_path / "paper.pdf"
    source.write_bytes(b"test")
    captured = {}

    class DummyWorkflow:
        def read_path(self, path):
            self.path = path

    def create_workflow(payload):
        captured["payload"] = payload
        return DummyWorkflow()

    monkeypatch.setattr(sdk_module, "create_workflow_from_payload", create_workflow)

    client = Client(convert_engine="mineru", mineru_token="constructor-token")
    await client.translate_async(str(source), skip_translate=True)

    payload = captured["payload"]
    assert payload.convert_engine == "mineru"
    assert payload.mineru_token == "constructor-token"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("filename", "expected_type"),
    [("encrypted.docx", DocxWorkflowParams), ("encrypted.xlsx", XlsxWorkflowParams)],
)
async def test_auto_workflow_preserves_office_password(
    monkeypatch, filename, expected_type
):
    service = TranslationService()
    captured = {}

    async def perform_translation(task_id, payload, file_contents, original_filename):
        captured["payload"] = payload

    monkeypatch.setattr(service, "_perform_translation", perform_translation)
    payload = TypeAdapter(TranslatePayload).validate_python(
        {
            "workflow_type": "auto",
            "skip_translate": True,
            "office_password": "secret-password",
        }
    )

    await service.start_translation("contract-task", payload, b"test", filename)
    await service.tasks_state["contract-task"]["current_task_ref"]

    routed_payload = captured["payload"]
    assert isinstance(routed_payload, expected_type)
    assert routed_payload.office_password == "secret-password"


def test_translator_runtime_honors_stream_policy_overrides():
    config = TXTTranslatorConfig(
        base_url="https://example.invalid/v1",
        api_key="test-key",
        model_id="test-model",
        streaming=False,
        stream_idle_timeout=17,
        non_stream_timeout=29,
    )

    translator = TXTTranslator(config)

    assert translator.translate_agent.streaming_enabled is False
    assert translator.translate_agent.stream_idle_timeout_seconds == 17
    assert translator.translate_agent.non_stream_total_timeout_seconds == 29


def test_every_translator_agent_config_forwards_stream_policy_fields():
    translator_root = (
        Path(__file__).parents[2]
        / "docutranslate"
        / "translator"
        / "ai_translator"
    )
    config_types = {
        "SegmentsTranslateAgentConfig",
        "MDTranslateAgentConfig",
        "GlossaryAgentConfig",
    }
    checked_calls = []

    for source_file in translator_root.glob("*.py"):
        tree = ast.parse(source_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id not in config_types:
                continue

            keywords = {keyword.arg for keyword in node.keywords}
            assert STREAM_POLICY_FIELDS <= keywords, (
                f"{source_file.name}:{node.lineno} 创建 {node.func.id} 时"
                f"没有完整透传 {sorted(STREAM_POLICY_FIELDS - keywords)}"
            )
            checked_calls.append((source_file.name, node.lineno, node.func.id))

    assert len(checked_calls) == 11


def test_segment_and_markdown_prompts_keep_rules_in_a_stable_prefix():
    shared = {
        "base_url": "https://example.invalid/v1",
        "api_key": "test-key",
        "model_id": "test-model",
        "to_lang": "中文",
        "glossary_dict": {
            "Beta": "贝塔",
            "Alpha": "阿尔法",
            "Unused": "未使用",
        },
    }
    cases = [
        (
            SegmentsTranslateAgent(SegmentsTranslateAgentConfig(**shared)),
            generate_segments_prompt('{"0":"Alpha text"}', "中文"),
            generate_segments_prompt('{"0":"Beta text"}', "中文"),
            "Every input ID must appear exactly once",
        ),
        (
            MDTranslateAgent(MDTranslateAgentConfig(**shared)),
            generate_markdown_prompt("# Alpha text", "中文"),
            generate_markdown_prompt("# Beta text", "中文"),
            "Output the translated markdown only",
        ),
    ]

    for agent, alpha_prompt, beta_prompt, static_rule in cases:
        alpha_system, alpha_user = agent._pre_send_handler(
            agent.system_prompt, alpha_prompt
        )
        beta_system, beta_user = agent._pre_send_handler(
            agent.system_prompt, beta_prompt
        )

        assert alpha_system == beta_system == agent.system_prompt
        assert static_rule in agent.system_prompt
        assert "Alpha text" not in agent.system_prompt
        assert "Beta text" not in agent.system_prompt
        assert "Alpha=>阿尔法" in alpha_user
        assert "Beta=>贝塔" not in alpha_user
        assert "Unused=>未使用" not in alpha_user
        assert "Beta=>贝塔" in beta_user
        assert "Alpha=>阿尔法" not in beta_user
        assert "Unused=>未使用" not in beta_user


def test_glossary_extraction_prompt_keeps_static_rules_before_dynamic_input():
    agent = GlossaryAgent(
        GlossaryAgentConfig(
            base_url="https://example.invalid/v1",
            api_key="test-key",
            model_id="test-model",
            to_lang="中文",
        )
    )
    first_prompt = generate_glossary_prompt('{"0":"DynamicPersonOne"}', "中文")
    second_prompt = generate_glossary_prompt('{"0":"DynamicPlaceTwo"}', "中文")

    assert "Include each source term only once" in agent.system_prompt
    assert "DynamicPersonOne" not in agent.system_prompt
    assert "DynamicPlaceTwo" not in agent.system_prompt
    assert "Include each source term only once" not in first_prompt
    assert "DynamicPersonOne" in first_prompt
    assert "DynamicPlaceTwo" in second_prompt


@pytest.mark.asyncio
async def test_deepseek_batch_warms_two_prompts_before_parallel_fanout(
    monkeypatch,
):
    agent = Agent(
        AgentConfig(
            base_url="https://api.deepseek.com",
            api_key="test-key",
            model_id="deepseek-chat",
            provider="deepseek",
            concurrent=4,
        )
    )
    events = []
    active = 0
    max_active = 0

    async def fake_send_async(*, prompt, **kwargs):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        events.append(("start", prompt))
        await asyncio.sleep(0.01)
        events.append(("end", prompt))
        active -= 1
        return f"translated:{prompt}"

    monkeypatch.setattr(agent, "send_async", fake_send_async)

    results = await agent.send_prompts_async(["p1", "p2", "p3", "p4"])

    assert events[:4] == [
        ("start", "p1"),
        ("end", "p1"),
        ("start", "p2"),
        ("end", "p2"),
    ]
    assert max_active == 2
    assert results == [
        "translated:p1",
        "translated:p2",
        "translated:p3",
        "translated:p4",
    ]


def test_conversion_engine_schema_matches_workflow_registry():
    from docutranslate.core.schemas import MarkdownWorkflowParams, UniversalParamsMixin
    from docutranslate.workflow.md_based_workflow import MarkdownBasedWorkflow

    expected = {"identity", "mineru", "mineru_deploy"}
    schema = MarkdownWorkflowParams.model_json_schema()
    assert set(schema["properties"]["convert_engine"]["enum"]) == expected
    universal_schema = UniversalParamsMixin.model_json_schema()
    choices = universal_schema["properties"]["convert_engine"]["anyOf"]
    assert set(next(choice["enum"] for choice in choices if "enum" in choice)) == expected
    assert set(MarkdownBasedWorkflow._converter_factory) == expected
