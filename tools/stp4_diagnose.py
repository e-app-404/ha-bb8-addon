from __future__ import annotations

import datetime
import json
import pathlib
import re
import sys

BASE = re.compile(r"^bb8/(power|stop|sleep|drive|heading|speed|led)/(set|state)$")
SCALARS = {"power", "stop", "sleep", "drive", "heading", "speed"}


def load_events(path: pathlib.Path):
    pjsonl = path / "ha_mqtt_trace_snapshot.jsonl"
    pjson = path / "ha_mqtt_trace_snapshot.json"
    if pjsonl.exists():
        return [
            json.loads(line) for line in pjsonl.read_text().splitlines() if line.strip()
        ]
    if pjson.exists():
        data = json.loads(pjson.read_text())
        if isinstance(data, dict) and "events" in data:
            return data["events"]
        if isinstance(data, list):
            return data
    raise SystemExit(f"TRACE NOT FOUND in {path}")


def norm_payload(raw):
    if isinstance(raw, dict | list):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return raw


def base_key(topic: str):
    m = BASE.match(topic or "")
    if not m:
        return None
    sig, kind = m.group(1), m.group(2)
    return sig, kind


def ts_of(evt):
    # prefer provided timestamps; fall back to ts/iso strings if present
    for k in ("state_ts", "command_ts", "ts", "time", "timestamp"):
        if k in evt and isinstance(evt[k], int | float):
            return float(evt[k])
    # ISO?
    for k in ("ts", "time", "timestamp"):
        v = evt.get(k)
        if isinstance(v, str):
            try:
                return datetime.datetime.fromisoformat(
                    v.replace("Z", "+00:00")
                ).timestamp()
            except Exception:
                pass
    return None


def main():
    if len(sys.argv) != 2:
        print("usage: python tools/stp4_diagnose.py <EVIDENCE_DIR>", file=sys.stderr)
        sys.exit(2)
    ed = pathlib.Path(sys.argv[1]).resolve()
    events = load_events(ed)
    # try to read timeout from manifest
    timeout = 3.0
    man = ed / "evidence_manifest.json"
    if man.exists():
        try:
            m = json.loads(man.read_text())
            timeout = float(m.get("timeouts_sec", timeout))
        except Exception:
            pass

    cmds = {}
    states = {}
    for e in events:
        topic = e.get("topic") or e.get("t") or ""
        bk = base_key(topic)
        if not bk:
            continue
        sig, kind = bk
        payload = norm_payload(e.get("payload"))
        tstamp = ts_of(e) or 0.0
        if kind == "set":
            cmds.setdefault(sig, []).append(
                {"ts": tstamp, "payload": payload, "raw": e}
            )
        else:
            # state
            states.setdefault(sig, []).append(
                {"ts": tstamp, "payload": payload, "raw": e}
            )

    overall_fail = False
    lines = []
    for sig in sorted(SCALARS | {"led"}):
        c = cmds.get(sig, [])
        s = states.get(sig, [])
        # naive pairing by nearest state after command
        latencies = []
        device_src = 0
        unmatched = 0
        s_sorted = sorted(s, key=lambda x: x["ts"])
        for ce in sorted(c, key=lambda x: x["ts"]):
            st = next((se for se in s_sorted if se["ts"] >= ce["ts"]), None)
            if not st:
                unmatched += 1
                continue
            lat = (st["ts"] - ce["ts"]) if st["ts"] and ce["ts"] else None
            if lat is not None:
                latencies.append(lat)
            pay = st["payload"]
            if sig in SCALARS:
                if (
                    isinstance(pay, dict)
                    and pay.get("source") == "device"
                    or (
                        isinstance(pay, dict)
                        and "value" in pay
                        and pay.get("source") == "device"
                    )
                ):
                    device_src += 1
            else:
                # LED shape check
                if not (isinstance(pay, dict) and set(pay.keys()) == {"r", "g", "b"}):
                    lines.append(f"[{sig}] LED payload shape FAIL: {pay}")
                    overall_fail = True
        p95 = maxlat = None
        if latencies:
            lat_sorted = sorted(latencies)
            p95 = lat_sorted[max(0, int(round(0.95 * (len(lat_sorted) - 1))))]
            maxlat = lat_sorted[-1]

        # Build verdicts
        v = []
        if sig in SCALARS and device_src < len(c):
            v.append(f"device_source {device_src}/{len(c)}")
        if unmatched:
            v.append(f"unmatched {unmatched}/{len(c)}")
        if maxlat is not None and maxlat > timeout:
            v.append(f"timeout_exceeded max={maxlat:.3f}s> {timeout:.1f}s")
        status = "OK" if not v else "FAIL"
        if status == "FAIL":
            overall_fail = True
        lat_s = "" if maxlat is None else f"lat_p95={p95:.3f}s max={maxlat:.3f}s"
        line = (
            f"[{sig}] cmds={len(c)} states={len(s)} dev_src={device_src} "
            f"{lat_s} → {status} "
        )
        if v:
            line += "; ".join(v)
        lines.append(line)

    print("\n".join(lines))
    if overall_fail:
        sys.exit(1)
    print("TRACE STRICT CHECKS: PASS")


if __name__ == "__main__":
    main()
