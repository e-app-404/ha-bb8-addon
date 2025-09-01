"""
╔═════════════════════════════════════════════════════════════════════╗
  BB-8 BLE GATT Scanner • Prints all Services and Characteristics   #
  Requirements: bleak==0.20+, Python 3.8+                           #
  Usage: python3 scan_bb8_gatt.py --adapter hci0 [--bb8_name BB8]   #
╚═════════════════════════════════════════════════════════════════════╝
"""

import argparse
import asyncio

from bleak import BleakClient, BleakScanner


async def main(adapter, bb8_name):
    print(f"Scanning for BB-8 (name: {bb8_name}) on {adapter} ...")
    device = None
    async with BleakScanner(adapter=adapter) as scanner:  # pragma: no cover
        await asyncio.sleep(4)  # pragma: no cover
        for d in scanner.discovered_devices:  # pragma: no cover
            if (
                bb8_name and bb8_name.lower() in (d.name or "").lower()
            ):  # pragma: no cover
                device = d  # pragma: no cover
                break  # pragma: no cover
        if not device and scanner.discovered_devices:  # pragma: no cover
            # Fallback: pick first Sphero/SpheroBB type device
            for d in scanner.discovered_devices:  # pragma: no cover
                if (
                    "sphero" in (d.name or "").lower()
                    or "bb8" in (d.name or "").lower()
                ):  # pragma: no cover
                    device = d  # pragma: no cover
                    break  # pragma: no cover
    if not device:  # pragma: no cover
        print(
            "BB-8 not found. Is it awake and advertising? "
            "Try tapping or removing from charger."
        )  # pragma: no cover
        return  # pragma: no cover

    print(f"Found BB-8: {device.name} [{device.address}]")  # pragma: no cover
    async with BleakClient(device, adapter=adapter) as client:  # pragma: no cover
        print("Connected. Querying services/characteristics...")  # pragma: no cover
        services = await client.get_services()  # pragma: no cover
        for service in services:  # pragma: no cover
            print(
                f"\n[Service] {service.uuid} | {service.description}"
            )  # pragma: no cover
            for char in service.characteristics:  # pragma: no cover
                props = ",".join(char.properties)  # pragma: no cover
                print(
                    f"  [Characteristic] {char.uuid} | "
                    f"{char.description} | properties: {props}"
                )  # pragma: no cover


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
