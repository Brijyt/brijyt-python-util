"""Unit tests for brijyt_util.logging."""

import json
import logging
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
