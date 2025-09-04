#!/usr/bin/env python3
import json
import os
import sys
import threading
import time
import warnings

import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion

warnings.filterwarnings(
    "ignore", category=DeprecationWarning, module="paho.mqtt.client"
)


def read_mqtt_env():
    host = os.environ.get("MQTT_HOST")
    port_s = os.environ.get("MQTT_PORT") or "1883"
    user = os.environ.get("MQTT_USERNAME") or os.environ.get("MQTT_USER") or ""
    pwd = os.environ.get("MQTT_PASSWORD") or ""
    base = os.environ.get("MQTT_BASE") or "bb8"
    try:
        port = int(port_s)
    except Exception as e:
        raise ValueError(f"Invalid MQTT_PORT: {port_s!r}") from e
    if not host:
        raise RuntimeError("MQTT_HOST is required")
    return host, port, user, pwd, base


def main(timeout=4.0):
    host, port, user, pwd, base = read_mqtt_env()
    seen_online = threading.Event()
    topic = f"{base}/status"

    def on_connect(client, _userdata, _flags, _reason_code, _properties):
        client.subscribe(topic, qos=0)

    def on_message(_client, _userdata, msg):
        try:
            pl = (msg.payload or b"").decode("utf-8", "ignore").strip().lower()
        except Exception:
            pl = ""
        if msg.topic == topic and pl == "online":
            seen_online.set()

    def get_mqtt_client():
        return mqtt.Client(
            client_id=f"precheck-{int(time.time())}",
            protocol=mqtt.MQTTv5,
            callback_api_version=CallbackAPIVersion.VERSION2,
        )

    client = get_mqtt_client()
    if user:
        client.username_pw_set(user, pwd)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host, port, keepalive=30)
    client.loop_start()
    seen_online.wait(timeout=timeout)
    client.loop_stop()
    client.disconnect()

    ok = seen_online.is_set()
    result = {"broker": f"{host}:{port}", "topic": topic, "bridge_online": ok}
    print(json.dumps(result))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
