"""Echo responder helpers for BB8 add-on.

Small runtime helpers used by the add-on for MQTT echo and BLE probes.
This module publishes echo acknowledgements and optionally performs a
BLE probe to validate device reachability.
"""

import asyncio
import contextlib
import json
import logging
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt

LOG = logging.getLogger(__name__)

OPTIONS_PATH = os.environ.get("OPTIONS_PATH", "/data/options.json")
DEFAULT_OPTS = {
    "mqtt_base": "bb8",
    "bb8_mac": "",
    "mqtt_topic_prefix": "bb8",
    "ble_adapter": "hci0",
}


def _load_opts(path: str = OPTIONS_PATH) -> dict:
    """Load options from JSON file at `path`. Returns defaults on error."""
    try:
        p = Path(path)
        with p.open() as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        LOG.warning("Failed to read %s: %s — using defaults", path, e)
        return DEFAULT_OPTS.copy()


_opts = _load_opts()
_base = _opts.get("mqtt_base") or _opts.get("mqtt_topic_prefix") or "bb8"

# --- BLE probe helpers (minimal; Supervisor-only) ---
try:
    from bleak import BleakClient, BleakScanner
except ImportError:  # bleak missing or import error
    BleakScanner = None
    BleakClient = None

_bb8_mac = (_opts.get("bb8_mac") or "").upper().strip()
_ble_adapter = (_opts.get("ble_adapter") or "hci0").strip()
if not _bb8_mac:
    LOG.warning("No bb8_mac found in options.json; BLE probe will always fail.")


def _ble_probe_once(timeout_s: float = 3.0) -> dict:
    """Minimal device-originated evidence: scan for the target MAC using Bleak.

    Returns: {"ok": bool, "latency_ms": int|None}.
    """
    if BleakScanner is None or not _bb8_mac:
        return {"ok": False, "latency_ms": None}
    t0 = time.time()
    try:
        # BleakScanner.discover is async; run it in the event loop
        async def _discover() -> list[Any]:
            return await BleakScanner.discover(
                timeout=timeout_s,
                adapter=_ble_adapter,
            )

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            devices = asyncio.run(_discover())
        else:
            future = asyncio.run_coroutine_threadsafe(_discover(), loop)
            devices = future.result()
            found = any((d.address or "").upper() == _bb8_mac for d in (devices or []))
            if found:
                ms = int((time.time() - t0) * 1000)
                return {"ok": True, "latency_ms": ms}
            return {"ok": False, "latency_ms": None}
    except (OSError, RuntimeError, TimeoutError) as e:
        LOG.info("BLE probe error: %s", e)
        return {"ok": False, "latency_ms": None}


def _publish_echo_roundtrip(
    client: mqtt.Client,
    base_ts: float,
    *,
    ble_ok: bool,
    ble_ms: int | None = None,
) -> None:
    """Publish echo roundtrip info to configured MQTT topic."""
    payload = {
        "ts": int(base_ts),
        "rtt_ms": 0,
        "ble_ok": bool(ble_ok),
        "ble_latency_ms": ble_ms if ble_ok else None,
    }
    client.publish(MQTT_ECHO_RTT, json.dumps(payload), qos=1, retain=False)


def _resolve_topic(
    opt_key: str,
    default_suffix: str,
    env_key: str | None = None,
) -> str:
    """Resolve configured topic name using ENV, options.json, or a default.

    Prefers an explicit ENV override, then the options.json setting, then the
    canonical default "{_base}/{default_suffix}". If the resolved topic
    contains MQTT wildcards it will be replaced with the safe default.
    """
    if env_key is None:
        env_key = opt_key.upper()
    raw = os.environ.get(env_key) or _opts.get(opt_key) or ""
    raw = str(raw).strip()
    topic = f"{_base}/{default_suffix}" if not raw else raw.lstrip("/")
    if "#" in topic or "+" in topic:
        LOG.warning(
            "Wildcard detected in %s='%s' - unsafe for pub/sub; blocking topic",
            opt_key,
            topic,
        )
        topic = f"{_base}/{default_suffix}"
    LOG.info("Resolved topic %s => %s", opt_key, topic)
    return topic


# --- Resolved topics (single source of truth) ---
MQTT_ECHO_CMD = _resolve_topic(
    "mqtt_echo_cmd_topic",
    "echo/cmd",
    "MQTT_ECHO_CMD_TOPIC",
)
MQTT_ECHO_ACK = _resolve_topic(
    "mqtt_echo_ack_topic",
    "echo/ack",
    "MQTT_ECHO_ACK_TOPIC",
)
MQTT_ECHO_STATE = _resolve_topic(
    "mqtt_echo_state_topic",
    "echo/state",
    "MQTT_ECHO_STATE_TOPIC",
)
MQTT_ECHO_RTT = _resolve_topic(
    "mqtt_telemetry_echo_roundtrip_topic",
    "telemetry/echo_roundtrip",
    "MQTT_TELEMETRY_ECHO_ROUNDTRIP_TOPIC",
)
MQTT_BLE_READY_CMD = _resolve_topic(
    "mqtt_ble_ready_cmd_topic",
    "ble_ready/cmd",
    "MQTT_BLE_READY_CMD_TOPIC",
)
MQTT_BLE_READY_SUMMARY = _resolve_topic(
    "mqtt_ble_ready_summary_topic",
    "ble_ready/summary",
    "MQTT_BLE_READY_SUMMARY_TOPIC",
)


# --- Robust health heartbeat (atomic writes + fsync) ---
def _env_truthy(val: str) -> bool:
    return str(val).strip().lower() in {"1", "true", "yes", "on"}


def _write_atomic(path: str, content: str) -> None:
    """Atomically write `content` to `path` using a temporary file."""
    p = Path(path)
    tmp = p.with_suffix(p.suffix + ".tmp") if p.suffix else Path(str(p) + ".tmp")
    try:
        with tmp.open("w") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(p)
    except OSError as e:
        msg = "atomic write failed"
        raise OSError(msg) from e


def _start_heartbeat(path: str, interval: int) -> None:
    """Start a background heartbeat thread writing timestamps to `path`."""
    interval = max(interval, 2)  # lower bound

    def _hb() -> None:
        # write immediately, then tick
        try:
            _write_atomic(path, f"{time.time()}\n")
        except OSError as e:
            LOG.debug("heartbeat initial write failed: %s", e)
        while True:
            try:
                _write_atomic(path, f"{time.time()}\n")
            except OSError as e:
                LOG.debug("heartbeat write failed: %s", e)
            time.sleep(interval)

    t = threading.Thread(target=_hb, daemon=True)
    t.start()


ENABLE_HEALTH_CHECKS = _env_truthy(os.environ.get("ENABLE_HEALTH_CHECKS", "0"))
HB_INTERVAL = int(os.environ.get("HEARTBEAT_INTERVAL_SEC", "5"))
HB_PATH_ECHO = str(Path(tempfile.gettempdir()) / "bb8_heartbeat_echo")
if ENABLE_HEALTH_CHECKS:
    LOG.info("echo_responder.py health check enabled: %s", HB_PATH_ECHO)
    try:
        _start_heartbeat(HB_PATH_ECHO, HB_INTERVAL)
    except OSError as e:
        LOG.warning("Failed to start heartbeat: %s", e)

MAX_INFLIGHT = int(os.environ.get("ECHO_MAX_INFLIGHT", "16"))
_inflight = threading.BoundedSemaphore(MAX_INFLIGHT)


def on_message(client: mqtt.Client, _: object, msg: mqtt.MQTTMessage) -> None:
    """Handle incoming MQTT messages for echo and BLE ready commands."""
    try:
        try:
            payload = json.loads(msg.payload.decode())
        except (json.JSONDecodeError, AttributeError) as e:
            LOG.warning("on_message received invalid JSON: %s", e)
            return
        now = time.time()
        if msg.topic == MQTT_ECHO_CMD:
            client.publish(
                MQTT_ECHO_ACK,
                json.dumps({"ts": now, "value": payload.get("value")}),
                qos=1,
                retain=False,
            )
            client.publish(
                MQTT_ECHO_STATE,
                json.dumps({"ts": now, "state": "touched"}),
                qos=1,
                retain=False,
            )

            def _probe_and_publish() -> None:
                res = _ble_probe_once(timeout_s=3.0)
                try:
                    _publish_echo_roundtrip(
                        client,
                        base_ts=now,
                        ble_ok=res["ok"],
                        ble_ms=res["latency_ms"],
                    )
                except (OSError, RuntimeError) as e:
                    LOG.warning("Echo publish failed (ack/state): %s", e)

            threading.Thread(target=_probe_and_publish, daemon=True).start()
        elif msg.topic == MQTT_BLE_READY_CMD:
            # Publish BLE ready summary
            client.publish(
                MQTT_BLE_READY_SUMMARY,
                json.dumps({"ts": now, "status": "ready"}),
                qos=1,
                retain=False,
            )
    except (OSError, RuntimeError, ValueError) as e:
        LOG.warning("on_message error: %s", e)


class BleTouch:
    """Helper to perform a BLE 'touch' to a configured device/characteristic."""

    def __init__(self) -> None:
        """Initialize BLE touch helper from environment variables."""
        self.addr = os.environ.get("BLE_ADDR")
        self.char = os.environ.get("BLE_TOUCH_CHAR")
        ble_touch_value = os.environ.get("BLE_TOUCH_VALUE", "01")
        try:
            self.value = bytes.fromhex(ble_touch_value)
        except ValueError:
            LOG.warning(
                "Invalid BLE_TOUCH_VALUE: %s; defaulting to 0x01",
                ble_touch_value,
            )
            self.value = b"\x01"

    def touch(self) -> tuple[bool, int | None]:  # pragma: no cover
        """Trigger a BLE touch; returns (success, latency_ms)."""

        async def _ble_touch() -> tuple[bool, int | None]:
            t0 = time.time()
            if not self.addr:
                LOG.warning("BLE_ADDR not set; cannot perform BLE touch")
                return False, None
            if not self.char:
                LOG.warning("BLE_TOUCH_CHAR not set; cannot perform BLE touch")
                return False, None
            try:
                # BleakClient imported at module level if available
                client = BleakClient(self.addr)
                await client.connect()
                await client.write_gatt_char(self.char, self.value)
                await client.disconnect()
            except Exception:
                LOG.exception("BLE touch error")
                return False, None
            else:
                latency = int((time.time() - t0) * 1000)
                return True, latency

        # asyncio is imported at module level
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(_ble_touch())
        else:
            future = asyncio.run_coroutine_threadsafe(_ble_touch(), loop)
            return future.result()


def get_mqtt_client() -> mqtt.Client:
    """Return a new paho-mqtt Client instance."""
    return mqtt.Client()


def on_connect(
    client: mqtt.Client,
    _userdata: object,
    _flags: object,
    rc: int,
) -> None:
    """MQTT on_connect callback: subscribe to needed topics."""
    LOG.info("Connected to MQTT broker with result code %s", rc)
    client.subscribe(MQTT_ECHO_CMD)
    client.subscribe(MQTT_BLE_READY_CMD)


def main() -> None:
    """Start the echo responder MQTT client loop."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    client = get_mqtt_client()
    client.on_connect = on_connect
    client.on_message = on_message

    with contextlib.suppress(Exception):
        client.reconnect_delay_set(min_delay=1, max_delay=5)

    mqtt_host = os.environ.get("MQTT_HOST") or os.environ.get("MQTT_SERVER")
    mqtt_port = int(os.environ.get("MQTT_PORT") or 1883)
    mqtt_user = os.environ.get("MQTT_USERNAME") or os.environ.get("MQTT_USER")
    mqtt_pass = os.environ.get("MQTT_PASSWORD") or os.environ.get("MQTT_PASS")
    if mqtt_user and mqtt_pass:
        client.username_pw_set(mqtt_user, mqtt_pass)
    client.connect(mqtt_host, mqtt_port, 60)  # pragma: no cover
    LOG.info("Starting MQTT loop on %s:%s", mqtt_host, mqtt_port)
    client.loop_forever()  # pragma: no cover


if __name__ == "__main__":
    try:
        main()
    except Exception:
        LOG.exception("Echo responder fatal error")
        for h in logging.getLogger().handlers:
            if hasattr(h, "flush"):
                h.flush()
        raise
