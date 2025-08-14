from __future__ import annotations
from .addon_config import load_config
CFG, SRC = load_config()

"""
ble_bridge.py

Orchestrates BLE operations for BB-8, manages device connection, and exposes diagnostics for Home Assistant add-on integration.
"""

from typing import Optional, Any, List, Tuple
import asyncio
import importlib.metadata
import json
import os
import time

from bleak import BleakClient
from bleak.exc import BleakCharacteristicNotFoundError
import paho.mqtt.publish as publish
from .logging_setup import logger
from spherov2.adapter.bleak_adapter import BleakAdapter
from spherov2.commands.core import IntervalOptions
from spherov2.scanner import find_toys
from spherov2.toy.bb8 import BB8

from .ble_utils import resolve_services
from .core import Core


# Use config for device name and MAC
BB8_NAME = CFG.get("BB8_NAME", "BB-8")
BB8_MAC = CFG.get("BB8_MAC", "B8:17:C2:A8:ED:45")

try:
    bleak_version = importlib.metadata.version("bleak")
except Exception:
    bleak_version = "unknown"
try:
    spherov2_version = importlib.metadata.version("spherov2")
except Exception:
    spherov2_version = "unknown"
logger.info({"event": "version_probe", "bleak": bleak_version, "spherov2": spherov2_version})

class BLEBridge:
    # --------- Extended shims (safe no-ops until wired) ---------
    def set_heading(self, degrees: int) -> None:
        try:
            v = max(0, min(359, int(degrees)))
            # TODO: implement via spherov2 API (orientation)
            logger.info({"event": "ble_heading_set", "degrees": v})
        except Exception as e:
            logger.error({"event": "ble_heading_error", "error": repr(e)})

    def set_speed(self, speed: int) -> None:
        try:
            v = max(0, min(255, int(speed)))
            # TODO: store/apply speed to drive profiles
            logger.info({"event": "ble_speed_set", "speed": v})
        except Exception as e:
            logger.error({"event": "ble_speed_error", "error": repr(e)})

    def drive(self, heading: int, speed: int) -> None:
        """Placeholder drive action; replace with timed roll when wired."""
        try:
            logger.info({"event": "ble_drive", "heading": int(heading), "speed": int(speed)})
            # TODO: spherov2 roll for a short burst
        except Exception as e:
            logger.error({"event": "ble_drive_error", "error": repr(e)})
    # =======================
    # Public handler surface
    # =======================
    def power(self, on: bool) -> None:
        """High-level power shim: ON -> connect(); OFF -> sleep(None)."""
        try:
            if on:
                self.connect()
            else:
                self.sleep(None)
        except Exception as e:
            logger.error({"event": "ble_power_error", "on": on, "error": repr(e)})

    def stop(self) -> None:
        """Halt motion; safe no-op if not connected."""
        with self._lock:
            try:
                if not getattr(self, "_toy", None):
                    logger.info({"event": "ble_stop_noop", "reason": "toy_not_connected"})
                    return
                # TODO: implement real stop via spherov2
                logger.info({"event": "ble_stop"})
            except Exception as e:
                logger.error({"event": "ble_stop_error", "error": repr(e)})

    def set_led_off(self) -> None:
        """Turn off LEDs."""
        self.set_led_rgb(0, 0, 0)

    def set_led_rgb(self, r: int, g: int, b: int) -> None:
        """Set LED color; clamps inputs; safe no-op if not connected."""
        r = max(0, min(255, int(r))); g = max(0, min(255, int(g))); b = max(0, min(255, int(b)))
        with self._lock:
            try:
                if not getattr(self, "_toy", None):
                    logger.info({"event": "ble_led_noop", "reason": "toy_not_connected", "r": r, "g": g, "b": b})
                    return
                # TODO: implement real LED set via spherov2
                logger.info({"event": "ble_led_set", "r": r, "g": g, "b": b})
            except Exception as e:
                logger.error({"event": "ble_led_error", "r": r, "g": g, "b": b, "error": repr(e)})

    def sleep(self, after_ms: Optional[int] = None) -> None:
        """Put device to sleep; default immediate. Safe no-op if not connected."""
        with self._lock:
            try:
                if not getattr(self, "_toy", None):
                    logger.info({"event": "ble_sleep_noop", "reason": "toy_not_connected", "after_ms": after_ms})
                    return
                # TODO: implement real sleep via spherov2 (respect after_ms if desired)
                logger.info({"event": "ble_sleep", "after_ms": after_ms})
            except Exception as e:
                logger.error({"event": "ble_sleep_error", "after_ms": after_ms, "error": repr(e)})

    def is_connected(self) -> bool:
        """Best-effort connection flag for telemetry/presence."""
        return bool(getattr(self, "_connected", False))

    def get_rssi(self) -> int:
        """Return RSSI dBm if the gateway exposes it; else 0."""
        try:
            gw_get = getattr(self.gateway, "get_rssi", None)
            if callable(gw_get):
                val = gw_get(self.target_mac)
                if isinstance(val, (int, float)):
                    return int(val)
        except Exception as e:
            logger.debug({"event": "ble_get_rssi_error", "error": repr(e)})
        return 0
    def attach_mqtt(self, client, base_topic: str, qos: int = 1, retain: bool = True) -> None:
        """
        Wire MQTT subscriptions for commands and set up state publishers.
        Expected topics (under base_topic):
          - power:    {base}/power/set   (payload: "ON"|"OFF")    -> {base}/power/state
          - stop:     {base}/stop/press  (payload: any)           -> {base}/stop/state ("pressed" then "idle")
          - led:      {base}/led/set     (json: {"r":..,"g":..,"b":..} or {"hex":"#rrggbb"} or "OFF")
                      -> {base}/led/state (json {"r":..,"g":..,"b":..} or {"state":"OFF"})
        Telemetry publishers (you can call these from your periodic loop):
          - presence: {base}/presence/state  ("ON"|"OFF")
          - rssi:     {base}/rssi/state      (int dBm)
        """
        from .logging_setup import logger
        import json
        import threading
        import time

        self._mqtt = {"client": client, "base": base_topic, "qos": qos, "retain": retain}

        def _pub(topic_suffix: str, payload, r: bool = retain):
            t = f"{base_topic}/{topic_suffix}"
            if isinstance(payload, (dict, list)):
                payload = json.dumps(payload, separators=(",", ":"))
            client.publish(t, payload=payload, qos=qos, retain=r)

        # --- Command handlers ---
        def _handle_power(_client, _userdata, msg):
            try:
                val = (msg.payload or b"").decode("utf-8").strip().upper()
                if val == "ON":
                    # Wake/connect
                    if hasattr(self, "connect") and callable(self.connect):
                        self.connect()
                    _pub("power/state", "ON")
                elif val == "OFF":
                    # Sleep/disconnect
                    if hasattr(self, "sleep") and callable(self.sleep):
                        self.sleep()
                    _pub("power/state", "OFF")
                else:
                    logger.warning({"event": "power_invalid_payload", "payload": val})
            except Exception as e:
                logger.error({"event": "power_handler_error", "error": repr(e)})

        def _parse_color(raw: str):
            raw = raw.strip()
            if raw.upper() == "OFF":
                return None
            try:
                obj = json.loads(raw)
                if isinstance(obj, dict):
                    if "hex" in obj and isinstance(obj["hex"], str):
                        h = obj["hex"].lstrip("#")
                        return {"r": int(h[0:2], 16), "g": int(h[2:4], 16), "b": int(h[4:6], 16)}
                    r = int(obj.get("r", 0)); g = int(obj.get("g", 0)); b = int(obj.get("b", 0))
                    return {"r": max(0, min(255, r)), "g": max(0, min(255, g)), "b": max(0, min(255, b))}
            except Exception:
                pass
            return None

        def _handle_led(_client, _userdata, msg):
            try:
                raw = (msg.payload or b"").decode("utf-8")
                rgb = _parse_color(raw)
                if rgb is None:
                    # OFF
                    if hasattr(self, "set_led_off"):
                        self.set_led_off()
                    _pub("led/state", {"state": "OFF"})
                else:
                    if hasattr(self, "set_led_rgb"):
                        self.set_led_rgb(rgb["r"], rgb["g"], rgb["b"])
                    _pub("led/state", {"r": rgb["r"], "g": rgb["g"], "b": rgb["b"]})
            except Exception as e:
                logger.error({"event": "led_handler_error", "error": repr(e)})

        def _handle_stop(_client, _userdata, _msg):
            try:
                if hasattr(self, "stop"):
                    self.stop()
                _pub("stop/state", "pressed", r=False)
                # auto-reset the momentary state to "idle" after a beat
                def _reset():
                    time.sleep(0.5)
                    _pub("stop/state", "idle", r=False)
                threading.Thread(target=_reset, daemon=True).start()
            except Exception as e:
                logger.error({"event": "stop_handler_error", "error": repr(e)})

        # --- Subscriptions ---
        client.message_callback_add(f"{base_topic}/power/set", _handle_power)
        client.subscribe(f"{base_topic}/power/set", qos=qos)

        client.message_callback_add(f"{base_topic}/led/set", _handle_led)
        client.subscribe(f"{base_topic}/led/set", qos=qos)

        client.message_callback_add(f"{base_topic}/stop/press", _handle_stop)
        client.subscribe(f"{base_topic}/stop/press", qos=qos)

        # --- Telemetry helpers (call from your polling loop) ---
        def publish_presence(online: bool):
            _pub("presence/state", "ON" if online else "OFF")

        def publish_rssi(dbm: int):
            _pub("rssi/state", str(int(dbm)))

        # expose helpers
        self.publish_presence = publish_presence  # type: ignore[attr-defined]
        self.publish_rssi = publish_rssi          # type: ignore[attr-defined]
        def attach_mqtt(self, client, base_topic: str, qos: int = 1, retain: bool = True) -> None:
            """Deprecated: forwarding to facade to avoid transport concerns in bridge."""
            from .facade import BB8Facade  # lazy import to avoid circular import
            BB8Facade(self).attach_mqtt(client, base_topic, qos=qos, retain=retain)
    def __init__(self, gateway, target_mac: Optional[str] = None, mac: Optional[str] = None, **kwargs) -> None:
        import threading
        self._lock = threading.RLock()
        self._connected: bool = False
        self.publish_presence = None
        self.publish_rssi = None
        self.gateway = gateway
        self.target_mac: Optional[str] = target_mac or mac
        if not self.target_mac:
            raise ValueError("BLEBridge requires target_mac/mac to be provided")
        # Runtime/control attributes referenced elsewhere
        self.timeout: float = float(kwargs.get("timeout", 10.0))
        self.controller: Optional[Any] = kwargs.get("controller")
        # Low-level core
        self.core = Core(address=self.target_mac, adapter=self.gateway.resolve_adapter())
        logger.debug({"event": "ble_bridge_init", "mac": self.target_mac, "adapter": self.gateway.resolve_adapter()})

    def connect_bb8(self):
        logger.debug({"event": "connect_bb8_start", "timeout": self.timeout})
        try:
            device = self.gateway.scan_for_device(timeout=self.timeout)
            logger.debug({"event": "connect_bb8_scan_result", "device": str(device)})
            if not device:
                msg = "BB-8 not found. Please tap robot or remove from charger and try again."
                publish_bb8_error(msg)
                logger.error({"event": "connect_bb8_not_found", "msg": msg})
                return None
            if self.controller is not None:
                logger.debug({"event": "connect_bb8_attach_device", "controller": str(type(self.controller)), "device": str(device)})
                self.controller.attach_device(device)
            else:
                logger.error({"event": "connect_bb8_controller_none"})
                return None
            if not hasattr(device, 'services') or not any(
                '22bb746f-2bbd-7554-2d6f-726568705327' in str(s) for s in getattr(device, 'services', [])):
                msg = "BB-8 not awake. Please tap robot or remove from charger and try again."
                publish_bb8_error(msg)
                logger.error({"event": "connect_bb8_not_awake", "msg": msg, "device": str(device)})
                raise BleakCharacteristicNotFoundError('22bb746f-2bbd-7554-2d6f-726568705327')
            logger.info({"event": "connect_bb8_success", "device": str(device)})
            return device
        except BleakCharacteristicNotFoundError:
            logger.error({"event": "connect_bb8_characteristic_not_found"})
            return None
        except Exception as e:
            publish_bb8_error(str(e))
            logger.error({"event": "connect_bb8_exception", "error": str(e)})
            return None

    def connect(self):
        logger.debug({"event": "connect_start", "timeout": self.timeout})
        device = self.gateway.scan_for_device(timeout=self.timeout)
        logger.debug({"event": "connect_scan_result", "device": str(device)})
        if not device:
            logger.error({"event": "connect_no_device_found"})
            return None
        if self.controller is not None:
            logger.debug({"event": "connect_attach_device", "controller": str(type(self.controller)), "device": str(device)})
            self.controller.attach_device(device)
        else:
            logger.error({"event": "connect_controller_none"})
            return None
        logger.info({"event": "connect_success", "device": str(device)})
        return device

    def diagnostics(self):
        logger.debug({"event": "diagnostics_start"})
        if self.controller is not None:
            diag = self.controller.get_diagnostics_for_mqtt()
            logger.debug({"event": "diagnostics_result", "diagnostics": diag})
            return diag
        else:
            logger.error({"event": "diagnostics_controller_none"})
            return {"error": "controller is None"}

    def shutdown(self):
        logger.debug({"event": "shutdown_start"})
        self.gateway.shutdown()
        if self.controller is not None:
            logger.debug({"event": "shutdown_controller_disconnect"})
            self.controller.disconnect()
        else:
            logger.warning({"event": "shutdown_controller_none"})

    # Example guard wherever controller is used later:
    def _with_controller(self, fn_name: str, *args, **kwargs):
        ctrl = self.controller
        if not ctrl:
            logger.debug({"event": "controller_missing", "fn": fn_name})
            return None
        fn = getattr(ctrl, fn_name, None)
        if not callable(fn):
            logger.debug({"event": "controller_attr_missing", "fn": fn_name})
            return None
        return fn(*args, **kwargs)

def bb8_find(timeout=10):
    logger.info("[BB-8] Scanning for BB-8...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        for toy in find_toys():
            if isinstance(toy, BB8):
                logger.info(f"[BB-8] Found BB-8 at {toy}")
                return BB8(toy, adapter_cls=BleakAdapter)
        time.sleep(1)
    logger.info("[BB-8] BB-8 not found after scan.")
    return None

def bb8_power_on_sequence(core_or_facade, *args, **kwargs):
    cm = getattr(core_or_facade, "__enter__", None)
    if callable(cm):
        with core_or_facade:
            return _power_on_sequence_body(core_or_facade, *args, **kwargs)
    else:
        logger.debug({"event": "power_on_no_context_manager"})
        core_or_facade.connect()
        try:
            return _power_on_sequence_body(core_or_facade, *args, **kwargs)
        finally:
            core_or_facade.disconnect()

def _power_on_sequence_body(bb8):
    # Defensive: check connection status if available
    is_connected = getattr(bb8, 'is_connected', lambda: None)
    if callable(is_connected):
        connected = is_connected()
    else:
        connected = is_connected
    logger.info(f"[BB-8] is_connected: {connected}")
    if connected is not None and not connected:
        logger.error("[BB-8] Not connected after context manager entry.")
        return
    # Timed LED command
    led_start = time.time()
    try:
        if hasattr(bb8, 'set_main_led'):
            bb8.set_main_led(255, 255, 255, None)
            logger.info(f"[BB-8] LED command succeeded in {time.time() - led_start:.2f}s")
        else:
            logger.warning("[BB-8] Device does not support set_main_led.")
    except Exception as e:
        logger.error(f"[BB-8][ERROR] LED command failed after {time.time() - led_start:.2f}s: {e}", exc_info=True)
        logger.info(f"[BB-8] Status after LED error: is_connected={getattr(bb8, 'is_connected', None)}")
        return
    roll_start = time.time()
    try:
        if hasattr(bb8, 'roll'):
            bb8.roll(30, 0, 1000)  # speed, heading, duration_ms
            logger.info(f"[BB-8] Roll command succeeded in {time.time() - roll_start:.2f}s")
        else:
            logger.warning("[BB-8] Device does not support roll.")
    except Exception as e:
        logger.error(f"[BB-8][ERROR] Roll command failed after {time.time() - roll_start:.2f}s: {e}", exc_info=True)
        logger.info(f"[BB-8] Status after roll error: is_connected={getattr(bb8, 'is_connected', None)}")
        return

def bb8_power_off_sequence():
    logger.info("[BB-8] Power OFF sequence: beginning...")
    try:
        bb8 = bb8_find()
        logger.info(f"[BB-8] After bb8_find(): {bb8}")
        if not bb8:
            logger.error("[BB-8] Power off failed: device not found.")
            return
        logger.info("[BB-8] After BB-8 connect...")
        with bb8:
            is_connected = getattr(bb8, 'is_connected', lambda: None)
            if callable(is_connected):
                connected = is_connected()
            else:
                connected = is_connected
            logger.info(f"[BB-8] is_connected: {connected}")
            if connected is not None and not connected:
                logger.error("[BB-8] Not connected after context manager entry.")
                return
            led_start = time.time()
            try:
                bb8.set_main_led(0, 100, 255, None)
                logger.info(f"[BB-8] LED command succeeded in {time.time() - led_start:.2f}s")
            except Exception as e:
                logger.error(f"[BB-8][ERROR] LED command failed after {time.time() - led_start:.2f}s: {e}", exc_info=True)
                logger.info(f"[BB-8] Status after LED error: is_connected={getattr(bb8, 'is_connected', None)}")
                return
            for i in reversed(range(0, 101, 20)):
                fade_start = time.time()
                try:
                    logger.info(f"[BB-8] Setting LED: (0, {i}, {int(2.55 * i)})")
                    bb8.set_main_led(0, i, int(2.55 * i), None)
                    logger.info(f"[BB-8] LED fade step succeeded in {time.time() - fade_start:.2f}s")
                except Exception as e:
                    logger.error(f"[BB-8][ERROR] LED fade step failed after {time.time() - fade_start:.2f}s: {e}", exc_info=True)
                    logger.info(f"[BB-8] Status after fade error: is_connected={getattr(bb8, 'is_connected', None)}")
                    return
                time.sleep(0.15)
            off_start = time.time()
            try:
                bb8.set_main_led(0, 0, 0, None)
                logger.info(f"[BB-8] After LED off in {time.time() - off_start:.2f}s")
            except Exception as e:
                logger.error(f"[BB-8][ERROR] LED off command failed after {time.time() - off_start:.2f}s: {e}", exc_info=True)
                logger.info(f"[BB-8] Status after LED off error: is_connected={getattr(bb8, 'is_connected', None)}")
                return
            sleep_start = time.time()
            try:
                bb8.sleep(IntervalOptions(IntervalOptions.NONE), 0, 0, None)  # type: ignore
                logger.info(f"[BB-8] After sleep in {time.time() - sleep_start:.2f}s")
            except Exception as e:
                logger.error(f"[BB-8][ERROR] Sleep command failed after {time.time() - sleep_start:.2f}s: {e}", exc_info=True)
                logger.info(f"[BB-8] Status after sleep error: is_connected={getattr(bb8, 'is_connected', None)}")
                return
        logger.info("[BB-8] Power OFF sequence: complete.")
    except Exception as e:
        logger.error(f"[BB-8][ERROR] Exception in power OFF sequence: {e}", exc_info=True)

def publish_bb8_error(msg):
    try:
        broker = CFG.get("MQTT_HOST", "localhost")
        topic_prefix = CFG.get("MQTT_BASE", "bb8")
        publish.single(f"{topic_prefix}/state/error", msg, hostname=broker)
    except Exception as e:
        logger.error(f"[BB-8][ERROR] Failed to publish error to MQTT: {e}")

def ble_command_with_retry(cmd_func, max_attempts=4, initial_cooldown=3, *args, **kwargs):
    cooldown = initial_cooldown
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"[BB-8] Attempt {attempt}/{max_attempts} for {cmd_func.__name__}")
            result = cmd_func(*args, **kwargs)
            logger.info(f"[BB-8] {cmd_func.__name__} succeeded on attempt {attempt}")
            return result
        except Exception as e:
            logger.error(f"[BB-8][ERROR] {cmd_func.__name__} failed on attempt {attempt}: {e}", exc_info=True)
            publish_bb8_error(str(e))
            if attempt < max_attempts:
                logger.info(f"[BB-8] Waiting {cooldown}s before retry...")
                time.sleep(cooldown)
                cooldown *= 2
            else:
                logger.critical(f"[BB-8] {cmd_func.__name__} failed after {max_attempts} attempts.")
                publish_bb8_error(f"{cmd_func.__name__} failed after {max_attempts} attempts: {e}")
    return None

def publish_discovery(topic, payload):
    try:
        broker = CFG.get("MQTT_HOST", "localhost")
        publish.single(topic, json.dumps(payload), hostname=broker)
    except Exception as e:
        logger.error(f"[BB-8][ERROR] Failed to publish discovery to MQTT: {e}")

async def connect_bb8_with_retry(address, max_attempts=5, retry_delay=3, adapter='hci0'):
    for attempt in range(1, max_attempts + 1):
        try:
            async with BleakClient(address, adapter=adapter) as client:
                try:
                    services = client.services  # Bleak >=0.20
                except AttributeError:
                    services = await resolve_services(client)
                    if services is None:
                        logger.debug("BLE services not available on this client/version")
                        return None
                found = any(
                    c.uuid.lower() == "22bb746f-2bbd-7554-2d6f-726568705327"
                    for s in services for c in s.characteristics
                )
                if found:
                    return client
                else:
                    raise Exception("Sphero control characteristic not found.")
        except Exception as e:
            logger.error(f"Connect attempt {attempt}/{max_attempts} failed: {e}")
            await asyncio.sleep(retry_delay)
    logger.error("Failed to connect to BB-8 after retries.")
    return None

def register_bb8_entities(bb8_mac):
    base_device = {
        "identifiers": [f"{CFG.get('MQTT_BASE', 'bb8')}_{bb8_mac.replace(':','')}"] ,
        "name": BB8_NAME,
        "model": BB8_NAME,
        "manufacturer": "Sphero"
    }
    ha_disc = CFG.get("HA_DISCOVERY_TOPIC", "homeassistant")
    topic_prefix = CFG.get("MQTT_BASE", "bb8")
    publish_discovery(
        f"{ha_disc}/switch/{topic_prefix}_power/config",
        {
            "name": f"{BB8_NAME} Power",
            "unique_id": f"{topic_prefix}_power_switch",
            "command_topic": f"{topic_prefix}/command/power",
            "state_topic": f"{topic_prefix}/state/power",
            "payload_on": "ON",
            "payload_off": "OFF",
            "device": base_device,
        }
    )
    publish_discovery(
        f"{ha_disc}/light/{topic_prefix}_led/config",
        {
            "name": f"{BB8_NAME} LED",
            "unique_id": f"{topic_prefix}_led",
            "command_topic": f"{topic_prefix}/command",
            "schema": "json",
            "rgb_command_template": "{{ {'command': 'set_led', 'r': red, 'g': green, 'b': blue} | tojson }}",
            "device": base_device,
        }
    )
    publish_discovery(
        f"{ha_disc}/button/{topic_prefix}_roll/config",
        {
            "name": f"{BB8_NAME} Roll",
            "unique_id": f"{topic_prefix}_roll",
            "command_topic": f"{topic_prefix}/command",
            "payload_press": '{"command": "roll", "heading": 0, "speed": 50}',
            "device": base_device,
        }
    )
    publish_discovery(
        f"{ha_disc}/button/{topic_prefix}_stop/config",
        {
            "name": f"{BB8_NAME} Stop",
            "unique_id": f"{topic_prefix}_stop",
            "command_topic": f"{topic_prefix}/command",
            "payload_press": '{"command": "stop"}',
            "device": base_device,
        }
    )
    publish_discovery(
        f"{ha_disc}/sensor/{topic_prefix}_heartbeat/config",
        {
            "name": f"{BB8_NAME} Heartbeat",
            "unique_id": f"{topic_prefix}_heartbeat",
            "state_topic": f"{topic_prefix}/state/heartbeat",
            "device": base_device,
        }
    )
    publish_discovery(
        f"{ha_disc}/sensor/{topic_prefix}_error/config",
        {
            "name": f"{BB8_NAME} Error State",
            "unique_id": f"{topic_prefix}_error",
            "state_topic": f"{topic_prefix}/state/error",
            "device": base_device,
        }
    )
    # MQTT Discovery for presence
    publish_discovery(
        f"{ha_disc}/binary_sensor/{topic_prefix}_presence/config",
        {
            "name": f"{BB8_NAME} Presence",
            "unique_id": f"{topic_prefix}_presence_001",
            "state_topic": f"{topic_prefix}/sensor/presence",
            "payload_on": "on",
            "payload_off": "off",
            "device_class": "connectivity",
            "device": base_device,
        }
    )
    # MQTT Discovery for RSSI
    publish_discovery(
        f"{ha_disc}/sensor/{topic_prefix}_rssi/config",
        {
            "name": f"{BB8_NAME} RSSI",
            "unique_id": f"{topic_prefix}_rssi_001",
            "state_topic": f"{topic_prefix}/sensor/rssi",
            "unit_of_measurement": "dBm",
            "device": base_device,
        }
    )
# [2025-08-08 xx:xx] Copilot patch: BLE Watchdog, Core Entity Surfacing, and Dynamic Discovery
# implemented for enhanced customization of  BB-8 control.
