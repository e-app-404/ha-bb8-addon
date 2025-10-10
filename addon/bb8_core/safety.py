"""
BB-8 Safety Layer - Rate limiting, duration caps, speed caps, and emergency stop

Implements comprehensive motion safety controls:
- Rate limiting: Enforces minimum 50ms between drive commands
- Duration capping: Limits motion duration to configurable maximum (default 2000ms)
- Speed capping: Limits speed to configurable maximum (default 180/255)
- Emergency stop: Latched stop that blocks all motion until cleared
- Hard stop timer: Automatically stops motion after duration expires
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from typing import Any

from .logging_setup import logger


@dataclass
class SafetyConfig:
    """Safety configuration parameters."""

    # Rate limiting
    min_drive_interval_ms: int = (
        50  # Minimum milliseconds between drive commands
    )

    # Duration limits
    max_drive_duration_ms: int = 2000  # Maximum drive duration in milliseconds

    # Speed limits
    max_drive_speed: int = 180  # Maximum drive speed (0-255)

    # Emergency stop
    estop_latched: bool = False  # Emergency stop latch state

    @classmethod
    def from_env(cls) -> SafetyConfig:
        """Load safety configuration from environment variables."""
        return cls(
            min_drive_interval_ms=int(
                os.getenv("BB8_MIN_DRIVE_INTERVAL_MS", "50")
            ),
            max_drive_duration_ms=int(
                os.getenv("BB8_MAX_DRIVE_DURATION_MS", "2000")
            ),
            max_drive_speed=int(os.getenv("BB8_MAX_DRIVE_SPEED", "180")),
            estop_latched=False,  # Always start with estop cleared
        )


class SafetyViolation(Exception):
    """Raised when a safety constraint is violated."""

    def __init__(self, message: str, constraint: str, value: Any = None):
        super().__init__(message)
        self.constraint = constraint
        self.value = value


class MotionSafetyController:
    """
    Controls motion safety with rate limiting, duration caps, and emergency stop.

    This controller acts as a gate between MQTT commands and the actual device,
    enforcing safety constraints and providing emergency stop functionality.
    """

    def __init__(self, config: SafetyConfig | None = None):
        """Initialize safety controller with configuration."""
        self.config = config or SafetyConfig.from_env()

        # State tracking
        self._last_drive_time: float = 0.0
        self._active_stop_tasks: set[asyncio.Task] = set()
        self._device_connected: bool = False

        # Emergency stop state
        self._estop_latched: bool = False
        self._estop_reason: str = ""

        logger.info({
            "event": "safety_controller_init",
            "min_interval_ms": self.config.min_drive_interval_ms,
            "max_duration_ms": self.config.max_drive_duration_ms,
            "max_speed": self.config.max_drive_speed,
        })

    def set_device_connected(self, connected: bool) -> None:
        """Update device connection state."""
        self._device_connected = connected
        logger.debug({
            "event": "safety_device_connection_state",
            "connected": connected,
        })

    def is_estop_active(self) -> bool:
        """Check if emergency stop is currently active."""
        return self._estop_latched

    def get_estop_reason(self) -> str:
        """Get reason for current emergency stop."""
        return self._estop_reason

    def validate_drive_command(
        self, speed: int, heading: int, duration_ms: int | None
    ) -> tuple[int, int, int]:
        """
        Validate and clamp drive command parameters.

        Parameters
        ----------
        speed : int
            Requested speed (0-255)
        heading : int
            Requested heading (0-359)
        duration_ms : int | None
            Requested duration in milliseconds

        Returns
        -------
        tuple[int, int, int]
            Validated (speed, heading, duration_ms)

        Raises
        ------
        SafetyViolation
            If safety constraints are violated
        """
        # Check emergency stop first
        if self._estop_latched:
            raise SafetyViolation(
                f"Motion blocked by emergency stop: {self._estop_reason}",
                "estop_active",
            )

        # Check device connection
        if not self._device_connected:
            raise SafetyViolation(
                "Motion blocked - device not connected", "device_offline"
            )

        # Check rate limiting (but not on first command)
        current_time = time.time()
        if self._last_drive_time > 0:  # Skip rate limit check for first command
            time_since_last = (
                current_time - self._last_drive_time
            ) * 1000  # Convert to ms

            if time_since_last < self.config.min_drive_interval_ms:
                raise SafetyViolation(
                    f"Drive command rate limit exceeded - {time_since_last:.1f}ms < {self.config.min_drive_interval_ms}ms",
                    "rate_limit",
                    time_since_last,
                )

        # Clamp speed
        original_speed = speed
        speed = max(0, min(self.config.max_drive_speed, speed))
        if speed != original_speed:
            logger.warning({
                "event": "safety_speed_clamped",
                "original": original_speed,
                "clamped": speed,
                "max_allowed": self.config.max_drive_speed,
            })

        # Clamp heading (0-359)
        original_heading = heading
        heading = heading % 360
        if heading != original_heading:
            logger.debug({
                "event": "safety_heading_wrapped",
                "original": original_heading,
                "wrapped": heading,
            })

        # Clamp duration
        if duration_ms is None:
            duration_ms = self.config.max_drive_duration_ms
        else:
            original_duration = duration_ms
            duration_ms = max(
                0, min(self.config.max_drive_duration_ms, duration_ms)
            )
            if duration_ms != original_duration:
                logger.warning({
                    "event": "safety_duration_clamped",
                    "original": original_duration,
                    "clamped": duration_ms,
                    "max_allowed": self.config.max_drive_duration_ms,
                })

        # Update last drive time
        self._last_drive_time = current_time

        logger.debug({
            "event": "safety_drive_validated",
            "speed": speed,
            "heading": heading,
            "duration_ms": duration_ms,
        })

        return speed, heading, duration_ms

    def schedule_auto_stop(self, duration_ms: int, stop_callback) -> None:
        """
        Schedule automatic stop after specified duration.

        Parameters
        ----------
        duration_ms : int
            Duration in milliseconds after which to stop
        stop_callback : callable
            Function to call to stop the device
        """
        if duration_ms <= 0:
            return

        async def _auto_stop():
            try:
                await asyncio.sleep(duration_ms / 1000.0)

                # Check if estop is active (don't double-stop)
                if not self._estop_latched:
                    logger.info({
                        "event": "safety_auto_stop_triggered",
                        "duration_ms": duration_ms,
                    })
                    await stop_callback()

            except asyncio.CancelledError:
                logger.debug({
                    "event": "safety_auto_stop_cancelled",
                    "duration_ms": duration_ms,
                })
            except Exception as e:
                logger.error({
                    "event": "safety_auto_stop_error",
                    "duration_ms": duration_ms,
                    "error": str(e),
                })

        # Cancel any existing auto-stop tasks
        self.cancel_auto_stop()

        # Schedule new auto-stop
        task = asyncio.create_task(_auto_stop())
        self._active_stop_tasks.add(task)
        task.add_done_callback(self._active_stop_tasks.discard)

        logger.debug({
            "event": "safety_auto_stop_scheduled",
            "duration_ms": duration_ms,
        })

    def cancel_auto_stop(self) -> None:
        """Cancel any pending auto-stop tasks."""
        for task in list(self._active_stop_tasks):
            if not task.done():
                task.cancel()
        self._active_stop_tasks.clear()

        logger.debug({"event": "safety_auto_stop_cancelled"})

    def activate_estop(self, reason: str = "Manual emergency stop") -> None:
        """
        Activate emergency stop - latches until explicitly cleared.

        Parameters
        ----------
        reason : str
            Reason for emergency stop activation
        """
        if self._estop_latched:
            logger.warning({
                "event": "safety_estop_already_active",
                "current_reason": self._estop_reason,
                "new_reason": reason,
            })
            return

        self._estop_latched = True
        self._estop_reason = reason

        # Cancel any pending auto-stop tasks
        self.cancel_auto_stop()

        logger.warning({
            "event": "safety_estop_activated",
            "reason": reason,
            "timestamp": time.time(),
        })

    def can_clear_estop(self) -> tuple[bool, str]:
        """
        Check if emergency stop can be safely cleared.

        Returns
        -------
        tuple[bool, str]
            (can_clear, reason)
        """
        if not self._estop_latched:
            return False, "Emergency stop is not currently active"

        if not self._device_connected:
            return False, "Cannot clear emergency stop - device not connected"

        # Add additional safety checks here if needed
        # For example: check device responsiveness, sensor readings, etc.

        return True, "Safe to clear emergency stop"

    def clear_estop(self) -> tuple[bool, str]:
        """
        Clear emergency stop if safe to do so.

        Returns
        -------
        tuple[bool, str]
            (cleared, reason)
        """
        can_clear, reason = self.can_clear_estop()

        if not can_clear:
            logger.warning({
                "event": "safety_estop_clear_denied",
                "reason": reason,
            })
            return False, reason

        self._estop_latched = False
        previous_reason = self._estop_reason
        self._estop_reason = ""

        logger.info({
            "event": "safety_estop_cleared",
            "previous_reason": previous_reason,
            "timestamp": time.time(),
        })

        return True, f"Emergency stop cleared (was: {previous_reason})"

    def get_safety_status(self) -> dict[str, Any]:
        """
        Get current safety status for telemetry.

        Returns
        -------
        dict
            Safety status information
        """
        return {
            "estop_active": self._estop_latched,
            "estop_reason": self._estop_reason,
            "device_connected": self._device_connected,
            "last_drive_time": self._last_drive_time,
            "active_stop_tasks": len(self._active_stop_tasks),
            "config": {
                "min_interval_ms": self.config.min_drive_interval_ms,
                "max_duration_ms": self.config.max_drive_duration_ms,
                "max_speed": self.config.max_drive_speed,
            },
        }

    async def shutdown(self) -> None:
        """Shutdown safety controller and cancel all tasks."""
        logger.info({"event": "safety_controller_shutdown"})

        # Cancel all auto-stop tasks
        self.cancel_auto_stop()

        # Wait for tasks to complete
        if self._active_stop_tasks:
            await asyncio.gather(
                *self._active_stop_tasks, return_exceptions=True
            )


# Global safety controller instance (initialized by bridge_controller)
_safety_controller: MotionSafetyController | None = None


def get_safety_controller() -> MotionSafetyController:
    """Get the global safety controller instance."""
    global _safety_controller
    if _safety_controller is None:
        _safety_controller = MotionSafetyController()
    return _safety_controller


def initialize_safety_controller(
    config: SafetyConfig | None = None,
) -> MotionSafetyController:
    """Initialize the global safety controller with optional configuration."""
    global _safety_controller
    _safety_controller = MotionSafetyController(config)
    return _safety_controller


async def shutdown_safety_controller() -> None:
    """Shutdown the global safety controller."""
    global _safety_controller
    if _safety_controller:
        await _safety_controller.shutdown()
        _safety_controller = None
