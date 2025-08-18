from __future__ import annotations

import importlib  # Ensure importlib is available
import sys

# Define __all__ before usage
__all__ = []

# Optional: expose start_bridge_controller from bridge_controller at package top-level
try:
    from .bridge_controller import start_bridge_controller  # noqa: F401

    __all__.append("start_bridge_controller")
except Exception:  # keep tests helpful
    # If symbol was renamed, create a thin alias
    try:
        _mod = importlib.import_module("bb8_core.bridge_controller")
        if hasattr(_mod, "start_bridge_controller"):
            start_bridge_controller = getattr(_mod, "start_bridge_controller")
            __all__.append("start_bridge_controller")
    except Exception:
        pass

# bb8_core package
"""
Shim + public exports.

Why:
- Tests import submodules like `bb8_core.mqtt_dispatcher`, `bb8_core.facade`, etc.
- In your repo, some of these exist as top-level modules (e.g., `mqtt_dispatcher.py`)
    rather than inside the `bb8_core/` package.
- This __init__ keeps your public API AND aliases submodule imports to the real modules.

Safe to remove once everything is organized under `bb8_core/` proper.
"""


# ---- Public symbols you already exported (keep these) ----
try:
    from .ble_bridge import BLEBridge  # if the module is inside bb8_core/
except Exception:  # noqa: BLE001
    BLEBridge = None  # will still be available via bb8_core.ble_bridge alias below

try:
    from .ble_gateway import BleGateway  # if the module is inside bb8_core/
except Exception:  # noqa: BLE001
    BleGateway = None

try:
    from .core import Core  # if the module is inside bb8_core/
except Exception:  # noqa: BLE001
    Core = None

# Facade export (handle both spellings if present)
try:
    from .facade import BB8Facade as Bb8Facade
except Exception:  # pragma: no cover
    try:
        from .facade import Bb8Facade  # type: ignore
    except Exception:
        Bb8Facade = None  # type: ignore

# start_bridge_controller passthrough if defined elsewhere
try:
    from .bridge_controller import start_bridge_controller  # type: ignore
except Exception:  # pragma: no cover
    start_bridge_controller = None  # type: ignore

__all__ = [
    "Core",
    "BleGateway",
    "BLEBridge",
]
if Bb8Facade:
    __all__.append("Bb8Facade")
if start_bridge_controller:
    __all__.append("start_bridge_controller")

# ---- Submodule aliasing ------------------------------------------------------
# Map `bb8_core.<submodule>` -> actual module object.
# We try in order:
#   1) in-package module (e.g., `bb8_core.mqtt_dispatcher`)
#   2) top-level module (e.g., `mqtt_dispatcher`)
# Add more keys here if tests import additional submodules.
_SUBMODULE_ALIASES = {
    "bb8_core.logging_setup": ("bb8_core.logging_setup", "logging_setup"),
    "bb8_core.mqtt_dispatcher": ("bb8_core.mqtt_dispatcher", "mqtt_dispatcher"),
    "bb8_core.ble_link": ("bb8_core.ble_link", "ble_link"),
    "bb8_core.facade": ("bb8_core.facade", "facade"),
    "bb8_core.mqtt_echo": ("bb8_core.mqtt_echo", "mqtt_echo"),
    "bb8_core.bb8_presence_scanner": (
        "bb8_core.bb8_presence_scanner",
        "bb8_presence_scanner",
    ),
    "bb8_core.ble_bridge": ("bb8_core.ble_bridge", "ble_bridge"),
    "bb8_core.ble_gateway": ("bb8_core.ble_gateway", "ble_gateway"),
    "bb8_core.core": ("bb8_core.core", "core"),
}


def _alias(submod: str, candidates: tuple[str, str]) -> None:
    for target in candidates:
        try:
            mod = importlib.import_module(target)
            sys.modules[submod] = mod
            return
        except ModuleNotFoundError:
            continue
    # Leave unresolved -> pytest will raise a clear ImportError if genuinely missing.


for dotted, candidates in _SUBMODULE_ALIASES.items():
    _alias(dotted, candidates)

# Optional: expose classes from aliased modules at package top-level if desired.
# e.g., make `from bb8_core.facade import BB8Facade` work AND `from bb8_core import BB8Facade` (optional):
try:
    _facade = sys.modules.get("bb8_core.facade")
    if _facade and hasattr(_facade, "BB8Facade"):
        BB8Facade = getattr(_facade, "BB8Facade")
        __all__.append("BB8Facade")
except Exception:
    pass
