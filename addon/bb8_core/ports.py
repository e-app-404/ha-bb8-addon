"""Protocol definitions for external ports used by the add-on.

These small Protocols document the minimal methods the runtime
infrastructure (MQTT, BLE, clock, logger) must provide. They are used
primarily for type checking and interface documentation.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MqttBus(Protocol):
    """Lightweight MQTT bus protocol used by the add-on.

    Implementations must provide async publish/subscribe/close operations.
    """

    async def publish(
        self,
        topic: str,
        payload: Any,
        retain: bool = False,
        qos: int = 0,
    ) -> None:
        """Publish a payload to the given MQTT topic."""

    async def subscribe(
        self,
        topic: str,
        cb: Callable[[str, bytes, bool], Awaitable[None]],
    ) -> None:
        """Subscribe; callback gets (topic, payload, retained)."""

    async def close(self) -> None:
        """Close the MQTT connection and release resources."""


@runtime_checkable
class BleTransport(Protocol):
    """Transport abstraction for BLE operations used by device drivers."""

    async def start(self) -> None:
        """Start BLE transport operations."""

    async def stop(self) -> None:
        """Stop BLE transport operations."""

    def on_event(self, cb: Callable[[str, dict], None]) -> None:
        """Register an event callback receiving (event_name, payload)."""


@runtime_checkable
class Clock(Protocol):
    """Clock protocol providing monotonic time and async sleep."""

    def monotonic(self) -> float:
        """Return a monotonic clock value (seconds)."""

    async def sleep(self, seconds: float) -> None:
        """Async sleep for the given number of seconds."""


@runtime_checkable
class Logger(Protocol):
    """Minimal logger API used by internal components."""

    def debug(self, *a, **k):
        """Log a debug message."""

    def info(self, *a, **k):
        """Log an informational message."""

    def warning(self, *a, **k):
        """Log a warning message."""

    def error(self, *a, **k):
        """Log an error message."""

    def exception(self, *a, **k):
        """Log an exception with traceback."""
