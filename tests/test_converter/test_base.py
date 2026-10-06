"""
Tests for converter base module
"""
import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass
from typing import Hashable

from docutranslate.converter.base import ConverterConfig, Converter


@dataclass(kw_only=True)
class ConcreteConverterConfig(ConverterConfig):
    """Concrete implementation of ConverterConfig for testing"""

    def gethash(self) -> Hashable:
        return "concrete_config_hash"


class ConcreteConverter(Converter):
    """Concrete implementation of Converter for testing"""

    def convert(self, document):
        return document

    async def convert_async(self, document):
        return document


class TestConverterConfig:
    """Test ConverterConfig abstract dataclass"""

    def test_converter_config_default(self):
        """Test ConverterConfig with default values"""
        config = ConcreteConverterConfig()
        assert config.logger is not None
        assert config.gethash() == "concrete_config_hash"

    def test_converter_config_with_logger(self):
        """Test ConverterConfig with custom logger"""
        import logging

        custom_logger = logging.getLogger("test_logger")
        config = ConcreteConverterConfig(logger=custom_logger)
        assert config.logger == custom_logger


class TestConverter:
    """Test Converter base class"""

    def test_converter_init_without_config(self):
        """Test Converter initialization without config"""
        converter = ConcreteConverter(config=None)
        assert converter.config is None
        assert not hasattr(converter, 'logger') or converter.logger is None

    def test_converter_init_with_config(self):
        """Test Converter initialization with config"""
        config = ConcreteConverterConfig()
        converter = ConcreteConverter(config=config)
        assert converter.config == config
        assert converter.logger == config.logger

    def test_converter_convert_abstract(self):
        """Test that Converter is abstract and cannot be instantiated directly"""
        with pytest.raises(TypeError):
            Converter()

    def test_converter_convert_method_is_abstract(self):
        """Test that convert method must be implemented by subclass"""
        config = ConcreteConverterConfig()

        # Create a subclass that doesn't implement convert
        class IncompleteConverter(Converter):
            pass

        with pytest.raises(TypeError):
            IncompleteConverter(config)
