# bb8_presence_scanner.py
# Daemon: Periodically scans for BB-8, publishes presence and RSSI to MQTT

import asyncio
from bleak import BleakScanner
import paho.mqtt.publish as publish
import os
import logging

BB8_NAME = os.getenv("BB8_NAME", "BB-8")
SCAN_INTERVAL = int(os.getenv("BB8_SCAN_INTERVAL", "10"))  # seconds
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bb8_presence_scanner")

def publish_discovery():
    # MQTT Discovery for presence
    presence_payload = {
        "name": "BB-8 Presence",
        "unique_id": "bb8_presence_001",
        "state_topic": "bb8/sensor/presence",
        "payload_on": "on",
        "payload_off": "off",
        "device_class": "connectivity"
    }
    publish.single(
        "homeassistant/binary_sensor/bb8_presence/config",
        payload=str(presence_payload).replace("'", '"'),
        hostname=MQTT_HOST
    )
    # MQTT Discovery for RSSI
    rssi_payload = {
        "name": "BB-8 RSSI",
        "unique_id": "bb8_rssi_001",
        "state_topic": "bb8/sensor/rssi",
        "unit_of_measurement": "dBm"
    }
    publish.single(
        "homeassistant/sensor/bb8_rssi/config",
        payload=str(rssi_payload).replace("'", '"'),
        hostname=MQTT_HOST
    )

async def scan_and_publish():
    publish_discovery()
    while True:
        try:
            devices = await BleakScanner.discover()
            found = False
            rssi = None
            for d in devices:
                if BB8_NAME.lower() in (d.name or "").lower():
                    found = True
                    # Try all known ways to get RSSI for Bleak BLEDevice
                    rssi = getattr(d, 'rssi', None)
                    if rssi is None:
                        rssi = getattr(d, 'details', {}).get('rssi')
                    logger.info(f"Found BB-8: {d.name} [{d.address}] RSSI: {rssi}")
                    break
            publish.single("bb8/sensor/presence", "on" if found else "off", hostname=MQTT_HOST)
            if rssi is not None:
                publish.single("bb8/sensor/rssi", str(rssi), hostname=MQTT_HOST)
            else:
                publish.single("bb8/sensor/rssi", "", hostname=MQTT_HOST)
        except Exception as e:
            logger.error(f"Presence scan error: {e}")
        await asyncio.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    asyncio.run(scan_and_publish())
