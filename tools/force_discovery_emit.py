from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import paho.mqtt.client as mqtt

LOG_CANDIDATES = [
    Path("addon/reports/ha_bb8_addon.log"),
    Path("reports/ha_bb8_addon.log"),
]


def find_mac_from_logs() -> str | None:
    rx = re.compile(r"(?:MAC[:=]\s*|mac:)\s*([0-9A-F]{2}(?::[0-9A-F]{2}){5})", re.I)
    for p in LOG_CANDIDATES:
        if p.exists():
            try:
                for line in p.read_text(errors="ignore").splitlines():
                    m = rx.search(line)
                    if m:
                        return m.group(1).upper()
            except Exception:
                pass
    return None


def main() -> int:
    host = os.getenv("MQTT_HOST", "127.0.0.1")
    port = int(os.getenv("MQTT_PORT", "1883"))
    user = os.getenv("MQTT_USERNAME")
    pw = os.getenv("MQTT_PASSWORD")
    mac = (os.getenv("BB8_MAC") or find_mac_from_logs() or "AA:BB:CC:DD:EE:FF").upper()
    if mac == "AA:BB:CC:DD:EE:FF":
        print("ERROR: Real MAC not provided or detectable. Set BB8_MAC=XX:XX:XX:XX:XX:XX and retry.", file=sys.stderr)
        return 2
    uid = mac.replace(":", "").lower()
    version = os.getenv("BB8_VERSION", "2025.08.20")
    dev = {
        "identifiers": ["bb8", f"mac:{mac}"],
        "connections": [["mac", mac]],
        "manufacturer": "Sphero",
        "model": "S33 BB84 LE",
        "name": "BB-8",
        "sw_version": version,
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
    c = mqtt.Client()
    if user:
        c.username_pw_set(user, pw or "")
    c.connect(host, port, keepalive=10)
    time.sleep(0.2)
    # retained config
    c.publish(
        "homeassistant/binary_sensor/bb8_presence/config",
        json.dumps(pres, separators=(",", ":")),
        qos=0,
        retain=True,
    )
    c.publish(
        "homeassistant/sensor/bb8_rssi/config",
        json.dumps(rssi, separators=(",", ":")),
        qos=0,
        retain=True,
    )
    # ensure retained states exist too
    c.publish("bb8/status", "online", qos=0, retain=True)
    c.publish("bb8/presence/state", "online", qos=0, retain=True)
    c.publish("bb8/rssi/state", "-60", qos=0, retain=True)
    print("FORCE_DISCOVERY: published retained configs & states for", mac)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
