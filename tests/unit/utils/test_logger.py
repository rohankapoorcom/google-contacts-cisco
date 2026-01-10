"""Unit tests for logging utilities.

This module tests the logging functionality including:
- Logger instance creation
- Log level configuration
- Handler setup
- Root logger configuration
"""

import logging
import sys
from unittest.mock import Mock, patch

from google_contacts_cisco.utils import logger as logger_module
from google_contacts_cisco.utils.logger import (
    DEFAULT_LOG_FORMAT,
    configure_root_logger,
    get_logger,
)


class TestDefaultLogFormat:
    """Test DEFAULT_LOG_FORMAT constant."""

    def test_default_log_format_is_string(self):
        """DEFAULT_LOG_FORMAT should be a string."""
        assert isinstance(DEFAULT_LOG_FORMAT, str)

    def test_default_log_format_includes_required_fields(self):
        """DEFAULT_LOG_FORMAT should include required logging fields."""
        assert "%(asctime)s" in DEFAULT_LOG_FORMAT
        assert "%(name)s" in DEFAULT_LOG_FORMAT
        assert "%(levelname)s" in DEFAULT_LOG_FORMAT
        assert "%(message)s" in DEFAULT_LOG_FORMAT


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_returns_logger_instance(self, monkeypatch):
        """Should return a logging.Logger instance."""
        mock_settings = Mock()
        mock_settings.log_level = "INFO"
        monkeypatch.setattr(logger_module, "settings", mock_settings)

        # Clear any existing handlers
        test_logger = logging.getLogger("test_module_1")
        test_logger.handlers.clear()

        result = get_logger("test_module_1")

        assert isinstance(result, logging.Logger)
        assert result.name == "test_module_1"

    def test_get_logger_sets_correct_level(self, monkeypatch):
        """Should set log level from settings."""
        mock_settings = Mock()
        mock_settings.log_level = "DEBUG"
        monkeypatch.setattr(logger_module, "settings", mock_settings)

        # Use unique logger name to avoid handler conflicts
        test_logger = logging.getLogger("test_module_debug")
        test_logger.handlers.clear()

        result = get_logger("test_module_debug")

        assert result.level == logging.DEBUG

    def test_get_logger_sets_warning_level(self, monkeypatch):
        """Should handle WARNING log level."""
        mock_settings = Mock()
        mock_settings.log_level = "WARNING"
        monkeypatch.setattr(logger_module, "settings", mock_settings)

        test_logger = logging.getLogger("test_module_warning")
        test_logger.handlers.clear()

        result = get_logger("test_module_warning")

        assert result.level == logging.WARNING

    def test_get_logger_sets_error_level(self, monkeypatch):
        """Should handle ERROR log level."""
        mock_settings = Mock()
        mock_settings.log_level = "ERROR"
        monkeypatch.setattr(logger_module, "settings", mock_settings)

        test_logger = logging.getLogger("test_module_error")
        test_logger.handlers.clear()

        result = get_logger("test_module_error")

        assert result.level == logging.ERROR

    def test_get_logger_adds_handler(self, monkeypatch):
        """Should add a StreamHandler."""
        mock_settings = Mock()
        mock_settings.log_level = "INFO"
        monkeypatch.setattr(logger_module, "settings", mock_settings)

        test_logger = logging.getLogger("test_module_handler")
        test_logger.handlers.clear()

        result = get_logger("test_module_handler")

        assert len(result.handlers) == 1
        assert isinstance(result.handlers[0], logging.StreamHandler)

    def test_get_logger_handler_outputs_to_stdout(self, monkeypatch):
        """Handler should output to stdout."""
        mock_settings = Mock()
        mock_settings.log_level = "INFO"
        monkeypatch.setattr(logger_module, "settings", mock_settings)

        test_logger = logging.getLogger("test_module_stdout")
        test_logger.handlers.clear()

        result = get_logger("test_module_stdout")

        handler = result.handlers[0]
        assert handler.stream == sys.stdout

    def test_get_logger_does_not_duplicate_handlers(self, monkeypatch):
        """Should not add duplicate handlers on repeated calls."""
        mock_settings = Mock()
        mock_settings.log_level = "INFO"
        monkeypatch.setattr(logger_module, "settings", mock_settings)

        test_logger = logging.getLogger("test_module_no_dup")
        test_logger.handlers.clear()

        # Call multiple times
        get_logger("test_module_no_dup")
        get_logger("test_module_no_dup")
        result = get_logger("test_module_no_dup")

        # Should still only have one handler
        assert len(result.handlers) == 1

    def test_get_logger_with_lowercase_level(self, monkeypatch):
        """Should handle lowercase log level."""
        mock_settings = Mock()
        mock_settings.log_level = "info"
        monkeypatch.setattr(logger_module, "settings", mock_settings)

        test_logger = logging.getLogger("test_module_lower")
        test_logger.handlers.clear()

        result = get_logger("test_module_lower")

        assert result.level == logging.INFO

    def test_get_logger_with_module_name_pattern(self, monkeypatch):
        """Should work with typical __name__ patterns."""
        mock_settings = Mock()
        mock_settings.log_level = "INFO"
        monkeypatch.setattr(logger_module, "settings", mock_settings)

        test_logger = logging.getLogger("google_contacts_cisco.services.test")
        test_logger.handlers.clear()

        result = get_logger("google_contacts_cisco.services.test")

        assert result.name == "google_contacts_cisco.services.test"

    def test_get_logger_handler_has_formatter(self, monkeypatch):
        """Handler should have a proper formatter configured."""
        mock_settings = Mock()
        mock_settings.log_level = "INFO"
        monkeypatch.setattr(logger_module, "settings", mock_settings)

        test_logger = logging.getLogger("test_module_formatter")
        test_logger.handlers.clear()

        result = get_logger("test_module_formatter")

        handler = result.handlers[0]
        assert handler.formatter is not None
        # Check format string matches the DEFAULT_LOG_FORMAT constant
        format_str = handler.formatter._fmt
        assert format_str == DEFAULT_LOG_FORMAT


class TestConfigureRootLogger:
    """Test configure_root_logger function."""

    def test_configure_root_logger_default_level(self, monkeypatch):
        """Should use settings log level by default."""
        mock_settings = Mock()
        mock_settings.log_level = "WARNING"
        monkeypatch.setattr(logger_module, "settings", mock_settings)

        with patch("logging.basicConfig") as mock_basic_config:
            configure_root_logger()

            mock_basic_config.assert_called_once()
            call_kwargs = mock_basic_config.call_args[1]
            assert call_kwargs["level"] == logging.WARNING

    def test_configure_root_logger_custom_level(self, monkeypatch):
        """Should use provided log level when specified."""
        mock_settings = Mock()
        mock_settings.log_level = "INFO"
        monkeypatch.setattr(logger_module, "settings", mock_settings)

        with patch("logging.basicConfig") as mock_basic_config:
            configure_root_logger(level="DEBUG")

            mock_basic_config.assert_called_once()
            call_kwargs = mock_basic_config.call_args[1]
            assert call_kwargs["level"] == logging.DEBUG

    def test_configure_root_logger_custom_format(self, monkeypatch):
        """Should use provided format string when specified."""
        mock_settings = Mock()
        mock_settings.log_level = "INFO"
        monkeypatch.setattr(logger_module, "settings", mock_settings)

        custom_format = "%(levelname)s: %(message)s"

        with patch("logging.basicConfig") as mock_basic_config:
            configure_root_logger(format_string=custom_format)

            mock_basic_config.assert_called_once()
            call_kwargs = mock_basic_config.call_args[1]
            assert call_kwargs["format"] == custom_format

    def test_configure_root_logger_has_handlers(self, monkeypatch):
        """Should configure with StreamHandler to stdout."""
        mock_settings = Mock()
        mock_settings.log_level = "INFO"
        monkeypatch.setattr(logger_module, "settings", mock_settings)

        with patch("logging.basicConfig") as mock_basic_config:
            configure_root_logger()

            call_kwargs = mock_basic_config.call_args[1]
            handlers = call_kwargs["handlers"]
            assert len(handlers) == 1
            assert isinstance(handlers[0], logging.StreamHandler)


class TestLoggerIntegration:
    """Integration tests for logger functionality."""

    def test_logger_can_log_messages(self, monkeypatch, capsys):
        """Logger should be able to log messages."""
        mock_settings = Mock()
        mock_settings.log_level = "DEBUG"
        monkeypatch.setattr(logger_module, "settings", mock_settings)

        # Get a fresh logger
        test_logger = logging.getLogger("test_integration_log")
        test_logger.handlers.clear()

        log = get_logger("test_integration_log")
        log.info("Test message")

        # Check output was written
        captured = capsys.readouterr()
        assert "Test message" in captured.out

    def test_logger_respects_level_filtering(self, monkeypatch, capsys):
        """Logger should not log messages below configured level."""
        mock_settings = Mock()
        mock_settings.log_level = "WARNING"
        monkeypatch.setattr(logger_module, "settings", mock_settings)

        test_logger = logging.getLogger("test_level_filter")
        test_logger.handlers.clear()

        log = get_logger("test_level_filter")
        log.debug("Debug message")
        log.info("Info message")

        captured = capsys.readouterr()
        assert "Debug message" not in captured.out
        assert "Info message" not in captured.out

    def test_logger_logs_at_and_above_level(self, monkeypatch, capsys):
        """Logger should log messages at or above configured level."""
        mock_settings = Mock()
        mock_settings.log_level = "WARNING"
        monkeypatch.setattr(logger_module, "settings", mock_settings)

        test_logger = logging.getLogger("test_level_allow")
        test_logger.handlers.clear()

        log = get_logger("test_level_allow")
        log.warning("Warning message")
        log.error("Error message")

        captured = capsys.readouterr()
        assert "Warning message" in captured.out
        assert "Error message" in captured.out
