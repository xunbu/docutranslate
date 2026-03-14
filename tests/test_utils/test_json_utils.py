"""
Tests for utils.json_utils module
"""
import json
import pytest

from docutranslate.utils.json_utils import (
    get_json_size,
    segments2json_chunks,
    fix_json_string,
    parse_json_response
)


def test_get_json_size_simple():
    """Test get_json_size with simple dictionary"""
    data = {"key": "value"}
    expected_size = len(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    assert get_json_size(data) == expected_size


def test_get_json_size_with_chinese():
    """Test get_json_size with Chinese characters"""
    data = {"key": "测试中文"}
    expected_size = len(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    assert get_json_size(data) == expected_size


def test_get_json_size_empty():
    """Test get_json_size with empty dictionary"""
    data = {}
    expected_size = len(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    assert get_json_size(data) == expected_size


def test_segments2json_chunks_empty_segments():
    """Test segments2json_chunks with empty segments list"""
    js, chunks, merged = segments2json_chunks([], 1000)
    assert js == {}
    assert chunks == []
    assert merged == []


def test_segments2json_chunks_single_small_segment():
    """Test segments2json_chunks with single small segment"""
    segments = ["Hello world"]
    js, chunks, merged = segments2json_chunks(segments, 1000)

    assert js == {"0": "Hello world"}
    assert len(chunks) == 1
    assert chunks[0] == {"0": "Hello world"}
    assert merged == []


def test_segments2json_chunks_multiple_small_segments():
    """Test segments2json_chunks with multiple small segments that fit in one chunk"""
    segments = ["Segment 1", "Segment 2", "Segment 3"]
    js, chunks, merged = segments2json_chunks(segments, 1000)

    assert js == {"0": "Segment 1", "1": "Segment 2", "2": "Segment 3"}
    assert len(chunks) == 1
    assert chunks[0] == js
    assert merged == []


def test_segments2json_chunks_single_large_segment():
    """Test segments2json_chunks with single large segment that needs splitting"""
    # Create a large segment with newlines to allow splitting
    large_segment = "\n".join(["a" * 50 for _ in range(4)])  # 4 lines * 50 chars = 200 chars + 3 newlines
    segments = [large_segment]

    # Set chunk size small enough to force splitting
    js, chunks, merged = segments2json_chunks(segments, 100)

    # The segment should be split into multiple parts
    assert len(js) > 1
    assert len(chunks) >= 1
    assert len(merged) == 1  # Should have merged indices for the split segment


def test_segments2json_chunks_mixed_size_segments():
    """Test segments2json_chunks with mix of small and large segments"""
    segments = [
        "Small segment 1",
        # Large segment with newlines to allow splitting
        "\n".join(["a" * 50 for _ in range(6)]),  # 6 lines * 50 chars = 300 chars
        "Small segment 2"
    ]

    js, chunks, merged = segments2json_chunks(segments, 150)

    # Check that large segment was split
    assert len(js) > 3
    assert len(merged) >= 1


def test_fix_json_string_simple():
    """Test fix_json_string with simple case"""
    input_json = '''{
        "0": "value1",
        "1": "value2"
    }'''
    result = fix_json_string(input_json)
    # Function removes spaces after commas
    assert '"0": "value1",\n"1":' in result


def test_fix_json_string_with_chinese_comma():
    """Test fix_json_string with Chinese commas"""
    input_json = '''{
        "0": "value1"，
        "1": "value2"
    }'''
    result = fix_json_string(input_json)
    # Chinese comma should be replaced with English comma
    assert '"0": "value1",\n"1":' in result


def test_fix_json_string_with_chinese_quotes():
    """Test fix_json_string with Chinese quotes around keys"""
    input_json = '''{
        "0": "value1",
        “1”: "value2"
    }'''
    result = fix_json_string(input_json)
    # Chinese quotes around numbers should be fixed
    assert '"1":' in result


def test_parse_json_response_normal_json():
    """Test parse_json_response with normal JSON string"""
    json_str = '{"key": "value", "number": 42}'
    result = parse_json_response(json_str)
    assert result == {"key": "value", "number": 42}


def test_parse_json_response_with_code_block():
    """Test parse_json_response with JSON wrapped in code block"""
    json_str = '''```json
{"key": "value", "number": 42}
```'''
    result = parse_json_response(json_str)
    assert result == {"key": "value", "number": 42}


def test_parse_json_response_broken_json():
    """Test parse_json_response with broken JSON that needs repair"""
    # Missing closing brace
    json_str = '{"key": "value", "number": 42'
    result = parse_json_response(json_str)
    assert result == {"key": "value", "number": 42}


def test_parse_json_response_with_trailing_comma():
    """Test parse_json_response with JSON that has trailing comma"""
    json_str = '{"key": "value", "number": 42,}'
    result = parse_json_response(json_str)
    assert result == {"key": "value", "number": 42}
