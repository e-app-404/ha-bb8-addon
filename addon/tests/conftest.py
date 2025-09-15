from __future__ import annotations

import asyncio
import importlib
import os
import sys
from pathlib import Path

import addon.bb8_core.mqtt_dispatcher as _dispatcher
import pytest

# --- BEGIN: ensure repo root on sys.path + test MQTT host before any imports ---
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


def _suppress_real_mqtt_connect(monkeypatch):
    try:
        paho = importlib.import_module("paho.mqtt.client")
    except Exception:
        return
    if os.environ.get("ALLOW_NETWORK_TESTS", "0") != "1":

        def _no_real_connect(self, *a, **k):
            raise OSError("suppressed real connect in tests")

        monkeypatch.setattr(paho.Client, "connect", _no_real_connect, raising=False)


@pytest.fixture(autouse=True)
def _auto_suppress_mqtt(monkeypatch):
    _suppress_real_mqtt_connect(monkeypatch)
    yield


# --- Deterministic discovery: clear the per-run published set ---
@pytest.fixture(autouse=True)
def _reset_discovery_published():
    _dispatcher._DISCOVERY_PUBLISHED.clear()
    yield
    _dispatcher._DISCOVERY_PUBLISHED.clear()


@pytest.fixture(autouse=True)
def _reset_discovery_published():
    _dispatcher._DISCOVERY_PUBLISHED.clear()
    yield
    _dispatcher._DISCOVERY_PUBLISHED.clear()


def _suppress_real_mqtt_connect(monkeypatch):
    try:
        paho = importlib.import_module("paho.mqtt.client")
    except Exception:
        return
    if os.environ.get("ALLOW_NETWORK_TESTS", "0") != "1":

        def _no_real_connect(self, *a, **k):
            raise OSError("suppressed real connect in tests")

        monkeypatch.setattr(paho.Client, "connect", _no_real_connect, raising=False)


@pytest.fixture(autouse=True)
def _auto_suppress_mqtt(monkeypatch):
    _suppress_real_mqtt_connect(monkeypatch)
    yield


# --- Deterministic discovery: clear the per-run published set ---
@pytest.fixture(autouse=True)
def _reset_discovery_published():
    _dispatcher._DISCOVERY_PUBLISHED.clear()
    yield
    _dispatcher._DISCOVERY_PUBLISHED.clear()
