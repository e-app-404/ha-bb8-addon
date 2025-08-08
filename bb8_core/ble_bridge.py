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

logger = getLogger("bb8_addon")

BB8_NAME = os.environ.get("BB8_NAME", "BB-8")
BB8_MAC = os.environ.get("BB8_MAC", "B8:17:C2:A8:ED:45")

class BLEBridge:
    def __init__(self, timeout=10):
        self.gateway = BleGateway(mode="bleak")
        self.controller = BB8Controller()
        self.timeout = timeout

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
        bb8 = bb8_find()
        logger.info(f"[BB-8] After bb8_find(): {bb8}")
        if not bb8:
            logger.error("[BB-8] Power on failed: device not found.")
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
                bb8.set_main_led(255, 255, 255)
                logger.info(f"[BB-8] LED command succeeded in {time.time() - led_start:.2f}s")
            except Exception as e:
                logger.error(f"[BB-8][ERROR] LED command failed after {time.time() - led_start:.2f}s: {e}", exc_info=True)
                logger.info(f"[BB-8] Status after LED error: is_connected={getattr(bb8, 'is_connected', None)}")
                return
            roll_start = time.time()
            try:
                bb8.roll(0, 30)
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
                bb8.set_main_led(0, 100, 255)
                logger.info(f"[BB-8] LED command succeeded in {time.time() - led_start:.2f}s")
            except Exception as e:
                logger.error(f"[BB-8][ERROR] LED command failed after {time.time() - led_start:.2f}s: {e}", exc_info=True)
                logger.info(f"[BB-8] Status after LED error: is_connected={getattr(bb8, 'is_connected', None)}")
                return
            for i in reversed(range(0, 101, 20)):
                fade_start = time.time()
                try:
                    logger.info(f"[BB-8] Setting LED: (0, {i}, {int(2.55 * i)})")
                    bb8.set_main_led(0, i, int(2.55 * i))
                    logger.info(f"[BB-8] LED fade step succeeded in {time.time() - fade_start:.2f}s")
                except Exception as e:
                    logger.error(f"[BB-8][ERROR] LED fade step failed after {time.time() - fade_start:.2f}s: {e}", exc_info=True)
                    logger.info(f"[BB-8] Status after fade error: is_connected={getattr(bb8, 'is_connected', None)}")
                    return
                time.sleep(0.15)
            off_start = time.time()
            try:
                bb8.set_main_led(0, 0, 0)
                logger.info(f"[BB-8] After LED off in {time.time() - off_start:.2f}s")
            except Exception as e:
                logger.error(f"[BB-8][ERROR] LED off command failed after {time.time() - off_start:.2f}s: {e}", exc_info=True)
                logger.info(f"[BB-8] Status after LED off error: is_connected={getattr(bb8, 'is_connected', None)}")
                return
            sleep_start = time.time()
            try:
                bb8.sleep()
                logger.info(f"[BB-8] After sleep in {time.time() - sleep_start:.2f}s")
            except Exception as e:
                logger.error(f"[BB-8][ERROR] Sleep command failed after {time.time() - sleep_start:.2f}s: {e}", exc_info=True)
                logger.info(f"[BB-8] Status after sleep error: is_connected={getattr(bb8, 'is_connected', None)}")
                return
        logger.info("[BB-8] Power OFF sequence: complete.")
    except Exception as e:
        logger.error(f"[BB-8][ERROR] Exception in power OFF sequence: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(scan_and_connect())
