import asyncio
import sys
from pathlib import Path

import pytest

# Add repository root to path for test imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bb8_core.ble_session import BleSession, BleSessionError


class _FailingToy:
    def set_main_led(self, r, g, b, _flags):
        raise RuntimeError("gatt write failed")


def test_led_hardware_failure_invalidates_session_truth():
    session = BleSession("AA:BB:CC:DD:EE:FF")
    session._connected = True
    session._toy = _FailingToy()

    with pytest.raises(BleSessionError, match="LED set failed"):
        asyncio.run(session.set_led(0, 255, 0))

    assert session.is_connected() is False
    assert session._connected is False
    assert session._toy is None