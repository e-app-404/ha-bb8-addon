from __future__ import annotations

import asyncio
import json
import os
import threading
from typing import Any


# Public constants & helpers shared across bridge/facade/ble
def _mqtt_base() -> str:
    return os.environ.get("MQTT_BASE", "bb8")


# Command topics (inbound). Support both legacy `/set` and new `/cmd` for LED.
CMD_TOPICS: dict[str, list[str]] = {
    "power": [f"{_mqtt_base()}/power/set"],
    "stop": [f"{_mqtt_base()}/stop/press", f"{_mqtt_base()}/stop/set"],
    "sleep": [f"{_mqtt_base()}/sleep/press", f"{_mqtt_base()}/sleep/set"],
    "drive": [f"{_mqtt_base()}/drive/press", f"{_mqtt_base()}/drive/set"],
    "heading": [f"{_mqtt_base()}/heading/set"],
    "speed": [f"{_mqtt_base()}/speed/set"],
    "led": [f"{_mqtt_base()}/led/set", f"{_mqtt_base()}/led/cmd"],
}

# Back-compat aliases (explicitly marked LEGACY) kept for docs/tools but
# gated at runtime by ENABLE_LEGACY_FLAT_TOPICS in the dispatcher.
LEGACY_CMD_TOPICS = CMD_TOPICS.copy()

# State topics (outbound) — STP4 expects '/state' suffix consistently
STATE_TOPICS: dict[str, str] = {
    "power": f"{_mqtt_base()}/power/state",
    "stop": f"{_mqtt_base()}/stop/state",
    "sleep": f"{_mqtt_base()}/sleep/state",
    "drive": f"{_mqtt_base()}/drive/state",
    "heading": f"{_mqtt_base()}/heading/state",
    "speed": f"{_mqtt_base()}/speed/state",
    "led": f"{_mqtt_base()}/led/state",
}


def _coerce_raw(value: Any) -> str | int | float:
    if isinstance(value, int | float | str):
        return value
    return str(value)


def publish_device_echo(
    client: Any,
    state_topic: str,
    value: Any,
    qos: int = 1,
) -> None:
    raw = _coerce_raw(value)
    client.publish(state_topic, payload=raw, qos=qos, retain=False)
    echo = {"value": value, "source": "device"}
    client.publish(state_topic, payload=json.dumps(echo), qos=qos, retain=False)


__all__ = ["CMD_TOPICS", "STATE_TOPICS", "publish_device_echo"]


# Replace publish with helper in handlers:
def on_power_set(client, payload):
    publish_device_echo(client, STATE_TOPICS["power"], payload)


def on_stop(client):
    publish_device_echo(client, STATE_TOPICS["stop"], "pressed")


def on_sleep(client):
    publish_device_echo(client, STATE_TOPICS["sleep"], "idle")


def on_drive(client, value):
    publish_device_echo(client, STATE_TOPICS["drive"], value)


def on_heading(client, value):
    publish_device_echo(client, STATE_TOPICS["heading"], value)


def on_speed(client, value):
    publish_device_echo(client, STATE_TOPICS["speed"], value)


def on_led_set(client, r, g, b):
    """Direct LED state publication helper.
    Does **not** publish to command topics.
    """
    payload = json.dumps({"r": int(r), "g": int(g), "b": int(b)})
    client.publish(STATE_TOPICS["led"], payload=payload, qos=1, retain=False)


# BLE loop thread setup

ble_loop = asyncio.new_event_loop()
threading.Thread(target=ble_loop.run_forever, name="BLEThread", daemon=True).start()

# All BLE calls must use:
# asyncio.run_coroutine_threadsafe(your_coro(), ble_loop)
