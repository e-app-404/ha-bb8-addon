import asyncio
import atexit
import contextlib
import json
import logging
import os
import threading
import time

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

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
MQTT_ECHO_CMD = _resolve_topic("mqtt_echo_cmd_topic", "echo/cmd", 
                               "MQTT_ECHO_CMD_TOPIC")
MQTT_ECHO_ACK = _resolve_topic("mqtt_echo_ack_topic", "echo/ack", 
                               "MQTT_ECHO_ACK_TOPIC")
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
    "mqtt_ble_ready_summary_topic", "ble_ready/summary",
      "MQTT_BLE_READY_SUMMARY_TOPIC"
)

LOG = logging.getLogger("echo_responder")


# --- Robust health heartbeat (atomic writes + fsync) ---
def _env_truthy(val: str) -> bool:
    return str(val).strip().lower() in {"1", "true", "yes", "on"}


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


@atexit.register
def _hb_exit():
    with contextlib.suppress(Exception):
        _write_atomic(HB_PATH_ECHO, f"{time.time()}\n")


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
                with contextlib.suppress(Exception):
                    h.flush()
    except Exception:
        # Last-gasp safety; avoid raising during interpreter shutdown
        pass


atexit.register(_flush_logs_echo)
# DIAG-END ECHO-STARTUP

# DIAG-BEGIN HEALTH-ECHO
ENABLE_HEALTH_CHECKS = bool(int(os.environ.get("ENABLE_HEALTH_CHECKS", "0")))


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
MQTT_ECHO_ACK = f"{MQTT_BASE}/echo/ack"
MQTT_ECHO_STATE = f"{MQTT_BASE}/echo/state"
MQTT_TELEMETRY = f"{MQTT_BASE}/telemetry/echo_roundtrip"

BLE_ADDR = os.environ.get("BLE_ADDR", None)
BLE_TOUCH_CHAR = os.environ.get("BLE_TOUCH_CHAR", None)
BLE_TOUCH_VALUE = os.environ.get("BLE_TOUCH_VALUE", "01")

# NOTE: Logging config is now set only when running as a script, not on import.

# -------- Concurrency guard (bounded inflight) --------
MAX_INFLIGHT = int(os.environ.get("ECHO_MAX_INFLIGHT", "16"))
_inflight = threading.BoundedSemaphore(MAX_INFLIGHT)

# Optional micro-rate limit (disabled by default)
_last_ts = 0.0
_last_ts: float = 0.0
_last_ts_lock = threading.Lock()
MIN_INTERVAL_MS = float(os.environ.get("ECHO_MIN_INTERVAL_MS", "0"))  # 0 = off


def pub(client, topic, payload, retain=False):
    LOG.debug(f"Publishing to {topic}: {payload}")
    client.publish(topic, json.dumps(payload), qos=0, retain=retain)  # pragma: no cover


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


def _spawn_ble_ready(client, base, mac, cfg):
    def worker():
        res = asyncio.run(_ble_ready_probe(mac, cfg))
        try:
            client.publish(
                f"{base}/ble_ready/summary", json.dumps(res), qos=1, retain=False
            )
        except Exception as e:
            print(f"[BB-8] BLE_READY publish error: {e}", flush=True)

    threading.Thread(target=worker, daemon=True).start()


async def _ble_ready_probe(bb8_mac, cfg):
    from bleak import BleakScanner

    mac_norm = (bb8_mac or "").upper()
    timeout_s = max(1, int(cfg.get("timeout_s", 12)))
    retry_s = max(0.2, float(cfg.get("retry_interval_s", 1.5)))
    max_tries = max(1, int(cfg.get("max_attempts", max(1, int(timeout_s / retry_s)))))
    nonce = cfg.get("nonce")
    attempts, detected, rssi, name = 0, False, None, None
    t0 = time.time()
    while attempts < max_tries and (time.time() - t0) < timeout_s:
        attempts += 1
        try:
            devices = await BleakScanner.discover(timeout=retry_s)
            for d in devices:
                if d.address.upper() == mac_norm:
                    detected = True
                    rssi = getattr(d, "rssi", None)
                    name = getattr(d, "name", None)
                    break
            if detected:
                break
        except Exception as e:
            print(f"[BB-8] BLE_READY probe error: {e}", flush=True)
        await asyncio.sleep(0)
    return {
        "ts": time.time(),
        "nonce": nonce,
        "detected": detected,
        "attempts": attempts,
        "mac": mac_norm,
        "rssi": rssi,
        "name": name,
    }


def handle_echo(client, payload):
    t0 = time.time()
    ack = {"ts": round(t0, 3), "value": payload.get("value", None)}
    pub(client, MQTT_ECHO_ACK, ack)  # pragma: no cover
    state = {"ts": round(time.time(), 3), "state": "touched"}
    pub(client, MQTT_ECHO_STATE, state)  # pragma: no cover
    ble_ok = False
    ble_latency = None
    if BLE_ADDR and BleakClient:
        try:
            ble_ok, ble_latency = BleTouch().touch()
        except Exception as e:
            LOG.error(f"BLE touch failed: {e}")
    t1 = time.time()
    telemetry = {
        "ts": int(t1),
        "rtt_ms": int((t1 - t0) * 1000),
        "ble_ok": ble_ok,
        "ble_latency_ms": ble_latency,
    }
    pub(client, MQTT_TELEMETRY, telemetry)  # pragma: no cover


class BleTouch:
    def __init__(self):
        self.addr = BLE_ADDR
        self.char = BLE_TOUCH_CHAR
        try:
            self.value = bytes.fromhex(BLE_TOUCH_VALUE)
        except ValueError:
            # Fallback to b"\x01" if BLE_TOUCH_VALUE is not a valid hex string.
            # Ensure fallback value is compatible with your BLE device's input.
            LOG.warning(
                f"Invalid BLE_TOUCH_VALUE hex string: {BLE_TOUCH_VALUE}, "
                f"defaulting to b'\\x01'"
            )
            self.value = b"\x01"

    def touch(self):  # pragma: no cover
        import asyncio

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

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, safe to use asyncio.run()
            return asyncio.run(_ble_touch())
        else:
            # Running inside an existing event loop (e.g., in a thread or async context)
            future = asyncio.run_coroutine_threadsafe(_ble_touch(), loop)
            return future.result()


def get_mqtt_client():
    client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
    return client  # pragma: no cover


def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    client = get_mqtt_client()
    client.on_connect = on_connect
    client.on_message = on_message

    # Backoff to prevent tight reconnect storms under broker/auth failures
    # (keeps CPU/memory stable if broker is down or credentials invalid)
    with contextlib.suppress(Exception):
        client.reconnect_delay_set(min_delay=1, max_delay=5)

    mqtt_host = (
        os.environ.get("MQTT_HOST") or os.environ.get("MQTT_SERVER") or "localhost"
    )
    mqtt_port = int(os.environ.get("MQTT_PORT") or 1883)
    # Accept either MQTT_USERNAME/PASSWORD or MQTT_USER/PASS
    mqtt_user = os.environ.get("MQTT_USERNAME") or os.environ.get("MQTT_USER")
    mqtt_pass = os.environ.get("MQTT_PASSWORD") or os.environ.get("MQTT_PASS")
    if mqtt_user and mqtt_pass:
        client.username_pw_set(mqtt_user, mqtt_pass)
    # Note: client.connect() is non-blocking; loop_forever() starts the
    # network loop and blocks the main thread.
    client.connect(mqtt_host, mqtt_port, 60)  # pragma: no cover
    LOG.info(f"Starting MQTT loop on {mqtt_host}:{mqtt_port}")
    client.loop_forever()  # pragma: no cover


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import logging
        import sys

        logging.basicConfig(level=logging.ERROR)
        logging.error(f"Echo responder fatal error: {e}", exc_info=True)
        # Ensure logs are flushed before exit
        for h in logging.getLogger().handlers:
            if hasattr(h, "flush"):
                h.flush()
        sys.exit(1)
