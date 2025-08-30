import json
import logging
import os
import signal
import threading
from typing import Optional
import time

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

try:
    from bleak import BleakClient
except ImportError:
    BleakClient = None
    LOG.warning("bleak library not found; BLE functionality will be disabled.")

MQTT_BASE = (
    os.environ.get("MQTT_BASE")
    or os.environ.get("MQTT_NAMESPACE")
    or "bb8"
)
MQTT_ECHO_CMD = f"{MQTT_BASE}/echo/cmd"
MQTT_ECHO_ACK = f"{MQTT_BASE}/echo/ack"
MQTT_ECHO_STATE = f"{MQTT_BASE}/echo/state"
MQTT_TELEMETRY = f"{MQTT_BASE}/telemetry/echo_roundtrip"

BLE_ADDR = os.environ.get("BLE_ADDR", None)
BLE_TOUCH_CHAR = os.environ.get("BLE_TOUCH_CHAR", None)
BLE_TOUCH_VALUE = os.environ.get("BLE_TOUCH_VALUE", "01")

LOG = logging.getLogger("echo_responder")
# NOTE: Logging configuration is now set only when running as a script, not on import.

# -------- Concurrency guard (bounded inflight) --------
MAX_INFLIGHT = int(os.environ.get("ECHO_MAX_INFLIGHT", "16"))
_inflight = threading.BoundedSemaphore(MAX_INFLIGHT)

# Optional micro-rate limit (disabled by default)
_last_ts = 0.0
_last_ts: float = 0.0
MIN_INTERVAL_MS = float(os.environ.get("ECHO_MIN_INTERVAL_MS", "0"))  # 0 = off


def pub(client, topic, payload, retain=False):
    LOG.debug(f"Publishing to {topic}: {payload}")
    client.publish(topic, json.dumps(payload), qos=0, retain=retain)


def on_connect(client, userdata, flags, rc, properties=None):
    LOG.info(f"Connected to MQTT broker with rc={rc}")
    client.subscribe(MQTT_ECHO_CMD)
    LOG.info(f"Subscribed to {MQTT_ECHO_CMD}")


def on_message(client, userdata, msg):
    LOG.info(f"Received message on {msg.topic}: {msg.payload}")
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except Exception:
        payload = {"raw": msg.payload.decode("utf-8", errors="replace")}

    # Optional rate limit
    if MIN_INTERVAL_MS > 0:
        global _last_ts
        now = time.time()
        with _last_ts_lock:
            if (now - _last_ts) < (MIN_INTERVAL_MS / 1000.0):
                LOG.warning("Echo throttled by MIN_INTERVAL_MS; dropping")
                return
            _last_ts = now

    # Bounded inflight protection
    acquired = _inflight.acquire(blocking=False)
    if not acquired:
        LOG.warning("Echo backlog full (MAX_INFLIGHT=%d); dropping", MAX_INFLIGHT)
        return

    def _task():
        try:
            handle_echo(client, payload)
        finally:
            _inflight.release()

    threading.Thread(target=_task, daemon=True).start()


def handle_echo(client, payload):
    t0 = time.time()
    ack = {"ts": round(t0, 3), "value": payload.get("value", None)}
    pub(client, MQTT_ECHO_ACK, ack)
    state = {"ts": round(time.time(), 3), "state": "touched"}
    pub(client, MQTT_ECHO_STATE, state)
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
    pub(client, MQTT_TELEMETRY, telemetry)


class BleTouch:
    def __init__(self):
        self.addr = BLE_ADDR
        self.char = BLE_TOUCH_CHAR
        try:
            self.value = bytes.fromhex(BLE_TOUCH_VALUE)
        except ValueError:
            # Fallback to b"\x01" if BLE_TOUCH_VALUE is not a valid hex string.
            # Ensure this fallback value is compatible with your BLE device's expected input.
            LOG.warning(f"Invalid BLE_TOUCH_VALUE hex string: {BLE_TOUCH_VALUE}, defaulting to b'\\x01'")
            self.value = b"\x01"

    def touch(self):
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
def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_message = on_message

    # Backoff to prevent tight reconnect storms under broker/auth failures
    # (keeps CPU/memory stable if broker is down or credentials invalid)
    try:
        client.reconnect_delay_set(min_delay=1, max_delay=5)
    except Exception:
        pass

    mqtt_host = os.environ.get("MQTT_HOST") or os.environ.get("MQTT_SERVER") or "localhost"
    mqtt_port = int(os.environ.get("MQTT_PORT") or 1883)
    # Accept either MQTT_USERNAME/PASSWORD or MQTT_USER/PASS
    mqtt_user = os.environ.get("MQTT_USERNAME") or os.environ.get("MQTT_USER")
    mqtt_pass = os.environ.get("MQTT_PASSWORD") or os.environ.get("MQTT_PASS")
    if mqtt_user and mqtt_pass:
        client.username_pw_set(mqtt_user, mqtt_pass)
    # Note: client.connect() is non-blocking; loop_forever() starts the network loop and blocks the main thread.
    client.connect(mqtt_host, mqtt_port, 60)
    LOG.info(f"Starting MQTT loop on {mqtt_host}:{mqtt_port}")
    client.loop_forever()


if __name__ == "__main__":
    main()
