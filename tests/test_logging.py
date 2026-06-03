"""Unit tests for brijyt_util.logging."""

import json
import logging
import re
from unittest.mock import Mock, patch

import pytest

from brijyt_util import (
    LoggerAdapter,
    configure_logging,
    get_correlation_id,
    get_log_context,
    get_logger,
    set_correlation_id,
    bind_contextvars,
    unbind_contextvars,
)


class TestCorrelationId:
    def test_get_correlation_id_default_empty(self):
        set_correlation_id("")
        assert get_correlation_id() == ""

    def test_set_and_get_correlation_id(self):
        set_correlation_id("req-123")
        assert get_correlation_id() == "req-123"


class TestLogContext:
    def test_get_log_context_includes_correlation_id(self):
        set_correlation_id("cid-456")
        ctx = get_log_context()
        assert ctx["correlationId"] == "cid-456"

    def test_get_log_context_includes_bound_vars(self):
        set_correlation_id("")
        bind_contextvars(userId="user-1", messageId="msg-2")
        ctx = get_log_context()
        assert ctx["userId"] == "user-1"
        assert ctx["messageId"] == "msg-2"
        unbind_contextvars("userId", "messageId")

    def test_unbind_contextvars_removes_keys(self):
        bind_contextvars(foo="bar", baz="qux")
        unbind_contextvars("foo")
        ctx = get_log_context()
        assert "foo" not in ctx
        assert ctx.get("baz") == "qux"
        unbind_contextvars("baz")


class TestConfigureLogging:
    @patch("brijyt_util.logging.logging.config.dictConfig")
    def test_configure_logging_calls_dict_config(self, mock_dict_config):
        configure_logging("1.0.0")
        mock_dict_config.assert_called_once()
        call_args = mock_dict_config.call_args[0][0]
        assert call_args["version"] == 1
        assert "app" in call_args["loggers"]
        assert "standard" in call_args["formatters"]
        formatter_config = call_args["formatters"]["standard"]
        assert formatter_config["api_version"] == "1.0.0"

    @patch("brijyt_util.logging.logging.config.dictConfig")
    def test_configure_logging_console_format_when_log_format_console(self, mock_dict_config):
        with patch.dict("os.environ", {"LOG_FORMAT": "console"}, clear=False):
            configure_logging("0.1.0")
        call_args = mock_dict_config.call_args[0][0]
        assert call_args["handlers"]["console"]["formatter"] == "console"
        assert "console" in call_args["formatters"]
        assert call_args["formatters"]["console"]["()"].__name__ == "ConsoleLog"

    @patch("brijyt_util.logging.logging.config.dictConfig")
    def test_configure_logging_console_format_when_log_format_human(self, mock_dict_config):
        with patch.dict("os.environ", {"LOG_FORMAT": "human"}, clear=False):
            configure_logging("0.1.0")
        call_args = mock_dict_config.call_args[0][0]
        assert call_args["handlers"]["console"]["formatter"] == "console"


class TestConsoleLogFormat:
    """Test ConsoleLog one-line format: HH:MM:SS LEVEL msg contextVar: {}."""

    def test_console_log_format_contains_time_level_msg_context_var(self):
        from brijyt_util.logging import ConsoleLog

        set_correlation_id("cid-123")
        formatter = ConsoleLog(api_version="1.0.0")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="hello",
            args=(),
            exc_info=None,
        )
        record.getMessage = lambda: "hello"
        output = formatter.format(record)
        assert re.search(r"\d{2}:\d{2}:\d{2}", output)
        assert "INFO" in output
        assert "hello" in output
        assert "contextVar:" in output
        assert "cid-123" in output or "correlationId" in output

    def test_console_log_format_includes_extra_kwargs(self):
        from brijyt_util.logging import ConsoleLog

        set_correlation_id("")
        formatter = ConsoleLog(api_version="")
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="",
            lineno=0,
            msg="msg",
            args=(),
            exc_info=None,
        )
        record.getMessage = lambda: "msg"
        record.userId = "u1"
        output = formatter.format(record)
        assert "contextVar:" in output
        assert "userId" in output or "u1" in output


class TestGetLogger:
    def test_get_logger_returns_logger_adapter(self):
        logger = get_logger("test_module")
        assert isinstance(logger, LoggerAdapter)
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "debug")

    @patch("brijyt_util.logging.logging.getLogger")
    def test_get_logger_calls_stdlib_get_logger(self, mock_get_logger):
        mock_stdlib_logger = Mock()
        mock_get_logger.return_value = mock_stdlib_logger
        result = get_logger("test.module")
        mock_get_logger.assert_called_once_with("test.module")
        assert isinstance(result, LoggerAdapter)
        assert result._logger is mock_stdlib_logger


class TestLoggerAdapter:
    def test_info_with_kwargs_forwards_extra(self):
        mock_logger = Mock()
        adapter = LoggerAdapter(mock_logger)
        adapter.info("hello", key="value")
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "hello"
        assert call_args[1]["extra"].get("key") == "value"

    def test_error_with_format_args(self):
        mock_logger = Mock()
        adapter = LoggerAdapter(mock_logger)
        adapter.error("Error: %s", "something failed")
        mock_logger.error.assert_called_once()
        assert mock_logger.error.call_args[0][:2] == ("Error: %s", "something failed")
        assert "extra" in mock_logger.error.call_args[1]

    def test_exception_forwards_to_stdlib(self):
        mock_logger = Mock()
        adapter = LoggerAdapter(mock_logger)
        adapter.exception("oops", code=500)
        mock_logger.exception.assert_called_once()
        assert mock_logger.exception.call_args[1]["extra"].get("code") == 500
        assert mock_logger.exception.call_args[1]["exc_info"] is True

    def test_error_with_exc_info_forwards_to_stdlib(self):
        mock_logger = Mock()
        adapter = LoggerAdapter(mock_logger)
        adapter.error("failed", code=500, exc_info=True)
        mock_logger.error.assert_called_once()
        call_kwargs = mock_logger.error.call_args[1]
        assert call_kwargs["exc_info"] is True
        assert call_kwargs["extra"].get("code") == 500
        assert "exc_info" not in call_kwargs["extra"]
