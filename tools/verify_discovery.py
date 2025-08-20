from __future__ import annotations

import json
import os
import time
from typing import Any

import paho.mqtt.client as mqtt

# --- PATCHED: Accept both short and long key styles ---

KEY_SYNONYMS = {
    "stat_t": ["stat_t", "state_topic"],
    "avty_t": ["avty_t", "availability_topic", "availability"],
    "uniq_id": ["uniq_id", "unique_id"],
    "dev": ["dev", "device"],
    "dev_cla": ["dev_cla", "device_class"],
    "unit_of_meas": ["unit_of_meas", "unit_of_measurement", "unit"],
}


KEY_SYNONYMS: dict[str, list[str]] = {
    "stat_t": ["stat_t", "state_topic"],
    "avty_t": ["avty_t", "availability_topic", "availability"],
    "uniq_id": ["uniq_id", "unique_id"],
    "dev": ["dev", "device"],
    "dev_cla": ["dev_cla", "device_class"],
    "unit_of_meas": ["unit_of_meas", "unit_of_measurement", "unit"],
}

CFG_REQUIRED = [
    ("homeassistant/binary_sensor/bb8_presence/config", "presence"),
    ("homeassistant/sensor/bb8_rssi/config", "rssi"),
]
CFG_LED = ("homeassistant/light/bb8_led/config", "led")

# Removed duplicate definition of first_identifiers

CFG_REQUIRED = [
    ("homeassistant/binary_sensor/bb8_presence/config", "presence"),
    ("homeassistant/sensor/bb8_rssi/config", "rssi"),
]
CFG_LED = ("homeassistant/light/bb8_led/config", "led")


def want_led() -> bool:
    return os.getenv("PUBLISH_LED_DISCOVERY", "0") == "1"


def get_any(d: dict[str, Any], key: str) -> Any:
    for k in KEY_SYNONYMS.get(key, [key]):
        if isinstance(d, dict) and k in d:
            return d[k]
    return None


def first_identifiers(dev: dict[str, Any] | None) -> list[str]:
    if isinstance(dev, dict):
        ids = dev.get("identifiers")
        if isinstance(ids, list):
            return ids
    return []


def extract_cfg(raw: str) -> dict[str, Any]:
    try:
        return json.loads(raw)
    except Exception:
        return {}


def verify(timeout: float = 3.0) -> tuple[list[dict[str, Any]], bool]:
    host = os.getenv("MQTT_HOST", "127.0.0.1")
    port = int(os.getenv("MQTT_PORT", "1883"))
    user = os.getenv("MQTT_USERNAME")
    pw = os.getenv("MQTT_PASSWORD")

    topics = list(CFG_REQUIRED)
    if want_led():
        topics.append(CFG_LED)
    want_topics = {t for t, _ in topics}

    results: dict[str, dict[str, Any]] = {}
    retained: dict[str, bool] = {}
    connected = False

    def on_connect(c, _u, _flags, rc):
        nonlocal connected
        connected = rc == 0

    def on_message(_c, _u, msg):
        if msg.topic in want_topics:
            retained[msg.topic] = bool(msg.retain)
            results[msg.topic] = extract_cfg(msg.payload.decode("utf-8", "ignore"))

    c = mqtt.Client()
    if user:
        c.username_pw_set(user, pw or "")
    c.on_connect = on_connect
    c.on_message = on_message
    c.connect(host, port, keepalive=10)
    c.loop_start()

    # wait until connected
    t0 = time.time()
    while not connected and time.time() - t0 < 2.0:
        time.sleep(0.05)

    # subscribe after connection established
    for t, _ in topics:
        c.subscribe(t, qos=0)

    # collect retained messages
    t1 = time.time()
    while time.time() - t1 < timeout and len(results) < len(want_topics):
        time.sleep(0.05)

    c.loop_stop()

    # build rows
    rows: list[dict[str, Any]] = []
    all_ok = True
    for topic, label in topics:
        cfg = results.get(topic, {})
        dev = get_any(cfg, "dev")
        row = {
            "topic": topic,
            "retained": bool(retained.get(topic, False)),
            "stat_t": get_any(cfg, "stat_t") or "",
            "avty_t": get_any(cfg, "avty_t") or "",
            "sw_version": (
                (dev or {}).get("sw_version", "") if isinstance(dev, dict) else ""
            ),
            "identifiers": first_identifiers(dev),
        }
        ok = True
        if label != "led" or want_led():
            ok = (
                row["retained"]
                and bool(row["stat_t"])
                and bool(row["avty_t"])
                and bool(row["identifiers"])
            )
        rows.append(row)
        all_ok = all_ok and ok

    # tiny debug hint when nothing arrived
    if not results:
        rows.append(
            {
                "topic": "DEBUG",
                "retained": False,
                "stat_t": f"no msgs in {timeout:.1f}s (host={host})",
                "avty_t": "",
                "sw_version": "",
                "identifiers": [],
            }
        )

    return rows, all_ok


def main() -> int:
    rows, ok = verify()
    print("Discovery Verification Results:")
    print(
        "Topic                      | Retained | stat_t              | avty_t      | "
        "sw_version      | identifiers"
    )
    print(
        "---------------------------|----------|---------------------|-------------|-"
        "---------------|-------------------"
    )
    for r in rows:
        print(
            f"{r['topic']} | {str(r['retained']):<7} | {r['stat_t']:<19} | "
            f"{r['avty_t']:<11} | {r['sw_version']:<14} | {r['identifiers']}"
        )
    print("\nPASS" if ok else "\nFAIL: One or more checks did not pass.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
