import json
import pytest
from pathlib import Path

from docutranslate.workflow.record_helper import RecordFieldMapping, RecordTranslationHelper


# ======================================================================
# RecordFieldMapping defaults
# ======================================================================

def test_default_field_mapping():
    fm = RecordFieldMapping()
    assert fm.id_field == "record_id"
    assert fm.text_field == "source_text"
    assert fm.records_key == "records"


def test_custom_field_mapping():
    fm = RecordFieldMapping(id_field="key", text_field="content", records_key="items")
    assert fm.id_field == "key"
    assert fm.text_field == "content"
    assert fm.records_key == "items"


# ======================================================================
# build_json_paths
# ======================================================================

def test_build_json_paths_default():
    helper = RecordTranslationHelper()
    assert helper.build_json_paths() == ["$.records[*].source_text"]


def test_build_json_paths_custom():
    helper = RecordTranslationHelper(
        RecordFieldMapping(id_field="pk", text_field="text", records_key="items")
    )
    assert helper.build_json_paths() == ["$.items[*].text"]


# ======================================================================
# build_payload
# ======================================================================

def test_build_payload():
    helper = RecordTranslationHelper()
    records = [
        {"record_id": "r1", "source_text": "你好"},
        {"record_id": "r2", "source_text": "世界"},
    ]
    payload = helper.build_payload(records)
    assert payload == {
        "records": [
            {"record_id": "r1", "source_text": "你好"},
            {"record_id": "r2", "source_text": "世界"},
        ]
    }


def test_build_payload_custom_key():
    helper = RecordTranslationHelper(
        RecordFieldMapping(records_key="items")
    )
    records = [{"record_id": "r1", "source_text": "你好"}]
    payload = helper.build_payload(records)
    assert "items" in payload
    assert len(payload["items"]) == 1


# ======================================================================
# extract_translated_records
# ======================================================================

def test_extract_translated_records_basic():
    helper = RecordTranslationHelper()
    original = [
        {"record_id": "r1", "source_text": "你好", "category": "doc"},
        {"record_id": "r2", "source_text": "世界", "category": "drawing"},
    ]
    translated_payload = {
        "records": [
            {"record_id": "r1", "source_text": "Hello"},
            {"record_id": "r2", "source_text": "World"},
        ]
    }
    result = helper.extract_translated_records(original, translated_payload)

    assert len(result) == 2
    # Text field updated
    assert result[0]["source_text"] == "Hello"
    assert result[1]["source_text"] == "World"
    # Non-text fields preserved
    assert result[0]["category"] == "doc"
    assert result[1]["category"] == "drawing"
    # ID field preserved
    assert result[0]["record_id"] == "r1"
    assert result[1]["record_id"] == "r2"


def test_extract_translated_records_missing_id():
    """If a record ID is missing from translated payload, original is returned."""
    helper = RecordTranslationHelper()
    original = [
        {"record_id": "r1", "source_text": "你好"},
        {"record_id": "r2", "source_text": "世界"},
    ]
    translated_payload = {
        "records": [
            {"record_id": "r1", "source_text": "Hello"},
            # r2 is missing
        ]
    }
    result = helper.extract_translated_records(original, translated_payload)

    assert result[0]["source_text"] == "Hello"
    assert result[1]["source_text"] == "世界"  # unchanged


def test_extract_translated_records_maintains_order():
    """Results must be in the same order as original records."""
    helper = RecordTranslationHelper()
    original = [
        {"record_id": "a", "source_text": "甲"},
        {"record_id": "b", "source_text": "乙"},
        {"record_id": "c", "source_text": "丙"},
    ]
    translated_payload = {
        "records": [
            {"record_id": "c", "source_text": "C"},
            {"record_id": "a", "source_text": "A"},
            {"record_id": "b", "source_text": "B"},
        ]
    }
    result = helper.extract_translated_records(original, translated_payload)

    assert [r["record_id"] for r in result] == ["a", "b", "c"]
    assert [r["source_text"] for r in result] == ["A", "B", "C"]


def test_extract_translated_records_non_dict_item_ignored():
    helper = RecordTranslationHelper()
    original = [{"record_id": "r1", "source_text": "你好"}]
    translated_payload = {"records": ["not a dict", {"record_id": "r1", "source_text": "Hello"}]}
    result = helper.extract_translated_records(original, translated_payload)
    assert result[0]["source_text"] == "Hello"


def test_extract_translated_records_empty_payload():
    helper = RecordTranslationHelper()
    original = [{"record_id": "r1", "source_text": "你好"}]
    result = helper.extract_translated_records(original, {"records": []})
    assert result[0]["source_text"] == "你好"  # unchanged


# ======================================================================
# write_payload_to_file / read_translated_payload
# ======================================================================

def test_write_and_read_payload(tmp_path):
    helper = RecordTranslationHelper()
    records = [{"record_id": "r1", "source_text": "你好"}]
    out_path = helper.write_payload_to_file(records, tmp_path / "test.json")

    assert out_path.exists()
    loaded = json.loads(out_path.read_text(encoding="utf-8"))
    assert loaded == {"records": [{"record_id": "r1", "source_text": "你好"}]}


def test_read_translated_payload(tmp_path):
    helper = RecordTranslationHelper()
    data = {"records": [{"record_id": "r1", "source_text": "Hello"}]}
    path = tmp_path / "translated.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    loaded = helper.read_translated_payload(path)
    assert loaded == data
