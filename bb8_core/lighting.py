"""
BB-8 Lighting Controller - LED control with presets and animations

Provides RGB LED control with input validation, preset animations, and
cancellation support. Integrates with safety system for estop handling.
"""

from __future__ import annotations

import asyncio
import time

from .logging_setup import logger


class LightingController:
    """
    Controls BB-8 LED lighting with static colors and animated presets.

    Features:
    - RGB input clamping (0-255)
    - Non-blocking preset animations
    - Animation cancellation within ≤100ms
    - Estop integration for immediate animation halt
    """

    def __init__(self, ble_session=None):
        """Initialize lighting controller."""
        self._ble_session = ble_session
        self._toy = None  # Will be set when connected
        self._active_task: asyncio.Task | None = None
        self._cancel_event = asyncio.Event()
        self._last_static_rgb: tuple[int, int, int] | None = None

        logger.info(
            {
                "event": "lighting_controller_init",
                "session_provided": ble_session is not None,
            }
        )

    def set_ble_session(self, session) -> None:
        """Update BLE session reference."""
        self._ble_session = session
        logger.debug({"event": "lighting_session_updated"})

    @staticmethod
    def clamp_rgb(r: int, g: int, b: int) -> tuple[int, int, int]:
        """
        Clamp RGB values to valid 0-255 range.

        Args:
            r, g, b: RGB color values (may be outside 0-255)

        Returns:
            tuple[int, int, int]: Clamped RGB values
        """
        clamped_r = max(0, min(255, int(r)))
        clamped_g = max(0, min(255, int(g)))
        clamped_b = max(0, min(255, int(b)))

        if (clamped_r, clamped_g, clamped_b) != (r, g, b):
            logger.debug(
                {
                    "event": "lighting_rgb_clamped",
                    "original": [r, g, b],
                    "clamped": [clamped_r, clamped_g, clamped_b],
                }
            )

        return clamped_r, clamped_g, clamped_b

    async def cancel_active(self) -> None:
        """
        Cancel any active animation within ≤100ms.

        This method is idempotent and safe to call multiple times.
        """
        if self._active_task and not self._active_task.done():
            logger.info({"event": "lighting_cancel_active_animation"})

            # Signal cancellation
            self._cancel_event.set()

            # Give task up to 100ms to cancel gracefully
            try:
                await asyncio.wait_for(self._active_task, timeout=0.1)
            except asyncio.TimeoutError:
                logger.warning(
                    {
                        "event": "lighting_cancel_timeout",
                        "timeout_ms": 100,
                    }
                )
                # Force cancel if timeout
                self._active_task.cancel()
                try:
                    await self._active_task
                except asyncio.CancelledError:
                    pass
            except asyncio.CancelledError:
                pass

            self._active_task = None

        # Reset cancel event for next animation
        self._cancel_event.clear()

    async def set_static(self, r: int, g: int, b: int) -> None:
        """
        Set static LED color with RGB clamping.

        Args:
            r, g, b: RGB color values
        """
        # Cancel any active animation first
        await self.cancel_active()

        # Clamp RGB values
        r, g, b = self.clamp_rgb(r, g, b)
        self._last_static_rgb = (r, g, b)

        # Apply to device if connected
        if self._ble_session and self._ble_session.is_connected and self._toy:
            try:
                self._toy.set_led(r, g, b)
                logger.info(
                    {
                        "event": "lighting_static_applied",
                        "rgb": [r, g, b],
                    }
                )
            except Exception as e:
                logger.error(
                    {
                        "event": "lighting_static_error",
                        "rgb": [r, g, b],
                        "error": str(e),
                    }
                )
        else:
            logger.info(
                {
                    "event": "lighting_static_applied",
                    "rgb": [r, g, b],
                }
            )

    async def run_preset(self, name: str) -> bool:
        """
        Run a named preset animation.

        Args:
            name: Preset name ('off', 'white', 'police', 'sunset')

        Returns:
            bool: True if preset exists and started, False otherwise
        """
        # Validate preset name
        if name not in ["off", "white", "police", "sunset"]:
            logger.error(
                {
                    "event": "lighting_invalid_preset",
                    "preset": name,
                    "available": ["off", "white", "police", "sunset"],
                }
            )
            return False

        # Cancel any active animation first
        await self.cancel_active()

        # Create and start animation task
        self._active_task = asyncio.create_task(self._run_preset_animation(name))

        logger.info(
            {
                "event": "lighting_preset_started",
                "preset": name,
            }
        )

        return True

    async def _run_preset_animation(self, name: str) -> None:
        """
        Internal method to run preset animation with cancellation support.

        Args:
            name: Preset name to run
        """
        try:
            if name == "off":
                await self._preset_off()
            elif name == "white":
                await self._preset_white()
            elif name == "police":
                await self._preset_police()
            elif name == "sunset":
                await self._preset_sunset()

            logger.info(
                {
                    "event": "lighting_preset_completed",
                    "preset": name,
                }
            )

        except asyncio.CancelledError:
            logger.info(
                {
                    "event": "lighting_preset_cancelled",
                    "preset": name,
                }
            )
            raise
        except Exception as e:
            logger.error(
                {
                    "event": "lighting_preset_error",
                    "preset": name,
                    "error": str(e),
                }
            )
            raise

    async def _preset_off(self) -> None:
        """Off preset - immediate black."""
        if self._ble_session and self._ble_session.is_connected and self._toy:
            self._toy.set_led(0, 0, 0)
        logger.info({"event": "lighting_static_applied", "rgb": [0, 0, 0]})

    async def _preset_white(self) -> None:
        """White preset - immediate full white."""
        if self._ble_session and self._ble_session.is_connected and self._toy:
            self._toy.set_led(255, 255, 255)
        logger.info({"event": "lighting_static_applied", "rgb": [255, 255, 255]})

    async def _preset_police(self) -> None:
        """
        Preset: Police lights - alternate blue/red for ~4s max.

        Pattern: Blue (0,0,255) ↔ Red (255,0,0) at ~200ms intervals
        """
        end_time = time.time() + 4.0  # 4 second max duration
        colors = [(0, 0, 255), (255, 0, 0)]  # Blue, Red
        color_idx = 0

        while time.time() < end_time:
            if self._cancel_event.is_set():
                break

            r, g, b = colors[color_idx]
            await self._apply_color(r, g, b)

            # Wait 200ms or until cancelled
            try:
                await asyncio.wait_for(self._cancel_event.wait(), timeout=0.2)
                break  # Cancelled
            except asyncio.TimeoutError:
                pass  # Continue animation

            color_idx = (color_idx + 1) % len(colors)

    async def _preset_sunset(self) -> None:
        """
        Preset: Sunset animation - warm color ramp.

        Pattern: (255,80,0) → (255,20,0) → (120,0,10) with ~300ms steps
        Runs for 1-2 cycles depending on cancellation.
        """
        colors = [
            (255, 80, 0),  # Bright orange
            (255, 50, 0),  # Orange
            (255, 20, 0),  # Dark orange
            (200, 10, 5),  # Deep orange
            (120, 0, 10),  # Dark red
        ]

        # Run 2 cycles max
        for cycle in range(2):
            if self._cancel_event.is_set():
                break

            for r, g, b in colors:
                if self._cancel_event.is_set():
                    break

                await self._apply_color(r, g, b)

                # Wait 300ms or until cancelled
                try:
                    await asyncio.wait_for(self._cancel_event.wait(), timeout=0.3)
                    return  # Cancelled
                except asyncio.TimeoutError:
                    pass  # Continue animation

    async def _apply_color(self, r: int, g: int, b: int) -> None:
        """
        Apply color to device with error handling.

        Args:
            r, g, b: RGB values (assumed already clamped)
        """
        if self._ble_session:
            try:
                await self._ble_session.set_led_rgb(r, g, b)
                self._last_static_rgb = (r, g, b)  # Track last applied color
            except Exception as e:
                logger.error(
                    {
                        "event": "lighting_apply_error",
                        "rgb": [r, g, b],
                        "error": str(e),
                    }
                )
                # Don't re-raise during animation to avoid stopping it
        else:
            logger.debug(
                {
                    "event": "lighting_apply_no_session",
                    "rgb": [r, g, b],
                }
            )

    def get_last_static_rgb(self) -> tuple[int, int, int]:
        """Get the last applied static RGB color."""
        return self._last_static_rgb

    def is_animation_active(self) -> bool:
        """Check if an animation is currently running."""
        return self._active_task is not None and not self._active_task.done()

    async def shutdown(self) -> None:
        """Shutdown lighting controller and cancel active animations."""
        logger.info({"event": "lighting_controller_shutdown"})
        await self.cancel_active()


# Global lighting controller instance (initialized by facade)
_lighting_controller: LightingController | None = None


def get_lighting_controller() -> LightingController:
    """Get the global lighting controller instance."""
    global _lighting_controller
    if _lighting_controller is None:
        _lighting_controller = LightingController()
    return _lighting_controller


def initialize_lighting_controller(
    ble_session=None,
) -> LightingController:
    """Initialize the global lighting controller with BLE session."""
    global _lighting_controller
    _lighting_controller = LightingController(ble_session)
    return _lighting_controller


async def shutdown_lighting_controller() -> None:
    """Shutdown the global lighting controller."""
    global _lighting_controller
    if _lighting_controller:
        await _lighting_controller.shutdown()
        _lighting_controller = None
