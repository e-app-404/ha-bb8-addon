from __future__ import annotations

import asyncio

# --- BEGIN: ensure repo root on sys.path + test MQTT host before any imports ---
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Force tests to use localhost, not the real HA broker.
# Must be set at module import time (before any bb8_core imports).
os.environ.setdefault("MQTT_HOST", "127.0.0.1")
# --- END ---


# Provide a stable event loop for tests that touch asyncio/BLE helpers.
# With asyncio_mode=auto this is usually not necessary,
# but it guards environments where plugin policies differ.
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.run_until_complete(asyncio.sleep(0))
        loop.close()
