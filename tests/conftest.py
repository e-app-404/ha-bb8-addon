"""
Pytest configuration for HA-BB8 tests.

- Ensures the repository root is on sys.path so imports like
  `from addon.bb8_core import ...` resolve consistently.
"""

from __future__ import annotations

import importlib
import os
import sys
import types
from pathlib import Path


def _ensure_repo_root_on_syspath() -> None:
    """Prepend the repository root to sys.path.

    Tests live under tests/**. We need the repository root on sys.path.
    """
    tests_dir = Path(__file__).resolve().parent
    repo_root = tests_dir.parent
    root_str = str(repo_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


_ensure_repo_root_on_syspath()


def _install_addon_import_aliases() -> None:
    """Provide compatibility aliases for legacy `addon.*` test imports."""
    bb8_core_pkg = importlib.import_module("bb8_core")
    facade_stub_mod = importlib.import_module("tests.helpers.facade_stub")

    addon_pkg = types.ModuleType("addon")
    addon_pkg.__path__ = []
    addon_pkg.bb8_core = bb8_core_pkg

    addon_tests_pkg = types.ModuleType("addon.tests")
    addon_tests_pkg.__path__ = []
    addon_helpers_pkg = types.ModuleType("addon.tests.helpers")
    addon_helpers_pkg.__path__ = []
    addon_helpers_pkg.facade_stub = facade_stub_mod

    sys.modules.setdefault("addon", addon_pkg)
    sys.modules.setdefault("addon.bb8_core", bb8_core_pkg)
    sys.modules.setdefault("addon.tests", addon_tests_pkg)
    sys.modules.setdefault("addon.tests.helpers", addon_helpers_pkg)
    sys.modules.setdefault("addon.tests.helpers.facade_stub", facade_stub_mod)


_install_addon_import_aliases()


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
