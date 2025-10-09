import types
from unittest.mock import AsyncMock

import pytest

import addon.bb8_core.ble_gateway as ble_gateway


class DummyDevice:
    def __init__(self, name="BB-8", address="AA:BB:CC:DD:EE:FF", rssi=-60):
        self.name = name
        self.address = address
        self.rssi = rssi


def test_init_and_resolve_adapter():
    g = ble_gateway.BleGateway(mode="bleak", adapter="hci0")
    assert g.mode == "bleak"
    assert g.adapter == "hci0"
    assert g.resolve_adapter() == "hci0"
    g2 = ble_gateway.BleGateway(mode="other", adapter=None)
    assert g2.resolve_adapter() is None


def test_get_connection_status():
    g = ble_gateway.BleGateway()
    # device not set
    assert g.get_connection_status()["connected"] is False
    # device set
    g.device = object()
    assert g.get_connection_status()["connected"] is True


@pytest.mark.asyncio
async def test_scan_bleak(monkeypatch):
    g = ble_gateway.BleGateway(mode="bleak", adapter="hci0")
    # Patch BleakScanner.discover to return dummy devices
    dummy_devices = [
        DummyDevice(),
        DummyDevice(name="Other", address="11:22:33:44:55:66", rssi=-70),
    ]
    monkeypatch.setattr(
        ble_gateway,
        "BleakScanner",
        types.SimpleNamespace(discover=AsyncMock(return_value=dummy_devices)),
    )
    result = await g.scan(seconds=1)
    assert isinstance(result, list)
    assert any(d["address"] == "AA:BB:CC:DD:EE:FF" for d in result)


@pytest.mark.asyncio
async def test_scan_non_bleak(monkeypatch):
    g = ble_gateway.BleGateway(mode="other")
    # BleakScanner is None, should bypass
    monkeypatch.setattr(ble_gateway, "BleakScanner", None)
    result = await g.scan(seconds=1)
    assert result == []


def test_shutdown_normal_and_error(monkeypatch):
    g = ble_gateway.BleGateway()
    # Normal shutdown
    g.device = object()
    g.shutdown()
    assert getattr(g, "device", None) is None

    # Error branch: simulate exception
    class ErrorDeviceGateway(ble_gateway.BleGateway):
        @property
        def device(self):
            raise RuntimeError("fail")

    g2 = ErrorDeviceGateway()
    # Should not raise
    g2.shutdown()


def test_init_and_initialized():
    # Reset _initialized
    ble_gateway._initialized = False
    ble_gateway.init()
    assert ble_gateway.initialized() is True
    # Second call should not change state
    ble_gateway.init()
