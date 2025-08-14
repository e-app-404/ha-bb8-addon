from __future__ import annotations
from typing import Any, Optional, Callable
import json
import threading
import time

from .logging_setup import logger
from .bb8_presence_scanner import publish_discovery  # uses retained config payloads


class BB8Facade:
    """
    High-level, MQTT-facing API for BB-8 Home Assistant integration.

    This class wraps a BLEBridge (device driver) and exposes commands, telemetry, and Home Assistant discovery via MQTT.

    Attributes
    ----------
    bridge : object
        BLEBridge instance for device operations.
    publish_presence : Callable[[bool], None] or None
        Telemetry publisher for presence state.
    publish_rssi : Callable[[int], None] or None
        Telemetry publisher for RSSI state.

    Example
    -------
    >>> facade = BB8Facade(bridge)
    >>> facade.attach_mqtt(client, "bb8", qos=1, retain=True)
    >>> facade.power(True)
    """
    def __init__(self, bridge: Any) -> None:
        """
        Initialize a BB8Facade instance.

        Parameters
        ----------
        bridge : object
            BLEBridge instance to wrap.
        """
        self.bridge = bridge
        self._mqtt = {"client": None, "base": None, "qos": 1, "retain": True}
        # telemetry publishers bound at attach_mqtt()
        self.publish_presence: Optional[Callable[[bool], None]] = None
        self.publish_rssi: Optional[Callable[[int], None]] = None

    # --------- High-level actions (validate → delegate to bridge) ---------
    def power(self, on: bool) -> None:
        """
        Power on or off the BB-8 device.

        Parameters
        ----------
        on : bool
            If True, connect; if False, sleep.
        """
        if not self.is_connected() and on is False:
            # Already offline, no need to sleep
            return
        if not self.is_connected() and on:
            self._publish_rejected("power", "offline")
            return
        if on:
            self.bridge.connect()
        else:
            self.bridge.sleep(None)

    def stop(self) -> None:
        """
        Stop the BB-8 device.
        """
        if not self.is_connected():
            self._publish_rejected("stop", "offline")
            return
        self.bridge.stop()

    def set_led_off(self) -> None:
        """
        Turn off the BB-8 LED.
        """
        if not self.is_connected():
            self._publish_rejected("set_led_off", "offline")
            return
        self.bridge.set_led_off()

    def set_led_rgb(self, r: int, g: int, b: int) -> None:
        """
        Set the BB-8 LED color.

        Parameters
        ----------
        r : int
            Red value (0-255).
        g : int
            Green value (0-255).
        b : int
            Blue value (0-255).
        """
        if not self.is_connected():
            self._publish_rejected("set_led_rgb", "offline")
            return
        r = max(0, min(255, int(r))); g = max(0, min(255, int(g))); b = max(0, min(255, int(b)))
        self.bridge.set_led_rgb(r, g, b)

    def _publish_rejected(self, cmd: str, reason: str) -> None:
        client = self._mqtt.get("client")
        base = self._mqtt.get("base")
        if client and base:
            topic = f"{base}/event/rejected"
            payload = json.dumps({"cmd": cmd, "reason": reason})
            client.publish(topic, payload=payload, qos=1, retain=False)

    def is_connected(self) -> bool:
        """
        Check if the BB-8 device is connected.

        Returns
        -------
        bool
            True if connected, False otherwise.
        """
        return bool(getattr(self.bridge, "is_connected", lambda: True)())

    def get_rssi(self) -> int:
        """
        Get the current RSSI value from the device.

        Returns
        -------
        int
            RSSI in dBm.
        """
        return int(getattr(self.bridge, "get_rssi", lambda: 0)())

    # --------- MQTT wiring (subscribe/dispatch/state echo + discovery) ---------
    def attach_mqtt(self, client, base_topic: str, qos: Optional[int] = None, retain: Optional[bool] = None) -> None:
        """
        Attach the facade to an MQTT client, subscribe to topics, and publish discovery and state.

        Parameters
        ----------
        client : object
            MQTT client instance.
        base_topic : str
            Base MQTT topic for this device.
        qos : int, optional
            MQTT QoS level (default: 1).
        retain : bool, optional
            Whether to retain published states (default: True).
        """
        """
        Subscribes to command topics and publishes retained discovery + state.
        Topics:
          - {base}/power/set       ("ON"|"OFF")  → {base}/power/state
          - {base}/stop/press      (any payload) → {base}/stop/state ("pressed"→"idle")
          - {base}/led/set         json {"r","g","b"} | {"hex":"#rrggbb"} | "OFF" → {base}/led/state
        Telemetry helpers (bound here):
          - presence: {base}/presence/state ("ON"/"OFF")
          - rssi:     {base}/rssi/state (int dBm)
        """

        from bb8_core.addon_config import load_config
        CFG, _ = load_config()
        MQTT_BASE = CFG.get("MQTT_BASE", "bb8")
        HA_DISCOVERY_TOPIC = CFG.get("HA_DISCOVERY_TOPIC", "homeassistant")
        DISCOVERY_RETAIN = CFG.get("DISCOVERY_RETAIN", True)
        MQTT_CLIENT_ID = CFG.get("MQTT_CLIENT_ID", "bb8_presence_scanner")
        BB8_NAME = CFG.get("BB8_NAME", "S33 BB84 LE")
        qos_val = qos if qos is not None else CFG.get("QOS", 1)
        retain_val = retain if retain is not None else CFG.get("RETAIN", True)
        # Compose base topic from prefix and client/device ID
        base_topic = f"{MQTT_BASE}/{MQTT_CLIENT_ID}"
        self._mqtt = {"client": client, "base": base_topic, "qos": qos_val, "retain": retain_val}

        # Only one definition per local function
        def _pub(suffix: str, payload, r: bool = retain_val):
            topic = f"{base_topic}/{suffix}"
            msg = json.dumps(payload, separators=(',', ':')) if isinstance(payload, (dict, list)) else payload
            client.publish(topic, payload=msg, qos=qos_val, retain=r)

        def _parse_color(raw: str) -> Optional[dict]:
            raw = raw.strip()
            if raw.upper() == "OFF":
                return None
            try:
                obj = json.loads(raw)
                if isinstance(obj, dict):
                    if "hex" in obj and isinstance(obj["hex"], str):
                        h = obj["hex"].lstrip("#")
                        return {"r": int(h[0:2], 16), "g": int(h[2:4], 16), "b": int(h[4:6], 16)}
                    return {
                        "r": max(0, min(255, int(obj.get("r", 0)))),
                        "g": max(0, min(255, int(obj.get("g", 0)))),
                        "b": max(0, min(255, int(obj.get("b", 0)))),
                    }
            except Exception:
                pass
            return None

        def _handle_power(_c, _u, msg):
            try:
                v = (msg.payload or b"").decode("utf-8").strip().upper()
                if v == "ON":
                    self.power(True)
                    _pub("power/state", {"value": "ON", "source": "facade"})
                elif v == "OFF":
                    self.power(False)
                    _pub("power/state", {"value": "OFF", "source": "facade"})
                else:
                    logger.warning({"event": "power_invalid_payload", "payload": v})
            except Exception as e:
                logger.error({"event": "power_handler_error", "error": repr(e)})

        def _handle_led(_c, _u, msg):
            try:
                raw = (msg.payload or b"").decode("utf-8")
                rgb = _parse_color(raw)
                if rgb is None:
                    self.set_led_off()
                    _pub("led/state", {"state": "OFF"})
                else:
                    self.set_led_rgb(rgb["r"], rgb["g"], rgb["b"])
                    _pub("led/state", {"r": rgb["r"], "g": rgb["g"], "b": rgb["b"]})
            except Exception as e:
                logger.error({"event": "led_handler_error", "error": repr(e)})

        def _handle_stop(_c, _u, _msg):
            try:
                self.stop()
                _pub("stop/state", "pressed", r=False)
                def _reset():
                    time.sleep(0.5)
                    _pub("stop/state", "idle", r=False)
                threading.Thread(target=_reset, daemon=True).start()
            except Exception as e:
                logger.error({"event": "stop_handler_error", "error": repr(e)})

        # discovery (idempotent; retained on broker)
        import os
        dbus_path = os.environ.get("BB8_DBUS_PATH") or CFG.get("BB8_DBUS_PATH", "/org/bluez/hci0")
        publish_discovery(
            client,
            MQTT_CLIENT_ID,
            dbus_path=dbus_path,
            model=BB8_NAME,
            name=BB8_NAME
        )

        # bind telemetry publishers for use by controller/telemetry loop
        self.publish_presence = lambda online: _pub("presence/state", "ON" if online else "OFF")
        self.publish_rssi = lambda dbm: _pub("rssi/state", str(int(dbm)))

        # ---- Subscriptions ----
        client.message_callback_add(f"{base_topic}/power/set", _handle_power)
        client.subscribe(f"{base_topic}/power/set", qos=qos_val)

        client.message_callback_add(f"{base_topic}/led/set", _handle_led)
        client.subscribe(f"{base_topic}/led/set", qos=qos_val)

        client.message_callback_add(f"{base_topic}/stop/press", _handle_stop)
        client.subscribe(f"{base_topic}/stop/press", qos=qos_val)

        logger.info({"event": "facade_mqtt_attached", "base": base_topic})


        # discovery (idempotent; retained on broker)
        import os
        dbus_path = os.environ.get("BB8_DBUS_PATH") or CFG.get("BB8_DBUS_PATH", "/org/bluez/hci0")
        # TODO: Store and map device_defaults from facade_mapping_table.json to retrievable dynamic variables
        # Use MQTT_CLIENT_ID as MAC/device ID for discovery, BB8_NAME for model and name
        publish_discovery(
            client,
            MQTT_CLIENT_ID,
            dbus_path=dbus_path,
            model=BB8_NAME,
            name=BB8_NAME
        )

        # bind telemetry publishers for use by controller/telemetry loop
        self.publish_presence = lambda online: _pub("presence/state", "ON" if online else "OFF")
        self.publish_rssi = lambda dbm: _pub("rssi/state", str(int(dbm)))

        # ---- Subscriptions ----
        client.message_callback_add(f"{base_topic}/power/set", _handle_power)
        client.subscribe(f"{base_topic}/power/set", qos=qos_val)

        client.message_callback_add(f"{base_topic}/led/set", _handle_led)
        client.subscribe(f"{base_topic}/led/set", qos=qos_val)

        client.message_callback_add(f"{base_topic}/stop/press", _handle_stop)
        client.subscribe(f"{base_topic}/stop/press", qos=qos_val)

        logger.info({"event": "facade_mqtt_attached", "base": base_topic})
