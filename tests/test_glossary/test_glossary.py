"""
Tests for glossary module
"""
import csv
from io import StringIO

import pytest

from docutranslate.glossary.glossary import Glossary


def test_glossary_initialization():
    """Test Glossary initialization"""
    # Empty glossary
    glossary = Glossary()
    assert glossary.glossary_dict == {}

    # With initial dict
    initial_dict = {"hello": "你好", "world": "世界"}
    glossary = Glossary(initial_dict)
    assert glossary.glossary_dict == initial_dict


def test_glossary_update():
    """Test Glossary update method"""
    glossary = Glossary()

    # Update with new terms
    glossary.update({"hello": "你好"})
    assert glossary.glossary_dict == {"hello": "你好"}

    # Update with mixed case, should be stored lowercase
    glossary.update({"HELLO": "您好"})
    assert glossary.glossary_dict.get("hello") == "你好"  # Should not overwrite

    # Update with new term
    glossary.update({"world": "世界"})
    assert glossary.glossary_dict == {"hello": "你好", "world": "世界"}

    # Update with stripped whitespace
    glossary.update({"  test  ": "测试"})
    assert "test" in glossary.glossary_dict
    assert glossary.glossary_dict["test"] == "测试"


def test_append_system_prompt():
    """Test Glossary append_system_prompt method"""
    glossary = Glossary({"hello": "你好", "world": "世界"})

    # Text with matching term
    prompt = glossary.append_system_prompt("Hello there!")
    assert "hello=>你好" in prompt
    assert "Glossary ends" in prompt
    assert "world=>世界" not in prompt

    # Text with multiple matching terms
    prompt = glossary.append_system_prompt("Hello world!")
    assert "hello=>你好" in prompt
    assert "world=>世界" in prompt

    # Text with no matching terms
    prompt = glossary.append_system_prompt("This is a test")
    assert prompt == ""


def test_append_system_prompt_case_insensitive():
    """Test append_system_prompt is case insensitive"""
    glossary = Glossary({"Hello": "你好"})

    prompt = glossary.append_system_prompt("hello there")
    assert "Hello=>你好" in prompt

    prompt = glossary.append_system_prompt("HELLO there")
    assert "Hello=>你好" in prompt


def test_glossary_dict2csv():
    """Test glossary_dict2csv static method"""
    glossary_dict = {"hello": "你好", "world": "世界"}
    doc = Glossary.glossary_dict2csv(glossary_dict)

    # Check document properties
    assert doc.suffix == ".csv"
    assert doc.stem == "glossary_gen"

    # Check content
    content = doc.content.decode("utf-8")
    assert content.startswith("\ufeff")  # Should have BOM
    assert "src,dst" in content
    assert "hello,你好" in content or "hello,你好" in content
    assert "world,世界" in content or "world,世界" in content

    # Parse the CSV and check
    content_without_bom = content[1:] if content.startswith("\ufeff") else content
    reader = csv.reader(StringIO(content_without_bom))
    rows = list(reader)
    assert rows[0] == ["src", "dst"]
    assert len(rows) == 3  # Header + 2 rows


def test_glossary_dict2csv_custom_delimiter():
    """Test glossary_dict2csv with custom delimiter"""
    glossary_dict = {"hello": "你好"}
    doc = Glossary.glossary_dict2csv(glossary_dict, delimiter="\t", stem="custom")

    assert doc.stem == "custom"
    content = doc.content.decode("utf-8")
    assert "src\tdst" in content
