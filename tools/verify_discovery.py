from __future__ import annotations

# --- PATCHED: Accept both short and long key styles ---
import json
import os
from typing import Any

import paho.mqtt.client as mqtt

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


def _want_led() -> bool:
    return os.getenv("PUBLISH_LED_DISCOVERY", "0") == "1"


def first_identifiers(dev: dict[str, Any] | None) -> list[str]:
    if not dev:
        return []
    for k in ("identifiers",):
        if k in dev and isinstance(dev[k], list):
            return dev[k]
    return []


def get_any(d: dict[str, Any], key: str) -> Any:
    for k in KEY_SYNONYMS.get(key, [key]):
        if k in d:
            return d[k]
    return None


def extract_cfg(raw: str) -> dict[str, object]:
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _connect() -> mqtt.Client:
    host = os.getenv("MQTT_HOST", "127.0.0.1")
    port = int(os.getenv("MQTT_PORT", "1883"))
    user = os.getenv("MQTT_USERNAME")
    pw = os.getenv("MQTT_PASSWORD")
    c = mqtt.Client()
    if user:
        c.username_pw_set(user, pw or "")
    c.connect(host, port, keepalive=10)
    return c


def verify(timeout: float = 2.0) -> tuple[list[dict[str, object]], bool]:
    topics = list(CFG_REQUIRED)
    if _want_led():
        topics.append(CFG_LED)

    c = _connect()
    results: dict[str, dict[str, object]] = {}
    retained: dict[str, bool] = {}
    want = {t for t, _ in topics}

    def on_message(_client, _userdata, msg):
        if msg.topic in want:
            retained[msg.topic] = bool(msg.retain)
            results[msg.topic] = extract_cfg(msg.payload.decode("utf-8", "ignore"))

    c.on_message = on_message
    c.loop(timeout=timeout)

    rows: list[dict[str, object]] = []
    all_ok = True
    for topic, label in topics:
        cfg = results.get(topic, {})
        dev = get_any(cfg, "dev")
        identifiers = []
        if isinstance(dev, dict):
            ids = dev.get("identifiers")
            if isinstance(ids, list):
                identifiers = ids
        row = {
            "topic": topic,
            "retained": bool(retained.get(topic, False)),
            "stat_t": get_any(cfg, "stat_t") or "",
            "avty_t": get_any(cfg, "avty_t") or "",
            "sw_version": (
                (dev or {}).get("sw_version", "") if isinstance(dev, dict) else ""
            ),
            "identifiers": identifiers,
        }
        if label == "led" and not _want_led():
            ok = True  # LED not required when disabled
        else:
            ok = (
                row["retained"]
                and bool(row["stat_t"])
                and bool(row["avty_t"])
                and bool(row["identifiers"])
            )
        all_ok = all_ok and ok
        rows.append(row)
    return rows, all_ok


def main() -> int:
    rows, ok = verify()
    print("Discovery Verification Results:")
    print(
        "Topic                      | Retained | stat_t              | avty_t      | "
        "sw_version      | identifiers"
    )
    print(
        "---------------------------|----------|---------------------|-------------|----------------|-------------------"
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
