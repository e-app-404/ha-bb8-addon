from __future__ import annotations
import warnings
warnings.filterwarnings("ignore", "Callback API version 1 is deprecated", DeprecationWarning, "paho")

import importlib
import sys

# Only define __all__ at the top level; do not import submodules here.
__all__ = [
    "Core",
    "BleGateway",
    "BLEBridge",
    "Bb8Facade",
    "start_bridge_controller",
]

# ---- Submodule aliasing ------------------------------------------------------
# Map `bb8_core.<submodule>` -> actual module object.
# We try in order:
#   1) in-package module (e.g., `bb8_core.mqtt_dispatcher`)
#   2) top-level module (e.g., `mqtt_dispatcher`)
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
