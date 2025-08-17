from .logging_setup import logger


def clamp(x: int, lo: int, hi: int) -> int:
    logger.debug({"event": "util_clamp", "x": x, "lo": lo, "hi": hi})
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x
