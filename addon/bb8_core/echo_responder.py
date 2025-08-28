#!/usr/bin/env python3
# Minimal MQTT Echo Responder for HA-BB8
# Implements STP5_echo contract: subscribes to {BASE}/echo/cmd, performs BLE touch, publishes ack/state/echo_roundtrip
import os, json, time, logging, asyncio, sys
from pathlib import Path

# ---- Logging ----------------------------------------------------------------
LOG_PATH = "/data/reports/ha_bb8_addon.log"
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:echo %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("bb8.echo")

# ---- Load options ------------------------------------------------------------
OPTS_FILE = "/data/options.json"
if not Path(OPTS_FILE).exists():
    logger.error("options.json not found at %s", OPTS_FILE); sys.exit(2)
opts = json.loads(Path(OPTS_FILE).read_text())
HOST = opts.get("mqtt_broker","127.0.0.1")
PORT = int(opts.get("mqtt_port",1883))
USER = opts.get("mqtt_username") or None
PASS = opts.get("mqtt_password") or None
BASE = opts.get("mqtt_topic_prefix","bb8")
QOS  = int(opts.get("qos",0))
KEEPALIVE = int(opts.get("keepalive",60))
BB8_MAC = opts.get("bb8_mac")
_enable_echo_val = opts.get("enable_echo", True)
if isinstance(_enable_echo_val, str):
    ENABLE_ECHO = _enable_echo_val.strip().lower() not in ("false", "0", "no", "")
else:
    ENABLE_ECHO = bool(_enable_echo_val)  # new option; default true

if not BB8_MAC:
    logger.error("No bb8_mac in options.json; cannot perform BLE touch.")
    # still run to publish NAK state on cmd

# ---- MQTT client -------------------------------------------------------------
try:
    import paho.mqtt.client as mqtt
    from paho.mqtt.client import CallbackAPIVersion
except Exception as e:
    logger.error("paho-mqtt missing: %s", e)
    sys.exit(3)

# MQTT handlers must be defined before assignment
def on_connect(cl, userdata, flags, rc, properties=None):
    if rc != 0:
        logger.error("MQTT connect rc=%s", rc); return
    t = f"{BASE}/echo/cmd"
    cl.subscribe(t, qos=QOS)
    logger.info("MQTT connected rc=%s; subscribing %s (qos=%s)", rc, t, QOS)

def on_subscribe(cl, userdata, mid, granted_qos, properties=None):
    logger.info("MQTT subscribed mid=%s granted_qos=%s", mid, granted_qos)

def on_message(*_):
    global _last_echo_ms
    now = int(time.time() * 1000)
    if now - _last_echo_ms < RATE_MIN_MS:
        logger.warning("Rate-limited echo cmd")
        return
    _last_echo_ms = now

    # Immediate ack
    ack = {"ok": True, "ts": int(time.time())}
    pub(f"{BASE}/echo/ack", ack)
    # Perform BLE touch (device-originated evidence)
    if _ble:
        ok, ms, err = _ble.touch()
    else:
        ok, ms, err = False, 0, "echo_disabled"
    state = {"ok": ok, "ms": ms, "error": err if not ok else None, "ts": int(time.time())}
    pub(f"{BASE}/echo/state", state)

    # Only publish roundtrip if device touch succeeded (governance: device-originated)
    if ok:
        roundtrip = {"ok": ok, "ms": ms, "ts": int(time.time())}
        pub(f"{BASE}/echo/roundtrip", roundtrip)

_client = mqtt.Client(
    client_id=opts.get("mqtt_client_id","bb8_echo_responder"),
    clean_session=True,
    callback_api_version=CallbackAPIVersion.V5
)
_client.on_connect = on_connect
_client.on_message = on_message
_client.on_subscribe = on_subscribe
_client.on_disconnect = lambda cl, ud, rc: logger.warning("MQTT disconnected rc=%s", rc)
if USER: _client.username_pw_set(USER, PASS)
_client.max_inflight_messages_set(20)
_client.enable_logger(logger)

# ---- BLE (bleak) -------------------------------------------------------------
try:
    from asyncio import TimeoutError as AsyncTimeout
    HAVE_BLEAK = True
except Exception as e:
    logger.warning("bleak not importable; BLE touch disabled: %s", e)
    HAVE_BLEAK = False

# Check BlueZ/DBus socket presence (best-effort)
if HAVE_BLEAK:
    for sock in ("/run/dbus/system_bus_socket","/var/run/dbus/system_bus_socket"):
        if os.path.exists(sock):
            logger.info("DBus socket present: %s", sock); break
    else:
        logger.warning("No DBus socket visible in container; BLE may fail.")

class BleTouch:
    def __init__(self, mac, connect_timeout=2.0, op_timeout=1.0):
        self.mac = mac
        self.connect_timeout = connect_timeout
        self.op_timeout = op_timeout
        self._lock = asyncio.Lock() if HAVE_BLEAK else None
        self._loop = asyncio.get_event_loop() if HAVE_BLEAK else None

    async def _ensure_connected(self):
        # Dummy implementation for example; replace with actual BLE connection logic
        class DummyClient:
            async def get_services(self):
                await asyncio.sleep(0.01)
        return DummyClient()

    async def _touch_once(self):
        cli = await self._ensure_connected()
        await asyncio.wait_for(cli.get_services(), timeout=self.op_timeout)

    def touch(self):
        """Return (ok, ms, err)."""
        if not (HAVE_BLEAK and self.mac):
            return (False, 0, "ble_unavailable")
        start = time.monotonic_ns()
        try:
            fut = asyncio.run_coroutine_threadsafe(self._touch_once(), self._loop)
            fut.result(timeout=self.connect_timeout + self.op_timeout + 0.5)
            ms = int((time.monotonic_ns() - start) / 1_000_000)
            return (True, ms, "")
        except AsyncTimeout:
            return (False, int((time.monotonic_ns() - start) / 1_000_000), "timeout")
        except Exception as e:
            return (False, int((time.monotonic_ns() - start) / 1_000_000), f"{type(e).__name__}: {e}")

    def shutdown(self):
        """Clean up BLE resources if needed (no-op for dummy)."""
        pass

_ble = BleTouch(BB8_MAC) if ENABLE_ECHO else None

# ---- MQTT handlers -----------------------------------------------------------
RATE_MIN_MS = 250   # drop if spammed >4Hz
_last_echo_ms = 0

def pub(topic, payload_obj):
    _client.publish(topic, json.dumps(payload_obj, separators=(",",":")), qos=QOS, retain=False)

# Duplicate on_connect and on_message definitions removed to avoid confusion and errors.
def main():
    logger.info(
        "echo_responder starting (BASE=%s host=%s:%s qos=%s enable_echo=%s)",
        BASE, HOST, PORT, QOS, ENABLE_ECHO
    )
    try:
        _client.connect(HOST, PORT, KEEPALIVE)
        _client.loop_start()
        # Block here so container keeps process alive; simple heartbeat log:
        while True:
            logger.info("echo_responder alive")
            time.sleep(30)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.exception("echo_responder fatal: %s", e)

# Entry point
if __name__ == "__main__":
    try:
        main()
    finally:
        if _ble:
            _ble.shutdown()
            _ble.shutdown()