#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion

# Project logging (structured, redacting)
try:
    # Prefer runtime-style imports when executed from addon/ root
    from addon.bb8_core.logging_setup import logger  # type: ignore
except Exception:
    try:
        from bb8_core.logging_setup import logger  # type: ignore
    except Exception:
        import logging as _logging

        logger = _logging.getLogger("b5_e2e")
        if not logger.handlers:
            logger.addHandler(_logging.StreamHandler(sys.stdout))
        logger.setLevel(_logging.INFO)


def _env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name, default)
    return v


@dataclass
class AckRecord:
    cmd: str
    cid: str
    ok: bool
    reason: str | None
    t_publish: float
    t_ack: float


class TimelineWriter:
    def __init__(self, out_path: Path):
        self.out_path = out_path
        self.out_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def write(self, topic: str, payload: bytes | str, ts: float | None = None):
        t = ts if ts is not None else time.time()
        try:
            s = payload.decode("utf-8", "ignore") if isinstance(payload, bytes) else str(payload)
        except Exception:
            s = "<binary>"
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(t))}.{int((t % 1) * 1000):03d}Z {topic} {s}\n"
        with self._lock:
            with self.out_path.open("a", encoding="utf-8") as fh:
                fh.write(line)


def build_client(client_id: str | None = None) -> mqtt.Client:
    cid = client_id or f"b5runner-{int(time.time() * 1000)}"
    client = mqtt.Client(client_id=cid, callback_api_version=CallbackAPIVersion.VERSION2)
    return client


def wait_for_event(flag: threading.Event, timeout_s: float, on_timeout: Callable[[], None] | None = None) -> bool:
    ok = flag.wait(timeout=timeout_s)
    if not ok and on_timeout:
        on_timeout()
    return ok


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="B5 E2E demo runner: wake → preset → drive → stop → sleep")
    ap.add_argument("--host", default=_env("MQTT_HOST", "core-mosquitto"))
    ap.add_argument("--port", type=int, default=int(_env("MQTT_PORT", "1883") or 1883))
    ap.add_argument("--user", default=_env("MQTT_USERNAME"))
    ap.add_argument("--password", default=_env("MQTT_PASSWORD"))
    ap.add_argument("--base", default=_env("MQTT_BASE", "bb8"))
    ap.add_argument("--log", default="reports/checkpoints/BB8-FUNC/b5_e2e_demo.log")
    ap.add_argument("--summary", default="reports/checkpoints/BB8-FUNC/b5_summary.md")
    ap.add_argument("--timeout", type=float, default=8.0, help="per-step ACK wait timeout (seconds)")
    ap.add_argument("--drive-speed", type=int, default=120)
    ap.add_argument("--drive-heading", type=int, default=90)
    ap.add_argument("--drive-ms", type=int, default=1500)
    ap.add_argument("--preset", default="sunset")
    ap.add_argument("--cids", default="b5-1,b5-2,b5-3,b5-4,b5-5")

    args = ap.parse_args(argv)

    out_path = Path(args.log)
    tw = TimelineWriter(out_path)

    host, port, base = args.host, args.port, args.base.rstrip("/")
    user, pwd = args.user, args.password

    cids = (args.cids.split(",") if isinstance(args.cids, str) else list(args.cids))
    if len(cids) != 5:
        logger.error({"event": "b5_bad_cids", "cids": cids})
        print("Expected 5 comma-separated cids (wake,preset,drive,stop,sleep)", file=sys.stderr)
        return 2

    # Shared state
    connected = threading.Event()
    stop_loop = threading.Event()
    safety_violation = threading.Event()
    telemetry_seen = {"connected": False, "estop": None, "last_cmd_ts": None, "battery_pct": None}
    ack_by_cid: dict[str, AckRecord] = {}
    publish_times: dict[str, float] = {}

    client = build_client()
    if user:
        client.username_pw_set(user, pwd or None)

    def _on_connect(client: mqtt.Client, userdata: Any, flags: dict, rc: int, properties=None):
        tw.write("[meta/connect]", json.dumps({"rc": rc}))
        if rc == 0:
            client.subscribe([(f"{base}/ack/#", 1), (f"{base}/status/#", 1), (f"{base}/event/#", 1)])
            connected.set()

    def _on_message(client: mqtt.Client, userdata: Any, msg):
        tw.write(msg.topic, msg.payload)
        topic = msg.topic or ""
        # Telemetry snapshot
        if topic == f"{base}/status/telemetry":
            try:
                p = json.loads(msg.payload.decode("utf-8"))
                telemetry_seen.update({k: p.get(k) for k in telemetry_seen})
                # Treat runtime estop asserted as violation
                if bool(p.get("estop")):
                    safety_violation.set()
            except Exception:
                pass
            return
        # ACK parsing
        if topic.startswith(f"{base}/ack/"):
            try:
                payload = json.loads(msg.payload.decode("utf-8"))
            except Exception:
                payload = {}
            cid = str(payload.get("cid") or "")
            ok = bool(payload.get("ok"))
            reason = payload.get("reason")
            cmd = topic.split("/")[-1]
            if cid:
                t_pub = publish_times.get(cid, time.time())
                ack_by_cid[cid] = AckRecord(cmd=cmd, cid=cid, ok=ok, reason=reason, t_publish=t_pub, t_ack=time.time())
            if not ok or (isinstance(reason, str) and ("safety" in reason.lower() or "estop" in reason.lower())):
                safety_violation.set()

    client.on_connect = _on_connect
    client.on_message = _on_message

    # Graceful shutdown
    def _sig(_n, _f):
        stop_loop.set()
        try:
            client.loop_stop()
            client.disconnect()
        except Exception:
            pass

    signal.signal(signal.SIGINT, _sig)
    signal.signal(signal.SIGTERM, _sig)

    client.connect(host, port, keepalive=10)
    client.loop_start()
    if not wait_for_event(connected, timeout_s=10.0):
        logger.error({"event": "b5_connect_timeout", "host": host, "port": port})
        return 3

    def publish_cmd(topic_suffix: str, payload_obj: dict[str, Any]) -> None:
        topic = f"{base}/cmd/{topic_suffix}"
        data = json.dumps(payload_obj, separators=(",", ":"))
        cid = str(payload_obj.get("cid") or "")
        publish_times[cid] = time.time()
        client.publish(topic, data, qos=1, retain=False)
        tw.write(topic, data)

    # Step 1: wake
    publish_cmd("power", {"action": "wake", "cid": cids[0]})
    wait_for_event(threading.Event(), 0.2)  # tiny spacing for readability

    # Step 2: preset
    publish_cmd("led_preset", {"name": args.preset, "cid": cids[1]})

    # Step 3: drive (≤2s per mandate)
    publish_cmd(
        "drive",
        {"speed": int(args.drive_speed), "heading": int(args.drive_heading), "ms": int(args.drive_ms), "cid": cids[2]},
    )

    # Step 4: stop
    publish_cmd("stop", {"cid": cids[3]})

    # Step 5: sleep
    publish_cmd("power", {"action": "sleep", "cid": cids[4]})

    # Await ACKs for all CIDs
    deadline = time.time() + float(args.timeout)
    while time.time() < deadline and not stop_loop.is_set():
        if all(cid in ack_by_cid for cid in cids):
            break
        time.sleep(0.05)

    client.loop_stop()
    try:
        client.disconnect()
    except Exception:
        pass

    # Summarize
    missing = [cid for cid in cids if cid not in ack_by_cid]
    any_nack = any((not r.ok) for r in ack_by_cid.values())
    any_safety = safety_violation.is_set()

    # Write summary markdown
    summary_path = Path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    latencies: list[int] = []

    def _ms(r: AckRecord) -> int:
        return int((r.t_ack - r.t_publish) * 1000)
    for r in ack_by_cid.values():
        latencies.append(_ms(r))

    mean_latency = int(sum(latencies) / len(latencies)) if latencies else None
    verdict = "ACCEPT" if (not missing and not any_nack and not any_safety) else "REWORK"
    with summary_path.open("w", encoding="utf-8") as fh:
        fh.write("[B5 Verdict]: " + verdict + "\n")
        fh.write("- Run sequence: wake → preset → drive → stop → sleep\n")
        fh.write(f"- MQTT acks: received {len(ack_by_cid)}/5; missing={missing}\n")
        fh.write(f"- Telemetry: connected={telemetry_seen['connected']} estop={telemetry_seen['estop']} last_cmd_ts={telemetry_seen['last_cmd_ts']} battery={telemetry_seen['battery_pct']}\n")
        fh.write(f"- Safety violations: {'yes' if any_safety else 'none'}\n")
        fh.write(f"- Mean ACK latency: {mean_latency if mean_latency is not None else 'n/a'} ms\n")
        fh.write(f"- Evidence: {args.log}, {args.summary}\n")

    # Update manifest.sha256 (Python implementation; avoids shell deps)
    try:
        import hashlib

        ck_dir = summary_path.parent
        entries = []
        for p in sorted(ck_dir.glob("*")):
            if p.is_file():
                h = hashlib.sha256()
                with p.open("rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        h.update(chunk)
                entries.append((p.name, h.hexdigest()))
        with (ck_dir / "manifest.sha256").open("w", encoding="utf-8") as mf:
            for name, digest in entries:
                mf.write(f"{digest}  {name}\n")
    except Exception as e:
        logger.warning({"event": "b5_manifest_error", "error": str(e)})

    if verdict != "ACCEPT":
        return 10
    return 0


if __name__ == "__main__":
    sys.exit(main())
