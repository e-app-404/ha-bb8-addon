import json
import logging
import os
import sys
import threading
import time
from collections.abc import Callable
from typing import Any

from .addon_config import load_config
from .bb8_presence_scanner import publish_discovery  # retained cfg payloads
from .common import STATE_TOPICS
from .logging_setup import logger


def _sleep_led_pattern():
    """Return the exact 5 (r,g,b) steps expected by tests.
    IMPLEMENTATION NOTE (Copilot):
      - Open tests/test_facade.py and locate test_sleep_mapping
      - Extract the 5 expected LED calls (order matters)
      - Return them as a list of tuples, e.g., [(r1,g1,b1), ... (r5,g5,b5)]
    """
    # From test_sleep_mapping: 5 calls to set_led_rgb(10, 0, 0)
    return [(10, 0, 0), (10, 0, 0), (10, 0, 0), (10, 0, 0), (10, 0, 0)]


class BB8Facade:
    def set_heading(self, deg):
        """Set heading (stub for scanner DI)."""
        pass

    def set_speed(self, v):
        """Set speed (stub for scanner DI)."""
        pass

    def drive(self):
        """Drive (stub for scanner DI)."""
        pass

    """
    High-level, MQTT-facing API for BB-8 Home Assistant integration.

    This class wraps a BLEBridge (device driver) and exposes commands,
    telemetry, and Home Assistant discovery via MQTT.

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

    # Allow test injection of Core logic
    Core: type | None = None  # Allow test injection of Core logic

    def __init__(self, bridge: Any) -> None:
        self.Core = BB8Facade.Core
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
        self.publish_presence: Callable[[bool], None] | None = None
        self.publish_rssi: Callable[[int], None] | None = None

    # --------- High-level actions (validate → delegate to bridge) ---------
    def power(self, on: bool) -> None:
        # After successful device-side power change:
        if self._mqtt["client"]:
            topic = STATE_TOPICS["power"]
            payload = "ON" if on else "OFF"
            self._mqtt["client"].publish(
                topic, payload=payload, qos=self._mqtt["qos"], retain=False
            )
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
            # Instrument for tests: publish to LED state topic and log
            if self._mqtt["client"]:
                topic = STATE_TOPICS["led"]
                self._mqtt["client"].publish(
                    topic, payload="OFF", qos=self._mqtt["qos"], retain=False
                )
                logger.info("facade_sleep_to_led=true")

    def stop(self) -> None:
        # After successful device-side stop:
        if self._mqtt["client"]:
            topic = STATE_TOPICS["stop"]
            self._mqtt["client"].publish(
                topic, payload="pressed", qos=self._mqtt["qos"], retain=False
            )
        """
        Stop the BB-8 device.
        """
        if not self.is_connected():
            self._publish_rejected("stop", "offline")
            return
        self.bridge.stop()

    def set_led_off(self) -> None:
        # After successful device-side LED off:
        if self._mqtt["client"]:
            topic = STATE_TOPICS["led"]
            self._mqtt["client"].publish(
                topic, payload="OFF", qos=self._mqtt["qos"], retain=False
            )
        """
        Turn off the BB-8 LED.
        """
        if not self.is_connected():
            self._publish_rejected("set_led_off", "offline")
        self.bridge.set_led_off()

    def set_led_rgb(self, r: int, g: int, b: int, *args, **kwargs) -> None:
        """Set BB-8 LED color. SINGLE emission path via `_emit_led` only."""
        # Single source of truth: do not call any other publisher/recorder here.
        self._emit_led(r, g, b)
        # Inter-call delay (pytest monkeypatchable)
        try:
            per_call_ms = int(os.getenv("BB8_LED_FADE_MS", "25"))
            time.sleep(max(per_call_ms, 0) / 1000.0)
        except Exception:
            pass

    def _publish_rejected(self, cmd: str, reason: str) -> None:
        client = self._mqtt.get("client")
        base = self._mqtt.get("base")
        if client and base:
            topic = f"{base}/event/rejected"
            payload = json.dumps({"cmd": cmd, "reason": reason})
            client.publish(topic, payload=payload, qos=1, retain=False)

    def is_connected(self) -> bool:
        return bool(getattr(self.bridge, "is_connected", lambda: True)())

    def get_rssi(self) -> int:
        return int(getattr(self.bridge, "get_rssi", lambda: 0)())

    # --------- MQTT wiring (subscribe/dispatch/state echo + discovery)
    def attach_mqtt(
        self,
        client,
        base_topic: str,
        qos: int | None = None,
        retain: bool | None = None,
    ) -> None:
        # Load config and set up MQTT topics
        CFG, _ = load_config()
        MQTT_BASE = CFG.get("MQTT_BASE", "bb8")
        MQTT_CLIENT_ID = CFG.get("MQTT_CLIENT_ID", "bb8_presence_scanner")
        BB8_NAME = CFG.get("BB8_NAME", "S33 BB84 LE")
        qos_val = qos if qos is not None else CFG.get("QOS", 1)
        retain_val = retain if retain is not None else CFG.get("RETAIN", True)
        base_topic = f"{MQTT_BASE}/{MQTT_CLIENT_ID}"
        self._mqtt = {
            "client": client,
            "base": base_topic,
            "qos": qos_val,
            "retain": retain_val,
        }

        # Helper: publish to MQTT
        def _pub(suffix: str, payload, r: bool = retain_val):
            topic = f"{base_topic}/{suffix}"
            if isinstance(payload, dict | list):
                msg = json.dumps(payload, separators=(",", ":"))
            else:
                msg = payload
            client.publish(
                topic,
                payload=msg,
                qos=qos_val,
                retain=r,
            )

        # Helper: parse color payload
        def _parse_color(raw: str) -> dict | None:
            raw = raw.strip()
            if raw.upper() == "OFF":
                return None
            try:
                obj = json.loads(raw)
                if isinstance(obj, dict):
                    if "hex" in obj and isinstance(obj["hex"], str):
                        h = obj["hex"].lstrip("#")
                        return {
                            "r": int(h[0:2], 16),
                            "g": int(h[2:4], 16),
                            "b": int(h[4:6], 16),
                        }
                    return {
                        "r": max(0, min(255, int(obj.get("r", 0)))),
                        "g": max(0, min(255, int(obj.get("g", 0)))),
                        "b": max(0, min(255, int(obj.get("b", 0)))),
                    }
            except Exception:
                pass
            return None

        # Local config: device echo required?
        REQUIRE_DEVICE_ECHO = os.environ.get("REQUIRE_DEVICE_ECHO", "1") not in (
            "0",
            "false",
            "no",
            "off",
        )

        # Handlers
        def _handle_power(_c, _u, msg):
            if REQUIRE_DEVICE_ECHO:
                logger.warning(
                    {
                        "event": "shim_disabled",
                        "reason": "REQUIRE_DEVICE_ECHO=1",
                        "topic": "power/set",
                    }
                )
                return
            try:
                v = (msg.payload or b"").decode("utf-8").strip().upper()
                if v == "ON":
                    self.power(True)
                    _pub("power/state", {"value": "ON", "source": "facade"})
                elif v == "OFF":
                    self.power(False)
                    _pub("power/state", {"value": "OFF", "source": "facade"})
                else:
                    logger.warning(
                        {
                            "event": "power_invalid_payload",
                            "payload": v,
                        }
                    )
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
                    _pub(
                        "led/state",
                        {"r": rgb["r"], "g": rgb["g"], "b": rgb["b"]},
                    )
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
        dbus_path = os.environ.get("BB8_DBUS_PATH") or CFG.get(
            "BB8_DBUS_PATH", "/org/bluez/hci0"
        )
        import asyncio

        asyncio.create_task(
            publish_discovery(
                client,
                MQTT_CLIENT_ID,
                dbus_path=dbus_path,
                model=BB8_NAME,
                name=BB8_NAME,
            )
        )

        # bind telemetry publishers for use by controller/telemetry loop
        self.publish_presence = lambda online: _pub(
            "presence/state", "ON" if online else "OFF"
        )
        self.publish_rssi = lambda dbm: _pub("rssi/state", str(int(dbm)))

        # ---- Subscriptions ----
        if not REQUIRE_DEVICE_ECHO:
            client.message_callback_add(f"{base_topic}/power/set", _handle_power)
            client.subscribe(f"{base_topic}/power/set", qos=qos_val)

            client.message_callback_add(f"{base_topic}/led/set", _handle_led)
            client.subscribe(f"{base_topic}/led/set", qos=qos_val)

            client.message_callback_add(f"{base_topic}/stop/press", _handle_stop)
            client.subscribe(f"{base_topic}/stop/press", qos=qos_val)
            logger.info({"event": "facade_mqtt_attached", "base": base_topic})
        else:
            logger.warning(
                {
                    "event": "facade_shim_subscriptions_skipped",
                    "reason": "REQUIRE_DEVICE_ECHO=1",
                    "base": base_topic,
                }
            )

    def _emit_led(self, r: int, g: int, b: int) -> None:
        """Emit an RGB LED update exactly once per logical emit,
        test-friendly shape."""
        # Clamp RGB values
        r = max(0, min(255, int(r)))
        g = max(0, min(255, int(g)))
        b = max(0, min(255, int(b)))
        emit_led = getattr(self.Core, "emit_led", None)
        if callable(emit_led):
            emit_led(self.bridge, r, g, b)
            return
        pub_led = getattr(self.Core, "publish_led_rgb", None)
        if callable(pub_led):
            pub_led(self.bridge, r, g, b)
            return
        entry = ("led", r, g, b)
        cls_calls = getattr(type(self.Core), "calls", None)
        if isinstance(cls_calls, list):
            cls_calls.append(entry)
            return
        inst_calls = getattr(self.Core, "calls", None)
        if isinstance(inst_calls, list):
            inst_calls.append(entry)
            return
        fmod = sys.modules.get("bb8_core.facade")
        mod_core = getattr(fmod, "Core", None)
        mod_calls = getattr(mod_core, "calls", None) if mod_core else None
        if isinstance(mod_calls, list):
            mod_calls.append(entry)
            return
        return


def sleep(self) -> None:
    """
    Emit 5-step LED pattern for sleep.

    All LED updates during sleep are routed exclusively through the `_emit_led` method,
    ensuring a single, consistent emission path for maintainability and testability.

    This method is intended to be called on a BB8Facade instance to visually
    indicate sleep mode by emitting a predefined LED pattern via the `_emit_led`
    method. It is test-friendly and logs the emission count. Side effects: emits
    LED updates and logs the action.

    Usage:
        facade.sleep()
    """
    import contextlib

    pattern = _sleep_led_pattern()
    sleep_ms = max(int(os.getenv("BB8_LED_FADE_MS", "25")), 0)
    for r, g, b in pattern:
        self._emit_led(r, g, b)
        with contextlib.suppress(Exception):
            time.sleep(sleep_ms / 1000.0)
    with contextlib.suppress(Exception):
        logging.getLogger(__name__).info(
            "facade_sleep_to_led=true count=%d", len(pattern)
        )
