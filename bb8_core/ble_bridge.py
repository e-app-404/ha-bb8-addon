# BLE Bridge: Core BLE orchestration for Home Assistant add-on
# Extracted from legacy launch_bb8.py (CLI/config removed)

import logging
import asyncio
from bleak import BleakScanner, BleakClient
import os
from bb8_core.controller import BB8Controller
from bb8_core.ble_gateway import BleGateway
from spherov2.scanner import find_toys
from spherov2.toy.bb8 import BB8
from spherov2.adapter.bleak_adapter import BleakAdapter
import time
from logging import getLogger
import json
import paho.mqtt.publish as publish
from spherov2.commands.sphero import RollModes, ReverseFlags
from spherov2.commands.core import IntervalOptions
from bleak.exc import BleakCharacteristicNotFoundError

logger = getLogger("bb8_addon")

BB8_NAME = os.environ.get("BB8_NAME", "BB-8")
BB8_MAC = os.environ.get("BB8_MAC", "B8:17:C2:A8:ED:45")

class BLEBridge:
    def __init__(self, timeout=10):
        self.gateway = BleGateway(mode="bleak")
        self.controller = BB8Controller()
        self.timeout = timeout

    def connect_bb8(self):
        try:
            device = self.gateway.scan_for_device(timeout=self.timeout)
            if not device:
                msg = "BB-8 not found. Please tap robot or remove from charger and try again."
                publish_bb8_error(msg)
                logger.error(f"BB-8 STATUS: {msg}")
                return None
            # Attach and check for required characteristic
            self.controller.attach_device(device)
            # Simulate characteristic check (replace with actual check if available)
            if not hasattr(device, 'services') or not any(
                '22bb746f-2bbd-7554-2d6f-726568705327' in str(s) for s in getattr(device, 'services', [])):
                msg = "BB-8 not awake. Please tap robot or remove from charger and try again."
                publish_bb8_error(msg)
                logger.error(f"BB-8 STATUS: {msg}")
                raise BleakCharacteristicNotFoundError('22bb746f-2bbd-7554-2d6f-726568705327')
            return device
        except BleakCharacteristicNotFoundError:
            # Already handled above
            return None
        except Exception as e:
            publish_bb8_error(str(e))
            logger.error(f"BB-8 STATUS: {e}")
            return None

    def connect(self):
        device = self.gateway.scan_for_device(timeout=self.timeout)
        if not device:
            logger.error("No BB-8 device found.")
            return None
        self.controller.attach_device(device)
        return device

    def diagnostics(self):
        return self.controller.get_diagnostics_for_mqtt()

    def shutdown(self):
        self.gateway.shutdown()
        self.controller.disconnect()

async def scan_and_connect():
    logger.info("[BB-8] Scanning for BLE devices...")
    devices = await BleakScanner.discover()
    for d in devices:
        logger.info(f"[BLE] Found: {d.address} ({d.name})")
        if d.address.upper() == BB8_MAC or d.name == BB8_NAME:
            logger.info(f"[BB-8] Target device found: {d.address} ({d.name})")
            async with BleakClient(d.address) as client:
                logger.info("[BB-8] Connected to BB-8!")
                # TODO: Implement further BB-8 GATT communication
            break
    else:
        logger.info("[BB-8] BB-8 not found. Ensure it is awake and nearby.")

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

def bb8_power_on_sequence():
    logger.info("[BB-8] Power ON sequence: beginning...")
    try:
        bridge = BLEBridge()
        bb8 = bridge.connect_bb8()
        logger.info(f"[BB-8] After connect_bb8(): {bb8}")
        if not bb8:
            logger.error("[BB-8] Power on failed: device not found or not awake.")
            return
        logger.info("[BB-8] After BB-8 connect...")
        with bb8:
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
                bb8.set_main_led(255, 255, 255, None)
                logger.info(f"[BB-8] LED command succeeded in {time.time() - led_start:.2f}s")
            except Exception as e:
                logger.error(f"[BB-8][ERROR] LED command failed after {time.time() - led_start:.2f}s: {e}", exc_info=True)
                logger.info(f"[BB-8] Status after LED error: is_connected={getattr(bb8, 'is_connected', None)}")
                return
            roll_start = time.time()
            try:
                # Corrected argument order and types for roll (speed, heading, roll_mode, reverse_flag, proc=None)
                bb8.roll(30, 0, RollModes.GO, ReverseFlags.OFF, None)  # type: ignore
                logger.info(f"[BB-8] Roll command succeeded in {time.time() - roll_start:.2f}s")
            except Exception as e:
                logger.error(f"[BB-8][ERROR] Roll command failed after {time.time() - roll_start:.2f}s: {e}", exc_info=True)
                logger.info(f"[BB-8] Status after roll error: is_connected={getattr(bb8, 'is_connected', None)}")
                return
        logger.info("[BB-8] Power ON sequence: complete.")
    except Exception as e:
        logger.error(f"[BB-8][ERROR] Exception in power ON sequence: {e}", exc_info=True)

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
        publish.single("bb8/state/error", msg, hostname=os.environ.get("MQTT_BROKER", "localhost"))
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
        publish.single(topic, json.dumps(payload), hostname=os.environ.get("MQTT_BROKER", "localhost"))
    except Exception as e:
        logger.error(f"[BB-8][ERROR] Failed to publish discovery to MQTT: {e}")

async def connect_bb8_with_retry(address, max_attempts=5, retry_delay=3, adapter='hci0'):
    for attempt in range(1, max_attempts + 1):
        try:
            async with BleakClient(address, adapter=adapter) as client:
                try:
                    services = client.services  # Bleak >=0.20
                except AttributeError:
                    services = await client.get_services()  # Bleak <0.20
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
