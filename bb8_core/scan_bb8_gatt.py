"""
╔═════════════════════════════════════════════════════════════════════╗
  BB-8 BLE GATT Scanner • Prints all Services and Characteristics   #
  Requirements: bleak==0.20+, Python 3.8+                           #
  Usage: python3 scan_bb8_gatt.py --adapter hci0 [--bb8_name BB8]   #
╚═════════════════════════════════════════════════════════════════════╝
"""

import argparse
import asyncio
import time

from bleak import BleakClient, BleakScanner


async def main(adapter, bb8_name):
    print(f"Scanning for BB-8 (name: {bb8_name}) on {adapter} ...")
    device = None
    async with BleakScanner(adapter=adapter) as scanner:
        await asyncio.sleep(4)
        for d in scanner.discovered_devices:
            if bb8_name and bb8_name.lower() in (d.name or "").lower():
                device = d
                break
        if not device and scanner.discovered_devices:
            # Fallback: pick first Sphero/SpheroBB type device
            for d in scanner.discovered_devices:
                if (
                    "sphero" in (d.name or "").lower()
                    or "bb8" in (d.name or "").lower()
                ):
                    device = d
                    break
    if not device:
        print(
            "BB-8 not found. Is it awake and advertising? "
            "Try tapping or removing from charger."
        )
        return

    print(f"Found BB-8: {device.name} [{device.address}]\n")
    print("Device info:")
    print(f"  MAC: {getattr(device, 'address', None)}")
    print(f"  Name: {getattr(device, 'name', None)}")
    rssi = getattr(device, "rssi", None)
    if rssi is None:
        # Try to get RSSI from BlueZ using busctl shell command
        import subprocess

        path = f"/org/bluez/{adapter}/dev_{device.address.replace(':', '_')}"
        try:
            cmd = [
                "busctl",
                "get-property",
                "org.bluez",
                path,
                "org.bluez.Device1",
                "RSSI",
            ]
            out = subprocess.check_output(cmd, text=True).strip()
            # Output is like 'i -60' (int32)
            parts = out.split()
            rssi = int(parts[1]) if len(parts) == 2 and parts[0] == "i" else None
        except Exception as e:
            print(f"  RSSI: unavailable (busctl query failed: {e})")
            rssi = None
    print(f"  RSSI: {rssi}")
    print(f"  Adapter: {adapter}")
    print(f"  Last seen: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    metadata = getattr(device, "metadata", {})
    print(f"  Metadata: {metadata}")
    print(f"  Advertised services: {metadata.get('uuids', [])}")
    print(f"  Manufacturer data: {metadata.get('manufacturer_data', {})}")
    print(f"  Address type: {metadata.get('address_type', 'unknown')}")
    print(f"  Appearance: {metadata.get('appearance', 'unknown')}")

    async with BleakClient(device, adapter=adapter, timeout=30.0) as client:
        print("\nConnected. Querying services/characteristics...")
        services = client.services
        for service in services:
            print(f"\n[Service] {service.uuid} | {service.description}")
            for char in service.characteristics:
                props = ",".join(char.properties)
                print(
                    f"  [Characteristic] {char.uuid} | {char.description} | "
                    f"properties: {props}"
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scan BB-8 BLE GATT Characteristics")
    parser.add_argument(
        "--adapter", default="hci0", help="BLE adapter name (default: hci0)"
    )
    parser.add_argument(
        "--bb8_name",
        default="BB-8",
        help="Name fragment to identify BB-8 (default: BB-8)",
    )
    args = parser.parse_args()

    asyncio.run(main(args.adapter, args.bb8_name))
