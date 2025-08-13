"""
bb8_presence_scanner.py
Daemon: Periodically scans for BB-8 (Sphero) and publishes presence/RSSI to MQTT.
Implements Home Assistant MQTT Discovery, explicit birth/LWT, and a rich device block.
"""

def publish_extended_discovery(client, base, device_id, device_block):
    """
    Publish extended Home Assistant discovery configs for LED, sleep, drive, heading, speed.
    Topics and payloads match those in discovery_publish.py for compatibility.
    """
    avail = {
        "availability_topic": "bb8/status",
        "payload_available": "online",
        "payload_not_available": "offline",
    }
    # All extended entities now use flat namespace topics (bb8/led, bb8/speed, etc.)

    # LED (light)
    # Clear old config (if structure changed)
    old_led_config = f"homeassistant/light/bb8_{device_id}_led/config"
    client.publish(old_led_config, payload="", qos=1, retain=True)
    led = {
        "name": "BB-8 LED",
        "unique_id": f"bb8_{device_id}_led",
        "schema": "json",
        "supported_color_modes": ["rgb", "brightness"],
        "command_topic": f"{base}/led/set",
        "state_topic": f"{base}/led/state",
        "optimistic": False,
        **avail,
        "device": device_block,
    }
    client.publish(old_led_config, json.dumps(led), qos=1, retain=True)

    # Sleep button (no state_topic in discovery)
    sleep = {
        "name": "BB-8 Sleep",
        "unique_id": f"bb8_{device_id}_sleep",
        "command_topic": f"{base}/stop/press",
        **avail,
        "entity_category": "config",
        "device": device_block,
    }
    client.publish(f"homeassistant/button/bb8_{device_id}_sleep/config", json.dumps(sleep), qos=1, retain=True)

    # Drive button (no state_topic in discovery)
    drive = {
        "name": "BB-8 Drive",
        "unique_id": f"bb8_{device_id}_drive",
        "command_topic": f"{base}/drive/set",
        **avail,
        "device": device_block,
    }
    client.publish(f"homeassistant/button/bb8_{device_id}_drive/config", json.dumps(drive), qos=1, retain=True)

    # Heading number
    heading = {
        "name": "BB-8 Heading",
        "unique_id": f"bb8_{device_id}_heading",
        "command_topic": f"{base}/heading/set",
        "state_topic": f"{base}/heading/state",
        **avail,
        "min": 0, "max": 359, "step": 1, "mode": "slider",
        "device": device_block,
    }
    client.publish(f"homeassistant/number/bb8_{device_id}_heading/config", json.dumps(heading), qos=1, retain=True)

    # Speed number
    speed = {
        "name": "BB-8 Speed",
        "unique_id": f"bb8_{device_id}_speed",
        "command_topic": f"{base}/speed/set",
        "state_topic": f"{base}/speed/state",
        **avail,
        "min": 0, "max": 255, "step": 1, "mode": "slider",
        "device": device_block,
    }
    client.publish(f"homeassistant/number/bb8_{device_id}_speed/config", json.dumps(speed), qos=1, retain=True)

    logger.info("Published extended HA discovery for device_id=%s", device_id)
# Step 2: Device Identity Helpers
def make_device_id(mac: str) -> str:
    """
    Normalize MAC to lowercase hex without colons (e.g., 'AA:BB:CC:DD:EE:FF' -> 'aabbccddeeff').
    """
    return (mac or '').replace(':', '').lower()

def make_base(device_id: str) -> str:
    return f"bb8/{device_id}"



import argparse
import asyncio
import json
import logging
import os
import time
import threading
from pathlib import Path

import yaml
from bleak import BleakScanner
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from .addon_config import load_config, log_config
logger = logging.getLogger("bb8_presence_scanner")



# --- Effective configuration --------------------------------------------------
CFG, SRC = load_config()
MQTT_BASE = CFG.get("MQTT_BASE", "bb8")
BB8_NAME  = CFG.get("BB8_NAME", "BB-8")
DISCOVERY_RETAIN    = CFG.get("DISCOVERY_RETAIN", False)
EXTENDED_DISCOVERY  = os.environ.get("EXTENDED_DISCOVERY", "1") not in ("0", "false", "no", "off")
EXTENDED_COMMANDS   = os.environ.get("EXTENDED_COMMANDS", "1") not in ("0", "false", "no", "off")
REQUIRE_DEVICE_ECHO = os.environ.get("REQUIRE_DEVICE_ECHO", "1") not in ("0", "false", "no", "off")
HA_DISCOVERY_TOPIC = CFG.get("HA_DISCOVERY_TOPIC", "homeassistant")
log_config(CFG, SRC, logger)

# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

parser = argparse.ArgumentParser(description="BB-8 BLE presence scanner and MQTT publisher")
parser.add_argument("--bb8_name", default=CFG.get("BB8_NAME", "BB-8"), help="BB-8 BLE name")
parser.add_argument("--scan_interval", type=int, default=int(CFG.get("BB8_SCAN_INTERVAL", 10)), help="Scan interval in seconds")
parser.add_argument("--mqtt_host", default=CFG.get("MQTT_HOST", "localhost"), help="MQTT broker host")
parser.add_argument("--mqtt_port", type=int, default=int(CFG.get("MQTT_PORT", 1883)), help="MQTT broker port")
parser.add_argument("--mqtt_user", default=CFG.get("MQTT_USERNAME", None), help="MQTT username")
parser.add_argument("--mqtt_password", default=CFG.get("MQTT_PASSWORD", None), help="MQTT password")
parser.add_argument("--print", action="store_true", help="Print discovery payloads and exit")
parser.add_argument("--once", action="store_true", help="Run one scan cycle and exit")
parser.add_argument("--json", action="store_true", help="Emit JSON on one-shot runs")
parser.add_argument("--verbose", "-v", action="store_true", help="Verbose not-found ticks")
parser.add_argument("--quiet", "-q", action="store_true", help="No periodic tick output")

# CLI toggles for extended entities are now ignored; use EXTENDED_DISCOVERY env var only

args = parser.parse_args()


# EXTENDED_ENABLED: single toggle, default off, controlled by EXTENDED_DISCOVERY env var
EXTENDED_ENABLED = os.environ.get("EXTENDED_DISCOVERY", "0") not in ("0", "false", "no", "off")

BB8_NAME = args.bb8_name
SCAN_INTERVAL = int(args.scan_interval)
MQTT_HOST = args.mqtt_host
MQTT_PORT = int(args.mqtt_port)
MQTT_USERNAME = args.mqtt_user
MQTT_PASSWORD = args.mqtt_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bb8_presence_scanner")

# ──────────────────────────────────────────────────────────────────────────────
# Optional bridge (BB8Facade) adapter
# ──────────────────────────────────────────────────────────────────────────────

class _NullBridge:
    """Safe no-op bridge so the scanner runs even if the real bridge is absent."""
    def connect(self): pass
    def sleep(self, after_ms=None): pass
    def stop(self): pass
    def set_led_off(self): pass
    def set_led_rgb(self, r:int, g:int, b:int): pass
    def set_heading(self, deg:int): pass
    def set_speed(self, v:int): pass
    def drive(self): pass
    def is_connected(self) -> bool: return False
    def get_rssi(self) -> int: return 0

class _NullFacade:
    """Safe no-op facade for when bridge is missing."""
    def power(self, on: bool): pass
    def stop(self): pass
    def set_led_off(self): pass
    def set_led_rgb(self, r, g, b): pass
    def set_heading(self, deg): pass
    def set_speed(self, v): pass
    def drive(self): pass
    def is_connected(self): return False
    def get_rssi(self): return 0



def _load_facade():
    try:
        from bb8_core.ble_bridge import BLEBridge
        from bb8_core.facade import BB8Facade
        # BLEBridge requires a gateway argument; pass None for scanner-only use
        bridge = BLEBridge(gateway=None)
        # Optionally: pass config/env to BLEBridge if needed
        # Patch facade to add set_heading, set_speed, drive if missing
        class PatchedFacade(BB8Facade):
            def set_heading(self, deg):
                return getattr(self.bridge, "set_heading", lambda d: None)(deg)
            def set_speed(self, v):
                return getattr(self.bridge, "set_speed", lambda s: None)(v)
            def drive(self):
                # Use last known heading/speed or defaults
                h = getattr(self, "_last_heading", 0)
                s = getattr(self, "_last_speed", 100)
                return getattr(self.bridge, "drive", lambda h,s: None)(h, s)
        return PatchedFacade(bridge)
    except Exception as e:
        logger.info("BB8Facade not available (%s). Commands will be no-ops.", e)
        return _NullFacade()

FACADE = _load_facade()

# -----------------------------------------------------------------------------
# MQTT client with birth/LWT
# -----------------------------------------------------------------------------


AVAIL_TOPIC = f"{MQTT_BASE}/status"
AVAIL_ON = CFG.get("AVAIL_ON", "online")
AVAIL_OFF = CFG.get("AVAIL_OFF", "offline")

# Use Paho v2 callback API to avoid deprecation warnings
mqtt_client = mqtt.Client(
    client_id=CFG.get("MQTT_CLIENT_ID", "bb8_presence_scanner"),
    protocol=mqtt.MQTTv311,
    callback_api_version=CallbackAPIVersion.VERSION2,
)
if MQTT_USERNAME and MQTT_PASSWORD:
    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
mqtt_client.will_set(AVAIL_TOPIC, payload=AVAIL_OFF, qos=1, retain=True)

# ──────────────────────────────────────────────────────────────────────────────


# Legacy command topics
CMD_POWER_SET   = f"{MQTT_BASE}/cmd/power_set"      # payload: "ON"|"OFF"
CMD_STOP_PRESS  = f"{MQTT_BASE}/cmd/stop_press"     # payload: anything
CMD_LED_SET     = f"{MQTT_BASE}/cmd/led_set"        # payload: {{"r":..,"g":..,"b":..}} | {{"hex":"#RRGGBB"}} | "OFF"
CMD_HEADING_SET = f"{MQTT_BASE}/cmd/heading_set"    # payload: number 0..359
CMD_SPEED_SET   = f"{MQTT_BASE}/cmd/speed_set"      # payload: number 0..255
CMD_DRIVE_PRESS = f"{MQTT_BASE}/cmd/drive_press"    # payload: anything

# Flat command topics (advertised by discovery)
FLAT_POWER_SET   = f"{MQTT_BASE}/power/set"
FLAT_LED_SET     = f"{MQTT_BASE}/led/set"
FLAT_STOP_PRESS  = f"{MQTT_BASE}/stop/press"
FLAT_DRIVE_SET   = f"{MQTT_BASE}/drive/set"
FLAT_HEADING_SET = f"{MQTT_BASE}/heading/set"
FLAT_SPEED_SET   = f"{MQTT_BASE}/speed/set"

# Flat state topics (advertised by discovery)
FLAT_LED_STATE     = f"{MQTT_BASE}/led/state"
FLAT_STOP_STATE    = f"{MQTT_BASE}/stop/state"
FLAT_HEADING_STATE = f"{MQTT_BASE}/heading/state"
FLAT_SPEED_STATE   = f"{MQTT_BASE}/speed/state"

# Legacy mirrors (optional; keep for compatibility until deprecation)
LEGACY_LED_STATE     = f"{MQTT_BASE}/state/led"
LEGACY_STOP_STATE    = f"{MQTT_BASE}/state/stop"
LEGACY_HEADING_STATE = f"{MQTT_BASE}/state/heading"
LEGACY_SPEED_STATE   = f"{MQTT_BASE}/state/speed"



def _on_connect(client, userdata, flags, rc, properties=None):
    client.publish(AVAIL_TOPIC, payload=AVAIL_ON, qos=1, retain=True)
    # Subscribe to both legacy and flat command topics for actuator control
    client.subscribe([
        # legacy
        (CMD_POWER_SET, 1),
        (CMD_STOP_PRESS, 1),
        (CMD_LED_SET, 1),
        (CMD_HEADING_SET, 1),
        (CMD_SPEED_SET, 1),
        (CMD_DRIVE_PRESS, 1),
        # flat (advertised by discovery)
        (FLAT_POWER_SET, 1),
        (FLAT_LED_SET, 1),
        (FLAT_STOP_PRESS, 1),
        (FLAT_DRIVE_SET, 1),
        (FLAT_HEADING_SET, 1),
        (FLAT_SPEED_SET, 1),
    ])
    # Route both sets to the same callbacks
    client.message_callback_add(CMD_POWER_SET,   _cb_power_set)
    client.message_callback_add(CMD_STOP_PRESS,  _cb_stop_press)
    client.message_callback_add(CMD_LED_SET,     _cb_led_set)
    client.message_callback_add(CMD_HEADING_SET, _cb_heading_set)
    client.message_callback_add(CMD_SPEED_SET,   _cb_speed_set)
    client.message_callback_add(CMD_DRIVE_PRESS, _cb_drive_press)
    # Flat topics
    client.message_callback_add(FLAT_POWER_SET,   _cb_power_set)
    client.message_callback_add(FLAT_LED_SET,     _cb_led_set)
    client.message_callback_add(FLAT_STOP_PRESS,  _cb_stop_press)
    client.message_callback_add(FLAT_DRIVE_SET,   _cb_drive_press)
    client.message_callback_add(FLAT_HEADING_SET, _cb_heading_set)
    client.message_callback_add(FLAT_SPEED_SET,   _cb_speed_set)



# ──────────────────────────────────────────────────────────────────────────────
# Helpers for parsing and clamping command payloads
# ──────────────────────────────────────────────────────────────────────────────
def _clamp(val: int, lo: int, hi: int) -> int:
    try:
        v = int(val)
    except Exception:
        return lo
    return max(lo, min(hi, v))

def _parse_led_payload(raw: bytes | str):
    """Accepts:
       - JSON dict {"color":{"r":..,"g":..,"b":..}}  (HA JSON light)
       - JSON dict {"r":..,"g":..,"b":..}            (legacy)
       - JSON dict {"hex":"#RRGGBB"}
       - String "OFF"
    """
    try:
        if isinstance(raw, memoryview):
            raw = raw.tobytes()
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8", "ignore")
        s = str(raw).strip()
        if s.upper() == "OFF":
            return ("OFF", None)

        obj = json.loads(s)
        if isinstance(obj, dict):
            # HA JSON schema: {"color":{"r":..,"g":..,"b":..}}
            if "color" in obj and isinstance(obj["color"], dict):
                c = obj["color"]
                if all(k in c for k in ("r","g","b")):
                    r = _clamp(c["r"],0,255); g = _clamp(c["g"],0,255); b = _clamp(c["b"],0,255)
                    return ("RGB", (r,g,b))

            # Legacy direct {r,g,b}
            if all(k in obj for k in ("r","g","b")):
                r = _clamp(obj["r"],0,255); g = _clamp(obj["g"],0,255); b = _clamp(obj["b"],0,255)
                return ("RGB", (r,g,b))

            # Hex form
            if "hex" in obj and isinstance(obj["hex"], str):
                hx = obj["hex"].lstrip("#")
                if len(hx) == 6:
                    r = int(hx[0:2],16); g = int(hx[2:4],16); b = int(hx[4:6],16)
                    return ("RGB", (r,g,b))
    except Exception:
        pass
    return ("INVALID", None)

# ──────────────────────────────────────────────────────────────────────────────
# MQTT command callbacks → bridge methods + state echoes
# ──────────────────────────────────────────────────────────────────────────────
def _cb_power_set(client, userdata, msg):
    payload = msg.payload
    if isinstance(payload, memoryview):
        payload = payload.tobytes()
    payload = (payload or b"").decode("utf-8", "ignore").strip().upper()
    if payload == "ON":
        try: FACADE.power(True)
        except Exception as e: logger.warning("facade.power(True) failed: %s", e)
        client.publish(f"{MQTT_BASE}/power/state", "ON", qos=1, retain=True)
    elif payload == "OFF":
        try: FACADE.power(False)
        except Exception as e: logger.warning("facade.power(False) failed: %s", e)
        client.publish(f"{MQTT_BASE}/power/state", "OFF", qos=1, retain=True)
    else:
        logger.warning("power_set invalid payload: %r", payload)

def _cb_stop_press(client, userdata, msg):
    try: FACADE.stop()
    except Exception as e: logger.warning("facade.stop() failed: %s", e)
    client.publish(FLAT_STOP_STATE, "pressed", qos=1, retain=False)
    client.publish(LEGACY_STOP_STATE, "pressed", qos=1, retain=False)
    threading.Timer(0.5, lambda: (
        client.publish(FLAT_STOP_STATE, "idle", qos=1, retain=False),
        client.publish(LEGACY_STOP_STATE, "idle", qos=1, retain=False)
    )).start()

def _cb_led_set(client, userdata, msg):
    raw = msg.payload.decode("utf-8", "ignore").strip() if msg.payload else ""
    state = {"state": "OFF"}
    try:
        d = json.loads(raw) if raw else {}
        # Accept HA-native: {"state":"ON","color":{"r":..,"g":..,"b":..},"brightness":...}
        if isinstance(d, dict) and d.get("state", "").upper() == "ON":
            col = d.get("color") or {}
            r, g, b = int(col.get("r", 0)), int(col.get("g", 0)), int(col.get("b", 0))
            brightness = int(d.get("brightness", 255))
            state = {"state": "ON", "color": {"r": r, "g": g, "b": b}, "color_mode": "rgb", "brightness": brightness}
            try: FACADE.set_led_rgb(r, g, b)
            except Exception as e: logger.warning("facade.set_led_rgb() failed: %s", e)
        # Accept legacy shapes too:
        elif "hex" in d:
            hx = d["hex"].lstrip("#")
            r, g, b = int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)
            brightness = int(d.get("brightness", 255))
            state = {"state": "ON", "color": {"r": r, "g": g, "b": b}, "color_mode": "rgb", "brightness": brightness}
            try: FACADE.set_led_rgb(r, g, b)
            except Exception as e: logger.warning("facade.set_led_rgb() failed: %s", e)
        elif {"r", "g", "b"}.issubset(d.keys()):
            r, g, b = int(d["r"]), int(d["g"]), int(d["b"])
            brightness = int(d.get("brightness", 255))
            state = {"state": "ON", "color": {"r": r, "g": g, "b": b}, "color_mode": "rgb", "brightness": brightness}
            try: FACADE.set_led_rgb(r, g, b)
            except Exception as e: logger.warning("facade.set_led_rgb() failed: %s", e)
        elif raw.upper() == "OFF":
            try: FACADE.set_led_off()
            except Exception as e: logger.warning("facade.set_led_off() failed: %s", e)
            state = {"state": "OFF"}
        else:
            return  # ignore unrecognized payload
    except Exception:
        if raw.upper() != "OFF":
            return
        try: FACADE.set_led_off()
        except Exception as e: logger.warning("facade.set_led_off() failed: %s", e)
        state = {"state": "OFF"}
    client.publish(FLAT_LED_STATE, json.dumps(state), qos=1, retain=True)
    client.publish(LEGACY_LED_STATE, json.dumps(state), qos=1, retain=True)

def _cb_heading_set(client, userdata, msg):
    payload = msg.payload
    if isinstance(payload, memoryview):
        payload = payload.tobytes()
    try:
        payload = (payload or b"").decode("utf-8","ignore").strip()
        deg = _clamp(int(float(payload)), 0, 359)
    except Exception:
        logger.warning("heading_set invalid payload: %r", msg.payload)
        return
    try: FACADE.set_heading(deg)
    except Exception as e: logger.warning("facade.set_heading(%s) failed: %s", deg, e)
    client.publish(FLAT_HEADING_STATE, str(deg), qos=1, retain=True)
    client.publish(LEGACY_HEADING_STATE, str(deg), qos=1, retain=True)

def _cb_speed_set(client, userdata, msg):
    payload = msg.payload
    if isinstance(payload, memoryview):
        payload = payload.tobytes()
    try:
        payload = (payload or b"").decode("utf-8","ignore").strip()
        spd = _clamp(int(float(payload)), 0, 255)
    except Exception:
        logger.warning("speed_set invalid payload: %r", msg.payload)
        return
    try: FACADE.set_speed(spd)
    except Exception as e: logger.warning("facade.set_speed(%s) failed: %s", spd, e)
    client.publish(FLAT_SPEED_STATE, str(spd), qos=1, retain=True)
    client.publish(LEGACY_SPEED_STATE, str(spd), qos=1, retain=True)

def _cb_drive_press(client, userdata, msg):
    try: FACADE.drive()
    except Exception as e: logger.warning("facade.drive() failed: %s", e)
    client.publish(FLAT_STOP_STATE, "pressed", qos=1, retain=False)
    client.publish(LEGACY_STOP_STATE, "pressed", qos=1, retain=False)
    threading.Timer(0.4, lambda: (
        client.publish(FLAT_STOP_STATE, "idle", qos=1, retain=False),
        client.publish(LEGACY_STOP_STATE, "idle", qos=1, retain=False)
    )).start()

mqtt_client.on_connect = _on_connect

def _connect_mqtt():
    mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    mqtt_client.loop_start()

# -----------------------------------------------------------------------------
# BLE helpers
# -----------------------------------------------------------------------------

def _extract_mac_and_dbus(device):
    """
    Return (MAC, D-Bus object path) from a Bleak BLEDevice, when possible.
    """
    details = getattr(device, "details", {}) or {}
    props = details.get("props", {}) or {}
    mac = (props.get("Address") or getattr(device, "address", "") or "").upper()
    if not mac and getattr(device, "address", ""):
        mac = device.address.upper()
    dbus_path = details.get("path") or (f"/org/bluez/hci0/dev_{mac.replace(':','_')}" if mac else None)
    return mac or None, dbus_path

def build_device_block(mac: str, dbus_path: str, model: str, name: str = "BB-8") -> dict:
    """
    Build a Home Assistant-compliant 'device' block for MQTT Discovery.
    """
    mac_norm = mac.upper()
    slug = "bb8-" + mac_norm.replace(":", "").lower()
    sw_version = CFG.get("ADDON_VERSION", "unknown")
    return {
        "identifiers": [
            f"ble:{mac_norm}",
            "uuid:0000fe07-0000-1000-8000-00805f9b34fb",
            f"mqtt:{slug}",
        ],
        "connections": [
            ["mac", mac_norm],
            ["dbus", dbus_path],
        ],
        "manufacturer": "Sphero",
        "model": model,
        "name": name,
        "sw_version": f"addon:{sw_version}",
    }

def publish_discovery(client: mqtt.Client, mac: str, dbus_path: str, model: str = "", name: str = ""):
    """
    Publish Home Assistant discovery for Presence and RSSI with full device block.
    """
    # TODO: Store and map device_defaults from facade_mapping_table.json to retrievable dynamic variables
    model_hint = model if model else CFG.get("BB8_NAME", "S33 BB84 LE")
    name_hint = name if name else CFG.get("BB8_NAME", "BB-8")
    base = MQTT_BASE
    device = build_device_block(mac, dbus_path, model=model_hint, name=name_hint)
    uid_suffix = mac.replace(":", "").lower()
    availability = {
        "availability_topic": AVAIL_TOPIC,
        "payload_available": AVAIL_ON,
        "payload_not_available": AVAIL_OFF,
    }
    presence_disc = {
        "name": f"{name_hint} Presence",
        "unique_id": f"bb8_presence_{uid_suffix}",
        "state_topic": f"{base}/sensor/presence",
        "payload_on": "on",
        "payload_off": "off",
        "device_class": "connectivity",
        **availability,
        "device": device,
    }
    rssi_disc = {
        "name": f"{name_hint} RSSI",
        "unique_id": f"bb8_rssi_{uid_suffix}",
        "state_topic": f"{base}/sensor/rssi",
        "unit_of_measurement": "dBm",
        "state_class": "measurement",
        "device_class": "signal_strength",
        **availability,
        "device": device,
    }
    client.publish(f"{HA_DISCOVERY_TOPIC}/binary_sensor/bb8_presence/config", json.dumps(presence_disc), qos=1, retain=True)
    client.publish(f"{HA_DISCOVERY_TOPIC}/sensor/bb8_rssi/config", json.dumps(rssi_disc), qos=1, retain=True)
    logger.info("Published HA discovery for MAC=%s", mac)

# -----------------------------------------------------------------------------
# Logging helpers
# -----------------------------------------------------------------------------

def tick_log(found: bool, name: str, addr: str | None, rssi):
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    if args.quiet:
        return
    if args.json:
        print(json.dumps({"ts": int(time.time()), "found": found, "name": name, "address": addr, "rssi": rssi}))
    else:
        if found:
            print(f"[{ts}] found name={name} addr={addr} rssi={rssi}")
        elif args.verbose:
            print(f"[{ts}] not_found name={name}")

# -----------------------------------------------------------------------------
# Main loop
# -----------------------------------------------------------------------------

async def scan_and_publish():
    """
    Scan loop: find BB-8, publish presence/RSSI (retained), publish discovery once per MAC.
    """
    published_discovery_for = None  # last MAC we advertised
    model_hint = CFG.get("BB8_NAME", "S33 BB84 LE")

    # Telemetry toggle (scanner role, unified config)
    enable_scanner_telemetry = CFG.get("ENABLE_SCANNER_TELEMETRY", True)
    src_scanner_telemetry = SRC.get("ENABLE_SCANNER_TELEMETRY", "default")
    while True:
        try:
            devices = await BleakScanner.discover()
            found = False
            rssi = None
            mac = None
            dbus_path = None

            for d in devices:
                if BB8_NAME.lower() in (d.name or "").lower():
                    found = True
                    rssi = getattr(d, "rssi", None)
                    if rssi is None:
                        rssi = ((getattr(d, "details", {}) or {}).get("props", {}) or {}).get("RSSI")
                    mac, dbus_path = _extract_mac_and_dbus(d)
                    logger.info("Found BB-8: %s [%s] RSSI: %s UUIDs: %s",
                                d.name, mac, rssi,
                                ((getattr(d, 'details', {}) or {}).get('props', {}) or {}).get('UUIDs'))
                    break

            # Publish discovery (once per MAC) after we know identifiers
            if found and mac and dbus_path and published_discovery_for != mac:
                # Minimal discovery (presence/RSSI)
                publish_discovery(mqtt_client, mac, dbus_path, model=model_hint, name="BB-8")
                # Extended discovery (if enabled)
                if EXTENDED_ENABLED:
                    device_id = make_device_id(mac)
                    base = make_base(device_id)
                    device_block = build_device_block(mac, dbus_path, model=model_hint, name="BB-8")
                    publish_extended_discovery(mqtt_client, base, device_id, device_block)
                published_discovery_for = mac

            # Telemetry (retained, only if enabled)
            if enable_scanner_telemetry:
                logger.info({
                    "event": "telemetry_start",
                    "interval_s": SCAN_INTERVAL,
                    "role": "scanner",
                    "provenance": {"ENABLE_SCANNER_TELEMETRY": src_scanner_telemetry}
                })
                mqtt_client.publish(f"{MQTT_BASE}/sensor/presence", "on" if found else "off", qos=1, retain=True)
                mqtt_client.publish(f"{MQTT_BASE}/sensor/rssi", "" if rssi is None else str(int(rssi)), qos=1, retain=True)
                logger.info({
                    "event": "telemetry_loop_started",
                    "interval_s": SCAN_INTERVAL,
                    "role": "scanner",
                    "provenance": {"ENABLE_SCANNER_TELEMETRY": src_scanner_telemetry}
                })

            tick_log(found, BB8_NAME, mac, rssi)

        except Exception as e:
            logger.error("Presence scan error: %s", e)

        await asyncio.sleep(SCAN_INTERVAL)

# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    if args.print:
        # Discovery is emitted lazily after MAC/DBus are known; nothing to print upfront
        print("# discovery will be published after a successful scan when MAC/DBus are known")
        raise SystemExit(0)

    if args.once:
        async def _once():
            devices = await BleakScanner.discover()
            res = {"found": False, "name": BB8_NAME, "address": None, "rssi": None}
            for d in devices:
                if BB8_NAME.lower() in (d.name or "").lower():
                    res = {"found": True, "name": d.name or BB8_NAME, "address": getattr(d, "address", None),
                           "rssi": getattr(d, "rssi", None)}
                    break
            if args.json:
                print(json.dumps(res))
            else:
                tick_log(res["found"], res["name"], res["address"], res["rssi"])
        asyncio.run(_once())
    else:
        _connect_mqtt()
        asyncio.run(scan_and_publish())
