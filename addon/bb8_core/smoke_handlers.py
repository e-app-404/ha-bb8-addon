#!/usr/bin/env python3
import json
import os
import threading
import time
import warnings

import paho.mqtt.client as mqtt

warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module="paho.mqtt.client",
)


def env():
    host = os.environ.get("MQTT_HOST")
    if host is None:
        raise ValueError("MQTT_HOST environment variable must be set")
    port = int(os.environ.get("MQTT_PORT") or "1883")
    base = os.environ.get("MQTT_BASE", "bb8")
    user = os.environ.get("MQTT_USERNAME") or os.environ.get("MQTT_USER") or ""
    pwd = os.environ.get("MQTT_PASSWORD") or ""
    return host, port, base, user, pwd


def main():
    host, port, base, user, _ = env()
    got = threading.Event()
    diag_t = f"{base}/_diag"
    # v5 client
    c = mqtt.Client(client_id=f"smoke-{int(time.time())}", protocol=mqtt.MQTTv5)

    def on_connect(cl, *_):
        cl.subscribe(diag_t, qos=0)
        # trigger one command the handlers subscribe to
        cl.publish(f"{base}/stop/press", "", qos=0, retain=False)

    def on_message(_, __, msg):
        try:
            ev = json.loads((msg.payload or b"{}").decode("utf-8", "ignore"))
        except Exception:
            ev = {}
        if ev.get("event", "") in (
            "flat_handlers_attached",
            "echo_stop",
            "subscribed",
        ):
            got.set()

    c.on_connect = on_connect
    c.on_message = on_message
    c.connect(host, port, keepalive=30)
    c.loop_start()
    got.wait(2.0)
    ok = got.is_set()
    c.loop_stop()
    c.disconnect()
    print(json.dumps({"handlers_active": ok}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
