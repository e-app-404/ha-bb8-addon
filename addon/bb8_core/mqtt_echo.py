"""Small helpers to publish scalar and LED MQTT echo messages.

These are tiny helpers used by bridge shims to emit MQTT state echoes
when real hardware is absent.
"""

import json
from typing import Any


def echo_scalar(
    mqtt: Any,
    base: str,
    topic: str,
    value: int | str,
    *,
    source: str = "device",
) -> None:
    """Publish a scalar echo value to ``{base}/{topic}/state``.

    The ``source`` is included in the JSON payload for traceability.
    """
    payload = json.dumps({"value": value, "source": source})
    mqtt.publish(f"{base}/{topic}/state", payload, qos=0, retain=False)


def echo_led(mqtt: Any, base: str, r: int, g: int, b: int) -> None:
    """Publish an RGB LED echo payload to ``{base}/led/state``.

    Values are integers 0..255.
    """
    payload = json.dumps({"r": r, "g": g, "b": b})
    mqtt.publish(f"{base}/led/state", payload, qos=0, retain=False)
