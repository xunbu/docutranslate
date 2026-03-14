"""
Tests for context module
"""
from unittest.mock import MagicMock, patch

import pytest

from docutranslate.context.md_mask_context import MDMaskUrisContext


def test_md_mask_context_initialization():
    """Test MDMaskUrisContext initialization"""
    mock_doc = MagicMock()
    context = MDMaskUrisContext(mock_doc)
    assert context.document == mock_doc
    assert context.mask_dict is not None


@patch('docutranslate.context.md_mask_context.uris2placeholder')
@patch('docutranslate.context.md_mask_context.placeholder2uris')
def test_md_mask_context_context_manager(mock_placeholder2uris, mock_uris2placeholder):
    """Test MDMaskUrisContext as a context manager"""
    # Setup mocks
    mock_doc = MagicMock()
    mock_doc.content = b"Original content with https://example.com"
    mock_uris2placeholder.return_value = "Masked content with URI_PLACEHOLDER_0"
    mock_placeholder2uris.return_value = "Restored content with https://example.com"

    # Use as context manager
    with MDMaskUrisContext(mock_doc):
        # Check that uris2placeholder was called on enter
        mock_uris2placeholder.assert_called_once()
        assert mock_doc.content == b"Masked content with URI_PLACEHOLDER_0"

    # Check that placeholder2uris was called on exit
    mock_placeholder2uris.assert_called_once()
    assert mock_doc.content == b"Restored content with https://example.com"


@patch('docutranslate.context.md_mask_context.uris2placeholder')
@patch('docutranslate.context.md_mask_context.placeholder2uris')
def test_md_mask_context_with_exception(mock_placeholder2uris, mock_uris2placeholder):
    """Test MDMaskUrisContext still restores even when exception occurs"""
    # Setup mocks
    mock_doc = MagicMock()
    mock_doc.content = b"Original content"
    mock_uris2placeholder.return_value = "Masked content"
    mock_placeholder2uris.return_value = "Restored content"

    # Test with exception
    try:
        with MDMaskUrisContext(mock_doc):
            raise ValueError("Test exception")
    except ValueError:
        pass

    # Verify cleanup still happened
    mock_placeholder2uris.assert_called_once()
    assert mock_doc.content == b"Restored content"
