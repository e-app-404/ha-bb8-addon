import logging

import pytest

from tests.helpers.util import assert_contains_log


@pytest.mark.usefixtures("caplog_level")
def test_logging_formatter(caplog):
    logger = logging.getLogger("bb8.test")
    logger.info("hello world")
    assert_contains_log(caplog, "hello world")
    for r in caplog.records:
        assert r.levelname == "INFO"
        assert "bb8" in r.name


@pytest.mark.usefixtures("caplog_level")
def test_no_duplicate_handlers():
    logger = logging.getLogger("bb8.test2")
    h1 = logging.StreamHandler()
    h2 = logging.StreamHandler()
    logger.addHandler(h1)
    logger.addHandler(h2)
    assert len(logger.handlers) == 2
    logger.handlers.clear()
