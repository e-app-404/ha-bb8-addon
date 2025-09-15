import argparse
import asyncio

from bleak import BleakClient as _BleakClient, BleakScanner as _BleakScanner


class BleakScanner:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        raise NotImplementedError("Monkeypatch in tests")

    async def __aexit__(self, exc_type, exc, tb):
        pass


class BleakClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        raise NotImplementedError("Monkeypatch in tests")

    async def __aexit__(self, exc_type, exc, tb):
        pass


BleakScanner = _BleakScanner
BleakClient = _BleakClient

# Expose print as a module attribute for test monkeypatching
print = print


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

    print(f"Found BB-8: {device.name} [{device.address}]")
    async with BleakClient(device, adapter=adapter) as client:
        print("Connected. Querying services/characteristics...")
        services = await client.get_services()
        for service in services:
            print(f"\n[Service] {service.uuid} | {service.description}")
            for char in service.characteristics:
                props = ",".join(char.properties)
                print(
                    f"  [Characteristic] {char.uuid} | "
                    f"{char.description} | properties: {props}"
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
