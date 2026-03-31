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


def test_connect_uses_to_thread_for_sync_discovery():
    session = BleSession("AA:BB:CC:DD:EE:FF")
    toy = _mock_toy("AA:BB:CC:DD:EE:FF")

    async def run_inline(func, *args, **kwargs):
        return func(*args, **kwargs)

    with patch("bb8_core.ble_session.find_toys", return_value=[toy]) as mock_find_toys:
        with patch("bb8_core.ble_session.BB8", None):
            with patch(
                "bb8_core.ble_session.asyncio.to_thread",
                new=AsyncMock(side_effect=run_inline),
            ) as mock_to_thread:
                asyncio.run(session.connect())

    assert session.is_connected()
    assert mock_to_thread.await_args_list[0].args[0] is mock_find_toys
    assert mock_to_thread.await_args_list[0].kwargs == {"timeout": 5.0}


def test_connect_consumes_discovery_result_after_threaded_scan():
    session = BleSession("AA:BB:CC:DD:EE:FF")
    toy = _mock_toy("AA:BB:CC:DD:EE:FF")

    async def run_inline(func, *args, **kwargs):
        return func(*args, **kwargs)

    with patch("bb8_core.ble_session.find_toys", return_value=[toy]):
        with patch("bb8_core.ble_session.BB8", None):
            with patch(
                "bb8_core.ble_session.asyncio.to_thread",
                new=AsyncMock(side_effect=run_inline),
            ):
                asyncio.run(session.connect())

    assert session._toy is toy
    assert session._connect_attempts == 1


def test_connect_raises_when_threaded_discovery_fails():
    session = BleSession("AA:BB:CC:DD:EE:FF")

    async def run_inline(func, *args, **kwargs):
        return func(*args, **kwargs)

    with patch(
        "bb8_core.ble_session.find_toys",
        side_effect=RuntimeError("scan boom"),
    ) as mock_find_toys:
        with patch(
            "bb8_core.ble_session.asyncio.to_thread",
            new=AsyncMock(side_effect=run_inline),
        ) as mock_to_thread:
            with patch("bb8_core.ble_session.asyncio.sleep", new=AsyncMock()):
                import pytest

                with pytest.raises(
                    ConnectionError,
                    match="Failed to connect after 2 attempts: scan boom",
                ):
                    asyncio.run(session.connect())

    assert not session.is_connected()
    assert mock_find_toys.call_count == 2
    assert mock_to_thread.await_count == 2