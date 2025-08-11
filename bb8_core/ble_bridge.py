#
"""
ble_bridge.py

Orchestrates BLE operations for BB-8, manages device connection, and exposes diagnostics for Home Assistant add-on integration.
"""
# Extracted from legacy launch_bb8.py (CLI/config removed)

from __future__ import annotations

from typing import Optional, Any, List, Tuple
import contextlib
import re
import asyncio
import importlib.metadata
import json
import logging
import os
import time

from bleak import BleakScanner, BleakClient
from bleak.exc import BleakCharacteristicNotFoundError
import paho.mqtt.publish as publish

from bb8_core.controller import BB8Controller
from bb8_core.ble_gateway import BleGateway
from bb8_core.logging_setup import logger
from spherov2.adapter.bleak_adapter import BleakAdapter
from spherov2.commands.core import IntervalOptions
from spherov2.commands.sphero import RollModes, ReverseFlags
from spherov2.scanner import find_toys
from spherov2.toy.bb8 import BB8

from .ble_utils import resolve_services
from .core import Core

BB8_NAME = os.environ.get("BB8_NAME", "BB-8")
BB8_MAC = os.environ.get("BB8_MAC", "B8:17:C2:A8:ED:45")

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
    def __init__(self, gateway, target_mac: Optional[str] = None, mac: Optional[str] = None, **kwargs) -> None:
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
        publish.single("bb8/state/error", msg, hostname=os.environ.get("MQTT_BROKER", "core-mosquitto"))
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
        publish.single(topic, json.dumps(payload), hostname=os.environ.get("MQTT_BROKER", "core-mosquitto"))
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
        "identifiers": [f"bb8_{bb8_mac.replace(':','')}"] ,
        "name": "Sphero BB-8",
        "model": "BB-8",
        "manufacturer": "Sphero"
    }
    publish_discovery(
        "homeassistant/switch/bb8_power/config",
        {
            "name": "BB-8 Power",
            "unique_id": "bb8_power_switch",
            "command_topic": "bb8/command/power",
            "state_topic": "bb8/state/power",
            "payload_on": "ON",
            "payload_off": "OFF",
            "device": base_device,
        }
    )
    publish_discovery(
        "homeassistant/light/bb8_led/config",
        {
            "name": "BB-8 LED",
            "unique_id": "bb8_led",
            "command_topic": "bb8/command",
            "schema": "json",
            "rgb_command_template": "{{ {'command': 'set_led', 'r': red, 'g': green, 'b': blue} | tojson }}",
            "device": base_device,
        }
    )
    publish_discovery(
        "homeassistant/button/bb8_roll/config",
        {
            "name": "BB-8 Roll",
            "unique_id": "bb8_roll",
            "command_topic": "bb8/command",
            "payload_press": '{"command": "roll", "heading": 0, "speed": 50}',
            "device": base_device,
        }
    )
    publish_discovery(
        "homeassistant/button/bb8_stop/config",
        {
            "name": "BB-8 Stop",
            "unique_id": "bb8_stop",
            "command_topic": "bb8/command",
            "payload_press": '{"command": "stop"}',
            "device": base_device,
        }
    )
    publish_discovery(
        "homeassistant/sensor/bb8_heartbeat/config",
        {
            "name": "BB-8 Heartbeat",
            "unique_id": "bb8_heartbeat",
            "state_topic": "bb8/state/heartbeat",
            "device": base_device,
        }
    )
    publish_discovery(
        "homeassistant/sensor/bb8_error/config",
        {
            "name": "BB-8 Error State",
            "unique_id": "bb8_error",
            "state_topic": "bb8/state/error",
            "device": base_device,
        }
    )
    # MQTT Discovery for presence
    publish_discovery(
        "homeassistant/binary_sensor/bb8_presence/config",
        {
            "name": "BB-8 Presence",
            "unique_id": "bb8_presence_001",
            "state_topic": "bb8/sensor/presence",
            "payload_on": "on",
            "payload_off": "off",
            "device_class": "connectivity",
            "device": base_device,
        }
    )
    # MQTT Discovery for RSSI
    publish_discovery(
        "homeassistant/sensor/bb8_rssi/config",
        {
            "name": "BB-8 RSSI",
            "unique_id": "bb8_rssi_001",
            "state_topic": "bb8/sensor/rssi",
            "unit_of_measurement": "dBm",
            "device": base_device,
        }
    )
# [2025-08-08 xx:xx] Copilot patch: BLE Watchdog, Core Entity Surfacing, and Dynamic Discovery
# implemented for enhanced customization of  BB-8 control.
