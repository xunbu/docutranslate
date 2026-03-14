"""
Tests for logger module
"""
import logging

from docutranslate.logger.logger import global_logger


def test_logger_initialization():
    """Test that logger is properly initialized"""
    assert isinstance(global_logger, logging.Logger)
    assert global_logger.name == "TranslaterLogger"
    assert global_logger.level == logging.DEBUG


def test_logger_has_console_handler():
    """Test that logger has a StreamHandler configured"""
    handlers = global_logger.handlers
    assert len(handlers) >= 1
    assert any(isinstance(h, logging.StreamHandler) for h in handlers)


def test_logger_can_log_messages(caplog):
    """Test that logger can log messages at different levels"""
    # Set caplog to capture DEBUG level
    caplog.set_level(logging.DEBUG)

    test_messages = [
        (logging.DEBUG, "Debug message"),
        (logging.INFO, "Info message"),
        (logging.WARNING, "Warning message"),
        (logging.ERROR, "Error message"),
        (logging.CRITICAL, "Critical message"),
    ]

    for level, message in test_messages:
        global_logger.log(level, message)

    # Check that all messages were logged
    for level, message in test_messages:
        assert any(
            record.levelno == level and message in record.message
            for record in caplog.records
        )
