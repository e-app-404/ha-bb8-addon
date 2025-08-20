from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time
from datetime import UTC, datetime
from typing import Any

import paho.mqtt.client as mqtt


def ts() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")


def logpath(kind: str) -> str:
    p = pathlib.Path("reports/preflight")
    p.mkdir(parents=True, exist_ok=True)
    return str(p / f"{kind}_{ts()}.log")


def wait_for_led_state(
    client: mqtt.Client,
    base: str,
    expect: dict[str, int],
    timeout: float = 3.0,
) -> dict[str, Any]:
    topic_state = f"{base}/led/state"
    got: dict[str, Any] = {"match": False, "payload": None, "topic": topic_state}
    done = False

    def _on_msg(client, userdata, msg):
        nonlocal done, got
        try:
            if msg.topic != topic_state:
                return
            payload = json.loads(msg.payload.decode("utf-8"))
            got["payload"] = payload
            if isinstance(payload, dict) and set(payload.keys()) == {"r", "g", "b"}:
                got["match"] = (
                    int(payload["r"]) == expect["r"]
                    and int(payload["g"]) == expect["g"]
                    and int(payload["b"]) == expect["b"]
                )
            done = True
        except Exception:
            done = True

    client.message_callback_add(topic_state, _on_msg)
    client.subscribe(topic_state, qos=1)
    t0 = time.monotonic()
    while not done and (time.monotonic() - t0) < timeout:
        client.loop(timeout=0.1)
        time.sleep(0.05)
    client.message_callback_remove(topic_state)
    return got


def one_round(
    client: mqtt.Client,
    base: str,
    rgb: dict[str, int],
    receipt_path: str,
    title: str,
) -> int:
    topic_cmd = f"{base}/led/cmd"
    topic_state = f"{base}/led/state"
    qos = 1
    payload = json.dumps(rgb, separators=(",", ":"))
    with open(receipt_path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n")
        f.write(f"publish {topic_cmd} {payload}\n")
        client.publish(topic_cmd, payload=payload, qos=qos, retain=False)
        got = wait_for_led_state(client, base, rgb, timeout=3.0)
        f.write(
            "wait {topic} -> {got}\n".format(
                topic=topic_state, got=json.dumps(got, separators=(",", ":"))
            )
        )
        ok = bool(got.get("match"))
        f.write(f"VERDICT={'PASS' if ok else 'FAIL'}\n")
        return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Verify bb8/led/cmd -> bb8/led/state echo path"
    )
    ap.add_argument("--host", default=os.getenv("MQTT_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.getenv("MQTT_PORT", "1883")))
    ap.add_argument("--user", default=os.getenv("MQTT_USERNAME"))
    ap.add_argument("--password", default=os.getenv("MQTT_PASSWORD"))
    ap.add_argument("--base", default=os.getenv("MQTT_BASE", "bb8"))
    ap.add_argument(
        "--pause-for-restart",
        action="store_true",
        help="Pause between rounds for manual restart",
    )
    ap.add_argument(
        "--log-optional",
        action="store_true",
        help="Emit CMD_LED_OPTIONAL receipt too",
    )
    args = ap.parse_args()

    if mqtt is None:
        print('{"pass": false, "error": "paho-mqtt not available"}')
        return 2

    client = mqtt.Client(
        client_id=f"bb8-cmd-verify-{int(time.time())}",
    )
    if args.user:
        client.username_pw_set(args.user, args.password or "")
    client.connect(args.host, args.port, keepalive=60)

    before = one_round(
        client,
        args.base,
        {"r": 255, "g": 64, "b": 0},
        logpath("CMD_BEFORE"),
        "BEFORE",
    )
    if args.pause_for_restart:
        print(
            ">>> Pause for restart now; resuming in 8s...",
            file=sys.stderr,
        )
        for _ in range(8):
            client.loop(timeout=0.1)
            time.sleep(1.0)
    after = one_round(
        client,
        args.base,
        {"r": 0, "g": 64, "b": 255},
        logpath("CMD_AFTER_RESTART"),
        "AFTER_RESTART",
    )
    opt_rc = 0
    if args.log_optional:
        opt_rc = one_round(
            client,
            args.base,
            {"r": 32, "g": 32, "b": 32},
            logpath("CMD_LED_OPTIONAL"),
            "OPTIONAL",
        )
    client.disconnect()
    return 0 if (before | after | opt_rc) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
