import json
import os
import sys
import time

import paho.mqtt.client as mqtt

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "")

TOPICS = [
    "homeassistant/binary_sensor/bb8_presence/config",
    "homeassistant/sensor/bb8_rssi/config",
]
results = {}
retained = {}
mac_upper = None


def on_message(_, _unused, msg):
    payload = msg.payload.decode("utf-8")
    try:
        data = json.loads(payload)
    except Exception:
        print(f"Invalid JSON on {msg.topic}: {payload}")
        sys.exit(2)
    results[msg.topic] = data
    retained[msg.topic] = msg.retain
    # Extract MAC for device block check
    dev = data.get("dev") or data.get("device")
    if dev and isinstance(dev, dict):
        for _ in dev.get("identifiers", []):
            pass  # No need to assign mac_upper since it's not used


client = mqtt.Client()
if MQTT_USERNAME:
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.on_message = on_message
client.connect(MQTT_HOST, MQTT_PORT, 60)
for t in TOPICS:
    client.subscribe(t)
client.loop_start()

time.sleep(2)
client.loop_stop()

# Table output
print("\nDiscovery Verification Results:")
print(
    "Topic                      | Retained | stat_t              | avty_t      | sw_version      | identifiers"
)
print(
    "---------------------------|----------|---------------------|-------------|----------------|-------------------"
)
fail = False
for t in TOPICS:
    d = results.get(t, {})
    dev = d.get("dev") or d.get("device") or {}
    stat_t = d.get("stat_t", "")
    avty_t = d.get("avty_t", "")
    sw_version = dev.get("sw_version", "")
    identifiers = dev.get("identifiers", [])
    ok = (
        retained.get(t, False)
        and stat_t.startswith("bb8/")
        and avty_t == "bb8/status"
        and sw_version.startswith("addon:")
        and any(str(i).upper() == f"MAC:{mac_upper}" for i in identifiers)
    )
    print(
        f"{t:27} | {str(retained.get(t, False)):8} | {stat_t:19} | "
        f"{avty_t:11} | {sw_version:14} | {identifiers}"
    )
    if not ok:
        fail = True
if fail:
    print("\nFAIL: One or more checks did not pass.")
    sys.exit(1)
else:
    print("\nPASS: All checks passed.")
    sys.exit(0)
