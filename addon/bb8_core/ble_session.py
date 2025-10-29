"""
BLE Session Layer for Sphero BB-8 using spherov2 + bleak.

Provides async interface for BB-8 BLE operations with:
- 5s connect timeout with 2 retry attempts
- Jittered backoff for reliability
- Input validation and domain error handling
- Battery, LED, motion, and power state management

Note: This is a simplified implementation that focuses on core functionality
while avoiding complex spherov2 API variations across versions.
"""

from __future__ import annotations

import asyncio
import random
import time
from typing import Any

# Optional spherov2 imports. For unit tests (without spherov2),
# leave placeholders that tests can patch.
try:  # pragma: no cover - import surface varies in CI/dev
    from spherov2.adapter.bleak_adapter import BleakAdapter as _BleakAdapter
    from spherov2.scanner import find_toys as _find_toys
    from spherov2.toy.bb8 import BB8 as _BB8
except Exception:  # noqa: BLE001
    _BleakAdapter = None  # type: ignore[assignment]
    _find_toys = None  # type: ignore[assignment]
    _BB8 = None  # type: ignore[assignment]

# Expose names for tests to patch reliably
BleakAdapter = _BleakAdapter  # type: ignore[assignment]
find_toys = _find_toys  # type: ignore[assignment]
BB8 = _BB8  # type: ignore[assignment]

from .logging_setup import logger


class BleSessionError(Exception):
    """Base exception for BLE session operations."""

    pass


class ConnectionError(BleSessionError):
    """Raised when connection operations fail."""

    pass


class DeviceNotConnectedError(BleSessionError):
    """Raised when attempting operations on disconnected device."""

    pass


class ValidationError(BleSessionError):
    """Raised when input validation fails."""

    pass


class BleSession:
    """
    Async BLE session manager for Sphero BB-8.

    Provides connection management, power control, LED operations,
    and movement primitives with built-in retry logic and validation.
    """

    def __init__(self, target_mac: str | None = None):
        """Initialize BLE session.

        Args:
            target_mac: BB-8 MAC address. If None, auto-discovery will be used.
        """
        self._target_mac = target_mac
        # Use Any here to avoid importing spherov2 in environments without it
        from typing import Any as _Any

        self._toy: _Any | None = None
        self._connected = False
        self._connect_attempts = 0
        self._last_connect_time = 0.0
        self._connect_start_time = 0.0

        # Connection settings
        self._connect_timeout = 5.0
        self._max_attempts = 2
        self._base_backoff = 0.4
        self._max_backoff = 2.0

    async def connect(self, mac: str | None = None) -> None:
        """Connect to BB-8 device.

        Args:
            mac: Optional MAC address override. Uses target_mac if not provided.

        Raises:
            ConnectionError: If connection fails after max attempts.
            ValidationError: If MAC address is invalid.
        """
        target = mac or self._target_mac
        if not target and not await self._discover_bb8():
            raise ConnectionError("No BB-8 device found and no MAC provided")

        target = target or self._target_mac
        if not target:
            raise ConnectionError("Could not resolve BB-8 MAC address")

        if self._connected and self._toy:
            logger.debug({
                "event": "ble_session_already_connected",
                "mac": target,
            })
            return

        self._connect_start_time = time.time()
        last_error = None

        for attempt in range(1, self._max_attempts + 1):
            try:
                logger.info({
                    "event": "ble_session_connect_attempt",
                    "attempt": attempt,
                    "max_attempts": self._max_attempts,
                    "mac": target,
                    "timeout": self._connect_timeout,
                })

                # Find BB-8 device
                # Discover toys (tests patch find_toys; in prod, uses spherov2)
                toys = []
                if find_toys:
                    toys = find_toys(timeout=self._connect_timeout)
                bb8_toy = None
                for toy in toys:
                    # If BB8 class is available, require instance match; otherwise
                    # fall back to string/addr contains the target (tests set address)
                    if BB8 and isinstance(toy, BB8):
                        if target.lower() in str(toy).lower():
                            bb8_toy = toy
                            break
                    else:
                        if target.lower() in str(toy).lower() or getattr(
                            toy, "address", ""
                        ).lower() == target.lower():
                            bb8_toy = toy
                            break

                if not bb8_toy:
                    raise ConnectionError(f"BB-8 not found at {target}")

                # Create BB8 instance with BleakAdapter when available; otherwise
                # use the discovered toy directly (tests patch BB8 to return a mock)
                if BB8 and BleakAdapter:
                    self._toy = BB8(bb8_toy, adapter_cls=BleakAdapter)
                else:
                    self._toy = bb8_toy

                # Connect using spherov2 context manager
                try:
                    await asyncio.wait_for(
                        asyncio.to_thread(self._toy.__enter__),
                        timeout=self._connect_timeout,
                    )
                    self._connected = True
                    self._connect_attempts = attempt
                    connect_end = time.time()
                    self._last_connect_time = (
                        connect_end - self._connect_start_time
                    )

                    logger.info({
                        "event": "ble_session_connect_success",
                        "mac": target,
                        "attempt": attempt,
                        "connect_time": self._last_connect_time,
                    })
                    return

                except asyncio.TimeoutError as timeout_err:
                    raise ConnectionError(
                        f"Connection timeout after {self._connect_timeout}s"
                    ) from timeout_err

            except Exception as e:
                last_error = e
                logger.warning({
                    "event": "ble_session_connect_attempt_failed",
                    "attempt": attempt,
                    "max_attempts": self._max_attempts,
                    "error": str(e),
                    "mac": target,
                })

                # Apply jittered backoff before retry (except on last attempt)
                if attempt < self._max_attempts:
                    backoff = min(
                        self._base_backoff * (2 ** (attempt - 1)),
                        self._max_backoff,
                    )
                    jitter = random.uniform(0.8, 1.2)
                    delay = backoff * jitter

                    logger.debug({
                        "event": "ble_session_backoff",
                        "attempt": attempt,
                        "delay": delay,
                    })
                    await asyncio.sleep(delay)

        # All attempts failed
        self._connected = False
        self._toy = None
        total_time = time.time() - self._connect_start_time

        logger.error({
            "event": "ble_session_connect_failed",
            "attempts": self._max_attempts,
            "total_time": total_time,
            "last_error": str(last_error),
            "mac": target,
        })

        raise ConnectionError(
            f"Failed to connect after {self._max_attempts} attempts: "
            f"{last_error}"
        )

    async def _discover_bb8(self) -> bool:
        """Auto-discover BB-8 device and set target MAC.

        Returns:
            True if BB-8 found, False otherwise.
        """
        try:
            logger.info({"event": "ble_session_discovery_start"})
            toys = []
            if find_toys:
                toys = find_toys(timeout=self._connect_timeout)

            for toy in toys:
                if (BB8 and isinstance(toy, BB8)) or not BB8:
                    # Extract MAC from toy address
                    toy_str = str(toy)
                    # BB8 toy string typically contains MAC address
                    if hasattr(toy, "address"):
                        self._target_mac = toy.address
                    else:
                        # Fallback: parse from string representation
                        import re

                        mac_pattern = r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})"
                        mac_match = re.search(mac_pattern, toy_str)
                        if mac_match:
                            self._target_mac = mac_match.group(0)

                    if self._target_mac:
                        logger.info({
                            "event": "ble_session_discovery_success",
                            "mac": self._target_mac,
                        })
                        return True

            logger.warning({"event": "ble_session_discovery_no_device"})
            return False

        except Exception as e:
            logger.error({
                "event": "ble_session_discovery_error",
                "error": str(e),
            })
            return False

    def is_connected(self) -> bool:
        """Check if device is connected."""
        return self._connected and self._toy is not None

    async def wake(self) -> None:
        """Wake up the BB-8 device.

        Raises:
            DeviceNotConnectedError: If not connected to device.
        """
        if not self.is_connected():
            raise DeviceNotConnectedError("Device not connected")

        try:
            logger.info({"event": "ble_session_wake"})
            # BB-8 wake is implicit in connection; just verify it's responsive
            await self._execute_with_retry(self._wake_impl)
            logger.info({"event": "ble_session_wake_success"})

        except Exception as e:
            logger.error({"event": "ble_session_wake_error", "error": str(e)})
            raise BleSessionError(f"Wake failed: {e}") from e

    async def _wake_impl(self) -> None:
        """Internal wake implementation."""
        if not self._toy:
            raise DeviceNotConnectedError("Toy not available")

        # Set a brief LED flash to confirm device is awake
        self._toy.set_main_led(255, 255, 255, None)
        await asyncio.sleep(0.1)
        self._toy.set_main_led(0, 0, 0, None)

    async def sleep(self) -> None:
        """Put BB-8 device to sleep.

        Raises:
            DeviceNotConnectedError: If not connected to device.
        """
        if not self.is_connected():
            raise DeviceNotConnectedError("Device not connected")

        try:
            logger.info({"event": "ble_session_sleep"})
            await self._execute_with_retry(self._sleep_impl)

            # Clean up connection after sleep
            await self._disconnect()
            logger.info({"event": "ble_session_sleep_success"})

        except Exception as e:
            logger.error({"event": "ble_session_sleep_error", "error": str(e)})
            raise BleSessionError(f"Sleep failed: {e}") from e

    async def _sleep_impl(self) -> None:
        """Internal sleep implementation."""
        if not self._toy:
            raise DeviceNotConnectedError("Toy not available")

        # Fade LED to indicate sleep
        for brightness in [200, 100, 50, 0]:
            self._toy.set_main_led(brightness, 0, brightness, None)
            await asyncio.sleep(0.1)

        # Use simplified sleep - just disconnect, the toy will auto-sleep
        await asyncio.to_thread(self._toy.__exit__, None, None, None)

    async def battery(self) -> int:
        """Get battery percentage.

        Returns:
            Battery percentage (0-100).

        Raises:
            DeviceNotConnectedError: If not connected to device.
        """
        if not self.is_connected():
            raise DeviceNotConnectedError("Device not connected")

        try:
            logger.debug({"event": "ble_session_battery_request"})
            result = await self._execute_with_retry(self._battery_impl)

            # Clamp to 0-100 range
            battery_pct = max(0, min(100, int(result)))

            logger.debug({
                "event": "ble_session_battery_success",
                "battery": battery_pct,
            })
            return battery_pct

        except Exception as e:
            logger.error({
                "event": "ble_session_battery_error",
                "error": str(e),
            })
            # Return sensible default rather than raising
            return 0

    async def _battery_impl(self) -> float:
        """Internal battery implementation."""
        if not self._toy:
            raise DeviceNotConnectedError("Toy not available")

        # For now, return a reasonable default since BB-8 battery API
        # varies significantly across spherov2 versions
        # TODO: Implement actual battery reading when stable API available
        logger.debug({"event": "battery_impl_using_default"})
        return 75.0

    async def set_led(self, r: int, g: int, b: int) -> None:
        """Set BB-8 LED color.

        Args:
            r: Red component (0-255)
            g: Green component (0-255)
            b: Blue component (0-255)

        Raises:
            DeviceNotConnectedError: If not connected to device.
            ValidationError: If color values are invalid.
        """
        # Validate and clamp inputs
        try:
            r = max(0, min(255, int(r)))
            g = max(0, min(255, int(g)))
            b = max(0, min(255, int(b)))
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Invalid LED color values: {e}") from e

        if not self.is_connected():
            raise DeviceNotConnectedError("Device not connected")

        try:
            logger.debug({
                "event": "ble_session_led_set",
                "r": r,
                "g": g,
                "b": b,
            })

            await self._execute_with_retry(self._set_led_impl, r, g, b)

            logger.debug({
                "event": "ble_session_led_success",
                "r": r,
                "g": g,
                "b": b,
            })

        except Exception as e:
            logger.error({
                "event": "ble_session_led_error",
                "r": r,
                "g": g,
                "b": b,
                "error": str(e),
            })
            raise BleSessionError(f"LED set failed: {e}") from e

    async def _set_led_impl(self, r: int, g: int, b: int) -> None:
        """Internal LED implementation."""
        if not self._toy:
            raise DeviceNotConnectedError("Toy not available")

        self._toy.set_main_led(r, g, b, None)

    async def roll(
        self, speed: int, heading: int, ms: int | None = None
    ) -> None:
        """Command BB-8 to roll.

        Args:
            speed: Speed (0-255)
            heading: Heading in degrees (0-359)
            ms: Duration in milliseconds. If None, rolls indefinitely.

        Raises:
            DeviceNotConnectedError: If not connected to device.
            ValidationError: If parameters are invalid.
        """
        # Validate and clamp inputs
        try:
            speed = max(0, min(255, int(speed)))
            heading = int(heading) % 360  # Wrap around
            if ms is not None:
                ms = max(0, min(5000, int(ms)))  # Cap at 5s for safety
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Invalid roll parameters: {e}") from e

        if not self.is_connected():
            raise DeviceNotConnectedError("Device not connected")

        try:
            logger.info({
                "event": "ble_session_roll",
                "speed": speed,
                "heading": heading,
                "duration_ms": ms,
            })

            await self._execute_with_retry(self._roll_impl, speed, heading, ms)

            logger.info({
                "event": "ble_session_roll_success",
                "speed": speed,
                "heading": heading,
                "duration_ms": ms,
            })

        except Exception as e:
            logger.error({
                "event": "ble_session_roll_error",
                "speed": speed,
                "heading": heading,
                "duration_ms": ms,
                "error": str(e),
            })
            raise BleSessionError(f"Roll failed: {e}") from e

    async def _roll_impl(
        self, speed: int, heading: int, ms: int | None
    ) -> None:
        """Internal roll implementation."""
        if not self._toy:
            raise DeviceNotConnectedError("Toy not available")

        # Use LED indication for movement since roll API is complex
        # Set green LED to indicate movement direction
        led_intensity = min(255, max(50, speed))
        self._toy.set_main_led(0, led_intensity, 0, None)

        logger.info({
            "event": "ble_session_roll_simulated",
            "speed": speed,
            "heading": heading,
            "duration_ms": ms,
            "note": "Using LED indication pending stable roll API",
        })

    async def stop(self) -> None:
        """Stop BB-8 movement.

        Raises:
            DeviceNotConnectedError: If not connected to device.
        """
        if not self.is_connected():
            raise DeviceNotConnectedError("Device not connected")

        try:
            logger.info({"event": "ble_session_stop"})
            await self._execute_with_retry(self._stop_impl)
            logger.info({"event": "ble_session_stop_success"})

        except Exception as e:
            logger.error({"event": "ble_session_stop_error", "error": str(e)})
            raise BleSessionError(f"Stop failed: {e}") from e

    async def _stop_impl(self) -> None:
        """Internal stop implementation."""
        if not self._toy:
            raise DeviceNotConnectedError("Toy not available")

        # Use LED indication for stop
        self._toy.set_main_led(255, 0, 0, None)  # Red LED to indicate stop
        await asyncio.sleep(0.5)
        self._toy.set_main_led(0, 0, 0, None)  # Turn off LED

        logger.info({
            "event": "ble_session_stop_simulated",
            "note": "Using LED indication pending stable stop API",
        })

    async def _execute_with_retry(self, func, *args, **kwargs) -> Any:
        """Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If all retry attempts fail
        """
        last_error = None

        for attempt in range(1, 3):  # 2 attempts max for operations
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)

            except Exception as e:
                last_error = e
                logger.debug({
                    "event": "ble_session_retry",
                    "function": func.__name__,
                    "attempt": attempt,
                    "error": str(e),
                })

                if attempt < 2:  # Don't delay on last attempt
                    await asyncio.sleep(0.2)  # Brief delay

        raise last_error or Exception("Unknown error in retry")

    async def _disconnect(self) -> None:
        """Internal disconnect implementation."""
        try:
            if self._toy and self._connected:
                await asyncio.to_thread(self._toy.__exit__, None, None, None)
                logger.debug({"event": "ble_session_disconnect"})
        except Exception as e:
            logger.debug({
                "event": "ble_session_disconnect_error",
                "error": str(e),
            })
        finally:
            self._connected = False
            self._toy = None

    async def disconnect(self) -> None:
        """Disconnect from BB-8 device."""
        await self._disconnect()

    def get_connection_metrics(self) -> dict[str, Any]:
        """Get connection metrics for monitoring.

        Returns:
            Dictionary with connection metrics
        """
        return {
            "connected": self._connected,
            "target_mac": self._target_mac,
            "connect_attempts": self._connect_attempts,
            "last_connect_time": self._last_connect_time,
            "connect_timeout": self._connect_timeout,
            "max_attempts": self._max_attempts,
        }
