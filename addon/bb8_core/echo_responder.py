import json
import logging
import os
import sys
import threading
import time

LOG = logging.getLogger(__name__)

OPTIONS_PATH = os.environ.get("OPTIONS_PATH", "/data/options.json")


def _load_opts(path=OPTIONS_PATH):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        LOG.warning("Failed to read %s: %s — using defaults", path, e)
        return {}


_opts = _load_opts()
_base = _opts.get("mqtt_base") or _opts.get("mqtt_topic_prefix") or "bb8"

# --- BLE probe helpers (minimal; Supervisor-only) ---
try:
    from bleak import BleakScanner
except Exception:  # bleak missing or import error
    BleakScanner = None

_bb8_mac = (_opts.get("bb8_mac") or "").upper().strip()
_ble_adapter = (_opts.get("ble_adapter") or "hci0").strip()
if not _bb8_mac:
    LOG.warning("No bb8_mac found in options.json; BLE probe will always fail.")


def _ble_probe_once(timeout_s: float = 3.0) -> dict:
    """
    Minimal device-originated evidence: scan for the target MAC using Bleak.
    Returns: {"ok": bool, "latency_ms": int|None}
    """
    if BleakScanner is None or not _bb8_mac:
        return {"ok": False, "latency_ms": None}
    t0 = time.time()
    try:
        # Note: BleakScanner.discover supports adapter via kwargs on Linux.
        devices = BleakScanner.discover(timeout=timeout_s, adapter=_ble_adapter)
        # BleakScanner.discover may be async in some versions; handle both:
        if hasattr(devices, "__await__"):
            devices = __import__("asyncio").get_event_loop().run_until_complete(devices)
        found = any((d.address or "").upper() == _bb8_mac for d in devices or [])
        if found:
            ms = int((time.time() - t0) * 1000)
            return {"ok": True, "latency_ms": ms}
        return {"ok": False, "latency_ms": None}
    except Exception as e:
        LOG.info("BLE probe error: %s", e)
        return {"ok": False, "latency_ms": None}


def _publish_echo_roundtrip(client, base_ts: float, ble_ok: bool, ble_ms: int | None):
    payload = {
        "ts": int(base_ts),
        "rtt_ms": 0,
        "ble_ok": bool(ble_ok),
        "ble_latency_ms": ble_ms if ble_ok else None,
    }
    client.publish(MQTT_ECHO_RTT, json.dumps(payload), qos=1, retain=False)


def _resolve_topic(opt_key: str, default_suffix: str, env_key: str = None) -> str:
    """
    Order of precedence:
      1) ENV override (if provided)
      2) /data/options.json value (opt_key)
      3) default: f"{_base}/{default_suffix}"
    Sanitizes leading/trailing slashes. Warn if wildcard topics accidentally set.
    """
    if env_key is None:
        env_key = opt_key.upper()
    raw = os.environ.get(env_key) or _opts.get(opt_key) or ""
    raw = str(raw).strip()
    if not raw:
        topic = f"{_base}/{default_suffix}"
    else:
        topic = raw.lstrip("/")  # absolute -> relative
    if "#" in topic or "+" in topic:
        LOG.warning(
            "Wildcard detected in %s='%s' — this is unsafe for pub/sub", opt_key, topic
        )
    LOG.info("Resolved topic %s => %s", opt_key, topic)
    return topic


# --- Resolved topics (single source of truth) ---
MQTT_ECHO_CMD = _resolve_topic("mqtt_echo_cmd_topic", "echo/cmd", "MQTT_ECHO_CMD_TOPIC")
MQTT_ECHO_ACK = _resolve_topic("mqtt_echo_ack_topic", "echo/ack", "MQTT_ECHO_ACK_TOPIC")
MQTT_ECHO_STATE = _resolve_topic(
    "mqtt_echo_state_topic", "echo/state", "MQTT_ECHO_STATE_TOPIC"
)
MQTT_ECHO_RTT = _resolve_topic(
    "mqtt_telemetry_echo_roundtrip_topic",
    "telemetry/echo_roundtrip",
    "MQTT_TELEMETRY_ECHO_ROUNDTRIP_TOPIC",
)
MQTT_BLE_READY_CMD = _resolve_topic(
    "mqtt_ble_ready_cmd_topic", "ble_ready/cmd", "MQTT_BLE_READY_CMD_TOPIC"
)
MQTT_BLE_READY_SUMMARY = _resolve_topic(
    "mqtt_ble_ready_summary_topic", "ble_ready/summary", "MQTT_BLE_READY_SUMMARY_TOPIC"
)
# import asyncio -- already imported below if needed
import atexit

import paho.mqtt.client as mqtt

# Use the same logger instance throughout the file
# LOG is already defined at the top as logging.getLogger(__name__)


def _write_atomic(path: str, content: str) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _start_heartbeat(path: str, interval: int) -> None:
    interval = 2 if interval < 2 else interval  # lower bound

    def _hb():
        # write immediately, then tick
        try:
            _write_atomic(path, f"{time.time()}\n")
        except Exception as e:
            LOG.debug("heartbeat initial write failed: %s", e)
        while True:
            try:
                _write_atomic(path, f"{time.time()}\n")
            except Exception as e:
                LOG.debug("heartbeat write failed: %s", e)
            time.sleep(interval)

    t = threading.Thread(target=_hb, daemon=True)
    t.start()


def _env_truthy(val):
    """Returns True if the environment variable value is truthy (not '0', '', 'false', 'no')."""
    return str(val).strip().lower() not in ("0", "", "false", "no", "none")


ENABLE_HEALTH_CHECKS = _env_truthy(os.environ.get("ENABLE_HEALTH_CHECKS", "0"))
HB_INTERVAL = int(os.environ.get("HEARTBEAT_INTERVAL_SEC", "5"))
HB_PATH_ECHO = "/tmp/bb8_heartbeat_echo"
if ENABLE_HEALTH_CHECKS:
    LOG.info(
        "echo_responder.py health check enabled: %s interval=%ss",
        HB_PATH_ECHO,
        HB_INTERVAL,
    )
    _start_heartbeat(HB_PATH_ECHO, HB_INTERVAL)


try:
    from bleak import BleakClient
except ImportError:
    BleakClient = None
    LOG.warning("bleak library not found; BLE functionality will be disabled.")

# DIAG-BEGIN ECHO-STARTUP
LOG.info(f"echo_responder.py started (PID={os.getpid()})")


def _flush_logs_echo():
    """Flush all logger handlers at process exit; resilient to handler errors."""
    try:
        LOG.info("echo_responder.py atexit: flushing logs before exit")
        for h in getattr(LOG, "handlers", []):
            if hasattr(h, "flush"):
                try:
                    h.flush()
                except Exception:
                    pass
    except Exception:
        # Last-gasp safety; avoid raising during interpreter shutdown
        pass


atexit.register(_flush_logs_echo)
# DIAG-END ECHO-STARTUP

# DIAG-BEGIN HEALTH-ECHO
ENABLE_HEALTH_CHECKS = _env_truthy(os.environ.get("ENABLE_HEALTH_CHECKS", "0"))


def _heartbeat_echo():
    while True:
        try:
            with open("/tmp/bb8_heartbeat_echo", "w") as f:
                f.write(f"{time.time()}\n")
        except Exception:
            # Don't crash the process if /tmp is unavailable; just retry next tick
            pass
        time.sleep(5)


if ENABLE_HEALTH_CHECKS:
    LOG.info("echo_responder.py health check enabled: /tmp/bb8_heartbeat_echo")
    threading.Thread(target=_heartbeat_echo, daemon=True).start()
# DIAG-END HEALTH-ECHO

MQTT_BASE = os.environ.get("MQTT_BASE") or os.environ.get("MQTT_NAMESPACE") or "bb8"
MQTT_ECHO_CMD = f"{MQTT_BASE}/echo/cmd"
# MQTT topic variables are already resolved above using _resolve_topic; do not redefine here.
BLE_TOUCH_CHAR = os.environ.get("BLE_TOUCH_CHAR", None)
BLE_TOUCH_VALUE = os.environ.get("BLE_TOUCH_VALUE", "01")

# NOTE: Logging configuration is set in main() and in the exception handler, not on import.

# -------- Concurrency guard (bounded inflight) --------
MAX_INFLIGHT = int(os.environ.get("ECHO_MAX_INFLIGHT", "16"))
# NOTE: Logging configuration is set both at the top (on import) and in main(), as well as in the exception handler.
# _last_ts: float = 0.0
# _last_ts_lock = threading.Lock()
MIN_INTERVAL_MS = float(os.environ.get("ECHO_MIN_INTERVAL_MS", "0"))  # 0 = off


def on_connect(client, userdata, flags, rc, properties=None):
    LOG.info("Connected to MQTT broker with rc=%s", getattr(rc, "name", rc))
    client.subscribe(MQTT_ECHO_CMD, qos=0)
    LOG.info("Subscribed to %s", MQTT_ECHO_CMD)
    client.subscribe(MQTT_BLE_READY_CMD, qos=0)
    LOG.info("Subscribed to %s", MQTT_BLE_READY_CMD)


def on_message(client, userdata, msg):
    LOG.info("Received message on %s: %s", msg.topic, msg.payload)
    if msg.topic == MQTT_ECHO_CMD:
        now = time.time()
        # Ack + state immediately
        try:
            client.publish(
                MQTT_ECHO_ACK, json.dumps({"ts": now, "value": 1}), qos=1, retain=False
            )
            client.publish(
                MQTT_ECHO_STATE,
                json.dumps({"ts": now, "state": "touched"}),
                qos=1,
                retain=False,
            )
        except Exception as e:
            LOG.exception("Echo publish failed (ack/state): %s", e)

        # Launch a short BLE probe in a thread; publish echo_roundtrip when done
        def _probe_and_publish():
            res = _ble_probe_once(
                timeout_s=3.0
            )  # tight probe; attestation drives repetition
            try:
                _publish_echo_roundtrip(
                    client, base_ts=now, ble_ok=res["ok"], ble_ms=res["latency_ms"]
                )
            except Exception as e:
                LOG.exception("Echo publish failed (roundtrip): %s", e)

        threading.Thread(target=_probe_and_publish, daemon=True).start()
    elif msg.topic == MQTT_BLE_READY_CMD:
        now = time.time()
        # minimal readiness reply; fill with actual probe if/when implemented
        res = _ble_probe_once(timeout_s=5.0)
        summary = {
            "ts": now,
            "detected": bool(res["ok"]),
            "attempts": 1,
            "latency_ms": res["latency_ms"],
            "source": "echo_responder",
        }
        try:
            client.publish(
                MQTT_BLE_READY_SUMMARY, json.dumps(summary), qos=1, retain=False
            )
        except Exception as e:
            LOG.exception("BLE-ready summary publish failed: %s", e)


class BleTouch:
    def __init__(self, addr):
        self.addr = addr
        self.char = BLE_TOUCH_CHAR
        try:
            self.value = bytes.fromhex(BLE_TOUCH_VALUE)
        except ValueError:
            # Fallback to b"\x01" if BLE_TOUCH_VALUE is not a valid hex string.
            LOG.warning(
                f"Invalid BLE_TOUCH_VALUE hex string: {BLE_TOUCH_VALUE}, defaulting to b'\\x01'"
            )
            self.value = b"\x01"

    def touch(self):  # pragma: no cover

        async def _ble_touch():
            t0 = time.time()
            if not self.char:
                LOG.warning("BLE_TOUCH_CHAR not set; cannot perform BLE touch")
                return False, None
            try:
                client = BleakClient(self.addr)
                await client.connect()
                await client.write_gatt_char(self.char, self.value)
                await client.disconnect()
                latency = int((time.time() - t0) * 1000)
                LOG.info(f"BLE touch success, latency={latency}ms")
                return True, latency
            except Exception as e:
                LOG.error(f"BLE touch error: {e}")
                return False, None


def get_mqtt_client():
    client = mqtt.Client()
    return client  # pragma: no cover


def handle_fatal_error(e):
    logging.error(f"Echo responder fatal error: {e}", exc_info=True)
    # Ensure logs are flushed before exit
    for h in logging.getLogger().handlers:
        if hasattr(h, "flush"):
            h.flush()
    sys.exit(1)


def main():
    client = get_mqtt_client()
    client.on_connect = on_connect
    client.on_message = on_message

    # Backoff to prevent tight reconnect storms under broker/auth failures
    try:
        client.reconnect_delay_set(min_delay=1, max_delay=5)
    except Exception:
        pass

    mqtt_host = (
        os.environ.get("MQTT_HOST") or os.environ.get("MQTT_SERVER") or "localhost"
    )
    mqtt_port = int(os.environ.get("MQTT_PORT") or 1883)
    mqtt_user = os.environ.get("MQTT_USERNAME") or os.environ.get("MQTT_USER")
    mqtt_pass = os.environ.get("MQTT_PASSWORD") or os.environ.get("MQTT_PASS")

    if mqtt_user and mqtt_pass:
        client.username_pw_set(mqtt_user, mqtt_pass)

    client.connect(mqtt_host, mqtt_port, keepalive=60)
    client.loop_forever()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        handle_fatal_error(e)
