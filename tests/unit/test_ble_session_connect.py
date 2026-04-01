import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add repository root to path for test imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bb8_core.ble_session import BleSession, ConnectionError


def _mock_toy(address: str) -> MagicMock:
    toy = MagicMock()
    toy.address = address
    toy.__enter__ = MagicMock(return_value=toy)
    toy.__exit__ = MagicMock(return_value=None)
    return toy


def test_connect_uses_async_safe_bleak_discovery():
    session = BleSession("AA:BB:CC:DD:EE:FF")
    toy = _mock_toy("AA:BB:CC:DD:EE:FF")

    with patch("bb8_core.ble_session.find_toys") as mock_find_toys:
        with patch("bb8_core.ble_session.BB8", None):
            with patch("bb8_core.ble_session.BleakScanner") as mock_scanner:
                mock_scanner.discover = AsyncMock(return_value=[toy])
                asyncio.run(session.connect())

    assert session.is_connected()
    mock_scanner.discover.assert_awaited_once_with(timeout=5.0)
    mock_find_toys.assert_not_called()


def test_connect_consumes_result_after_async_safe_scan():
    session = BleSession("AA:BB:CC:DD:EE:FF")
    toy = _mock_toy("AA:BB:CC:DD:EE:FF")

    with patch("bb8_core.ble_session.find_toys") as mock_find_toys:
        with patch("bb8_core.ble_session.BB8", None):
            with patch("bb8_core.ble_session.BleakScanner") as mock_scanner:
                mock_scanner.discover = AsyncMock(return_value=[toy])
                asyncio.run(session.connect())

    assert session._toy is toy
    assert session._connect_attempts == 1
    mock_find_toys.assert_not_called()


def test_connect_raises_when_async_safe_discovery_fails():
    session = BleSession("AA:BB:CC:DD:EE:FF")

    with patch("bb8_core.ble_session.find_toys") as mock_find_toys:
        with patch("bb8_core.ble_session.BleakScanner") as mock_scanner:
            mock_scanner.discover = AsyncMock(side_effect=RuntimeError("scan boom"))
            with patch("bb8_core.ble_session.asyncio.sleep", new=AsyncMock()):
                import pytest

                with pytest.raises(
                    ConnectionError,
                    match="Failed to connect after 2 attempts: scan boom",
                ):
                    asyncio.run(session.connect())

    assert not session.is_connected()
    assert mock_scanner.discover.await_count == 2
    mock_find_toys.assert_not_called()