from __future__ import annotations

import warnings

warnings.filterwarnings(
    "ignore", "Callback API version 1 is deprecated", DeprecationWarning, "paho"
)

import argparse
import asyncio
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Final, TypedDict

import paho.mqtt.client as mqtt
from bleak import BleakScanner
from paho.mqtt.enums import CallbackAPIVersion

from .addon_config import load_config


class RgbTD(TypedDict):
    r: int
    g: int
    b: int


def read_version_or_default() -> str:
    try:
        VERSION_FILE: Final = Path(__file__).resolve().parents[1] / "VERSION"
        txt = VERSION_FILE.read_text(encoding="utf-8").strip()
        return txt or "addon:dev"
    except Exception:
        return "addon:dev"


def _device_block(mac_upper: str) -> dict[str, Any]:
    return {
        "identifiers": ["bb8", f"mac:{mac_upper}"],
        "connections": [["mac", mac_upper]],
        "manufacturer": "Sphero",
        "model": "S33 BB84 LE",
        "name": "BB-8",
        "sw_version": read_version_or_default(),
    }


async def publish_discovery(
    mqtt, mac_upper: str, dbus_path: str | None = None, **_ignored
) -> None:
    """
    Publish Home Assistant discovery for presence & rssi.
    `mqtt` is an async bus with publish(topic, payload, retain=False, qos=0).
    """
    dev = _device_block(mac_upper)
    uid = mac_upper.lower().replace(":", "")
    pres_cfg = {
        "name": "BB-8 Presence",
        "unique_id": f"bb8_presence_{uid}",
        "uniq_id": f"bb8_presence_{uid}",
        "state_topic": "bb8/presence/state",
        "stat_t": "bb8/presence/state",
        "availability_topic": "bb8/status",
        "avty_t": "bb8/status",
        "payload_on": "online",
        "pl_on": "online",
        "payload_off": "offline",
        "pl_off": "offline",
        "device": dev,
        "dev": dev,
    }
    rssi_cfg = {
        "name": "BB-8 RSSI",
        "unique_id": f"bb8_rssi_{uid}",
        "uniq_id": f"bb8_rssi_{uid}",
        "state_topic": "bb8/rssi/state",
        "stat_t": "bb8/rssi/state",
        "availability_topic": "bb8/status",
        "avty_t": "bb8/status",
        "device_class": "signal_strength",
        "dev_cla": "signal_strength",
        "unit_of_measurement": "dBm",
        "unit_of_meas": "dBm",
        "device": dev,
        "dev": dev,
    }
    topic1 = "homeassistant/binary_sensor/bb8_presence/config"
    await mqtt.publish(
        topic1,
        json.dumps(pres_cfg, separators=(",", ":")),
        0,
        True,
    )  # pragma: no cover
    logger.info(f"discovery: published topic={topic1}")

    topic2 = "homeassistant/sensor/bb8_rssi/config"
    await mqtt.publish(
        topic2,
        json.dumps(rssi_cfg, separators=(",", ":")),
        0,
        True,
    )  # pragma: no cover
    logger.info(f"discovery: published topic={topic2}")

    # Optional LED discovery (disabled by default)
    import os

    if os.getenv("PUBLISH_LED_DISCOVERY", "0") == "1":
        led_cfg = {
            "name": "BB-8 LED",
            "unique_id": f"bb8_led_{uid}",
            "uniq_id": f"bb8_led_{uid}",
            "command_topic": "bb8/led/set",
            "state_topic": "bb8/led/state",
            "device": dev,
            "dev": dev,
            "availability_topic": "bb8/status",
            "avty_t": "bb8/status",
        }
        topic3 = "homeassistant/light/bb8_led/config"
        await mqtt.publish(
            topic3,
            json.dumps(led_cfg, separators=(",", ":")),
            0,
            True,
        )  # pragma: no cover
        logger.info(f"discovery: published topic={topic3}")


logger = logging.getLogger("bb8_presence_scanner")


def log_config(cfg: dict, src_path, logger: logging.Logger):
    lines = [
        "[DEBUG] Effective configuration:",
        f"  BB8_NAME='{cfg.get('BB8_NAME')}'",
        f"  BB8_MAC='{cfg.get('BB8_MAC')}'",
        f"  MQTT_HOST='{cfg.get('MQTT_HOST')}'",
        f"  MQTT_PORT={cfg.get('MQTT_PORT')}",
        f"  MQTT_USER='{cfg.get('MQTT_USERNAME')}'",
        f"  MQTT_PASSWORD={'***' if cfg.get('MQTT_PASSWORD') else None}",
        f"  MQTT_BASE='{cfg.get('MQTT_BASE')}'",
        f"  ENABLE_BRIDGE_TELEMETRY={cfg.get('ENABLE_BRIDGE_TELEMETRY')}",
        f"  TELEMETRY_INTERVAL_S={cfg.get('TELEMETRY_INTERVAL_S')}",
        f"  Add-on version: {cfg.get('ADDON_VERSION')}",
        f"  Config source: {src_path}",
    ]
    logger.debug("\n" + "\n".join(lines))


_scanner_dispatcher_initialized = False


def _cb_led_set(client, userdata, msg):
    raw = msg.payload.decode("utf-8", "ignore").strip() if msg.payload else ""
    state = {"state": "OFF"}
    # Refactored: Use DI/lazy import for facade
    try:
        d = json.loads(raw) if raw else {}
        if isinstance(d, dict) and d.get("state", "").upper() == "ON":
            col = d.get("color") or {}
            r = int(col.get("r", 0))
            g = int(col.get("g", 0))
            b = int(col.get("b", 0))
            brightness = int(d.get("brightness", 255))
            state = {
                "state": "ON",
                "color": {"r": r, "g": g, "b": b},
                "color_mode": "rgb",
                "brightness": brightness,
            }
            # Lazy import facade
            from .facade import BB8Facade

            BB8Facade(None).set_led_rgb(r, g, b)
        elif "hex" in d:
            hx = d["hex"].lstrip("#")
            r, g, b = int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)
            brightness = int(d.get("brightness", 255))
            state = {
                "state": "ON",
                "color": {"r": r, "g": g, "b": b},
                "color_mode": "rgb",
                "brightness": brightness,
            }
            from .facade import BB8Facade

            BB8Facade(None).set_led_rgb(r, g, b)
        elif {"r", "g", "b"}.issubset(d.keys()):
            r, g, b = int(d["r"]), int(d["g"]), int(d["b"])
            brightness = int(d.get("brightness", 255))
            state = {
                "state": "ON",
                "color": {"r": r, "g": g, "b": b},
                "color_mode": "rgb",
                "brightness": brightness,
            }
            from .facade import BB8Facade

            BB8Facade(None).set_led_rgb(r, g, b)
        elif raw.upper() == "OFF":
            from .facade import BB8Facade

            BB8Facade(None).set_led_off()
            state = {"state": "OFF"}
        else:
            return
    except Exception:
        if raw.upper() != "OFF":
            return
        from .facade import BB8Facade

        BB8Facade(None).set_led_off()
        state = {"state": "OFF"}
    client.publish(
        FLAT_LED_STATE, json.dumps(state), qos=1, retain=False
    )  # pragma: no cover
    client.publish(
        LEGACY_LED_STATE, json.dumps(state), qos=1, retain=False
    )  # pragma: no cover


def ensure_discovery_initialized() -> None:
    """
    Ensure discovery/dispatch is active exactly once from the scanner POV.
    Uses the mqtt_dispatcher singleton rather than a third-party dispatcher.
    """
    global _scanner_dispatcher_initialized
    if _scanner_dispatcher_initialized:
        return
    # Refactored: Remove direct dispatcher dependency, use DI
    _scanner_dispatcher_initialized = True


# call early during module load or main()
ensure_discovery_initialized()


def publish_extended_discovery(client, base, device_id, device_block):
    """
    Publish extended Home Assistant discovery configs for LED, sleep, drive,
    heading, speed. Topics and payloads match those in discovery_publish.py for
    compatibility.
    """
    avail = {
        "availability_topic": "bb8/status",
        "payload_available": "online",
        "payload_not_available": "offline",
    }
    # All extended entities use flat namespace topics (bb8/led, bb8/speed, etc.)

    # LED (light)
    # Clear old config (if structure changed)
    old_led_config = f"homeassistant/light/bb8_{device_id}_led/config"
    client.publish(old_led_config, payload="", qos=1, retain=False)  # pragma: no cover
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
    client.publish(
        old_led_config, json.dumps(led), qos=1, retain=True
    )  # pragma: no cover

    # Sleep button (no state_topic in discovery)
    sleep = {
        "name": "BB-8 Sleep",
        "unique_id": f"bb8_{device_id}_sleep",
        "command_topic": f"{base}/stop/press",
        **avail,
        "entity_category": "config",
        "device": device_block,
    }
    client.publish(
        f"homeassistant/button/bb8_{device_id}_sleep/config",
        json.dumps(sleep),
        qos=1,
        retain=True,
    )  # pragma: no cover

    # Drive button (no state_topic in discovery)
    drive = {
        "name": "BB-8 Drive",
        "unique_id": f"bb8_{device_id}_drive",
        "command_topic": f"{base}/drive/set",
        **avail,
        "device": device_block,
    }
    client.publish(
        f"homeassistant/button/bb8_{device_id}_drive/config",
        json.dumps(drive),
        qos=1,
        retain=True,
    )  # pragma: no cover

    # Heading number
    heading = {
        "name": "BB-8 Heading",
        "unique_id": f"bb8_{device_id}_heading",
        "command_topic": f"{base}/heading/set",
        "state_topic": f"{base}/heading/state",
        **avail,
        "min": 0,
        "max": 359,
        "step": 1,
        "mode": "slider",
        "device": device_block,
    }
    client.publish(
        f"homeassistant/number/bb8_{device_id}_heading/config",
        json.dumps(heading),
        qos=1,
        retain=True,
    )  # pragma: no cover

    # Speed number
    speed = {
        "name": "BB-8 Speed",
        "unique_id": f"bb8_{device_id}_speed",
        "command_topic": f"{base}/speed/set",
        "state_topic": f"{base}/speed/state",
        **avail,
        "min": 0,
        "max": 255,
        "step": 1,
        "mode": "slider",
        "device": device_block,
    }
    client.publish(
        f"homeassistant/number/bb8_{device_id}_speed/config",
        json.dumps(speed),
        qos=1,
        retain=True,
    )  # pragma: no cover

    logger.info("Published extended HA discovery for device_id=%s", device_id)


# Step 2: Device Identity Helpers
def make_device_id(mac: str) -> str:
    """
    Normalize MAC to lowercase hex without colons.
    Example: 'AA:BB:CC:DD:EE:FF' -> 'aabbccddeeff'.
    """
    return (mac or "").replace(":", "").lower()


def make_base(device_id: str) -> str:
    return f"bb8/{device_id}"


logger = logging.getLogger("bb8_presence_scanner")

# --- Effective configuration --------------------------------------------------
CFG, SRC_PATH = load_config()
MQTT_BASE = CFG.get("MQTT_BASE", "bb8")
BB8_NAME = CFG.get("BB8_NAME", "BB-8")
DISCOVERY_RETAIN = CFG.get("DISCOVERY_RETAIN", False)
EXTENDED_DISCOVERY = os.environ.get("EXTENDED_DISCOVERY", "1") not in (
    "0",
    "false",
    "no",
    "off",
)
EXTENDED_COMMANDS = os.environ.get("EXTENDED_COMMANDS", "1") not in (
    "0",
    "false",
    "no",
    "off",
)
REQUIRE_DEVICE_ECHO = os.environ.get("REQUIRE_DEVICE_ECHO", "1") not in (
    "0",
    "false",
    "no",
    "off",
)
HA_DISCOVERY_TOPIC = CFG.get("HA_DISCOVERY_TOPIC", "homeassistant")
log_config(CFG, SRC_PATH, logger)

# Ensure MQTT_USERNAME and MQTT_PASSWORD are always defined
MQTT_USERNAME = CFG.get("MQTT_USERNAME", None)
MQTT_PASSWORD = CFG.get("MQTT_PASSWORD", None)


def _connect_mqtt():
    mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    mqtt_client.loop_start()


# -----------------------------------------------------------------------------
# Main loop
# -----------------------------------------------------------------------------
async def scan_and_publish(client):
    """
    Scan loop: find BB-8, publish presence/RSSI (retained),
    publish discovery once per MAC.
    """
    published_discovery_for = None  # last MAC we advertised
    while True:
        try:
            devices = await BleakScanner.discover()  # pragma: no cover
            found = False
            rssi = None
            mac = None
            dbus_path = None

            for d in devices:
                if BB8_NAME.lower() in (d.name or "").lower():
                    found = True
                    rssi = getattr(d, "rssi", None)
                    if rssi is None:
                        rssi = (
                            (getattr(d, "details", {}) or {}).get("props", {}) or {}
                        ).get("RSSI")
                    mac, dbus_path = _extract_mac_and_dbus(d)
                    # Ensure dbus_path is a string
                    dbus_path = str(dbus_path) if dbus_path is not None else ""
                    logger.info(
                        "Found BB-8: %s [%s] RSSI: %s UUIDs: %s",
                        d.name,
                        mac,
                        rssi,
                        ((getattr(d, "details", {}) or {}).get("props", {}) or {}).get(
                            "UUIDs"
                        ),
                    )
                    break

            # Device block for discovery and state
            mac_upper = mac.upper() if mac else ""
            if found and mac and published_discovery_for != mac:
                # Publish discovery using new retained config
                dev = _device_block(mac_upper)
                pres_cfg = {
                    "name": "BB-8 Presence",
                    "uniq_id": f"bb8_presence_{mac_upper.lower().replace(':', '')}",
                    "stat_t": "bb8/presence/state",
                    "pl_on": "online",
                    "pl_off": "offline",
                    "avty_t": "bb8/status",
                    "dev": dev,
                }
                rssi_cfg = {
                    "name": "BB-8 RSSI",
                    "uniq_id": f"bb8_rssi_{mac_upper.lower().replace(':', '')}",
                    "stat_t": "bb8/rssi/state",
                    "dev_cla": "signal_strength",
                    "unit_of_meas": "dBm",
                    "avty_t": "bb8/status",
                    "dev": dev,
                }
                mqtt_client.publish(
                    "homeassistant/binary_sensor/bb8_presence/config",
                    json.dumps(pres_cfg, separators=(",", ":")),
                    qos=1,
                    retain=True,
                )  # pragma: no cover
                mqtt_client.publish(
                    "homeassistant/sensor/bb8_rssi/config",
                    json.dumps(rssi_cfg, separators=(",", ":")),
                    qos=1,
                    retain=True,
                )  # pragma: no cover
                published_discovery_for = mac

            # Presence/RSSI state publishing (flat topics, retain True)
            if found and mac:
                mqtt_client.publish(
                    "bb8/presence/state",
                    "online",
                    qos=1,
                    retain=True,
                )  # pragma: no cover
                if rssi is not None:
                    mqtt_client.publish(
                        "bb8/rssi/state",
                        str(rssi),
                        qos=1,
                        retain=True,
                    )  # pragma: no cover
            else:
                mqtt_client.publish(
                    "bb8/presence/state",
                    "offline",
                    qos=1,
                    retain=True,
                )  # pragma: no cover

            tick_log(found, BB8_NAME, mac, rssi)

        except Exception as e:
            logger.error("Presence scan error: %s", e)

        await asyncio.sleep(SCAN_INTERVAL)


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

parser = argparse.ArgumentParser(
    description="BB-8 BLE presence scanner and MQTT publisher"
)

if __name__ == "__main__":
    args = parser.parse_args()
    EXTENDED_ENABLED = os.environ.get("EXTENDED_DISCOVERY", "0") not in (
        "0",
        "false",
        "no",
        "off",
    )

    parser.add_argument(
        "--bb8_name", default=CFG.get("BB8_NAME", "BB-8"), help="BB-8 BLE name"
    )
    parser.add_argument(
        "--scan_interval",
        type=int,
        default=int(CFG.get("BB8_SCAN_INTERVAL", 10)),
        help="Scan interval in seconds",
    )
    parser.add_argument(
        "--mqtt_host",
        default=CFG.get("MQTT_HOST", "localhost"),
        help="MQTT broker host",
    )
    parser.add_argument(
        "--mqtt_port",
        type=int,
        default=int(CFG.get("MQTT_PORT", 1883)),
        help="MQTT broker port",
    )
    parser.add_argument(
        "--mqtt_user",
        default=CFG.get("MQTT_USERNAME", None),
        help="MQTT username",
    )
    parser.add_argument(
        "--mqtt_password",
        default=CFG.get("MQTT_PASSWORD", None),
        help="MQTT password",
    )
    parser.add_argument(
        "--print", action="store_true", help="Print discovery payloads and exit"
    )
    parser.add_argument(
        "--once", action="store_true", help="Run one scan cycle and exit"
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit JSON on one-shot runs"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose not-found ticks"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="No periodic tick output"
    )

    BB8_NAME = args.bb8_name
    SCAN_INTERVAL = int(args.scan_interval)
    MQTT_HOST = args.mqtt_host
    MQTT_PORT = int(args.mqtt_port)
    # Override MQTT_USERNAME and MQTT_PASSWORD from args if provided
    MQTT_USERNAME = args.mqtt_user
    MQTT_PASSWORD = args.mqtt_password

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("bb8_presence_scanner")

    # --------------
    # Entrypoint
    # --------------

    if __name__ == "__main__":
        # ...existing CLI setup...
        if args.print:
            # Discovery is emitted lazily after MAC/DBus are known;
            # nothing to print upfront
            print(
                "# discovery will be published after a successful scan "
                "when MAC/DBus are known"
            )
            raise SystemExit(0)

        if args.once:

            async def _once():
                devices = await BleakScanner.discover()
                res = {
                    "found": False,
                    "name": BB8_NAME,
                    "address": None,
                    "rssi": None,
                }
                for d in devices:
                    if BB8_NAME.lower() in (d.name or "").lower():
                        res = {
                            "found": True,
                            "name": d.name or BB8_NAME,
                            "address": getattr(d, "address", None),
                            "rssi": getattr(d, "rssi", None),
                        }
                        break
                if args.json:
                    print(json.dumps(res))
                else:
                    tick_log(res["found"], res["name"], res["address"], res["rssi"])

            asyncio.run(_once())
        else:
            mqtt_client = get_mqtt_client()
            setup_callbacks(mqtt_client)
            _connect_mqtt(mqtt_client)
            asyncio.run(scan_and_publish(mqtt_client))

# ──────────────────────────────────────────────────────────────────────────────
# Optional bridge (BB8Facade) adapter
# ──────────────────────────────────────────────────────────────────────────────


class _NullBridge:
    """Safe no-op bridge so the scanner runs even
    if the real bridge is absent."""

    def connect(self):
        pass

    def sleep(self, after_ms=None):
        pass

    def stop(self):
        pass

    def set_led_off(self):
        pass

    def set_led_rgb(self, r: int, g: int, b: int):
        pass

    def set_heading(self, deg: int):
        pass

    def set_speed(self, v: int):
        pass

    def drive(self):
        pass

    def is_connected(self) -> bool:
        return False

    def get_rssi(self) -> int:
        return 0


class _NullFacade:
    pass
    """Safe no-op facade for when bridge is missing."""

    def power(self, on: bool):
        pass

    def stop(self):
        pass

    def set_led_off(self):
        pass

    def set_led_rgb(self, r, g, b):
        pass

    def set_heading(self, deg):
        pass

    def set_speed(self, v):
        pass

    def drive(self):
        pass

    def is_connected(self):
        return False

    def get_rssi(self):
        return 0


def _load_facade():
    # Refactored: Use DI/lazy import for facade
    try:
        from .facade import BB8Facade

        return BB8Facade(None)
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


def get_mqtt_client():
    import warnings

    warnings.filterwarnings(
        "ignore",
        "Callback API version 1 is deprecated",
        DeprecationWarning,
        "paho.mqtt.client",
    )
    client = mqtt.Client(
        callback_api_version=CallbackAPIVersion.VERSION1,
        client_id=CFG.get("MQTT_CLIENT_ID", "bb8_presence_scanner"),
        protocol=mqtt.MQTTv311,
    )
    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.will_set(AVAIL_TOPIC, payload=AVAIL_OFF, qos=1, retain=True)
    return client


mqtt_client = None  # Initialize mqtt_client as None

# ──────────────────────────────────────────────────────────────────────────────

# Legacy command topics
CMD_POWER_SET = f"{MQTT_BASE}/cmd/power_set"  # payload: "ON"|"OFF"
CMD_STOP_PRESS = f"{MQTT_BASE}/cmd/stop_press"  # payload: anything
CMD_LED_SET = f"{MQTT_BASE}/cmd/led_set"  # payload:
#   {"r":..,"g":..,"b":..} | {"hex":"#RRGGBB"} | "OFF"
CMD_HEADING_SET = f"{MQTT_BASE}/cmd/heading_set"  # payload: number 0..359
CMD_SPEED_SET = f"{MQTT_BASE}/cmd/speed_set"  # payload: number 0..255
CMD_DRIVE_PRESS = f"{MQTT_BASE}/cmd/drive_press"  # payload: anything

# Flat command topics (advertised by discovery)
FLAT_POWER_SET = f"{MQTT_BASE}/power/set"
FLAT_LED_SET = f"{MQTT_BASE}/led/set"
FLAT_STOP_PRESS = f"{MQTT_BASE}/stop/press"
FLAT_DRIVE_SET = f"{MQTT_BASE}/drive/set"
FLAT_HEADING_SET = f"{MQTT_BASE}/heading/set"
FLAT_SPEED_SET = f"{MQTT_BASE}/speed/set"

# Flat state topics (advertised by discovery)
FLAT_LED_STATE = f"{MQTT_BASE}/led/state"
FLAT_STOP_STATE = f"{MQTT_BASE}/stop/state"
FLAT_HEADING_STATE = f"{MQTT_BASE}/heading/state"
FLAT_SPEED_STATE = f"{MQTT_BASE}/speed/state"

# Legacy mirrors (optional; keep for compatibility until deprecation)
LEGACY_LED_STATE = f"{MQTT_BASE}/state/led"
LEGACY_STOP_STATE = f"{MQTT_BASE}/state/stop"
LEGACY_HEADING_STATE = f"{MQTT_BASE}/state/heading"
LEGACY_SPEED_STATE = f"{MQTT_BASE}/state/speed"


def _on_connect(client, userdata, flags, rc, properties=None):
    client.publish(AVAIL_TOPIC, payload=AVAIL_ON, qos=1, retain=False)
    # Subscribe to both legacy and flat command topics for actuator control
    client.subscribe(
        [
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
        ]
    )
    # Route both sets to the same callbacks
    client.message_callback_add(CMD_POWER_SET, _cb_power_set)
    client.message_callback_add(CMD_STOP_PRESS, _cb_stop_press)
    client.message_callback_add(CMD_LED_SET, _cb_led_set)
    client.message_callback_add(CMD_HEADING_SET, _cb_heading_set)
    client.message_callback_add(CMD_SPEED_SET, _cb_speed_set)
    client.message_callback_add(CMD_DRIVE_PRESS, _cb_drive_press)
    # Flat topics
    client.message_callback_add(FLAT_POWER_SET, _cb_power_set)
    client.message_callback_add(FLAT_LED_SET, _cb_led_set)
    client.message_callback_add(FLAT_STOP_PRESS, _cb_stop_press)
    client.message_callback_add(FLAT_DRIVE_SET, _cb_drive_press)
    client.message_callback_add(FLAT_HEADING_SET, _cb_heading_set)
    client.message_callback_add(FLAT_SPEED_SET, _cb_speed_set)


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
                if all(k in c for k in ("r", "g", "b")):
                    r = _clamp(c["r"], 0, 255)
                    g = _clamp(c["g"], 0, 255)
                    b = _clamp(c["b"], 0, 255)
                    return ("RGB", (r, g, b))

            # Legacy direct {r,g,b}
            if all(k in obj for k in ("r", "g", "b")):
                r = _clamp(obj["r"], 0, 255)
                g = _clamp(obj["g"], 0, 255)
                b = _clamp(obj["b"], 0, 255)
                return ("RGB", (r, g, b))

            # Hex form
            if "hex" in obj and isinstance(obj["hex"], str):
                hx = obj["hex"].lstrip("#")
                if len(hx) == 6:
                    r = int(hx[0:2], 16)
                    g = int(hx[2:4], 16)
                    b = int(hx[4:6], 16)
                    return ("RGB", (r, g, b))
    except Exception:
        pass
    return ("INVALID", None)


# ──────────────────────────────────────────────────────────────────────────────
# MQTT connection helper
def _connect_mqtt(client):
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()


# ──────────────────────────────────────────────────────────────────────────────
# MQTT command callbacks → bridge methods + state echoes
# ──────────────────────────────────────────────────────────────────────────────
def _cb_power_set(client, userdata, msg):
    payload = msg.payload
    if isinstance(payload, memoryview):
        payload = payload.tobytes()
    payload = (payload or b"").decode("utf-8", "ignore").strip().upper()
    if payload == "ON":
        try:
            FACADE.power(True)
        except Exception as e:
            logger.warning("facade.power(True) failed: %s", e)
        client.publish(f"{MQTT_BASE}/power/state", "ON", qos=1, retain=False)
    elif payload == "OFF":
        try:
            FACADE.power(False)
        except Exception as e:
            logger.warning("facade.power(False) failed: %s", e)
        client.publish(f"{MQTT_BASE}/power/state", "OFF", qos=1, retain=False)
    else:
        logger.warning("power_set invalid payload: %r", payload)


def _cb_stop_press(client, userdata, msg):
    try:
        FACADE.stop()
    except Exception as e:
        logger.warning("facade.stop() failed: %s", e)
    client.publish(FLAT_STOP_STATE, "pressed", qos=1, retain=False)  # pragma: no cover
    client.publish(
        LEGACY_STOP_STATE, "pressed", qos=1, retain=False
    )  # pragma: no cover
    threading.Timer(
        0.5,
        lambda: (
            client.publish(
                FLAT_STOP_STATE, "idle", qos=1, retain=False
            ),  # pragma: no cover
            client.publish(
                LEGACY_STOP_STATE, "idle", qos=1, retain=False
            ),  # pragma: no cover
        ),
    ).start()


def _cb_heading_set(client, userdata, msg):
    payload = msg.payload
    if isinstance(payload, memoryview):
        payload = payload.tobytes()
    try:
        payload = (payload or b"").decode("utf-8", "ignore").strip()
        deg = _clamp(int(float(payload)), 0, 359)
    except Exception:
        logger.warning("heading_set invalid payload: %r", msg.payload)
        return
    try:
        FACADE.set_heading(deg)
    except Exception as e:
        logger.warning("facade.set_heading(%s) failed: %s", deg, e)
    client.publish(
        FLAT_HEADING_STATE, str(deg), qos=1, retain=False
    )  # pragma: no cover
    client.publish(
        LEGACY_HEADING_STATE, str(deg), qos=1, retain=False
    )  # pragma: no cover


def _cb_speed_set(client, userdata, msg):
    payload = msg.payload
    if isinstance(payload, memoryview):
        payload = payload.tobytes()
    try:
        spd = _clamp(int(float(payload)), 0, 255)
    except Exception:
        logger.warning("speed_set invalid payload: %r", msg.payload)
        return
    try:
        FACADE.set_speed(spd)
    except Exception as e:
        logger.warning("facade.set_speed(%s) failed: %s", spd, e)
    client.publish(FLAT_SPEED_STATE, str(spd), qos=1, retain=False)  # pragma: no cover
    client.publish(
        LEGACY_SPEED_STATE, str(spd), qos=1, retain=False
    )  # pragma: no cover


def _cb_drive_press(client, userdata, msg):
    try:
        FACADE.drive()
    except Exception as e:
        logger.warning("facade.drive() failed: %s", e)
    client.publish(FLAT_STOP_STATE, "pressed", qos=1, retain=False)  # pragma: no cover
    client.publish(
        LEGACY_STOP_STATE, "pressed", qos=1, retain=False
    )  # pragma: no cover
    threading.Timer(
        0.4,
        lambda: (
            client.publish(
                FLAT_STOP_STATE, "idle", qos=1, retain=False
            ),  # pragma: no cover
            client.publish(
                LEGACY_STOP_STATE, "idle", qos=1, retain=False
            ),  # pragma: no cover
        ),
    ).start()


def setup_callbacks(client):
    client.on_connect = _on_connect


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
    dbus_path = details.get("path") or (
        f"/org/bluez/hci0/dev_{mac.replace(':', '_')}" if mac else None
    )
    return mac or None, dbus_path


def build_device_block(
    mac: str, dbus_path: str, model: str, name: str = "BB-8"
) -> dict:
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


def publish_discovery_old(
    client: mqtt.Client,
    mac: str,
    dbus_path: str,
    model: str = "",
    name: str = "",
):
    """
    Publish Home Assistant discovery for Presence and RSSI with full device block.
    """
    # TODO: Store and map device_defaults from facade_mapping_table.json
    # to retrievable dynamic variables
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
        "state_topic": f"{base}/presence/state",
        "payload_on": "on",
        "payload_off": "off",
        "device_class": "connectivity",
        **availability,
        "device": device,
    }
    rssi_disc = {
        "name": f"{name_hint} RSSI",
        "unique_id": f"bb8_rssi_{uid_suffix}",
        "state_topic": f"{base}/rssi/state",
        "unit_of_measurement": "dBm",
        "state_class": "measurement",
        "device_class": "signal_strength",
        **availability,
        "device": device,
    }
    client.publish(
        f"{HA_DISCOVERY_TOPIC}/binary_sensor/bb8_presence/config",
        json.dumps(presence_disc),
        qos=1,
        retain=True,
    )
    client.publish(
        f"{HA_DISCOVERY_TOPIC}/sensor/bb8_rssi/config",
        json.dumps(rssi_disc),
        qos=1,
        retain=True,
    )
    logger.info("Published HA discovery for MAC=%s", mac)

    mqtt_client = get_mqtt_client()  # Get the mqtt_client instance
    _connect_mqtt(mqtt_client)  # Pass the client to the connect function


# Logging helpers
# -----------------------------------------------------------------------------
def tick_log(found: bool, name: str, addr: str | None, rssi):
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    if args.quiet:
        return
    if args.json:
        print(
            json.dumps(
                {
                    "ts": int(time.time()),
                    "found": found,
                    "name": name,
                    "address": addr,
                    "rssi": rssi,
                }
            )
        )
    else:
        if found:
            print(f"[{ts}] found name={name} addr={addr} rssi={rssi}")
        elif args.verbose:
            print(f"[{ts}] not_found name={name}")
