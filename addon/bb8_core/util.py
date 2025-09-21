"""Small utility helpers used by the add-on.

These helpers are intentionally tiny and used across the bridge and
device driver modules.
"""

from .logging_setup import logger


def clamp(x: int, lo: int, hi: int) -> int:
    """Clamp ``x`` to the inclusive range ``[lo, hi]``.

    Returns ``lo`` if ``x < lo``, ``hi`` if ``x > hi``, otherwise ``x``.
    """
    logger.debug({"event": "util_clamp", "x": x, "lo": lo, "hi": hi})
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x
