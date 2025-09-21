"""Compact type and Protocol definitions for bb8_core public surfaces.

Keep these definitions small to avoid import-time cycles in tests and
applications that only need type hints.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

# ---------------------------
# Simple aliases (stable)
# ---------------------------
RGB = tuple[int, int, int]
Scalar = (
    "Scalar"
    # alias for readable callbacks used in callback type names
)


# ---------------------------
# Callback signatures
# ---------------------------
BoolCallback = Callable[[bool], None]
IntCallback = Callable[[int], None]
OptIntCallback = Callable[[int | None], None]
RGBCallback = Callable[[int, int, int], None]
ScalarCallback = Callable[[Any], None]  # Scalar echo: bool|int|float|str


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
        """Publish a string payload to topic."""


# ---------------------------
# Device/link abstractions
# ---------------------------
@runtime_checkable
class BLELink(Protocol):
    """Protocol representing a BLE link/connection used by the bridge."""

    def start(self) -> None:
        """Start the BLE link."""

    def stop(self) -> None:
        """Stop the BLE link."""


# ---------------------------
# Controller/facade/bridge interfaces (minimal, non-circular)
# ---------------------------
@runtime_checkable
class BridgeController(Protocol):
    """Interface a concrete bridge controller should implement."""

    base_topic: str
    mqtt: MqttClient

    # Command handlers (examples; keep surface minimal and stable)
    def on_power(self, value: bool) -> None:
        """Handle power on/off requests."""

    def on_stop(self) -> None:
        """Handle a stop command."""

    def on_sleep(self) -> None:
        """Handle a sleep command."""

    def on_drive(self, speed: int) -> None:
        """Handle a drive command with speed."""

    def on_heading(self, degrees: int) -> None:
        """Handle heading change commands."""

    def on_led(self, r: int, g: int, b: int) -> None:
        """Handle LED color updates."""

    # Optional lifecycle hooks
    def start(self) -> None:
        """Start the controller."""

    def shutdown(self) -> None:
        """Shutdown the controller and cleanup."""


@runtime_checkable
class Facade(Protocol):
    """Shim/facade interface (kept tiny to avoid import churn)."""

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
