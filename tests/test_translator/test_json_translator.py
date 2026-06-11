import json

import pytest

from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.json_translator import JsonTranslator, JsonTranslatorConfig


class _FakeTranslateAgent:
    def send_segments(self, segments, chunk_size):
        return [f"EN::{segment}" for segment in segments]


def _build_translator(*, json_paths: list[str]) -> JsonTranslator:
    config = JsonTranslatorConfig(
        base_url="https://example.com/v1",
        api_key="test-api-key",
        model_id="test-model",
        to_lang="English",
        json_paths=json_paths,
        skip_translate=True,
    )
    return JsonTranslator(config)


def test_translate_only_updates_explicit_json_paths():
    document = Document.from_bytes(
        json.dumps(
            {
                "items": [
                    {"id": "a-1", "text": "总说明", "status": "draft"},
                    {"id": "a-2", "text": "平面图", "status": "approved"},
                ],
                "owner": "Alice",
            },
            ensure_ascii=False,
        ).encode("utf-8"),
        suffix=".json",
        stem="sample",
    )
    translator = _build_translator(json_paths=["$.items[*].text"])
    translator.translate_agent = _FakeTranslateAgent()

    translator.translate(document)
    translated = json.loads(document.content.decode("utf-8"))

    assert [item["text"] for item in translated["items"]] == ["EN::总说明", "EN::平面图"]
    assert [item["id"] for item in translated["items"]] == ["a-1", "a-2"]
    assert [item["status"] for item in translated["items"]] == ["draft", "approved"]
    assert translated["owner"] == "Alice"


def test_invalid_json_path_raises_clear_error():
    translator = _build_translator(json_paths=["$.items["])

    with pytest.raises(ValueError, match=r"Invalid json_paths expression: \$\.items\["):
        translator._collect_strings_for_translation({"items": [{"text": "hello"}]})
