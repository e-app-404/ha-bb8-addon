#!/usr/bin/env python
import argparse
import json
import os
import threading
import time

import paho.mqtt.client as mqtt


def env(name, default=None, required=False):
    v = os.environ.get(name, default)
    if required and (v is None or v == ""):
        raise SystemExit(f"[probe] missing env {name}")
    if v is None:
        v = ""
    return str(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=8)
    ap.add_argument("--require-echo", default="1")
    args = ap.parse_args()

    host = env("MQTT_HOST", default="", required=True)
    port = int(env("MQTT_PORT", "1883"))
    user = env("MQTT_USERNAME")
    pwd = env("MQTT_PASSWORD")
    base = env("MQTT_BASE", "bb8")

    client = mqtt.Client(client_id=f"probe-{int(time.time())}")
    if user:
        client.username_pw_set(user, pwd or None)
    res = {"connected": False, "roundtrip": "FAIL", "schema": "UNKNOWN"}
    got_echo = threading.Event()
    payload_seen: dict | None = None

    def on_message(c, ud, msg):
        nonlocal payload_seen
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            return
        if msg.topic == f"{base}/echo/state":
            payload_seen = payload
            got_echo.set()

    def on_connect(c, ud, flags, rc, props=None):
        cid = getattr(c, "_client_id", b"")
        try:
            cid = cid.decode() if hasattr(cid, "decode") else str(cid)
        except Exception:
            cid = str(cid)
        print(f"mqtt_on_connect rc={rc} client_id={cid}")
        if rc == 0:
            res["connected"] = True
            c.subscribe([(f"{base}/#", 0)])
            cmd = {"value": 1, "ts": int(time.time())}
            c.publish(f"{base}/echo/cmd", json.dumps(cmd), qos=0, retain=False)

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host, port, keepalive=10)
    client.loop_start()
    got_echo.wait(timeout=args.timeout)
    client.loop_stop()
    client.disconnect()

    if got_echo.is_set() and payload_seen:
        if payload_seen.get("source") == "device":
            res["roundtrip"] = "PASS"
        else:
            res["roundtrip"] = "FAIL"
        res["schema"] = "PASS" if "source" in payload_seen else "FAIL"

    print(
        f"probe: connected={res['connected']} "
        f"roundtrip={res['roundtrip']} "
        f"schema={res['schema']}"
    )
    if not res["connected"]:
        print("probe_exit reason=not_connected")
        raise SystemExit(2)
    if res["roundtrip"] != "PASS" and os.environ.get("REQUIRE_DEVICE_ECHO", "1") == "1":
        print("probe_exit reason=roundtrip_fail")
        raise SystemExit(3)


if __name__ == "__main__":
    main()
