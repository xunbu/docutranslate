"""Chunking regressions for ``segments2json_chunks``.

A single line longer than ``chunk_size`` used to be emitted as one oversized JSON
chunk (e.g. 10 000 characters with ``chunk_size=3000``), which can blow the
request budget and hurt translation quality.
"""
import json

from docutranslate.utils.json_utils import get_json_size, segments2json_chunks


def _chunk_size(chunk: dict) -> int:
    return get_json_size(chunk)


def test_oversized_single_line_is_split():
    limit = 200
    segments = ["a" * 5000]

    _, chunks, _ = segments2json_chunks(segments, limit)

    assert chunks, "must produce at least one chunk"
    for chunk in chunks:
        assert _chunk_size(chunk) <= limit, _chunk_size(chunk)


def test_oversized_line_split_preserves_content():
    limit = 200
    original = "x" * 1500 + "\n" + "y" * 1500

    full, chunks, merged = segments2json_chunks([original], limit)

    reassembled = ""
    for index in range(len(full)):
        reassembled += full[str(index)]
    assert reassembled == original
    assert all(_chunk_size(chunk) <= limit for chunk in chunks)


def test_binary_search_never_returns_empty_subslices():
    limit = 60
    _, chunks, _ = segments2json_chunks(["中" * 800], limit)

    for chunk in chunks:
        for value in chunk.values():
            assert value != ""
        assert _chunk_size(chunk) <= limit


def test_small_segments_still_batched():
    segments = ["one", "two", "three"]

    full, chunks, merged = segments2json_chunks(segments, 4000)

    assert list(full.values()) == segments
    assert len(chunks) == 1
    assert merged == []
