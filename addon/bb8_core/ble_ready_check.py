#!/usr/bin/env python3
"""
ble_ready_check.py: Checks if BB-8 BLE device is awake and ready.
Emits a JSON summary artifact and returns exit code 0 if detected, 1 if not.
Leverages existing BLE scan logic from bb8_core modules.
"""

import json
import os
import sys
import time
from pathlib import Path

try:
    from addon.bb8_core.auto_detect import scan_for_bb8
    from bleak import BleakClient
except ImportError:
    print(json.dumps({"error": "Could not import scan_for_bb8 or BleakClient"}))
    sys.exit(2)

SCAN_TIMEOUT = int(os.environ.get("BLE_SCAN_TIMEOUT", "45"))
RETRY_INTERVAL = float(os.environ.get("BLE_SCAN_RETRY_INTERVAL", "2.0"))
MAX_ATTEMPTS = int(
    os.environ.get("BLE_SCAN_MAX_ATTEMPTS", str(SCAN_TIMEOUT // int(RETRY_INTERVAL)))
)
ARTIFACT_PATH = os.environ.get("BLE_READY_ARTIFACT", "/tmp/ble_ready_summary.json")
REGISTRY_PATH = os.environ.get(
    "BB8_REGISTRY_PATH",
    os.path.join(os.path.dirname(__file__), "bb8_device_registry.yaml"),
)

summary = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "attempts": 0,
    "detected": False,
    "device_info": None,
    "error": None,
    "services": [],
    "characteristics": [],
    "rssi": None,
}


def update_registry(device_info, services, characteristics, rssi, last_seen):
    import yaml

    registry = {}
    if Path(REGISTRY_PATH).exists():
        with open(REGISTRY_PATH) as f:
            try:
                registry = yaml.safe_load(f) or {}
            except Exception:
                registry = {}
    updated = False
    # Essentials
    essentials = {
        "bb8_mac": device_info.get("address"),
        "bb8_name": device_info.get("name"),
        "ble_adapter": device_info.get("adapter", "hci0"),
        "bb8_rssi": rssi,
        "bb8_last_seen": last_seen,
        "bb8_services": services,
        "bb8_characteristics": characteristics,
    }
    for k, v in essentials.items():
        if registry.get(k) != v:
            registry[k] = v
            updated = True
    if updated:
        with open(REGISTRY_PATH, "w") as f:
            yaml.safe_dump(registry, f)
    return updated


def main():
    device = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        summary["attempts"] = attempt
        try:
            devices = scan_for_bb8(int(RETRY_INTERVAL), adapter=None)
            if devices:
                device = devices[0]
                summary["detected"] = True
                summary["device_info"] = device
                break
        except Exception as e:
            summary["error"] = str(e)
        time.sleep(RETRY_INTERVAL)
    if summary["detected"] and device:
        # Connect and enumerate services/characteristics
        try:
            from bleak import BleakScanner

            # Find device by MAC
            found = None

            async def find_and_connect():
                scanner = BleakScanner()
                await scanner.start()
                await asyncio.sleep(4)
                await scanner.stop()
                for d in scanner.discovered_devices:
                    if d.address == device.get("address"):
                        return d
                return None

            import asyncio

            ble_device = asyncio.run(find_and_connect())
            if ble_device:
                rssi = getattr(ble_device, "rssi", None)
                summary["rssi"] = rssi
                last_seen = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

                async def connect_and_enumerate():
                    async with BleakClient(ble_device) as client:
                        services = client.services
                        svc_uuids = [svc.uuid for svc in services]
                        char_uuids = []
                        for svc in services:
                            for char in svc.characteristics:
                                char_uuids.append(char.uuid)
                        return svc_uuids, char_uuids

                svcs, chars = asyncio.run(connect_and_enumerate())
                summary["services"] = svcs
                summary["characteristics"] = chars
                # Update registry
                update_registry(device, svcs, chars, rssi, last_seen)
        except Exception as e:
            summary["error"] = f"Service/characteristic enumeration failed: {e}"
    # Emit artifact
    try:
        Path(os.path.dirname(ARTIFACT_PATH)).mkdir(parents=True, exist_ok=True)
        with open(ARTIFACT_PATH, "w") as f:
            json.dump(summary, f, indent=2)
    except Exception as e:
        print(json.dumps({"error": f"Failed to write artifact: {e}"}))
    print(json.dumps(summary))
    sys.exit(0 if summary["detected"] else 1)


if __name__ == "__main__":
    main()
