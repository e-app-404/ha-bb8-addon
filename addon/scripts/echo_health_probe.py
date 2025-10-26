#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion

try:
    from addon.bb8_core.logging_setup import logger  # type: ignore
except Exception:
    import logging as _logging

    logger = _logging.getLogger("echo_probe")
    if not logger.handlers:
        logger.addHandler(_logging.StreamHandler(sys.stdout))
    logger.setLevel(_logging.INFO)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Echo responder health probe (append summary)")
    ap.add_argument("--host", default=os.environ.get("MQTT_HOST", "core-mosquitto"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("MQTT_PORT", "1883")))
    ap.add_argument("--base", default=os.environ.get("MQTT_BASE", "bb8"))
    ap.add_argument("--user", default=os.environ.get("MQTT_USERNAME"))
    ap.add_argument("--password", default=os.environ.get("MQTT_PASSWORD"))
    ap.add_argument("--timeout", type=float, default=6.0)
    ap.add_argument("--out", default="reports/checkpoints/BB8-FUNC/b5_summary.md")
    ap.add_argument("--append", action="store_true")
    args = ap.parse_args(argv)

    base = args.base.rstrip("/")
    t0 = time.time()

    got = {"ok": False, "ms": None}

    client = mqtt.Client(client_id=f"echo-{int(t0 * 1000)}", callback_api_version=CallbackAPIVersion.VERSION2)
    if args.user:
        client.username_pw_set(args.user, args.password or None)

    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            client.subscribe([(f"{base}/echo/state", 0)])
            payload = json.dumps({"value": 1, "ts": int(t0)})
            client.publish(f"{base}/echo/cmd", payload, qos=0, retain=False)

    def on_message(client, userdata, msg):
        if msg.topic == f"{base}/echo/state":
            try:
                p = json.loads(msg.payload.decode("utf-8"))
            except Exception:
                p = {}
            src = p.get("source")
            if src == "device":
                got["ok"] = True
                got["ms"] = int((time.time() - t0) * 1000)

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.host, args.port, keepalive=8)
    client.loop_start()
    deadline = t0 + args.timeout
    while time.time() < deadline and not got["ok"]:
        time.sleep(0.05)
    client.loop_stop()
    import contextlib

    with contextlib.suppress(Exception):
        client.disconnect()

    line = (
        f"- Echo health: {'green' if got['ok'] else 'fail'} "
        f"(round-trip {got['ms'] if got['ms'] is not None else 'n/a'} ms)\n"
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if args.append else "w"
    with out.open(mode, encoding="utf-8") as fh:
        fh.write(line)
    return 0 if got["ok"] else 4


if __name__ == "__main__":
    sys.exit(main())
