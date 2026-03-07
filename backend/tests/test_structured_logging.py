"""Tests for the structured logging system."""
import json
import logging

from core_app.core.logging import StructuredJsonFormatter, configure_logging, get_logger


def test_structured_formatter_produces_valid_json() -> None:
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["message"] == "hello world"
    assert parsed["level"] == "INFO"
    assert parsed["service"] == "fusionems-core"
    assert "timestamp" in parsed


def test_structured_formatter_includes_correlation_id() -> None:
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="t.py", lineno=1,
        msg="test", args=(), exc_info=None,
    )
    record.correlation_id = "abc-123"  # type: ignore[attr-defined]
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["correlation_id"] == "abc-123"


def test_structured_formatter_includes_exception() -> None:
    formatter = StructuredJsonFormatter()
    try:
        raise ValueError("test error")
    except ValueError:
        import sys
        exc_info = sys.exc_info()
    record = logging.LogRecord(
        name="test", level=logging.ERROR, pathname="t.py", lineno=1,
        msg="failed", args=(), exc_info=exc_info,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["exception"]["type"] == "ValueError"
    assert parsed["exception"]["message"] == "test error"


def test_get_logger_returns_named_logger() -> None:
    lg = get_logger("mymodule")
    assert lg.name == "mymodule"


def test_configure_logging_sets_level() -> None:
    configure_logging("WARNING")
    root = logging.getLogger()
    assert root.level == logging.WARNING
    # Reset
    configure_logging("INFO")
