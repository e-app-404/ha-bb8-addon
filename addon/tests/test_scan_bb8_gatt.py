import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest

import addon.bb8_core.scan_bb8_gatt as scan_bb8_gatt

sys.modules["bleak"] = types.SimpleNamespace(
    BleakClient=MagicMock(), BleakScanner=MagicMock()
)


@pytest.mark.asyncio
async def test_main_device_found(monkeypatch):
    # Setup mocks
    mock_device = MagicMock()
    mock_device.name = "BB-8"
    mock_device.address = "12:34:56:78:90:AB"
    mock_service = MagicMock()
    mock_service.uuid = "service-uuid"
    mock_service.description = "Service Desc"
    mock_char = MagicMock()
    mock_char.uuid = "char-uuid"
    mock_char.description = "Char Desc"
    mock_char.properties = ["read", "write"]
    mock_service.characteristics = [mock_char]
    mock_client = AsyncMock()
    mock_client.get_services.return_value = [mock_service]
    mock_scanner = MagicMock()
    mock_scanner.discovered_devices = [mock_device]

    # Patch BleakScanner context manager
    class DummyScanner:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return mock_scanner

        async def __aexit__(self, exc_type, exc, tb):
            pass

    # Patch BleakClient context manager
    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return mock_client

        async def __aexit__(self, exc_type, exc, tb):
            pass

    monkeypatch.setattr(scan_bb8_gatt, "BleakScanner", DummyScanner)
    monkeypatch.setattr(scan_bb8_gatt, "BleakClient", DummyClient)
    # Patch asyncio.sleep to skip delay
    monkeypatch.setattr(scan_bb8_gatt.asyncio, "sleep", AsyncMock())
    # Capture print output
    output = []
    monkeypatch.setattr(
        scan_bb8_gatt, "print", lambda *a, **k: output.append(" ".join(map(str, a)))
    )
    await scan_bb8_gatt.main("hci0", "BB-8")
    assert any("Found BB-8" in line for line in output)
    assert any(
        "Connected. Querying services/characteristics" in line for line in output
    )
    assert any("[Service]" in line for line in output)
    assert any("[Characteristic]" in line for line in output)


@pytest.mark.asyncio
async def test_main_device_not_found(monkeypatch):
    # No devices found
    mock_scanner = MagicMock()
    mock_scanner.discovered_devices = []

    class DummyScanner:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return mock_scanner

        async def __aexit__(self, exc_type, exc, tb):
            pass

    monkeypatch.setattr(scan_bb8_gatt, "BleakScanner", DummyScanner)
    monkeypatch.setattr(scan_bb8_gatt.asyncio, "sleep", AsyncMock())
    output = []
    monkeypatch.setattr(
        scan_bb8_gatt, "print", lambda *a, **k: output.append(" ".join(map(str, a)))
    )
    await scan_bb8_gatt.main("hci0", "BB-8")
    assert any("BB-8 not found" in line for line in output)


@pytest.mark.asyncio
async def test_main_fallback_device(monkeypatch):
    # Fallback to Sphero device
    mock_device = MagicMock()
    mock_device.name = "SpheroBB"
    mock_device.address = "12:34:56:78:90:AB"
    mock_scanner = MagicMock()
    mock_scanner.discovered_devices = [mock_device]

    class DummyScanner:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return mock_scanner

        async def __aexit__(self, exc_type, exc, tb):
            pass

    monkeypatch.setattr(scan_bb8_gatt, "BleakScanner", DummyScanner)
    monkeypatch.setattr(scan_bb8_gatt.asyncio, "sleep", AsyncMock())
    output = []
    monkeypatch.setattr(
        scan_bb8_gatt, "print", lambda *a, **k: output.append(" ".join(map(str, a)))
    )

    # Patch BleakClient to skip connection
    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return AsyncMock()

        async def __aexit__(self, exc_type, exc, tb):
            pass

    monkeypatch.setattr(scan_bb8_gatt, "BleakClient", DummyClient)
    await scan_bb8_gatt.main("hci0", "BB-8")
    assert any("Found BB-8" in line for line in output)
