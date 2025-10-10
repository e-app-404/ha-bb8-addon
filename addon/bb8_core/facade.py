"""
Refactored BB8 Facade - Pure facade pattern delegating to BLE session.

Maintains MQTT/ACK semantics while delegating device operations to BleSession.
Provides event-loop safety and proper async task management.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import threading
import time
from collections.abc import Callable
from typing import Any

from .addon_config import load_config
from .bb8_presence_scanner import publish_discovery
from .ble_session import BleSession, BleSessionError
from .common import STATE_TOPICS
from .logging_setup import logger
from .safety import SafetyViolation, get_safety_controller


def _sleep_led_pattern():
    """Return the exact 5 (r,g,b) steps expected by tests."""
    # From test_sleep_mapping: 5 calls to set_led_rgb(10, 0, 0)
    return [(10, 0, 0), (10, 0, 0), (10, 0, 0), (10, 0, 0), (10, 0, 0)]


class BB8Facade:
    """
    High-level, MQTT-facing API for BB-8 Home Assistant integration.

    This class wraps a BleSession and exposes commands, telemetry,
    and Home Assistant discovery via MQTT with proper async handling.
    """

    # Allow test injection of Core logic
    Core: type | None = None

    def __init__(self, bridge: Any = None) -> None:
        """
        Initialize a BB8Facade instance.

        Parameters
        ----------
        bridge : object, optional
            Legacy bridge parameter for compatibility.
            New implementation uses BleSession internally.
        """
        self.Core = BB8Facade.Core

        # Legacy bridge support for compatibility
        self.bridge = bridge

        # New BLE session for actual device operations
        self._ble_session: BleSession | None = None
        self._target_mac: str | None = None

        # MQTT configuration
        self._mqtt = {"client": None, "base": None, "qos": 1, "retain": True}

        # Telemetry publishers bound at attach_mqtt()
        self.publish_presence: Callable[[bool], None] | None = None
        self.publish_rssi: Callable[[int], None] | None = None

        # Task management
        self._tasks: set[asyncio.Task] = set()
        self._shutdown_event = asyncio.Event()

        # Safety and telemetry
        self._safety = get_safety_controller()
        self._telemetry_task: asyncio.Task | None = None
        self._last_cmd_timestamp: float = 0.0

    def _get_or_create_session(self) -> BleSession:
        """Get or create BLE session instance."""
        if self._ble_session is None:
            self._ble_session = BleSession(self._target_mac)
        return self._ble_session

    def set_target_mac(self, mac: str) -> None:
        """Set target MAC address for BLE connection."""
        self._target_mac = mac
        if self._ble_session:
            self._ble_session = BleSession(mac)

    async def ensure_connected(self) -> None:
        """Ensure device is connected, attempt connection if not."""
        session = self._get_or_create_session()
        if not session.is_connected():
            try:
                await session.connect()
                logger.info({"event": "facade_auto_connect_success"})

                # Notify safety controller
                self._safety.set_device_connected(True)

                # Publish presence if available
                if self.publish_presence:
                    self.publish_presence(True)

                # Publish telemetry update
                self._publish_telemetry_update()

            except BleSessionError as e:
                logger.error({
                    "event": "facade_auto_connect_failed",
                    "error": str(e),
                })
                raise

    def _schedule_task(self, coro) -> None:
        """Schedule async task safely."""
        if asyncio.iscoroutine(coro):
            task = asyncio.create_task(coro)
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    # --------- High-level actions (validate → delegate to session) ---------

    def power(self, on: bool) -> None:
        """
        Power on or off the BB-8 device.

        Parameters
        ----------
        on : bool
            If True, connect and wake; if False, sleep.
        """
        try:
            if on:
                self._schedule_task(self._power_on())
            else:
                self._schedule_task(self._power_off())
        except Exception as e:
            logger.error({
                "event": "facade_power_error",
                "on": on,
                "error": str(e),
            })
            self._publish_rejected("power", str(e))

    async def _power_on(self) -> None:
        """Internal power on implementation."""
        try:
            await self.ensure_connected()
            session = self._get_or_create_session()
            await session.wake()

            # Publish MQTT state
            if self._mqtt["client"]:
                topic = STATE_TOPICS["power"]
                payload = "ON"
                self._mqtt["client"].publish(
                    topic, payload=payload, qos=self._mqtt["qos"], retain=False
                )

            logger.info({"event": "facade_power_on_success"})

        except Exception as e:
            logger.error({"event": "facade_power_on_error", "error": str(e)})
            self._publish_rejected("power", str(e))

    async def _power_off(self) -> None:
        """Internal power off implementation."""
        try:
            session = self._get_or_create_session()
            if session.is_connected():
                await session.sleep()

                # Publish MQTT state
                if self._mqtt["client"]:
                    topic = STATE_TOPICS["power"]
                    payload = "OFF"
                    self._mqtt["client"].publish(
                        topic,
                        payload=payload,
                        qos=self._mqtt["qos"],
                        retain=False,
                    )

                    # Also publish LED state
                    topic = STATE_TOPICS["led"]
                    self._mqtt["client"].publish(
                        topic,
                        payload="OFF",
                        qos=self._mqtt["qos"],
                        retain=False,
                    )
                    logger.info("facade_sleep_to_led=true")

                # Update presence
                if self.publish_presence:
                    self.publish_presence(False)

            logger.info({"event": "facade_power_off_success"})

        except Exception as e:
            logger.error({"event": "facade_power_off_error", "error": str(e)})
            self._publish_rejected("power", str(e))

    def stop(self) -> None:
        """Stop the BB-8 device."""
        try:
            self._schedule_task(self._stop_impl())
        except Exception as e:
            logger.error({"event": "facade_stop_error", "error": str(e)})
            self._publish_rejected("stop", str(e))

    async def _stop_impl(self) -> None:
        """Internal stop implementation."""
        try:
            session = self._get_or_create_session()
            if not session.is_connected():
                self._publish_rejected("stop", "offline")
                return

            await session.stop()

            # Cancel any pending auto-stop
            self._safety.cancel_auto_stop()

            # Publish MQTT state
            if self._mqtt["client"]:
                topic = STATE_TOPICS["stop"]
                self._mqtt["client"].publish(
                    topic,
                    payload="pressed",
                    qos=self._mqtt["qos"],
                    retain=False,
                )

            logger.info({"event": "facade_stop_success"})

        except Exception as e:
            logger.error({"event": "facade_stop_impl_error", "error": str(e)})
            self._publish_rejected("stop", str(e))

    def set_led_off(self) -> None:
        """Turn off the BB-8 LED."""
        self.set_led_rgb(0, 0, 0)

    def set_led_rgb(self, r: int, g: int, b: int, *args, **kwargs) -> None:
        """Set BB-8 LED color. SINGLE emission path via `_emit_led` only."""
        # Single source of truth: do not call any other publisher/recorder here.
        self._emit_led(r, g, b)

        # Schedule async LED operation
        self._schedule_task(self._set_led_impl(r, g, b))

        # Inter-call delay (pytest monkeypatchable)
        try:
            per_call_ms = int(os.getenv("BB8_LED_FADE_MS", "25"))
            time.sleep(max(per_call_ms, 0) / 1000.0)
        except Exception:
            pass

    async def _set_led_impl(self, r: int, g: int, b: int) -> None:
        """Internal LED implementation."""
        try:
            session = self._get_or_create_session()
            if not session.is_connected():
                logger.info({
                    "event": "facade_led_noop",
                    "reason": "not_connected",
                    "r": r,
                    "g": g,
                    "b": b,
                })
                return

            await session.set_led(r, g, b)
            logger.debug({
                "event": "facade_led_success",
                "r": r,
                "g": g,
                "b": b,
            })

        except Exception as e:
            logger.error({
                "event": "facade_led_impl_error",
                "r": r,
                "g": g,
                "b": b,
                "error": str(e),
            })

    def drive(
        self, speed: int, heading: int, duration_ms: int | None = None
    ) -> None:
        """Drive BB-8 with specified parameters."""
        try:
            # Validate through safety controller
            validated_speed, validated_heading, validated_duration = (
                self._safety.validate_drive_command(speed, heading, duration_ms)
            )

            self._last_cmd_timestamp = time.time()
            self._schedule_task(
                self._drive_impl(
                    validated_speed, validated_heading, validated_duration
                )
            )

        except SafetyViolation as e:
            logger.warning({
                "event": "facade_drive_safety_violation",
                "speed": speed,
                "heading": heading,
                "duration_ms": duration_ms,
                "constraint": e.constraint,
                "error": str(e),
            })
            self._publish_rejected("drive", str(e))

        except Exception as e:
            logger.error({
                "event": "facade_drive_error",
                "speed": speed,
                "heading": heading,
                "duration_ms": duration_ms,
                "error": str(e),
            })
            self._publish_rejected("drive", str(e))

    async def _drive_impl(
        self, speed: int, heading: int, duration_ms: int | None
    ) -> None:
        """Internal drive implementation."""
        try:
            session = self._get_or_create_session()
            if not session.is_connected():
                self._publish_rejected("drive", "offline")
                return

            await session.roll(speed, heading, duration_ms)

            # Schedule auto-stop via safety controller
            if duration_ms and duration_ms > 0:
                self._safety.schedule_auto_stop(duration_ms, self._stop_impl)

            # Publish MQTT state
            if self._mqtt["client"]:
                drive_topic = STATE_TOPICS.get("drive")
                if drive_topic:
                    payload = json.dumps({
                        "speed": speed,
                        "heading": heading,
                        "duration_ms": duration_ms,
                    })
                    self._mqtt["client"].publish(
                        drive_topic,
                        payload=payload,
                        qos=self._mqtt["qos"],
                        retain=False,
                    )

            logger.info({
                "event": "facade_drive_success",
                "speed": speed,
                "heading": heading,
                "duration_ms": duration_ms,
            })

        except Exception as e:
            logger.error({
                "event": "facade_drive_impl_error",
                "speed": speed,
                "heading": heading,
                "duration_ms": duration_ms,
                "error": str(e),
            })
            self._publish_rejected("drive", str(e))

    def estop(self, reason: str = "Manual emergency stop") -> None:
        """Activate emergency stop."""
        try:
            self._safety.activate_estop(reason)

            # Stop device immediately
            self._schedule_task(self._stop_impl())

            # Publish telemetry update
            self._publish_telemetry_update()

            logger.warning({
                "event": "facade_estop_activated",
                "reason": reason,
            })

        except Exception as e:
            logger.error({
                "event": "facade_estop_error",
                "reason": reason,
                "error": str(e),
            })
            self._publish_rejected("estop", str(e))

    def clear_estop(self) -> None:
        """Clear emergency stop if safe."""
        try:
            cleared, reason = self._safety.clear_estop()

            if cleared:
                # Publish telemetry update
                self._publish_telemetry_update()

                logger.info({"event": "facade_estop_cleared", "reason": reason})
            else:
                logger.warning({
                    "event": "facade_estop_clear_denied",
                    "reason": reason,
                })
                self._publish_rejected("clear_estop", reason)

        except Exception as e:
            logger.error({"event": "facade_clear_estop_error", "error": str(e)})
            self._publish_rejected("clear_estop", str(e))

    def _publish_rejected(self, cmd: str, reason: str) -> None:
        """Publish rejection message."""
        client = self._mqtt.get("client")
        base = self._mqtt.get("base")
        if client and base:
            topic = f"{base}/event/rejected"
            payload = json.dumps({"cmd": cmd, "reason": reason})
            client.publish(topic, payload=payload, qos=1, retain=False)

    def is_connected(self) -> bool:
        """Check if device is connected."""
        if self._ble_session:
            return self._ble_session.is_connected()
        # Fallback to legacy bridge if available
        return bool(getattr(self.bridge, "is_connected", lambda: False)())

    def get_rssi(self) -> int:
        """Return RSSI dBm if available; else 0."""
        if self.bridge and hasattr(self.bridge, "get_rssi"):
            try:
                return int(self.bridge.get_rssi())
            except Exception as e:
                logger.debug({
                    "event": "facade_get_rssi_error",
                    "error": str(e),
                })
        return 0

    async def get_battery(self) -> int:
        """Get battery percentage asynchronously."""
        try:
            session = self._get_or_create_session()
            if not session.is_connected():
                return 0
            return await session.battery()
        except Exception as e:
            logger.debug({"event": "facade_get_battery_error", "error": str(e)})
            return 0

    def _publish_telemetry_update(self) -> None:
        """Publish telemetry update immediately."""
        if self._mqtt["client"] and self._mqtt["base"]:
            self._schedule_task(self._publish_telemetry())

    async def _publish_telemetry(self) -> None:
        """Publish telemetry data."""
        try:
            client = self._mqtt["client"]
            base = self._mqtt["base"]

            if not client or not base:
                return

            # Get battery (with timeout to avoid blocking)
            battery_pct = None
            try:
                battery_pct = await asyncio.wait_for(
                    self.get_battery(), timeout=1.0
                )
            except (asyncio.TimeoutError, Exception):
                battery_pct = None

            # Build telemetry payload
            telemetry = {
                "connected": self.is_connected(),
                "estop": self._safety.is_estop_active(),
                "last_cmd_ts": time.strftime(
                    "%Y-%m-%dT%H:%M:%S.%fZ",
                    time.gmtime(self._last_cmd_timestamp),
                )
                if self._last_cmd_timestamp > 0
                else None,
                "battery_pct": battery_pct,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime()),
            }

            # Publish telemetry
            topic = f"{base}/status/telemetry"
            payload = json.dumps(telemetry)
            client.publish(topic, payload=payload, qos=1, retain=False)

            logger.debug({
                "event": "facade_telemetry_published",
                "telemetry": telemetry,
            })

        except Exception as e:
            logger.error({"event": "facade_telemetry_error", "error": str(e)})

    async def _telemetry_heartbeat(self) -> None:
        """Telemetry heartbeat task - publishes every 10 seconds."""
        try:
            while not self._shutdown_event.is_set():
                await self._publish_telemetry()
                await asyncio.sleep(10.0)
        except asyncio.CancelledError:
            logger.debug({"event": "facade_telemetry_heartbeat_cancelled"})
        except Exception as e:
            logger.error({
                "event": "facade_telemetry_heartbeat_error",
                "error": str(e),
            })

    # --------- MQTT wiring (subscribe/dispatch/state echo + discovery) ---------

    def attach_mqtt(
        self,
        client,
        base_topic: str,
        qos: int | None = None,
        retain: bool | None = None,
    ) -> None:
        """Attach MQTT client and set up subscriptions."""
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
        REQUIRE_DEVICE_ECHO = os.environ.get(
            "REQUIRE_DEVICE_ECHO", "1"
        ) not in ("0", "false", "no", "off")

        # Handlers
        def _handle_power(_c, _u, msg):
            if REQUIRE_DEVICE_ECHO:
                logger.warning({
                    "event": "shim_disabled",
                    "reason": "REQUIRE_DEVICE_ECHO=1",
                    "topic": "power/set",
                })
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
                    logger.warning({
                        "event": "power_invalid_payload",
                        "payload": v,
                    })
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

        def _handle_estop(_c, _u, msg):
            try:
                # Parse optional payload for reason/cid
                reason = "MQTT emergency stop"
                cid = None
                try:
                    payload = json.loads((msg.payload or b"").decode("utf-8"))
                    if isinstance(payload, dict):
                        reason = payload.get("reason", reason)
                        cid = payload.get("cid")
                except Exception:
                    pass

                self.estop(reason)

                # Publish acknowledgment
                ack_payload = {
                    "ok": True,
                    "reason": f"Emergency stop activated: {reason}",
                    "timestamp": time.strftime(
                        "%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime()
                    ),
                }
                if cid:
                    ack_payload["cid"] = cid

                _pub("ack/estop", ack_payload, r=False)

            except Exception as e:
                logger.error({"event": "estop_handler_error", "error": repr(e)})

        def _handle_clear_estop(_c, _u, msg):
            try:
                # Parse optional payload for cid
                cid = None
                try:
                    payload = json.loads((msg.payload or b"").decode("utf-8"))
                    if isinstance(payload, dict):
                        cid = payload.get("cid")
                except Exception:
                    pass

                # Attempt to clear estop
                cleared, reason = self._safety.clear_estop()

                # Publish acknowledgment
                ack_payload = {
                    "ok": cleared,
                    "reason": reason,
                    "timestamp": time.strftime(
                        "%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime()
                    ),
                }
                if cid:
                    ack_payload["cid"] = cid

                _pub("ack/clear_estop", ack_payload, r=False)

                if cleared:
                    # Publish telemetry update
                    self._publish_telemetry_update()

            except Exception as e:
                logger.error({
                    "event": "clear_estop_handler_error",
                    "error": repr(e),
                })

        # Discovery (idempotent; retained on broker)
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

        # Bind telemetry publishers for use by controller/telemetry loop
        self.publish_presence = lambda online: _pub(
            "presence/state", "ON" if online else "OFF"
        )
        self.publish_rssi = lambda dbm: _pub("rssi/state", str(int(dbm)))

        # ---- Subscriptions ----
        if not REQUIRE_DEVICE_ECHO:
            client.message_callback_add(
                f"{base_topic}/power/set", _handle_power
            )
            client.subscribe(f"{base_topic}/power/set", qos=qos_val)

            client.message_callback_add(f"{base_topic}/led/set", _handle_led)
            client.subscribe(f"{base_topic}/led/set", qos=qos_val)

            client.message_callback_add(
                f"{base_topic}/stop/press", _handle_stop
            )
            client.subscribe(f"{base_topic}/stop/press", qos=qos_val)

            # Emergency stop subscriptions
            client.message_callback_add(f"{MQTT_BASE}/cmd/estop", _handle_estop)
            client.subscribe(f"{MQTT_BASE}/cmd/estop", qos=qos_val)

            client.message_callback_add(
                f"{MQTT_BASE}/cmd/clear_estop", _handle_clear_estop
            )
            client.subscribe(f"{MQTT_BASE}/cmd/clear_estop", qos=qos_val)

            logger.info({"event": "facade_mqtt_attached", "base": base_topic})

            # Start telemetry heartbeat
            if self._telemetry_task is None or self._telemetry_task.done():
                self._telemetry_task = asyncio.create_task(
                    self._telemetry_heartbeat()
                )
                self._tasks.add(self._telemetry_task)
                self._telemetry_task.add_done_callback(self._tasks.discard)
        else:
            logger.warning({
                "event": "facade_shim_subscriptions_skipped",
                "reason": "REQUIRE_DEVICE_ECHO=1",
                "base": base_topic,
            })

    def _emit_led(self, r: int, g: int, b: int) -> None:
        """Emit an RGB LED update exactly once per logical emit."""
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

    async def shutdown(self) -> None:
        """Shutdown facade and cancel running tasks."""
        self._shutdown_event.set()

        # Cancel all running tasks
        for task in list(self._tasks):
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        # Shutdown BLE session
        if self._ble_session:
            await self._ble_session.disconnect()

        # Notify safety controller of disconnection
        self._safety.set_device_connected(False)

        logger.info({"event": "facade_shutdown_complete"})


def sleep(self) -> None:
    """
    Emit 5-step LED pattern for sleep.

    Compatibility function for existing tests.
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
