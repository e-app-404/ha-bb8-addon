# ╔═════════════════════════════════════════════════════════════════════╗
#   BB-8 BLE GATT Scanner • Prints all Services and Characteristics   #
#   Requirements: bleak==0.20+, Python 3.8+                           #
#   Usage: python3 scan_bb8_gatt.py --adapter hci0 [--bb8_name BB8]   #
# ╚═════════════════════════════════════════════════════════════════════╝

import argparse
import asyncio
from bleak import BleakScanner, BleakClient

async def main(adapter, bb8_name):
    print(f"Scanning for BB-8 (name: {bb8_name}) on {adapter} ...")
    device = None
    async with BleakScanner(adapter=adapter) as scanner:
        await asyncio.sleep(4)  # 4 seconds scan window
        for d in scanner.discovered_devices:
            if bb8_name and bb8_name.lower() in (d.name or "").lower():
                device = d
                break
        if not device and scanner.discovered_devices:
            # Fallback: pick first Sphero/SpheroBB type device
            for d in scanner.discovered_devices:
                if "sphero" in (d.name or "").lower() or "bb8" in (d.name or "").lower():
                    device = d
                    break
    if not device:
        print("BB-8 not found. Is it awake and advertising? Try tapping or removing from charger.")
        return

    print(f"Found BB-8: {device.name} [{device.address}]")
    async with BleakClient(device, adapter=adapter) as client:
        print("Connected. Querying services/characteristics...")
        for service in client.services:
            print(f"\n[Service] {service.uuid} | {service.description}")
            for char in service.characteristics:
                props = ','.join(char.properties)
                print(f"  [Characteristic] {char.uuid} | {char.description} | properties: {props}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scan BB-8 BLE GATT Characteristics")
    parser.add_argument("--adapter", default="hci0", help="BLE adapter name (default: hci0)")
    parser.add_argument("--bb8_name", default="BB-8", help="Name fragment to identify BB-8 (default: BB-8)")
    args = parser.parse_args()

    asyncio.run(main(args.adapter, args.bb8_name))
