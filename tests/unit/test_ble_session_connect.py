import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add repository root to path for test imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bb8_core.ble_session import BleSession, ConnectionError


def _mock_toy(address: str) -> MagicMock:
    toy = MagicMock()
    toy.address = address
    toy.name = ""
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
    mock_scanner.discover.assert_awaited_once_with(timeout=6.0)
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
                with pytest.raises(
                    ConnectionError,
                    match="Failed to connect after 2 attempts: scan boom",
                ):
                    asyncio.run(session.connect())

    assert not session.is_connected()
    assert mock_scanner.discover.await_count == 2
    mock_find_toys.assert_not_called()


def test_select_candidate_uses_normalized_mac_name_priority():
    session = BleSession("AA:BB:CC:DD:EE:FF")
    session._target_name = "BB-B54A"
    weak_name_match = _mock_toy("11:22:33:44:55:66")
    weak_name_match.name = "BB-B54A"
    exact_mac_match = _mock_toy("AA:BB:CC:DD:EE:FF")
    exact_mac_match.name = "Other"

    selected = session._select_candidate([weak_name_match, exact_mac_match])

    assert selected is exact_mac_match


def test_select_candidate_prefers_configured_identity_when_visibility_is_intermittent():
    session = BleSession("AA:BB:CC:DD:EE:FF")
    session._target_name = "BB-B54A"
    fallback_probable = _mock_toy("22:33:44:55:66:77")
    fallback_probable.name = "Sphero Droid"
    exact_name_match = _mock_toy("33:44:55:66:77:88")
    exact_name_match.name = "BB-B54A"

    selected = session._select_candidate([fallback_probable, exact_name_match])

    assert selected is exact_name_match
