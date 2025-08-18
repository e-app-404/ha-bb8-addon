# beep_boop_bb8/bb8_core/types.py
from __future__ import annotations

from typing import Any, Callable, Optional, Protocol, Tuple, runtime_checkable

# ---------------------------
# Simple aliases (stable)
# ---------------------------
RGB = Tuple[int, int, int]
Scalar = (
    "Scalar"  # alias for readable callbacks below (string-based to avoid 3.8 | syntax)
)

# NB: Avoid importing any local modules at runtime to prevent cycles.
# If you must reference concrete classes for typing only, do:
# if TYPE_CHECKING:
#     from .bridge_controller import BridgeController  # noqa: F401


# ---------------------------
# Callback signatures
# ---------------------------
BoolCallback = Callable[[bool], None]
IntCallback = Callable[[int], None]
OptIntCallback = Callable[[Optional[int]], None]
RGBCallback = Callable[[int, int, int], None]
ScalarCallback = Callable[[Any], None]  # Scalar echo: bool|int|float|str


# ---------------------------
# Minimal external client surfaces
# ---------------------------
class MqttClient(Protocol):
    def publish(
        self, topic: str, payload: str, qos: int = ..., retain: bool = ...
    ) -> Any: ...


# ---------------------------
# Device/link abstractions
# ---------------------------
@runtime_checkable
class BLELink(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...


# ---------------------------
# Controller/facade/bridge interfaces (minimal, non-circular)
# ---------------------------
@runtime_checkable
class BridgeController(Protocol):
    base_topic: str
    mqtt: MqttClient

    # Command handlers (examples; keep surface minimal and stable)
    def on_power(self, value: bool) -> None: ...
    def on_stop(self) -> None: ...
    def on_sleep(self) -> None: ...
    def on_drive(self, speed: int) -> None: ...
    def on_heading(self, degrees: int) -> None: ...
    def on_led(self, r: int, g: int, b: int) -> None: ...

    # Optional lifecycle hooks
    def start(self) -> None: ...
    def shutdown(self) -> None: ...


@runtime_checkable
class Facade(Protocol):
    """Shim/facade interface (kept tiny to avoid import churn)."""

    base_topic: str

    def publish_scalar_echo(
        self, topic: str, value: Any, *, source: str = "facade"
    ) -> None: ...
    def publish_led_echo(self, r: int, g: int, b: int) -> None: ...


__all__ = [
    "RGB",
    "Scalar",
    "BoolCallback",
    "IntCallback",
    "OptIntCallback",
    "RGBCallback",
    "ScalarCallback",
    "MqttClient",
    "BLELink",
    "BridgeController",
    "Facade",
]
