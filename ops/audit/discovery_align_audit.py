from __future__ import annotations

import json
import os
import sys

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

sys.path.insert(0, "tools")
# Ensure these functions exist in verify_discovery.py or update the
# import to match the actual function names.
from addon.bb8_core.util import extract_cfg, first_identifiers, get_any

REQ_TOPICS = [
    "homeassistant/binary_sensor/bb8_presence/config",
    "homeassistant/sensor/bb8_rssi/config",
]
OPT_TOPICS = ["homeassistant/light/bb8_led/config"]


def fetch_configs(client: mqtt.Client, topics: list[str], timeout=2.0):
    data = {}

    def on_message(client, userdata, msg):
        data[msg.topic] = (
            bool(msg.retain),
            extract_cfg(msg.payload.decode("utf-8", "ignore")),
        )

    client.on_message = on_message
    for t in topics:
        client.subscribe(t, qos=0)
    import time

    t0 = time.time()
    while time.time() - t0 < timeout and len(data) < len(topics):
        client.loop(timeout=0.1)
    return data


def main() -> int:
    host = os.getenv("MQTT_HOST", "127.0.0.1")
    port = int(os.getenv("MQTT_PORT", "1883"))
    user = os.getenv("MQTT_USERNAME")
    pw = os.getenv("MQTT_PASSWORD")
    c = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
    if user:
        c.username_pw_set(user, pw or "")
    c.connect(host, port, 10)
    cfgs = fetch_configs(c, REQ_TOPICS + OPT_TOPICS)
    # validate device block alignment
    dev_ids = set()
    for _, (_, cfg) in cfgs.items():
        dev = get_any(cfg, "dev") or {}
        ids = tuple(first_identifiers(dev))
        if ids:
            dev_ids.add(ids)
    ok = len(dev_ids) <= 1
    out = {
        "aligned": ok,
        "device_id_sets": list(map(list, dev_ids)),
        "topics": list(cfgs.keys()),
    }
    print(json.dumps(out, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
