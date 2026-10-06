"""Fidelity regressions for the layout-aware Markdown splitter.

``join_markdown_with_layout(*split_markdown_with_layout(text))`` must reproduce
``text`` exactly. The old implementation dropped the indentation before the first
block, dropped trailing whitespace/CRLF, and inserted a blank line at every seam
of an oversized fenced code block.
"""
import random

import pytest

from docutranslate.utils.markdown_splitter import (
    MERGE_CODE_TOKEN,
    join_markdown_with_layout,
    split_markdown_with_layout,
)

GIANT_FENCE = "```python\n" + "\n".join(f"line_{i} = {i}  # padding" for i in range(200)) + "\n```\n"

SAMPLES = {
    "empty": "",
    "whitespace only": "\n\n   \n",
    "simple": "# Title\n\nbody\n",
    "no trailing newline": "# Title\n\nbody",
    "indented first block": "    code line\n\nnormal\n",
    "crlf": "a\r\n\r\nb\r\n",
    "leading blank lines": "\n\n\n# H\n\ntext\n",
    "trailing blank lines": "# H\n\ntext\n\n\n\n",
    "tabs": "\tindented\n\tmore\n\nplain\n",
    "nested list": "- a\n  - b\n    - c\n\npara\n",
    "inline code": "Run `echo $$` to get the pid.\n\nnext\n",
    "display math": "before\n\n$$\nx=1\n$$\n\nafter\n",
    "placeholder": "![img](a.png)\n\ntext\n",
    "table": "| a | b |\n|---|---|\n| 1 | 2 |\n\ntext\n",
    "pep8 fence": "```python\ndef a():\n    pass\n\n\ndef b():\n    pass\n```\n",
    "fence with crlf": "```sh\r\necho hi\r\n```\r\n\r\nnext\r\n",
    "two fences": "```a\n1\n```\n\nmid\n\n```b\n2\n```\n",
    "giant fence": GIANT_FENCE,
    "giant fence + text": "intro para\n\n" + GIANT_FENCE + "\ntail para\n",
    "giant plain text": ("word " * 600) + "\n\nend\n",
    "unicode crlf": "# Ünïcode\n\n中文\r\n\r\nmore\r\n",
}

LIMITS = [10, 50, 200, 3000]


@pytest.mark.parametrize("limit", LIMITS)
def test_round_trip_is_lossless(limit):
    for name, text in SAMPLES.items():
        chunks, separators = split_markdown_with_layout(text, max_block_size=limit)
        rebuilt = join_markdown_with_layout(chunks, separators)
        assert rebuilt == text, f"{name!r} changed at max_block_size={limit}"


def test_separator_contract_length():
    chunks, separators = split_markdown_with_layout("# A\n\ntext\n\n## B\n", max_block_size=8)
    assert len(separators) == len(chunks) + 1


def test_legacy_separator_list_is_still_accepted():
    chunks, separators = split_markdown_with_layout("a\n\nb\n", max_block_size=3000)
    assert join_markdown_with_layout(chunks, separators[1:-1]) == "a\n\nb"


def test_whitespace_only_input_survives():
    chunks, separators = split_markdown_with_layout("\n\n   \n")
    assert chunks == []
    assert join_markdown_with_layout(chunks, separators) == "\n\n   \n"


def test_oversized_code_block_has_no_spurious_blank_line():
    text = "```python\n" + "\n".join(f"line_{i} = {i}" for i in range(200)) + "\n```\n"
    chunks, separators = split_markdown_with_layout(text, max_block_size=200)

    assert chunks, "the oversized fence must be split"
    assert all("\n\n" not in chunk for chunk in chunks), chunks[:3]
    assert separators.count(MERGE_CODE_TOKEN) == len(chunks) - 1
    assert join_markdown_with_layout(chunks, separators) == text


def test_seeded_fuzz_round_trip():
    rng = random.Random(20261005)
    alphabet = ["a", "b", " ", "\n", "\t", "#", "`", "$", "*", "-", "中", "\r", "|", "(", ")"]
    for _ in range(300):
        text = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 120)))
        limit = rng.choice([5, 16, 64, 256])
        chunks, separators = split_markdown_with_layout(text, max_block_size=limit)
        assert join_markdown_with_layout(chunks, separators) == text, (text, limit)
