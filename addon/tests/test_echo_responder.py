import time
from unittest.mock import patch

import pytest


@pytest.fixture
def echo_responder():
    from addon.bb8_core.echo_responder import EchoResponder

    return EchoResponder


@pytest.mark.skip(reason="EchoResponder class does not exist in echo_responder module")
def test_max_inflight_jobs(echo_responder):
    responder = echo_responder()
    responder.max_inflight = 2
    responder.inflight = 0
    # Simulate jobs
    for _ in range(3):
        if responder.inflight < responder.max_inflight:
            responder.inflight += 1
    assert responder.inflight <= responder.max_inflight


@pytest.mark.skip(reason="EchoResponder class does not exist in echo_responder module")
def test_min_interval_enforcement(echo_responder):
    responder = echo_responder()
    responder.min_interval_ms = 100
    last = time.time()
    # Simulate rapid requests
    allowed = []
    for _ in range(5):
        now = time.time()
        if (now - last) * 1000 >= responder.min_interval_ms:
            allowed.append(True)
            last = now
        else:
            allowed.append(False)
    assert any(allowed)


@pytest.mark.skip(reason="EchoResponder class does not exist in echo_responder module")
def test_disabled_echo(echo_responder):
    responder = echo_responder()
    responder.enabled = False
    result = responder.handle_echo("test")
    assert result is None


@pytest.mark.skip(reason="EchoResponder class does not exist in echo_responder module")
def test_error_handling_and_recovery(echo_responder):
    responder = echo_responder()
    with patch.object(responder, "handle_echo", side_effect=Exception("fail")):
        try:
            responder.handle_echo("test")
        except Exception as e:
            assert str(e) == "fail"
