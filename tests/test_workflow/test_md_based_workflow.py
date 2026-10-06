"""
Tests for MarkdownBasedWorkflow module
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from docutranslate.workflow.md_based_workflow import MarkdownBasedWorkflowConfig, MarkdownBasedWorkflow
from docutranslate.ir.document import Document


class TestMarkdownBasedWorkflowConfig:
    """Test MarkdownBasedWorkflowConfig dataclass"""

    def test_md_workflow_config_creation(self):
        """Test creating MarkdownBasedWorkflowConfig"""
        config = MarkdownBasedWorkflowConfig(
            convert_engine="identity",
            converter_config=None,
            translator_config=MagicMock(),
            html_exporter_config=MagicMock(),
            md2docx_exporter_config=None
        )
        assert config.convert_engine == "identity"
        assert config.converter_config is None


class TestMarkdownBasedWorkflow:
    """Test MarkdownBasedWorkflow class"""

    def test_md_workflow_init(self):
        """Test MarkdownBasedWorkflow initialization"""
        config = MagicMock(spec=MarkdownBasedWorkflowConfig)
        config.convert_engine = "identity"
        config.logger = None
        config.converter_config = None
        config.translator_config = MagicMock()
        config.html_exporter_config = MagicMock()
        config.md2docx_exporter_config = None

        workflow = MarkdownBasedWorkflow(config)

        assert workflow.convert_engine == "identity"
        assert workflow.document_original is None
        assert workflow.document_translated is None

    def test_md_workflow_read_path(self):
        """Test MarkdownBasedWorkflow read_path"""
        config = MagicMock(spec=MarkdownBasedWorkflowConfig)
        config.convert_engine = "identity"
        config.logger = None
        config.converter_config = None
        config.translator_config = MagicMock()
        config.html_exporter_config = MagicMock()
        config.md2docx_exporter_config = None

        workflow = MarkdownBasedWorkflow(config)

        # Create a mock document
        mock_document = MagicMock(spec=Document)
        mock_document.suffix = ".md"

        with patch.object(Document, 'from_path', return_value=mock_document) as mock_from_path:
            path = Path("/test/path.md")
            result = workflow.read_path(path)

            assert result == workflow
            assert workflow.document_original == mock_document
            mock_from_path.assert_called_once_with(path)

    def test_md_workflow_read_bytes(self):
        """Test MarkdownBasedWorkflow read_bytes"""
        config = MagicMock(spec=MarkdownBasedWorkflowConfig)
        config.convert_engine = "identity"
        config.logger = None
        config.converter_config = None
        config.translator_config = MagicMock()
        config.html_exporter_config = MagicMock()
        config.md2docx_exporter_config = None

        workflow = MarkdownBasedWorkflow(config)

        # Create a mock document
        mock_document = MagicMock(spec=Document)
        mock_document.suffix = ".md"

        with patch.object(Document, 'from_bytes', return_value=mock_document) as mock_from_bytes:
            content = b"test content"
            result = workflow.read_bytes(content, stem="test", suffix=".md")

            assert result == workflow
            assert workflow.document_original == mock_document
            mock_from_bytes.assert_called_once_with(content=content, stem="test", suffix=".md")

    def test_md_workflow_export_to_markdown(self):
        """Test export_to_markdown method"""
        config = MagicMock(spec=MarkdownBasedWorkflowConfig)
        config.convert_engine = "identity"
        config.logger = None
        config.converter_config = None
        config.translator_config = MagicMock()
        config.html_exporter_config = MagicMock()
        config.md2docx_exporter_config = None

        workflow = MarkdownBasedWorkflow(config)

        # Set up a translated document
        mock_document = MagicMock(spec=Document)
        mock_document.content = b"# Test"

        workflow.document_translated = mock_document

        with patch('docutranslate.workflow.md_based_workflow.MD2MDExporter') as mock_exporter_class:
            mock_exporter = MagicMock()
            mock_exporter.export.return_value = mock_document
            mock_exporter_class.return_value = mock_exporter

            result = workflow.export_to_markdown()

            mock_exporter_class.assert_called_once()
            mock_exporter.export.assert_called_once()

    def test_md_workflow_export_to_html(self):
        """Test export_to_html method"""
        config = MagicMock(spec=MarkdownBasedWorkflowConfig)
        config.convert_engine = "identity"
        config.logger = None
        config.converter_config = None
        config.translator_config = MagicMock()
        config.html_exporter_config = MagicMock()
        config.md2docx_exporter_config = None

        workflow = MarkdownBasedWorkflow(config)

        # Set up a translated document
        mock_document = MagicMock(spec=Document)
        mock_document.content = b"<html>Test</html>"

        workflow.document_translated = mock_document

        with patch('docutranslate.workflow.md_based_workflow.MD2HTMLExporter') as mock_exporter_class:
            mock_exporter = MagicMock()
            mock_exporter.export.return_value = mock_document
            mock_exporter_class.return_value = mock_exporter

            result = workflow.export_to_html()

            mock_exporter_class.assert_called_once()
            mock_exporter.export.assert_called_once()

    def test_md_workflow_export_without_translation(self):
        """Test that export raises RuntimeError when document not translated"""
        config = MagicMock(spec=MarkdownBasedWorkflowConfig)
        config.convert_engine = "identity"
        config.logger = None
        config.converter_config = None
        config.translator_config = MagicMock()
        config.html_exporter_config = MagicMock()
        config.md2docx_exporter_config = None

        workflow = MarkdownBasedWorkflow(config)

        with pytest.raises(RuntimeError, match="Document has not been translated yet"):
            workflow.export_to_markdown()
