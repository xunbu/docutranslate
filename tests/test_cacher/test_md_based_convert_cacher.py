"""
Tests for cacher module
"""
import os
from unittest.mock import MagicMock, patch

import pytest

from docutranslate.cacher.md_based_convert_cacher import MDBasedCovertCacher, md_based_convert_cacher


def test_cacher_initialization():
    """Test cacher initialization"""
    cacher = MDBasedCovertCacher()
    assert len(cacher.cache_dict) == 0


def test_get_hashcode():
    """Test _get_hashcode method"""
    cacher = MDBasedCovertCacher()

    # Mock dependencies
    mock_document = MagicMock()
    mock_document.suffix = ".pdf"
    mock_document.content = b"test content"

    mock_config = MagicMock()
    mock_config.gethash.return_value = "config-hash"

    # Test with config
    hash1 = cacher._get_hashcode(mock_document, "mineru", mock_config)
    assert isinstance(hash1, str)

    # Test without config
    hash2 = cacher._get_hashcode(mock_document, "mineru", None)
    assert isinstance(hash2, str)
    assert hash1 != hash2

    # Test same parameters produce same hash
    hash3 = cacher._get_hashcode(mock_document, "mineru", mock_config)
    assert hash1 == hash3

    # Test different engine produces different hash
    hash4 = cacher._get_hashcode(mock_document, "docling", mock_config)
    assert hash1 != hash4


def test_cache_and_get_result():
    """Test cache_result and get_cached_result methods"""
    cacher = MDBasedCovertCacher()

    # Mock dependencies
    mock_document = MagicMock()
    mock_document.suffix = ".pdf"
    mock_document.content = b"test content"

    mock_config = MagicMock()
    mock_config.gethash.return_value = "config-hash"

    mock_md_doc = MagicMock()
    mock_md_doc.copy.return_value = mock_md_doc

    # Test cache is empty initially
    result = cacher.get_cached_result(mock_document, "mineru", mock_config)
    assert result is None

    # Cache the result
    cached = cacher.cache_result(mock_md_doc, mock_document, "mineru", mock_config)
    assert cached == mock_md_doc
    assert len(cacher.cache_dict) == 1

    # Retrieve from cache
    retrieved = cacher.get_cached_result(mock_document, "mineru", mock_config)
    assert retrieved is not None
    assert retrieved == mock_md_doc
    mock_md_doc.copy.assert_called()


def test_cache_lru_eviction():
    """Test that LRU eviction works when cache exceeds limit"""
    cacher = MDBasedCovertCacher()

    # Create 12 items (default CACHE_NUM is 10)
    # Logic: check length before adding, pop only if > CACHE_NUM
    # So max size is CACHE_NUM + 1 = 11
    for i in range(12):
        mock_doc = MagicMock()
        mock_doc.suffix = f".{i}"
        mock_doc.content = f"content{i}".encode()

        mock_config = MagicMock()
        mock_config.gethash.return_value = f"hash{i}"

        mock_md = MagicMock()
        mock_md.copy.return_value = mock_md

        cacher.cache_result(mock_md, mock_doc, "mineru", mock_config)

    # Should keep 11 items (CACHE_NUM + 1)
    assert len(cacher.cache_dict) == 11

    # Add one more, should still be 11
    mock_doc = MagicMock()
    mock_doc.suffix = ".12"
    mock_doc.content = b"content12"
    mock_config = MagicMock()
    mock_config.gethash.return_value = "hash12"
    mock_md = MagicMock()
    mock_md.copy.return_value = mock_md
    cacher.cache_result(mock_md, mock_doc, "mineru", mock_config)

    assert len(cacher.cache_dict) == 11


def test_clear_cache():
    """Test clear method"""
    cacher = MDBasedCovertCacher()

    # Add some items
    mock_doc = MagicMock()
    mock_doc.suffix = ".pdf"
    mock_doc.content = b"test"
    mock_config = MagicMock()
    mock_config.gethash.return_value = "hash"
    mock_md = MagicMock()
    mock_md.copy.return_value = mock_md

    cacher.cache_result(mock_md, mock_doc, "mineru", mock_config)
    assert len(cacher.cache_dict) == 1

    # Clear cache
    cacher.clear()
    assert len(cacher.cache_dict) == 0


def test_singleton_instance():
    """Test that the global singleton instance exists"""
    assert isinstance(md_based_convert_cacher, MDBasedCovertCacher)
