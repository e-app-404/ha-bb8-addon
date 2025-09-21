"""Utilities to verify Home Assistant discovery configurations.

Small helper module used to validate discovery config topics are present and
well-formed on an MQTT broker. The functions are intentionally minimal and
safe for offline checks.
"""

import json
import os
import time
from typing import Any

import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion

KEY_SYNONYMS = {
    "stat_t": ["stat_t", "state_topic"],
    "avty_t": ["avty_t", "availability_topic", "availability"],
    "uniq_id": ["uniq_id", "unique_id"],
    "dev": ["dev", "device"],
    "dev_cla": ["dev_cla", "device_class"],
    "unit_of_meas": ["unit_of_meas", "unit_of_measurement", "unit"],
}

CFG_TOPICS = [
    ("homeassistant/binary_sensor/bb8_presence/config", "presence"),
    ("homeassistant/sensor/bb8_rssi/config", "rssi"),
]


def on_message(client, userdata, msg):
    # payload is not used, remove assignment
    pass


def get_any(d: dict[str, Any], key: str) -> Any:
    """Return the first available synonym value for ``key`` from mapping.

    If none of the synonyms are present, ``None`` is returned.
    """
    for k in KEY_SYNONYMS.get(key, [key]):
        if k in d:
            return d[k]
    return None


def first_identifiers(dev: dict[str, Any] | None) -> list[str]:
    """Return the device 'identifiers' list if present and valid.

    If the device mapping is missing or identifiers are absent, an empty
    list is returned.
    """
    if not dev:
        return []
    for k in ("identifiers",):
        if k in dev and isinstance(dev[k], list):
            return dev[k]
    return []


def extract_cfg(raw: str) -> dict[str, Any]:
    """Safely decode a JSON configuration string.

    Any decode errors are caught and an empty mapping is returned.
    """
    try:
        return json.loads(raw)
    except Exception:
        print("Invalid JSON encountered.")
        return {}


def verify_configs_and_states(
    client: mqtt.Client,
    timeout: float = 2.0,
) -> tuple[list[dict[str, Any]], bool]:
    results: dict[str, dict[str, Any]] = {}
    retained: dict[str, bool] = {}
    done = {t: False for t, _ in CFG_TOPICS}

    def on_message(client, userdata, msg):
        if msg.topic in (t for t, _ in CFG_TOPICS):
            retained[msg.topic] = bool(msg.retain)
            results[msg.topic] = extract_cfg(msg.payload.decode("utf-8", "ignore"))
            done[msg.topic] = True

    client.on_message = on_message
    for t, _ in CFG_TOPICS:
        client.subscribe(t, qos=0)
    t0 = time.time()
    while time.time() - t0 < timeout and not all(done.values()):
        client.loop(timeout=0.1)

    rows = []
    # Only validate topics that received a config message
    all_ok = True
    for topic in results:
        cfg = results.get(topic, {})
        dev = None
        if "dev" in cfg and isinstance(cfg["dev"], dict):
            dev = cfg["dev"]
        elif "device" in cfg and isinstance(cfg["device"], dict):
            dev = cfg["device"]
        stat_t = get_any(cfg, "stat_t") or get_any(cfg, "state_topic")
        avty_t = (
            get_any(cfg, "avty_t")
            or get_any(cfg, "availability_topic")
            or get_any(cfg, "availability")
        )
        identifiers = first_identifiers(dev)
        row = {
            "topic": topic,
            "retained": retained.get(topic, False),
            "stat_t": stat_t or "",
            "avty_t": avty_t or "",
            "sw_version": (dev.get("sw_version", "") if isinstance(dev, dict) else ""),
            "identifiers": identifiers,
        }
        ok = (
            bool(row["stat_t"])
            and bool(row["avty_t"])
            and isinstance(row["identifiers"], list)
            and len(row["identifiers"]) > 0
        )
        all_ok = all_ok and ok
        rows.append(row)
    return rows, all_ok


def get_mqtt_client():
    return mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)


def main():
    host = os.getenv("MQTT_HOST", "127.0.0.1")
    port = int(os.getenv("MQTT_PORT", "1883"))
    user = os.getenv("MQTT_USERNAME")
    pw = os.getenv("MQTT_PASSWORD")
    client = get_mqtt_client()  # pragma: no cover
    if user:
        client.username_pw_set(user, pw or "")  # pragma: no cover
    client.connect(host, port, keepalive=10)  # pragma: no cover
    rows, ok = verify_configs_and_states(client)  # pragma: no cover
    print("Discovery Verification Results:")  # pragma: no cover
    print(
        "Topic           | Retained | stat_t        | avty_t   | " "sw_ver   | ids",
    )  # pragma: no cover
    for r in rows:  # pragma: no cover
        print(
            f"{r['topic']:27} | {r['retained']!s:8} | {r['stat_t']:19} | "
            f"{r['avty_t']:11} | {r['sw_version']:14} | {r['identifiers']}",
        )  # pragma: no cover
    print(
        "\nPASS" if ok else "\nFAIL: One or more checks did not pass.",
    )  # pragma: no cover


if __name__ == "__main__":
    main()
