"""
Tests for IR (Intermediate Representation) modules
"""
from pathlib import Path

import pytest

from docutranslate.ir.document import Document
from docutranslate.ir.markdown_document import MarkdownDocument
from docutranslate.ir.attachment_manager import (
    AttachMent,
    AttachMentManager,
    AttachMentIdentifier
)


# ==================== Document tests ====================
def test_document_initialization():
    """Test Document initialization"""
    content = b"test content"
    doc = Document(suffix=".txt", content=content, stem="test", path=None)
    assert doc.suffix == ".txt"
    assert doc.content == content
    assert doc._stem == "test"
    assert doc.path is None


def test_document_stem_property():
    """Test Document stem property"""
    # With stem
    doc = Document(suffix=".txt", content=b"test", stem="mydoc")
    assert doc.stem == "mydoc"

    # Without stem
    doc = Document(suffix=".txt", content=b"test")
    assert doc.stem is None


def test_document_name_property():
    """Test Document name property"""
    # With stem
    doc = Document(suffix=".txt", content=b"test", stem="mydoc")
    assert doc.name == "mydoc.txt"

    # Without stem
    doc = Document(suffix=".txt", content=b"test")
    assert doc.name is None


def test_document_from_bytes():
    """Test Document.from_bytes classmethod"""
    content = b"test from bytes"
    doc = Document.from_bytes(content=content, suffix=".md", stem="testdoc")
    assert doc.content == content
    assert doc.suffix == ".md"
    assert doc.stem == "testdoc"


def test_document_from_path(temp_dir):
    """Test Document.from_path classmethod"""
    # Create a test file
    test_file = temp_dir / "testfile.txt"
    test_content = b"test file content"
    test_file.write_bytes(test_content)

    # Read with from_path
    doc = Document.from_path(str(test_file))
    assert doc.suffix == ".txt"
    assert doc.content == test_content
    assert doc.stem == "testfile"
    assert doc.path == test_file

    # Read with Path object
    doc = Document.from_path(test_file)
    assert doc.suffix == ".txt"
    assert doc.content == test_content


def test_document_copy():
    """Test Document.copy method"""
    doc1 = Document(suffix=".txt", content=b"original", stem="test")
    doc2 = doc1.copy()

    # Should be different objects
    assert doc1 is not doc2
    # But have same values
    assert doc1.suffix == doc2.suffix
    assert doc1.content == doc2.content
    assert doc1.stem == doc2.stem


# ==================== MarkdownDocument tests ====================
def test_markdown_document_initialization():
    """Test MarkdownDocument initialization"""
    content = b"# Test markdown"
    doc = MarkdownDocument(content=content, suffix=".md", stem="test")
    assert isinstance(doc, MarkdownDocument)
    assert isinstance(doc, Document)
    assert doc.content == content
    assert doc.suffix == ".md"


def test_markdown_document_copy():
    """Test MarkdownDocument.copy method"""
    doc1 = MarkdownDocument(content=b"# Test", suffix=".md", stem="test")
    doc2 = doc1.copy()

    assert doc1 is not doc2
    assert doc1.content == doc2.content
    assert isinstance(doc2, MarkdownDocument)


# ==================== Attachment tests ====================
def test_attachment_initialization():
    """Test AttachMent initialization"""
    mock_doc = Document(suffix=".csv", content=b"test", stem="glossary")
    attachment = AttachMent(identifier="glossary", document=mock_doc)
    assert attachment.identifier == "glossary"
    assert attachment.document == mock_doc


def test_attachment_repr():
    """Test AttachMent __repr__ method"""
    mock_doc = Document(suffix=".csv", content=b"test", stem="glossary")
    attachment = AttachMent(identifier="glossary", document=mock_doc)
    assert repr(attachment) == "glossary.csv"


def test_attachment_manager_initialization():
    """Test AttachMentManager initialization"""
    manager = AttachMentManager()
    assert manager.attachment_dict == {}


def test_attachment_manager_add_document():
    """Test AttachMentManager.add_document method"""
    manager = AttachMentManager()
    mock_doc = Document(suffix=".csv", content=b"test", stem="glossary")
    manager.add_document("glossary", mock_doc)
    assert "glossary" in manager.attachment_dict
    assert manager.attachment_dict["glossary"] == mock_doc


def test_attachment_manager_add_attachment():
    """Test AttachMentManager.add_attachment method"""
    manager = AttachMentManager()
    mock_doc = Document(suffix=".csv", content=b"test", stem="glossary")
    attachment = AttachMent(identifier="glossary", document=mock_doc)
    manager.add_attachment(attachment)
    assert "glossary" in manager.attachment_dict
    assert manager.attachment_dict["glossary"] == mock_doc


def test_attachment_manager_multiple_attachments():
    """Test AttachMentManager with multiple attachments"""
    manager = AttachMentManager()

    # Add multiple attachments
    for identifier in ["glossary", "mineru", "docling"]:
        doc = Document(suffix=".txt", content=f"{identifier} content".encode(), stem=identifier)
        manager.add_document(identifier, doc)

    assert len(manager.attachment_dict) == 3
    assert "glossary" in manager.attachment_dict
    assert "mineru" in manager.attachment_dict
    assert "docling" in manager.attachment_dict
