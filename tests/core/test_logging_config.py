import json
import logging
from unittest.mock import MagicMock

from server.core.logging_config import JsonLogFormatter, LoggingConfigurator


def test_json_log_formatter_includes_request_id_and_exception():
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="prm.test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="boom",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-123"
    try:
        raise ValueError("fail")
    except ValueError:
        import sys

        record.exc_info = sys.exc_info()

    payload = json.loads(formatter.format(record))
    assert payload["level"] == "ERROR"
    assert payload["message"] == "boom"
    assert payload["request_id"] == "req-123"
    assert "ValueError" in payload["exc_info"]
    assert "timestamp" in payload


def test_logging_configurator_text_format():
    settings = MagicMock()
    settings.log_format = "text"
    root = logging.getLogger()
    previous = list(root.handlers)

    LoggingConfigurator().configure(settings)

    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0].formatter, logging.Formatter)
    assert not isinstance(root.handlers[0].formatter, JsonLogFormatter)
    assert root.level == logging.INFO

    root.handlers.clear()
    for handler in previous:
        root.addHandler(handler)


def test_logging_configurator_json_format():
    settings = MagicMock()
    settings.log_format = "json"
    root = logging.getLogger()
    previous = list(root.handlers)

    LoggingConfigurator().configure(settings)

    assert isinstance(root.handlers[0].formatter, JsonLogFormatter)

    root.handlers.clear()
    for handler in previous:
        root.addHandler(handler)
