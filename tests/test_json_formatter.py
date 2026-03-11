"""Unit tests for CustomJSONLog formatter (JSON output fields)."""

import json
import logging

from brijyt_util import (
    CustomJSONLog,
    bind_contextvars,
    get_correlation_id,
    set_correlation_id,
    unbind_contextvars,
)


class TestCustomJSONLog:
    def test_format_produces_expected_fields(self):
        set_correlation_id("test-correlation-123")
        formatter = CustomJSONLog(api_version="0.1.0")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="hello",
            args=(),
            exc_info=None,
        )
        record.module = "mymodule"
        record.funcName = "myfunc"
        output = formatter.format(record)
        data = json.loads(output)
        assert data["@timestamp"]
        assert data["level"] == "INFO"
        assert data["msg"] == "hello"
        assert data["method"] == "mymodule.myfunc"
        assert data["correlationId"] == "test-correlation-123"
        assert data["version"] == "0.1.0"

    def test_format_includes_extra_from_record(self):
        set_correlation_id("")
        formatter = CustomJSONLog(api_version="1.0.0")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="msg",
            args=(),
            exc_info=None,
        )
        record.module = "x"
        record.funcName = "y"
        record.custom_key = "custom_value"
        output = formatter.format(record)
        data = json.loads(output)
        assert data["custom_key"] == "custom_value"
