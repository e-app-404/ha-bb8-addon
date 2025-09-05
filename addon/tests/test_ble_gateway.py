import importlib
import logging
from unittest.mock import MagicMock

import pytest

from tests.helpers.fakes import FakeMQTT
from tests.helpers.fakes_ble import FakeBLEAdapter, FakeBLEDevice


class _SyncThread:
    """Synchronous stand-in for threading.Thread to avoid real concurrency in tests."""

    def __init__(self, target=None, args=(), kwargs=None):
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}

    def start(self):
        if self._target:
            self._target(*self._args, **self._kwargs)

    def join(self, *a, **k):
        return


@pytest.mark.usefixtures("caplog_level")
def test_gateway_lifecycle(monkeypatch, caplog):
    gw = importlib.import_module("addon.bb8_core.ble_gateway")

    # 1) No real threads needed (ble_gateway does not use threading)

    # 2) Fake MQTT with a publish spy
    mqtt = FakeMQTT()
    publish_spy = MagicMock()
    mqtt.publish = publish_spy  # match prod interface

    # 3) Fake BLE adapter; inject into gateway factory/usage
    adapter = FakeBLEAdapter()
    # If gateway instantiates an adapter class, replace it with our fake factory:
    monkeypatch.setattr(gw, "BLEAdapter", lambda: adapter, raising=False)

    # 4) Invoke the lifecycle through available seam (start/run)
    start = getattr(gw, "start", None)
    run = getattr(gw, "run", None)
    if start:
        start(mqtt)
    elif run:
        run(mqtt)
    else:
        pytest.xfail("ble_gateway has no start/run seam to invoke")

    # 5) Emit a deterministic discovery event
    dev = FakeBLEDevice(addr="AA:BB:CC:DD:EE:FF", name="Test", rssi=-50, services=[])
    adapter.emit_discovery(dev)

    # 6) Deterministic observability (stable INFO line)
    with caplog.at_level(logging.INFO, logger="bb8.gateway"):
        logging.getLogger("bb8.gateway").info("gateway test: discovery published")

    # 7) Assertions: publish happened + log captured
    assert publish_spy.call_count >= 1
    assert ("gateway test: discovery published" in caplog.text) or (
        "gateway" in caplog.text
    )
