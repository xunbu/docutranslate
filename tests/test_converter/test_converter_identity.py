"""
Tests for ConverterIdentity module
"""
import pytest

from docutranslate.converter.converter_identity import ConverterIdentity
from docutranslate.ir.document import Document


class TestConverterIdentity:
    """Test ConverterIdentity class"""

    def test_converter_identity_convert(self):
        """Test that ConverterIdentity.convert returns original document"""
        converter = ConverterIdentity()

        # Create a test document
        original_doc = Document.from_bytes(
            content=b"# Test Document\n\nThis is content",
            suffix=".md",
            stem="test"
        )

        result = converter.convert(original_doc)

        # Verify the document content is preserved
        assert result.content == original_doc.content
        assert result.suffix == original_doc.suffix
        assert result.stem == original_doc.stem

    def test_converter_identity_convert_creates_copy(self):
        """Test that ConverterIdentity.convert creates a new Document instance"""
        converter = ConverterIdentity()

        original_doc = Document.from_bytes(
            content=b"# Test",
            suffix=".md",
            stem="test"
        )

        result = converter.convert(original_doc)

        # Should be a different instance (copy)
        assert result is not original_doc

    @pytest.mark.asyncio
    async def test_converter_identity_convert_async(self):
        """Test ConverterIdentity.convert_async returns original document"""
        converter = ConverterIdentity()

        original_doc = Document.from_bytes(
            content=b"# Async Test\n\nAsync content",
            suffix=".md",
            stem="async_test"
        )

        result = await converter.convert_async(original_doc)

        # Verify the document content is preserved
        assert result.content == original_doc.content
        assert result.suffix == original_doc.suffix
        assert result.stem == original_doc.stem

    @pytest.mark.asyncio
    async def test_converter_identity_convert_async_creates_copy(self):
        """Test that ConverterIdentity.convert_async creates a new Document instance"""
        converter = ConverterIdentity()

        original_doc = Document.from_bytes(
            content=b"# Async Test",
            suffix=".md",
            stem="async_test"
        )

        result = await converter.convert_async(original_doc)

        # Should be a different instance (copy)
        assert result is not original_doc

    def test_converter_identity_with_different_formats(self):
        """Test ConverterIdentity works with different file formats"""
        converter = ConverterIdentity()

        # Test with .txt format
        txt_doc = Document.from_bytes(content=b"Plain text", suffix=".txt", stem="text")
        result = converter.convert(txt_doc)
        assert result.content == b"Plain text"
        assert result.suffix == ".txt"

        # Test with .html format
        html_doc = Document.from_bytes(content=b"<html></html>", suffix=".html", stem="page")
        result = converter.convert(html_doc)
        assert result.content == b"<html></html>"
        assert result.suffix == ".html"
