#!/usr/bin/env python
import argparse
import json
import os
import time

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion


def env(name, default=None, required=False):
    v = os.environ.get(name, default)
    if required and (v is None or v == ""):
        if default is not None:
            return default
        raise SystemExit(f"[trace] missing env {name}")
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=int, default=12)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    host = env("MQTT_HOST", required=True)
    port = int(env("MQTT_PORT", "1883"))
    user = env("MQTT_USERNAME")
    pwd = env("MQTT_PASSWORD")
    base = env("MQTT_BASE", "bb8")

    out = args.out
    with open(out, "w", encoding="utf-8") as fh:
        start = time.time()
        client = mqtt.Client(
            client_id=f"trace-{int(start)}",
            callback_api_version=CallbackAPIVersion.VERSION2,
        )
        if user:
            client.username_pw_set(user, pwd or None)

        def on_connect(client, _userdata, _flags, rc):
            if rc == 0:
                client.subscribe([(f"{base}/#", 0), ("homeassistant/#", 0)])

        def on_message(_client, _userdata, msg):
            try:
                payload = msg.payload.decode("utf-8", "ignore")
            except Exception:
                payload = "<bin>"
            rec = {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "topic": msg.topic,
                "payload": payload,
                "qos": msg.qos,
                "retain": bool(msg.retain),
            }
            fh.write(json.dumps(rec) + "\n")
            fh.flush()

        client.on_message = on_message
        client.on_connect = on_connect

        if host is None:
            raise SystemExit(
                "[trace] MQTT_HOST environment variable is required and missing.",
            )

        client.connect(host, port, keepalive=10)
        client.loop_start()
        while time.time() - start < args.duration:
            time.sleep(0.2)
        client.loop_stop()
        client.disconnect()
    print(f"[trace] wrote {out}")


if __name__ == "__main__":
    main()
