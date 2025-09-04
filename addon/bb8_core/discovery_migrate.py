from __future__ import annotations

import json
import os
import sys

import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion

REQ_TOPICS = [
    "homeassistant/binary_sensor/bb8_presence/config",
    "homeassistant/sensor/bb8_rssi/config",
]
OPT_TOPICS = ["homeassistant/light/bb8_led/config"]


def publish_retained(c: mqtt.Client, topic: str, payload: dict):
    c.publish(topic, json.dumps(payload, separators=(",", ":")), qos=0, retain=True)


def main() -> int:
    host = os.getenv("MQTT_HOST", "127.0.0.1")
    port = int(os.getenv("MQTT_PORT", "1883"))
    user = os.getenv("MQTT_USERNAME")
    pw = os.getenv("MQTT_PASSWORD")
    mac = os.getenv("BB8_MAC", "").upper()
    if not mac or mac == "AA:BB:CC:DD:EE:FF":
        print("ERROR: set BB8_MAC=<REAL_MAC>", file=sys.stderr)
        return 2
    uid = mac.replace(":", "").lower()
    dev = {
        "identifiers": ["bb8", f"mac:{mac}"],
        "connections": [["mac", mac]],
        "manufacturer": "Sphero",
        "model": "S33 BB84 LE",
        "name": "BB-8",
        "sw_version": os.getenv("BB8_VERSION", "2025.08.20"),
    }
    pres = {
        "name": "BB-8 Presence",
        "unique_id": f"bb8_presence_{uid}",
        "uniq_id": f"bb8_presence_{uid}",
        "state_topic": "bb8/presence/state",
        "stat_t": "bb8/presence/state",
        "availability_topic": "bb8/status",
        "avty_t": "bb8/status",
        "payload_on": "online",
        "pl_on": "online",
        "payload_off": "offline",
        "pl_off": "offline",
        "device": dev,
        "dev": dev,
    }
    rssi = {
        "name": "BB-8 RSSI",
        "unique_id": f"bb8_rssi_{uid}",
        "uniq_id": f"bb8_rssi_{uid}",
        "state_topic": "bb8/rssi/state",
        "stat_t": "bb8/rssi/state",
        "availability_topic": "bb8/status",
        "avty_t": "bb8/status",
        "device_class": "signal_strength",
        "dev_cla": "signal_strength",
        "unit_of_measurement": "dBm",
        "unit_of_meas": "dBm",
        "device": dev,
        "dev": dev,
    }
    led = {
        "name": "BB-8 LED",
        "unique_id": f"bb8_led_{uid}",
        "uniq_id": f"bb8_led_{uid}",
        "command_topic": "bb8/led/set",
        "state_topic": "bb8/led/state",
        "availability_topic": "bb8/status",
        "avty_t": "bb8/status",
        "device": dev,
        "dev": dev,
    }

    def get_mqtt_client():
        return mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)

    c = get_mqtt_client()
    if user:
        c.username_pw_set(user, pw or "")
    c.connect(host, port, 10)
    # Telemetry hook (non-fatal)
    try:
        from .telemetry import led_discovery

        duplicates_count = 0  # If you have a way to count duplicates, set here
        led_discovery(c, led["unique_id"], duplicates_count)
    except Exception:
        pass
    # prune all existing configs
    for t in REQ_TOPICS + OPT_TOPICS:
        c.publish(t, None, qos=0, retain=True)
    # re-emit required
    publish_retained(c, REQ_TOPICS[0], pres)
    publish_retained(c, REQ_TOPICS[1], rssi)
    # optionally emit LED if requested
    if os.getenv("PUBLISH_LED_DISCOVERY", "0") == "1":
        publish_retained(c, OPT_TOPICS[0], led)
    # ensure retained states exist
    c.publish("bb8/status", "online", qos=0, retain=True)
    c.publish("bb8/presence/state", "online", qos=0, retain=True)
    c.publish("bb8/rssi/state", "-60", qos=0, retain=True)
    print("MIGRATE: discovery re-published for", mac)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
