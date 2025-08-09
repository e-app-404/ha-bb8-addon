from dataclasses import dataclass
from typing import Optional, Tuple
from .core import Core  # low-level encoder/transport
from .util import clamp  # small helper: clamp(x, lo, hi)
from spherov2.commands.core import IntervalOptions
import time
from bb8_core.logging_setup import logger

@dataclass(frozen=True)
class Rgb:
    r: int
    g: int
    b: int
    def clamped(self) -> "Rgb":
        return Rgb(clamp(self.r, 0, 255), clamp(self.g, 0, 255), clamp(self.b, 0, 255))

class Bb8Facade:
    """
    High-level, type-safe façade for BB-8.
    This is the ONLY layer upstream code (MQTT/HA) should call.
    """

    def __init__(self, toy):
        self._toy = toy
        logger.info({"event": "facade_init", "toy": str(toy)})

    # ----- Sleep ------------------------------------------------------------
    def sleep(self, after_ms: int = 0) -> None:
        logger.info({"event": "facade_sleep", "after_ms": after_ms})
        if after_ms > 0:
            time.sleep(after_ms / 1000.0)
        try:
            self._toy.sleep(IntervalOptions.NONE, 0, 0, 0)
            logger.info({"event": "facade_sleep_done"})
        except Exception as e:
            logger.error({"event": "facade_sleep_error", "error": str(e)})

    # ----- Main LED ---------------------------------------------------------
    def set_led(self, color: Rgb, transition_ms: int = 0, steps: int = 10) -> None:
        c = color.clamped()
        logger.info({"event": "facade_set_led", "color": c.__dict__, "transition_ms": transition_ms, "steps": steps})
        if transition_ms <= 0:
            try:
                self._toy.set_main_led(c.r, c.g, c.b, None)
                logger.info({"event": "facade_set_led_done", "color": c.__dict__})
            except Exception as e:
                logger.error({"event": "facade_set_led_error", "error": str(e)})
            return
        cur = self.get_led() or Rgb(0, 0, 0)
        dt = max(1, transition_ms // max(1, steps))
        for i in range(1, steps + 1):
            t = i / steps
            ri = int(cur.r + (c.r - cur.r) * t)
            gi = int(cur.g + (c.g - cur.g) * t)
            bi = int(cur.b + (c.b - cur.b) * t)
            try:
                self._toy.set_main_led(ri, gi, bi, None)
                logger.debug({"event": "facade_set_led_fade_step", "step": i, "color": {"r": ri, "g": gi, "b": bi}})
            except Exception as e:
                logger.error({"event": "facade_set_led_fade_error", "step": i, "error": str(e)})
            time.sleep(dt / 1000.0)
        logger.info({"event": "facade_set_led_fade_done", "color": c.__dict__})

    def get_led(self) -> Optional[Rgb]:
        logger.debug({"event": "facade_get_led"})
        return None

    # ----- Motion (heading/speed convenience) ------------------------------
    def drive(self, heading_deg: int, speed_0_255: int, duration_ms: Optional[int] = None) -> None:
        h = int(heading_deg) % 360
        s = clamp(int(speed_0_255), 0, 255)
        logger.info({"event": "facade_drive", "heading": h, "speed": s, "duration_ms": duration_ms})
        try:
            if hasattr(self._toy, 'set_heading'):
                self._toy.set_heading(h, None)
            if hasattr(self._toy, 'set_speed'):
                self._toy.set_speed(s, None)
            if duration_ms and duration_ms > 0:
                time.sleep(duration_ms / 1000.0)
                if hasattr(self._toy, 'set_speed'):
                    self._toy.set_speed(0, None)
            logger.info({"event": "facade_drive_done"})
        except Exception as e:
            logger.error({"event": "facade_drive_error", "error": str(e)})

# Notes
#   • We intentionally freeze the Core.sleep(...) mapping in one place so we can field‑test the exact tuple on real hardware and adjust if needed without touching MQTT contracts.
#   • LED fades are done in userspace for now (simple linear tween). That’s sufficient for HA scenes/automations.
