# --- PATCHED: Accept both short and long key styles ---
import json
import os
import time
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


<<<<<<< HEAD:bb8_core/verify_discovery.py
def on_message(_, _unused, msg):
    payload = msg.payload.decode("utf-8")
=======
def get_any(d: dict[str, Any], key: str) -> Any:
    for k in KEY_SYNONYMS.get(key, [key]):
        if k in d:
            return d[k]
    return None


def first_identifiers(dev: dict[str, Any] | None) -> list[str]:
    if not dev:
        return []
    for k in ("identifiers",):
        if k in dev and isinstance(dev[k], list):
            return dev[k]
    return []


def extract_cfg(raw: str) -> dict[str, Any]:
>>>>>>> 2c13418 (fix(discovery): verifier accepts short+long keys; scanner publishes both; retained configs):tools/verify_discovery.py
    try:
        return json.loads(raw)
    except Exception:
<<<<<<< HEAD:bb8_core/verify_discovery.py
        print(f"Invalid JSON on {msg.topic}: {payload}")
        sys.exit(2)
    results[msg.topic] = data
    retained[msg.topic] = msg.retain
    # Extract MAC for device block check
    dev = data.get("dev") or data.get("device")
    if dev and isinstance(dev, dict):
        for _ in dev.get("identifiers", []):
            pass  # No need to assign mac_upper since it's not used
=======
        return {}
>>>>>>> 2c13418 (fix(discovery): verifier accepts short+long keys; scanner publishes both; retained configs):tools/verify_discovery.py


CFG_TOPICS = [
    ("homeassistant/binary_sensor/bb8_presence/config", "presence"),
    ("homeassistant/sensor/bb8_rssi/config", "rssi"),
]


def verify_configs_and_states(
    client: mqtt.Client, timeout: float = 2.0
) -> tuple[list[dict[str, Any]], bool]:
    results: dict[str, dict[str, Any]] = {}
    retained: dict[str, bool] = {}
    done = {t: False for t, _ in CFG_TOPICS}

    def on_message(_c, _u, msg):
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
    all_ok = True
    for topic, _label in CFG_TOPICS:
        cfg = results.get(topic, {})
        dev = get_any(cfg, "dev")
        row = {
            "topic": topic,
            "retained": retained.get(topic, False),
            "stat_t": get_any(cfg, "stat_t") or "",
            "avty_t": get_any(cfg, "avty_t") or "",
            "sw_version": (dev or {}).get("sw_version", "")
            if isinstance(dev, dict)
            else "",
            "identifiers": first_identifiers(dev),
        }
        ok = (
            row["retained"]
            and bool(row["stat_t"])
            and bool(row["avty_t"])
            and bool(row["identifiers"])
        )
        all_ok = all_ok and ok
        rows.append(row)
    return rows, all_ok


def main():
    host = os.getenv("MQTT_HOST", "127.0.0.1")
    port = int(os.getenv("MQTT_PORT", "1883"))
    user = os.getenv("MQTT_USERNAME")
    pw = os.getenv("MQTT_PASSWORD")
    client = mqtt.Client()
    if user:
        client.username_pw_set(user, pw or "")
    client.connect(host, port, keepalive=10)
    rows, ok = verify_configs_and_states(client)
    print("Discovery Verification Results:")
    print(
        "Topic                      | Retained | stat_t              | avty_t      | sw_version      | identifiers"
    )
    print(
<<<<<<< HEAD:bb8_core/verify_discovery.py
        f"{t:27} | {str(retained.get(t, False)):8} | {stat_t:19} | "
        f"{avty_t:11} | {sw_version:14} | {identifiers}"
=======
        "---------------------------|----------|---------------------|-------------|----------------|-------------------"
>>>>>>> 2c13418 (fix(discovery): verifier accepts short+long keys; scanner publishes both; retained configs):tools/verify_discovery.py
    )
    for r in rows:
        print(
            f"{r['topic']} | {str(r['retained']):<7} | {r['stat_t']:<19} | {r['avty_t']:<11} | {r['sw_version']:<14} | {r['identifiers']}"
        )
    print("\nPASS" if ok else "\nFAIL: One or more checks did not pass.")


if __name__ == "__main__":
    main()
