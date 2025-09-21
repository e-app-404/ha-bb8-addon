from __future__ import annotations

from .logging_setup import logger


class Core:
    """Low-level BB-8 BLE driver wrapper.
    This class isolates vendor/BLE specifics from higher layers.
    """

    def __init__(self, address: str, adapter: str | None = None) -> None:
        self.address = address
        self.adapter = adapter
        self._connected = False
        self.publish_led_rgb = None  # Optional LED publisher seam
        logger.info(
            {
                "event": "core_init",
                "address": address,
                "adapter": adapter,
            },
        )

    def __enter__(self) -> Core:
        """Context-manager entry: connect and return self."""
        logger.info({"event": "core_enter", "address": self.address})
        self.connect()
        return self

    def __exit__(self, exc_type, _, __) -> None:
        """Context-manager exit: disconnect and log any exception type."""
        logger.info(
            {
                "event": "core_exit",
                "address": self.address,
                "exc_type": str(exc_type),
            },
        )
        self.disconnect()
        self.disconnect()

    def connect(self) -> None:
        """Establish low-level BLE connection (shim in tests).

        Production should implement a real BLE connect (e.g., bleak).
        """
        logger.info({"event": "core_connect", "address": self.address})
        # TODO: real BLE connect (e.g., bleak)
        self._connected = True
        logger.info({"event": "core_connected", "address": self.address})

    def disconnect(self) -> None:
        """Tear down the BLE connection (shim)."""
        logger.info({"event": "core_disconnect", "address": self.address})
        # TODO: real BLE disconnect
        self._connected = False
        logger.info({"event": "core_disconnected", "address": self.address})

    def set_main_led(self, r: int, g: int, b: int, persist: bool | None = None) -> None:
        """Set the primary LED color on the device (shim).

        `persist` controls whether the LED state should survive power cycle.
        """
        logger.info(
            {
                "event": "core_set_main_led",
                "address": self.address,
                "r": r,
                "g": g,
                "b": b,
                "persist": persist,
            },
        )
        # TODO: send LED command over BLE

    def roll(self, speed: int, heading: int, duration_ms: int) -> None:
        """Command the device to roll at `speed` towards `heading`.

        `duration_ms` controls the duration of the motion.
        """
        logger.info(
            {
                "event": "core_roll",
                "address": self.address,
                "speed": speed,
                "heading": heading,
                "duration_ms": duration_ms,
            },
        )
        # TODO: send roll/drive

    def sleep(self, interval_option, p1: int, p2: int, p3: int) -> None:
        """Send device sleep command using provided interval options.

        The p1/p2/p3 parameters match the underlying Sphero API.
        """
        logger.info(
            {
                "event": "core_sleep",
                "address": self.address,
                "interval_option": str(interval_option),
                "p1": p1,
                "p2": p2,
                "p3": p3,
            },
        )
        # TODO: send sleep

    # Optional seam used by facade/tests
    def emit_led(self, bridge, r: int, g: int, b: int) -> None:
        """Emit LED RGB; tests may spy on this seam.
        Production forwards to publisher.
        """
        if hasattr(self, "publish_led_rgb") and callable(self.publish_led_rgb):
            self.publish_led_rgb(bridge, r, g, b)
        else:
            # keep silent if LED publisher not wired; facade will fallback
            return
