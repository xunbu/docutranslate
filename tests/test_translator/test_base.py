"""
Tests for translator base module
"""
import pytest
from unittest.mock import MagicMock

from docutranslate.translator.base import TranslatorConfig, Translator


class ConcreteTranslator(Translator):
    """Concrete implementation of Translator for testing"""

    def translate(self, document):
        return document

    async def translate_async(self, document):
        return document


class TestTranslatorConfig:
    """Test TranslatorConfig dataclass"""

    def test_translator_config_default(self):
        """Test TranslatorConfig with default values"""
        config = TranslatorConfig()
        assert config.logger is not None
        assert config.progress_tracker is None

    def test_translator_config_with_logger(self):
        """Test TranslatorConfig with custom logger"""
        import logging

        custom_logger = logging.getLogger("test_logger")
        config = TranslatorConfig(logger=custom_logger)
        assert config.logger == custom_logger

    def test_translator_config_with_progress_tracker(self):
        """Test TranslatorConfig with progress tracker"""
        mock_tracker = MagicMock()
        config = TranslatorConfig(progress_tracker=mock_tracker)
        assert config.progress_tracker == mock_tracker


class TestTranslator:
    """Test Translator base class"""

    def test_translator_init_without_config(self):
        """Test Translator initialization without config"""
        translator = ConcreteTranslator(config=None)
        assert translator.config is None
        assert translator.logger is not None

    def test_translator_init_with_config(self):
        """Test Translator initialization with config"""
        config = TranslatorConfig()
        translator = ConcreteTranslator(config=config)
        assert translator.config == config
        assert translator.logger == config.logger
        assert translator.progress_tracker is None

    def test_translator_init_with_progress_tracker(self):
        """Test Translator initialization with progress tracker"""
        mock_tracker = MagicMock()
        config = TranslatorConfig(progress_tracker=mock_tracker)
        translator = ConcreteTranslator(config=config)
        assert translator.progress_tracker == mock_tracker
