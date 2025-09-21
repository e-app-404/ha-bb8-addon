"""Small stable type aliases and Protocols used across bb8_core.

This module contains compact type aliases and Protocols that are
imported in multiple places. Docstrings here are intentionally
short to avoid import-time side effects in tests and tools.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

# ---------------------------
# Simple aliases (stable)
# ---------------------------
RGB = tuple[int, int, int]
# Scalar: alias for readable callbacks below (bool|int|float|str)
# Used for type hinting; not a runtime value.
Scalar = bool | int | float | str

# NB: Avoid importing any local modules at runtime to prevent cycles.
# If you must reference concrete classes for typing only, do:
# if TYPE_CHECKING:
#     from .bridge_controller import BridgeController


# ---------------------------
# Callback signatures
# ---------------------------
BoolCallback = Callable[[bool], None]
IntCallback = Callable[[int], None]
OptIntCallback = Callable[[int | None], None]
RGBCallback = Callable[[int, int, int], None]
ScalarCallback = Callable[
    [bool | int | float | str],
    None,
]  # Scalar echo: bool|int|float|str


# ---------------------------
# Minimal external client surfaces
# ---------------------------
@runtime_checkable
class MqttClient(Protocol):
    """Minimal MQTT client API used by internal components."""

    def publish(
        self,
        topic: str,
        payload: str,
        qos: int = ...,
        retain: bool = ...,
    ) -> Any:
        """Publish a string payload to a topic."""


# ---------------------------
# Device/link abstractions
# ---------------------------
@runtime_checkable
class BLELink(Protocol):
    """Represents a BLE connection/link lifecycle."""

    def start(self) -> None:
        """Start the BLE link."""

    def stop(self) -> None:
        """Stop the BLE link."""


# ---------------------------
# Controller/facade/bridge interfaces (minimal, non-circular)
# ---------------------------
@runtime_checkable
class BridgeController(Protocol):
    """Minimal controller surface used by the bridge/facade layers."""

    base_topic: str
    # Base MQTT topic for device communication.
    base_topic: str
    mqtt: MqttClient

    # Command handlers (examples; keep surface minimal and stable)
    def on_power(self, value: bool) -> None:
        """Handle power on/off events."""

    def on_stop(self) -> None:
        """Handle a stop/sleep command."""

    def on_sleep(self) -> None:
        """Handle device sleep request."""

    def on_drive(self, speed: int) -> None:
        """Handle a drive command with given speed."""

    def on_heading(self, degrees: int) -> None:
        """Handle heading change commands."""

    def on_led(self, r: int, g: int, b: int) -> None:
        """Handle LED color updates."""

    # Optional lifecycle hooks
    def start(self) -> None:
        """Start controller activity."""

    def shutdown(self) -> None:
        """Shutdown controller and release resources."""


@runtime_checkable
class Facade(Protocol):
    """Facade interface used by the bridge/controller for MQTT echoes."""

    base_topic: str

    def publish_scalar_echo(
        self,
        topic: str,
        value: Any,
        *,
        source: str = "facade",
    ) -> None:
        """Publish a scalar echo value to MQTT."""

    def publish_led_echo(self, r: int, g: int, b: int) -> None:
        """Publish an RGB LED echo to MQTT."""


__all__ = [
    "RGB",
    "BLELink",
    "BoolCallback",
    "BridgeController",
    "Facade",
    "IntCallback",
    "MqttClient",
    "OptIntCallback",
    "RGBCallback",
    "Scalar",
    "ScalarCallback",
]
