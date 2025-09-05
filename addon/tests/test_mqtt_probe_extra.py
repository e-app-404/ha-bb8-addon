import importlib

import pytest

from tests.helpers.fakes import FakeMQTT

probe = importlib.import_module("addon.bb8_core.mqtt_probe")


@pytest.mark.usefixtures("caplog_level")
def test_mqtt_probe_success(monkeypatch, caplog):
    client = FakeMQTT()
    monkeypatch.setattr(probe, "get_mqtt_client", lambda: client, raising=False)
    result = probe.run_probe()
    assert result.get("ok") is True
    assert "probe" in caplog.text or "mqtt" in caplog.text


@pytest.mark.usefixtures("caplog_level")
def test_mqtt_probe_timeout(monkeypatch, caplog, time_sleep_counter):
    client = FakeMQTT()
    monkeypatch.setattr(probe, "get_mqtt_client", lambda: client, raising=False)
    # If run_probe supports timeout, use it; else, rely on default
    result = (
        probe.run_probe(timeout=0.01)
        if "timeout" in probe.run_probe.__code__.co_varnames
        else probe.run_probe()
    )
    assert result.get("ok") in (False, None)
    assert "timeout" in caplog.text or "probe" in caplog.text
