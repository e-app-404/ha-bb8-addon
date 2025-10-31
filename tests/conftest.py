"""
Pytest configuration for HA-BB8 tests.

- Ensures the repository root is on sys.path so imports like
  `from addon.bb8_core import ...` resolve consistently.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _ensure_repo_root_on_syspath() -> None:
    """Prepend the repository root to sys.path.

    Tests live under addon/tests/**. We need the parent of 'addon' (repo root)
    on sys.path so that the package import style `addon.bb8_core.*` works.
    """
    tests_dir = Path(__file__).resolve().parent
    addon_dir = tests_dir.parent  # addon/
    repo_root = addon_dir.parent  # repo root
    root_str = str(repo_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


_ensure_repo_root_on_syspath()


def pytest_configure(config):  # noqa: D401
    """Pytest entry to ensure env defaults helpful for fast tests."""
    # Avoid slow BLE operations by default unless explicitly enabled
    os.environ.setdefault("ALLOW_MOTION_TESTS", "0")
    # Provide a harmless default base if tests inspect it
    os.environ.setdefault("MQTT_BASE", "bb8")
    # Prefer local MQTT host for unit tests unless explicitly overridden
    os.environ.setdefault("MQTT_HOST", "127.0.0.1")

# Provide a lightweight stub for 'bleak' if not installed so that modules
# importing BleakScanner/BleakClient at import time don't fail collection.
try:  # pragma: no cover - depends on dev env
    import bleak as _bleak  # type: ignore
except Exception:  # noqa: BLE001
    import types as _types

    _bleak_stub = _types.ModuleType("bleak")

    class _BleakScanner:  # type: ignore
        @staticmethod
        async def discover(*args, **kwargs):
            return []

    class _BleakClient:  # type: ignore
        def __init__(self, *a, **k):
            pass

    _exc = _types.ModuleType("bleak.exc")

    class _BleakCharacteristicNotFoundError(Exception):
        pass

    _exc.BleakCharacteristicNotFoundError = _BleakCharacteristicNotFoundError
    _bleak_stub.BleakScanner = _BleakScanner
    _bleak_stub.BleakClient = _BleakClient
    sys.modules["bleak"] = _bleak_stub
    sys.modules["bleak.exc"] = _exc
