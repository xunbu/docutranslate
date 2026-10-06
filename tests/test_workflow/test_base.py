"""
Tests for workflow base module
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from docutranslate.workflow.base import WorkflowConfig, Workflow
from docutranslate.ir.document import Document


class TestWorkflowConfig:
    """Test WorkflowConfig dataclass"""

    def test_workflow_config_default(self):
        """Test WorkflowConfig with default values"""
        config = WorkflowConfig()
        assert config.logger is not None
        assert config.progress_tracker is None

    def test_workflow_config_with_logger(self):
        """Test WorkflowConfig with custom logger"""
        import logging

        custom_logger = logging.getLogger("test_logger")
        config = WorkflowConfig(logger=custom_logger)
        assert config.logger == custom_logger


class ConcreteWorkflow(Workflow):
    """Concrete implementation of Workflow for testing"""

    def translate(self, *args, **kwargs):
        self.document_translated = self.document_original
        return self

    async def translate_async(self, *args, **kwargs):
        self.document_translated = self.document_original
        return self


class TestWorkflow:
    """Test Workflow base class"""

    def test_workflow_init_with_config(self):
        """Test Workflow initialization with config"""
        config = WorkflowConfig()
        workflow = ConcreteWorkflow(config=config)
        assert workflow.config == config
        assert workflow.logger == config.logger

    def test_workflow_init_without_translate(self):
        """Test workflow document_original is None initially"""
        config = WorkflowConfig()
        workflow = ConcreteWorkflow(config=config)
        assert workflow.document_original is None
        assert workflow.document_translated is None

    def test_workflow_read_path(self):
        """Test Workflow read_path method"""
        config = WorkflowConfig()
        workflow = ConcreteWorkflow(config=config)

        # Create a mock document
        mock_document = MagicMock(spec=Document)
        mock_document.suffix = ".md"

        with patch.object(Document, 'from_path', return_value=mock_document) as mock_from_path:
            path = Path("/test/path.md")
            result = workflow.read_path(path)

            assert result == workflow
            assert workflow.document_original == mock_document
            mock_from_path.assert_called_once_with(path)

    def test_workflow_read_bytes(self):
        """Test Workflow read_bytes method"""
        config = WorkflowConfig()
        workflow = ConcreteWorkflow(config=config)

        # Create a mock document
        mock_document = MagicMock(spec=Document)
        mock_document.suffix = ".md"

        with patch.object(Document, 'from_bytes', return_value=mock_document) as mock_from_bytes:
            content = b"test content"
            result = workflow.read_bytes(content, stem="test", suffix=".md")

            assert result == workflow
            assert workflow.document_original == mock_document
            mock_from_bytes.assert_called_once_with(content=content, stem="test", suffix=".md")

    def test_workflow_export_without_translation(self):
        """Test that export raises RuntimeError when document not translated"""
        config = WorkflowConfig()
        workflow = ConcreteWorkflow(config=config)

        # Create a mock exporter
        mock_exporter = MagicMock()

        with pytest.raises(RuntimeError, match="Document has not been translated yet"):
            workflow._export(mock_exporter)

    def test_workflow_save(self, temp_dir):
        """Test Workflow save method"""
        config = WorkflowConfig()
        workflow = ConcreteWorkflow(config=config)

        # Set up a translated document
        mock_document = MagicMock(spec=Document)
        mock_document.name = "test_output.md"
        mock_document.content = b"translated content"

        # Set the translated document so _export will work
        workflow.document_translated = mock_document

        # Create a mock exporter that returns the mock document
        mock_exporter = MagicMock()
        mock_exporter.export.return_value = mock_document

        # Run the save method
        output_file = temp_dir / "test_output.md"
        result = workflow._save(mock_exporter, name="test_output.md", output_dir=temp_dir)

        assert result == workflow
        assert output_file.exists()
        assert output_file.read_bytes() == b"translated content"

    def test_workflow_get_attachment(self):
        """Test Workflow get_attachment method"""
        config = WorkflowConfig()
        workflow = ConcreteWorkflow(config=config)

        attachment = workflow.get_attachment()
        assert attachment is not None
        # Verify attachment manager is initialized
        assert hasattr(workflow, 'attachment')
