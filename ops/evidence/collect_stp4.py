#!/usr/bin/env python3
"""
Collect STP4 MQTT/HA roundtrip evidence.

Outputs:
  - ha_discovery_dump.json      # retained discovery configs observed
  - ha_mqtt_trace_snapshot.json # per-entity command→state traces w/ timestamps & latency
  - evidence_manifest.json      # summary, pass/fail attestation
Exit code:
  0 on PASS (all checks ok), 1 on FAIL (any roundtrip or schema check failed)
"""

from curses import echo
import argparse, json, os, sys, time, threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional


try:
    import paho.mqtt.client as mqtt
    from paho.mqtt.enums import CallbackAPIVersion
except Exception as e:
    print("ERR: paho-mqtt not installed. pip install paho-mqtt", file=sys.stderr)
    raise

# ----- config / args -----
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default=os.environ.get("MQTT_HOST","localhost"))
    p.add_argument("--port", type=int, default=int(os.environ.get("MQTT_PORT","1883")))
    p.add_argument("--user", default=os.environ.get("MQTT_USER"))
    p.add_argument("--password", default=os.environ.get("MQTT_PASSWORD"))
    p.add_argument("--base", default=os.environ.get("MQTT_BASE","bb8"))
    p.add_argument("--out", default="reports/stp4_"+datetime.now().strftime("%Y%m%d_%H%M%S"))
    p.add_argument("--timeout", type=float, default=2.0, help="State echo timeout seconds")
    return p.parse_args()

# ----- helpers -----
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def dump_json(path: str, obj: Any):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)

# Minimal HA discovery key presence check
def validate_discovery_obj(obj: Dict[str, Any]) -> Tuple[bool, str]:
    required = ["name", "unique_id", "availability_topic"]
    for k in required:
        if k not in obj:
            return False, f"missing_key:{k}"
    return True, "ok"

# Aggregator: filter and validate only relevant discovery configs for this device
def validate_discovery(configs, device_identifiers, base_topic=None):
    """
    Validate only discovery payloads that belong to this device.
    Minimal HA-required keys per entity:
      - unique_id, name, state_topic
      - command_topic for commandables
      - device.identifiers includes one of device_identifiers
    """
    relevant = []
    for item in configs:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            topic, payload = item[0], item[1]
        elif isinstance(item, dict):
            topic, payload = item.get("topic"), item.get("payload")
        else:
            continue
        if payload is None:
            continue
        try:
            o = json.loads(payload)
        except Exception:
            continue
        dev = (o.get("device") or {})
        ids = set(dev.get("identifiers") or [])
        if not ids.intersection(set(device_identifiers)):
            continue
        relevant.append((topic, o))

    results = []
    ok = True
    for topic, o in relevant:
        req = ["unique_id","name","state_topic","device"]
        missing = [k for k in req if k not in o]
        if missing:
            results.append({"topic":topic,"valid":False,"reason":f"missing:{missing}"}); ok=False; continue
        if o["device"].get("identifiers") in (None, [],):
            results.append({"topic":topic,"valid":False,"reason":"device.identifiers missing"}); ok=False; continue
        # commandables need command_topic
        if any(x in topic for x in ("/light/","/switch/","/button/","/number/")):
            if "command_topic" not in o:
                results.append({"topic":topic,"valid":False,"reason":"command_topic missing"}); ok=False; continue
        results.append({"topic":topic,"valid":True})
    return {"valid": ok, "count": len(relevant), "details": results}

# ----- collector -----
class Collector:
    def __init__(self, host: str, port: int, user: Optional[str], password: Optional[str], base: str, outdir: str, timeout: float):
        self.host, self.port, self.user, self.password = host, port, user, password
        self.base, self.outdir, self.timeout = base, outdir, timeout
        self.client = mqtt.Client(
            client_id=f"stp4-evidence-{int(time.time())}",
            protocol=mqtt.MQTTv5,
            callback_api_version=CallbackAPIVersion.VERSION2,
        )
        if user is not None:
            self.client.username_pw_set(user, password or None)
        self.msg_log: List[Dict[str, Any]] = []
        self.msg_cv = threading.Condition()
        self.connected = threading.Event()
        self.discovery_dump: Dict[str, Any] = {}
        # subscribe topic list
        self.state_topics = [
            f"{base}/power/state",
            f"{base}/stop/state",
            f"{base}/led/state",
            f"{base}/presence/state",
            f"{base}/rssi/state",
            f"{base}/sleep/state",
            f"{base}/drive/state",
            f"{base}/heading/state",
            f"{base}/speed/state",
        ]

    # MQTT callbacks
    def on_connect(self, c, u, flags, rc, properties=None):
        self.connected.set()
        # Discovery retained topics
        disc_prefix = "homeassistant/"
        c.subscribe(f"{disc_prefix}#")
        # State topics
        for t in self.state_topics:
            c.subscribe(t, qos=1)

    def on_message(self, c, u, msg):
        ts = utc_now_iso()
        entry = {
            "ts": ts,
            "topic": msg.topic,
            "payload_raw": msg.payload.decode("utf-8","replace"),
            "qos": msg.qos,
            "retain": getattr(msg, "retain", False),
        }
        # collect discovery JSONs
        if msg.topic.startswith("homeassistant/") and msg.payload:
            try:
                obj = json.loads(entry["payload_raw"])
                ok, reason = validate_discovery_obj(obj)
                self.discovery_dump[msg.topic] = {
                    "valid": ok, "reason": reason, "obj": obj
                }
            except Exception as e:
                self.discovery_dump[msg.topic] = {"valid": False, "reason": f"json_error:{e}"}
        # log and notify
        with self.msg_cv:
            self.msg_log.append(entry)
            self.msg_cv.notify_all()

    def wait_for_topic(self, topic: str, predicate, timeout: float) -> Optional[Dict[str, Any]]:
        deadline = time.time() + timeout
        with self.msg_cv:
            # search backlog first
            for m in reversed(self.msg_log):
                if m["topic"] == topic and predicate(m):
                    # Only accept state with ts >= command_ts (reject stale/prestate)
                    return self._extract_state(m)
            # wait for new ones
            while time.time() < deadline:
                remaining = deadline - time.time()
                if remaining <= 0: break
                self.msg_cv.wait(timeout=remaining)
                for m in reversed(self.msg_log):
                    if m["topic"] == topic and predicate(m):
                        # Only accept state with ts >= command_ts (reject stale/prestate)
                        return self._extract_state(m)
        return None

    def _extract_state(self, evt: Dict[str, Any]) -> Dict[str, Any]:
        src = "device"
        try:
            data = json.loads(evt["payload_raw"])
            src = data.get("source", src)
        except Exception:
            pass
        return {
            "state_ts": evt["ts"],
            "state_topic": evt["topic"],
            "state_payload": evt["payload_raw"],
            "source": src,
        }

    def connect(self):
        self.client.enable_logger()  # optional: route to std logging if configured
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.will_set(f"{self.base}/status", payload="offline", qos=1, retain=True)
        self.client.connect(self.host, self.port, keepalive=60)
        self.client.loop_start()
        self.connected.wait(timeout=5)

    def disconnect(self):
        try:
            self.client.loop_stop()
        finally:
            try:
                self.client.disconnect()
            except:
                pass

    def publish(self, topic: str, payload: Optional[str], qos=1, retain=False):
        # allow None -> empty payload
        if payload is None:
            payload = ""
        self.client.publish(topic, payload=payload, qos=qos, retain=retain)

    # Roundtrip test helpers
    def run(self) -> Dict[str, Any]:
        ensure_dir(self.outdir)
        self.connect()

        traces: List[Dict[str, Any]] = []
        failures: List[str] = []

        def record(entity: str, cmd_t: str, cmd_p: str, state_t: str, expect, m: Optional[Dict[str, Any]], note: str=""):
            now = utc_now_iso()
            cmd = {
                "entity": entity,
                "command_topic": cmd_t,
                "command_payload": cmd_p,
                "command_ts": now,
                "source": "facade",
            }
            echo = m
            passed, note_val = False, "timeout"
            # Enforce ordering: state must be after command
            if echo:
                if echo.get("state_ts") and echo["state_ts"] >= cmd["command_ts"]:
                    # Relaxed payload comparison
                    try:
                        # Accept raw string match
                        if echo["state_payload"] == expect:
                            passed, note_val = True, ""
                        else:
                            j_echo = None
                            j_expect = None
                            try:
                                j_echo = json.loads(echo["state_payload"])
                            except Exception:
                                pass
                            try:
                                j_expect = json.loads(expect)
                            except Exception:
                                pass
                            if j_echo is not None and j_expect is not None and j_echo == j_expect:
                                passed, note_val = True, ""
                            elif str(echo["state_payload"]).strip() == str(expect).strip():
                                passed, note_val = True, ""
                    except Exception:
                        if str(echo["state_payload"]).strip() == str(expect).strip():
                            passed, note_val = True, ""
                else:
                    passed, note_val = False, "prestate"
                echo.setdefault("source", "device")
                require_device = (os.getenv("REQUIRE_DEVICE_ECHO", "1") != "0")
                is_commandable = ("/cmd/" in cmd_t) or cmd_t.endswith("/set")
                print(f"[DEBUG] REQUIRE_DEVICE_ECHO={os.getenv('REQUIRE_DEVICE_ECHO')}, require_device={require_device}, is_commandable={is_commandable}, echo_source={echo.get('source')}")
                if require_device and is_commandable and echo.get("source") != "device":
                    passed, note_val = False, "facade_only"

            res = {
                **cmd,
                "state_topic": state_t,
                "state_payload": echo["state_payload"] if echo else None,
                "state_ts": echo["state_ts"] if echo else None,
                "expect": expect,
                "pass": passed,
                "note": note or note_val,
            }
            traces.append(res)
            if not res["pass"]:
                failures.append(f"{entity}:{res['note'] or 'timeout'}")

        base = self.base
        to = self.timeout

        # ---- Core five ----
        # power = ON
        self.publish(f"{base}/power/set", "ON")
        def power_pred(x):
            # Accept raw "ON" or JSON with value "ON"
            try:
                if x["payload_raw"] == "ON": return True
                j = json.loads(x["payload_raw"])
                return j.get("value") == "ON"
            except Exception:
                return False
        m = self.wait_for_topic(f"{base}/power/state", power_pred, to)
        record("power_on", f"{base}/power/set", "ON", f"{base}/power/state", "ON", m)

        # stop press -> 'pressed' then 'idle'
        self.publish(f"{base}/stop/press", None)
        m1 = self.wait_for_topic(f"{base}/stop/state", lambda x: x["payload_raw"]=="pressed", to)
        record("stop_pressed", f"{base}/stop/press", "", f"{base}/stop/state", "pressed", m1)
        m2 = self.wait_for_topic(f"{base}/stop/state", lambda x: x["payload_raw"]=="idle", to+1.0)
        record("stop_idle", f"{base}/stop/press", "", f"{base}/stop/state", "idle", m2)

        # led set -> hex color
        hex_payload = json.dumps({"hex":"#FF6600"})
        self.publish(f"{base}/led/set", hex_payload)
        def led_pred(x):
            # Accept any RGB dict
            try:
                j = json.loads(x["payload_raw"])
                return all(k in j for k in ("r","g","b"))
            except Exception:
                return False
        m = self.wait_for_topic(f"{base}/led/state", led_pred, to)
        record("led_rgb", f"{base}/led/set", hex_payload, f"{base}/led/state", '{"r":255,"g":102,"b":0}', m, note="shape_json")

        # presence & rssi: just capture current retained (no command)
        pres = self.wait_for_topic(f"{base}/presence/state", lambda x: x["payload_raw"] is not None and str(x["payload_raw"]).strip() != "", to)
        traces.append({
            "entity": "presence_state",
            "state_topic": f"{base}/presence/state",
            "state_payload": pres.get("payload_raw") if pres else None,
            "pass": bool(pres)
        })
        if not pres:
            failures.append("presence:no_state")
        rssi = self.wait_for_topic(f"{base}/rssi/state", lambda x: x["payload_raw"] is not None and str(x["payload_raw"]).strip() != "", to)
        traces.append({
            "entity": "rssi_state",
            "state_topic": f"{base}/rssi/state",
            "state_payload": rssi.get("payload_raw") if rssi else None,
            "pass": bool(rssi)
        })
        if not rssi:
            failures.append("rssi:no_state")

        # ---- Extended ----
        # sleep button
        self.publish(f"{base}/sleep/press", None)
        m1 = self.wait_for_topic(f"{base}/sleep/state", lambda x: x["payload_raw"]=="pressed", to)
        record("sleep_pressed", f"{base}/sleep/press","", f"{base}/sleep/state","pressed", m1)
        m2 = self.wait_for_topic(f"{base}/sleep/state", lambda x: x["payload_raw"]=="idle", to+1.0)
        record("sleep_idle", f"{base}/sleep/press","", f"{base}/sleep/state","idle", m2)

        # heading number
        self.publish(f"{base}/heading/set", "270")
        m = self.wait_for_topic(f"{base}/heading/state", lambda x: x["payload_raw"]=="270", to)
        record("heading_set_270", f"{base}/heading/set","270", f"{base}/heading/state","270", m)

        # speed number
        self.publish(f"{base}/speed/set", "128")
        m = self.wait_for_topic(f"{base}/speed/state", lambda x: x["payload_raw"]=="128", to)
        record("speed_set_128", f"{base}/speed/set","128", f"{base}/speed/state","128", m)

        # drive button
        self.publish(f"{base}/drive/press", None)
        m1 = self.wait_for_topic(f"{base}/drive/state", lambda x: x["payload_raw"]=="pressed", to)
        record("drive_pressed", f"{base}/drive/press","", f"{base}/drive/state","pressed", m1)
        m2 = self.wait_for_topic(f"{base}/drive/state", lambda x: x["payload_raw"]=="idle", to+1.0)
        record("drive_idle", f"{base}/drive/press","", f"{base}/drive/state","idle", m2)

        # ----- dump artifacts -----
        ensure_dir(self.outdir)
        dump_json(os.path.join(self.outdir, "ha_discovery_dump.json"), self.discovery_dump)
        dump_json(os.path.join(self.outdir, "ha_mqtt_trace_snapshot.json"), traces)


        # schema verdict (scoped)
        # Build identifiers for THIS device only
        bb8_mac = (os.getenv("BB8_MAC") or "").upper()
        dev_ids = []
        if bb8_mac:
            dev_ids.append(f"ble:{bb8_mac}")
        dev_ids.append(f"mqtt:{os.getenv('MQTT_BASE', 'bb8')}")

        # Prepare configs as (topic, payload) tuples from discovery_dump
        configs = [(topic, entry["obj"] if isinstance(entry, dict) and "obj" in entry else "{}")
                   for topic, entry in self.discovery_dump.items()]
        # Convert obj back to JSON string for validation
        configs = [(topic, json.dumps(obj) if isinstance(obj, dict) else obj) for topic, obj in configs]

        schema_result = validate_discovery(configs, device_identifiers=dev_ids, base_topic=os.getenv("MQTT_BASE","bb8"))
        disc_ok = schema_result["valid"]
        roundtrip_ok = all(t.get("pass") for t in traces if isinstance(t, dict))

        attn = {
            "generated_at": utc_now_iso(),
            "broker": {"host": self.host, "port": self.port, "user_present": bool(self.user)},
            "base_topic": self.base,
            "schema": "PASS" if disc_ok else "FAIL",
            "schema_details": schema_result,
            "roundtrip": "PASS" if roundtrip_ok else "FAIL",
            "STP4/roundtrip": ("PASS" if (disc_ok and roundtrip_ok) else "FAIL") + (" (explain if FAIL)" if not (disc_ok and roundtrip_ok) else ""),
            "timeouts_sec": self.timeout,
            "files": ["ha_discovery_dump.json", "ha_mqtt_trace_snapshot.json"]
        }
        dump_json(os.path.join(self.outdir, "evidence_manifest.json"), attn)

        self.disconnect()
        return {"ok": disc_ok and roundtrip_ok, "attestation": attn}

def main():
    args = parse_args()
    ensure_dir(args.out)
    col = Collector(args.host, args.port, args.user, args.password, args.base, args.out, args.timeout)
    res = col.run()
    print(json.dumps(res["attestation"], indent=2))
    sys.exit(0 if res["ok"] else 1)

if __name__ == "__main__":
    main()
