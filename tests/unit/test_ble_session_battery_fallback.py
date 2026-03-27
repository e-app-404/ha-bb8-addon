import asyncio
import sys
from pathlib import Path

# Add repository root to path for test imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bb8_core.ble_session import BleSession


def test_battery_unavailable_backend_returns_graceful_fallback():
    session = BleSession("AA:BB:CC:DD:EE:FF")
    session._connected = True
    session._toy = object()

    battery_pct = asyncio.run(session.battery())

    assert battery_pct == 0
