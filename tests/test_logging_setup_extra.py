import io
import logging
import os

from addon.bb8_core import logging_setup as ls


def test_get_log_level_override(monkeypatch):
    # explicit override should be respected
    assert ls.get_log_level("debug") == logging.DEBUG
    assert ls.get_log_level("INFO") == logging.INFO


def test__get_log_level_env(monkeypatch):
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("LOGGING_LEVEL", raising=False)
    monkeypatch.setenv("BB8_LOG_LEVEL", "WARNING")
    assert ls._get_log_level() == logging.WARNING


def test_redact_masks_secrets():
    s = "password=supersecret token=abcd1234 other=ok"
    r = ls.redact(s)
    assert "***REDACTED***" in r
    assert "supersecret" not in r
    assert "abcd1234" not in r


def test_json_redacting_handler_emits_redacted():
    handler = ls.JsonRedactingHandler()
    stream = io.StringIO()
    handler.stream = stream
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg={"password": "secret", "user": "u"},
        args=(),
        exc_info=None,
    )
    handler.emit(record)
    out = stream.getvalue()
    assert "***REDACTED***" in out
    assert "secret" not in out


def test_setup_logging_changes_level():
    # Ensure setup_logging sets level appropriately
    ls.setup_logging("WARNING")
    assert ls.logger.level == logging.WARNING
    assert ls.bridge_logger.level == logging.WARNING
    assert ls.ble_logger.level == logging.WARNING
