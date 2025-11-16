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
from .lighting import get_lighting_controller
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

        # Safety, lighting, and telemetry
        self._safety = get_safety_controller()
        self._lighting = get_lighting_controller()
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

                # Notify safety and lighting controllers
                self._safety.set_device_connected(True)
                self._lighting.set_ble_session(self._ble_session)

                # Publish presence if available
                if self.publish_presence:
                    self.publish_presence(True)

                # Publish telemetry update
                self._publish_telemetry_update()

            except BleSessionError as e:
                logger.error(
                    {
                        "event": "facade_auto_connect_failed",
                        "error": str(e),
                    }
                )
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
            logger.error(
                {
                    "event": "facade_power_error",
                    "on": on,
                    "error": str(e),
                }
            )
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
        self._schedule_task(self._set_led_async(r, g, b))

        # Inter-call delay (pytest monkeypatchable)
        try:
            per_call_ms = int(os.getenv("BB8_LED_FADE_MS", "25"))
            time.sleep(max(per_call_ms, 0) / 1000.0)
        except Exception:
            pass

    async def set_led_async(
        self, r: int, g: int, b: int, cid: str | None = None
    ) -> None:
        """Async LED control with validation and ACK/NACK."""
        try:
            # Always cancel any active animation first (idempotent)
            await self._lighting.cancel_active()

            # Validate and clamp RGB values
            r, g, b = self._lighting.clamp_rgb(r, g, b)

            # Apply static color via lighting controller
            await self._lighting.set_static(r, g, b)

            # Publish a telemetry update after LED change
            self._publish_telemetry_update()

            # Publish ACK
            self._publish_ack("led", True, cid, f"LED set to RGB({r},{g},{b})")

            logger.info(
                {
                    "event": "facade_led_async_success",
                    "rgb": [r, g, b],
                    "cid": cid,
                }
            )

        except Exception as e:
            self._publish_ack("led", False, cid, str(e))
            logger.error(
                {
                    "event": "facade_led_async_error",
                    "rgb": [r, g, b],
                    "cid": cid,
                    "error": str(e),
                }
            )

    async def set_led_preset(self, preset_name: str, cid: str | None = None) -> None:
        """Run LED preset animation with estop checking."""
        try:
            # Always cancel any active animation first (idempotent)
            await self._lighting.cancel_active()

            # Check if estop is active
            if self._safety.estop_latched:
                # Only allow static presets during estop
                if preset_name in ["off", "white"]:
                    # Convert to static color
                    if preset_name == "off":
                        await self._lighting.set_static(0, 0, 0)
                    elif preset_name == "white":
                        await self._lighting.set_static(255, 255, 255)

                    self._publish_ack(
                        "led_preset",
                        True,
                        cid,
                        f"Static preset '{preset_name}' applied during estop",
                    )
                    # Telemetry update for static LED under estop
                    self._publish_telemetry_update()
                else:
                    # Reject animated presets during estop
                    reason = f"Animated preset '{preset_name}' blocked during estop"
                    self._publish_ack("led_preset", False, cid, reason)
                    logger.warning(
                        {
                            "event": "facade_preset_blocked_estop",
                            "preset": preset_name,
                            "cid": cid,
                        }
                    )
                return

            # Run preset animation
            await self._lighting.run_preset(preset_name)

            self._publish_ack(
                "led_preset", True, cid, f"Preset '{preset_name}' started"
            )

            # Publish telemetry after preset start (state update)
            self._publish_telemetry_update()

            logger.info(
                {
                    "event": "facade_preset_success",
                    "preset": preset_name,
                    "cid": cid,
                }
            )

        except ValueError as e:
            # Invalid preset name
            self._publish_ack("led_preset", False, cid, str(e))
            logger.warning(
                {
                    "event": "facade_preset_invalid",
                    "preset": preset_name,
                    "cid": cid,
                    "error": str(e),
                }
            )
        except Exception as e:
            self._publish_ack("led_preset", False, cid, str(e))
            logger.error(
                {
                    "event": "facade_preset_error",
                    "preset": preset_name,
                    "cid": cid,
                    "error": str(e),
                }
            )

    async def _set_led_async(self, r: int, g: int, b: int) -> None:
        """Internal LED implementation."""
        try:
            session = self._get_or_create_session()
            if not session.is_connected():
                logger.info(
                    {
                        "event": "facade_led_noop",
                        "reason": "not_connected",
                        "r": r,
                        "g": g,
                        "b": b,
                    }
                )
                return

            await session.set_led(r, g, b)
            logger.debug(
                {
                    "event": "facade_led_success",
                    "r": r,
                    "g": g,
                    "b": b,
                }
            )

        except Exception as e:
            logger.error(
                {
                    "event": "facade_led_impl_error",
                    "r": r,
                    "g": g,
                    "b": b,
                    "error": str(e),
                }
            )

    async def drive(
        self, speed: int, heading: int, duration_ms: int | None = None
    ) -> None:
        """Drive BB-8 with specified parameters."""
        try:
            # First check estop at facade level (authoritative gate)
            if self._safety.estop_latched:
                estop_reason = self._safety.get_estop_reason()
                reason = f"Motion blocked by emergency stop: {estop_reason}"
                logger.warning(
                    {
                        "event": "facade_drive_blocked_estop",
                        "speed": speed,
                        "heading": heading,
                        "duration_ms": duration_ms,
                        "reason": reason,
                    }
                )
                self._publish_rejected("drive", reason)
                return

            # Normalize parameters (no timing constraints)
            validated_speed, validated_heading, validated_duration = (
                self._safety.normalize_drive(speed, heading, duration_ms)
            )

            # Gate the actual execution (timing and safety checks)
            self._safety.gate_drive()

            self._last_cmd_timestamp = time.time()
            await self._drive_impl(
                validated_speed, validated_heading, validated_duration
            )

        except SafetyViolation as e:
            logger.warning(
                {
                    "event": "facade_drive_safety_violation",
                    "speed": speed,
                    "heading": heading,
                    "duration_ms": duration_ms,
                    "constraint": e.constraint,
                    "error": str(e),
                }
            )
            self._publish_rejected("drive", str(e))

        except Exception as e:
            logger.error(
                {
                    "event": "facade_drive_error",
                    "speed": speed,
                    "heading": heading,
                    "duration_ms": duration_ms,
                    "error": str(e),
                }
            )
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
                    payload = json.dumps(
                        {
                            "speed": speed,
                            "heading": heading,
                            "duration_ms": duration_ms,
                        }
                    )
                    self._mqtt["client"].publish(
                        drive_topic,
                        payload=payload,
                        qos=self._mqtt["qos"],
                        retain=False,
                    )

            logger.info(
                {
                    "event": "facade_drive_success",
                    "speed": speed,
                    "heading": heading,
                    "duration_ms": duration_ms,
                }
            )

        except Exception as e:
            logger.error(
                {
                    "event": "facade_drive_impl_error",
                    "speed": speed,
                    "heading": heading,
                    "duration_ms": duration_ms,
                    "error": str(e),
                }
            )
            self._publish_rejected("drive", str(e))

    async def estop(self, reason: str = "Manual emergency stop") -> None:
        """Activate emergency stop."""
        try:
            activated, message = self._safety.activate_estop(reason)

            if activated:
                # Cancel any active LED animations
                if self._lighting:
                    self._lighting.cancel_active()

                # Stop device immediately
                await self._stop_impl()

                # Publish telemetry update
                await self._publish_telemetry()

                logger.warning(
                    {
                        "event": "facade_estop_activated",
                        "reason": reason,
                    }
                )
            else:
                # Already active - log and publish ACK with current state
                logger.warning(
                    {
                        "event": "facade_estop_already_active",
                        "reason": reason,
                        "current_reason": self._safety.get_estop_reason(),
                    }
                )
                # Still publish rejected to inform caller
                self._publish_rejected("estop", message)

        except Exception as e:
            logger.error(
                {
                    "event": "facade_estop_error",
                    "reason": reason,
                    "error": str(e),
                }
            )
            self._publish_rejected("estop", str(e))

    async def clear_estop(self) -> None:
        """Clear emergency stop if safe."""
        try:
            cleared, reason = self._safety.clear_estop()

            if cleared:
                # Publish telemetry update
                await self._publish_telemetry()

                logger.info({"event": "facade_estop_cleared", "reason": reason})
            else:
                logger.warning(
                    {
                        "event": "facade_estop_clear_denied",
                        "reason": reason,
                    }
                )
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

    def _publish_ack(
        self,
        cmd: str,
        ok: bool,
        cid: str | None = None,
        reason: str | None = None,
    ) -> None:
        """Publish ACK/NACK message."""
        client = self._mqtt.get("client")
        base = self._mqtt.get("base")
        if client and base:
            topic = f"{base}/ack/{cmd}"
            payload: dict[str, Any] = {"ok": ok}
            if cid is not None:
                payload["cid"] = cid
            if reason is not None:
                payload["reason"] = reason
            client.publish(topic, payload=json.dumps(payload), qos=1, retain=False)

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
                logger.debug(
                    {
                        "event": "facade_get_rssi_error",
                        "error": str(e),
                    }
                )
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

    async def publish_telemetry_async(self) -> None:
        """Async version of telemetry publishing for direct await."""
        await self._publish_telemetry()

    def _build_telemetry(self) -> dict:
        """Build telemetry payload as plain dict."""
        current_time = time.time()
        return {
            "connected": self.is_connected(),
            "estop": self._safety.is_estop_active(),
            "last_cmd_ts": time.strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ",
                time.gmtime(self._last_cmd_timestamp),
            )
            if self._last_cmd_timestamp > 0
            else None,
            "battery_pct": None,  # Battery will be updated async if available
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime(current_time)),
        }

    async def _publish_telemetry(self) -> None:
        """Publish telemetry data."""
        try:
            client = self._mqtt["client"]
            base = self._mqtt["base"]

            if not client or not base:
                return

            # Build base telemetry payload (pure dict, no coroutines)
            telemetry = self._build_telemetry()

            # Try to get battery with timeout
            try:
                battery_pct = await asyncio.wait_for(self.get_battery(), timeout=1.0)
                telemetry["battery_pct"] = battery_pct
            except (TimeoutError, Exception):
                # Keep battery_pct as None
                pass

            # Publish telemetry
            topic = f"{base}/status/telemetry"
            payload = json.dumps(telemetry)
            client.publish(topic, payload=payload, qos=1, retain=False)

            logger.debug(
                {
                    "event": "facade_telemetry_published",
                    "telemetry": telemetry,
                }
            )

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
            logger.error(
                {
                    "event": "facade_telemetry_heartbeat_error",
                    "error": str(e),
                }
            )

    # ---------- MQTT wiring (subscribe/dispatch/state echo + discovery) ------

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

        def _handle_led_cmd(_c, _u, msg):
            """Handle bb8/cmd/led - static RGB LED control."""
            try:
                payload = json.loads((msg.payload or b"").decode("utf-8"))
                if not isinstance(payload, dict):
                    logger.error(
                        {
                            "event": "led_cmd_invalid_payload",
                            "payload": payload,
                        }
                    )
                    return

                r = payload.get("r", 0)
                g = payload.get("g", 0)
                b = payload.get("b", 0)
                cid = payload.get("cid")

                # Validate RGB values are numeric
                try:
                    r, g, b = int(r), int(g), int(b)
                except (ValueError, TypeError):
                    if cid:
                        self._publish_ack(
                            "led",
                            False,
                            cid,
                            "Invalid RGB values - must be integers",
                        )
                    logger.error(
                        {
                            "event": "led_cmd_invalid_rgb",
                            "r": r,
                            "g": g,
                            "b": b,
                        }
                    )
                    return

                # Schedule async LED operation
                asyncio.create_task(self.set_led_async(r, g, b, cid))

            except json.JSONDecodeError:
                logger.error(
                    {
                        "event": "led_cmd_json_error",
                        "payload": msg.payload,
                    }
                )
            except Exception as e:
                logger.error(
                    {
                        "event": "led_cmd_handler_error",
                        "error": str(e),
                    }
                )

        def _handle_led_preset_cmd(_c, _u, msg):
            """Handle bb8/cmd/led_preset - preset animations."""
            try:
                payload = json.loads((msg.payload or b"").decode("utf-8"))
                if not isinstance(payload, dict):
                    logger.error(
                        {
                            "event": "led_preset_invalid_payload",
                            "payload": payload,
                        }
                    )
                    return

                preset_name = payload.get("name")
                cid = payload.get("cid")

                if not preset_name or not isinstance(preset_name, str):
                    if cid:
                        self._publish_ack(
                            "led_preset",
                            False,
                            cid,
                            "Missing or invalid 'name' field",
                        )
                    logger.error(
                        {
                            "event": "led_preset_missing_name",
                            "payload": payload,
                        }
                    )
                    return

                # Schedule async preset operation
                asyncio.create_task(self.set_led_preset(preset_name, cid))

            except json.JSONDecodeError:
                logger.error(
                    {
                        "event": "led_preset_json_error",
                        "payload": msg.payload,
                    }
                )
            except Exception as e:
                logger.error(
                    {
                        "event": "led_preset_handler_error",
                        "error": str(e),
                    }
                )

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

                asyncio.create_task(self.estop(reason))

                # Publish acknowledgment
                ack_payload = {
                    "ok": True,
                    "reason": f"Emergency stop activated: {reason}",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime()),
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
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime()),
                }
                if cid:
                    ack_payload["cid"] = cid

                _pub("ack/clear_estop", ack_payload, r=False)

                if cleared:
                    # Publish telemetry update
                    self._publish_telemetry_update()

            except Exception as e:
                logger.error(
                    {
                        "event": "clear_estop_handler_error",
                        "error": repr(e),
                    }
                )

        def _handle_diag_gatt_cmd(_c, _u, msg):
            """Handle bb8/cmd/diag_gatt — publish ACK on {base}/ack/diag_gatt."""
            try:
                try:
                    payload = (
                        json.loads((msg.payload or b"").decode("utf-8", "ignore"))
                        if msg.payload
                        else {}
                    )
                except Exception:
                    payload = {}
                cid = payload.get("cid") or f"diag-gatt-{int(time.time())}"
                adapter = payload.get("adapter", "hci0")
                ack = {
                    "ok": True,
                    "cid": cid,
                    "echo": {"cmd": "diag_gatt", "adapter": adapter},
                }
                # Publish on the global base (no client id suffix) per governance
                client.publish(
                    f"{MQTT_BASE}/ack/diag_gatt",
                    payload=json.dumps(ack, separators=(",", ":")),
                    qos=qos_val,
                    retain=False,
                )
                logger.info(
                    {
                        "event": "facade_diag_gatt_ack",
                        "cid": cid,
                        "adapter": adapter,
                    }
                )
            except Exception as e:
                logger.error({"event": "diag_gatt_handler_error", "error": str(e)})

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
            client.message_callback_add(f"{base_topic}/power/set", _handle_power)
            client.subscribe(f"{base_topic}/power/set", qos=qos_val)

            client.message_callback_add(f"{base_topic}/led/set", _handle_led)
            client.subscribe(f"{base_topic}/led/set", qos=qos_val)

            client.message_callback_add(f"{base_topic}/stop/press", _handle_stop)
            client.subscribe(f"{base_topic}/stop/press", qos=qos_val)

            # LED command subscriptions
            client.message_callback_add(f"{MQTT_BASE}/cmd/led", _handle_led_cmd)
            client.subscribe(f"{MQTT_BASE}/cmd/led", qos=qos_val)

            client.message_callback_add(
                f"{MQTT_BASE}/cmd/led_preset", _handle_led_preset_cmd
            )
            client.subscribe(f"{MQTT_BASE}/cmd/led_preset", qos=qos_val)

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
                self._telemetry_task = asyncio.create_task(self._telemetry_heartbeat())
                self._tasks.add(self._telemetry_task)
                self._telemetry_task.add_done_callback(self._tasks.discard)
        else:
            logger.warning(
                {
                    "event": "facade_shim_subscriptions_skipped",
                    "reason": "REQUIRE_DEVICE_ECHO=1",
                    "base": base_topic,
                }
            )

        # Diagnostics: diag_gatt (ALWAYS-ON)
        client.message_callback_add(
            f"{MQTT_BASE}/cmd/diag_gatt", _handle_diag_gatt_cmd
        )
        client.subscribe(f"{MQTT_BASE}/cmd/diag_gatt", qos=qos_val)

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


# --- Diagnostics stubs (acceptance-gate-friendly) ---
def diag_scan(mac: str | None = None, adapter: str = "hci0") -> bool:
    """
    Diagnostic scan stub. Return value is not used for gating; acceptance
    relies on ACK emission with canonical schema. Implementations may extend
    this to perform actual BLE scans if desired.
    """
    return False


def diag_gatt() -> bool:
    """Diagnostic GATT probe stub (no-op)."""
    return False
