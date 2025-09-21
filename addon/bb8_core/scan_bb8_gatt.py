"""Small CLI to scan BB-8 BLE GATT characteristics.

This script provides a simple command-line scan helper used by
developers and in tests (where bleak is monkeypatched).
"""

import argparse
import asyncio
import logging

try:
    from bleak import BleakClient as _BleakClient
    from bleak import BleakScanner as _BleakScanner
except ImportError:  # pragma: no cover - fallback for test monkeypatching

    class _BleakScanner:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> object:
            msg = "Monkeypatch in tests"
            raise NotImplementedError(msg)

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
            pass

    class _BleakClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> object:
            msg = "Monkeypatch in tests"
            raise NotImplementedError(msg)

        async def __aexit__(
            self,
            exc_type: object,
            exc: object,
            tb: object,
        ) -> None:
            pass


# Expose the names expected by the rest of the module
BleakScanner = _BleakScanner
BleakClient = _BleakClient
LOG = logging.getLogger(__name__)


async def main(adapter: str, bb8_name: str) -> None:
    """Scan for a BB-8 device using the given adapter and name fragment.

    adapter: BLE adapter name (eg 'hci0').
    bb8_name: substring to match device name.
    """
    LOG.info("Scanning for BB-8 (name: %s) on %s ...", bb8_name, adapter)
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
        LOG.warning(
            "BB-8 not found. Is it awake and advertising? "
            "Try tapping or removing from charger.",
        )
        return
    LOG.info("Found BB-8: %s [%s]", device.name, device.address)
    async with BleakClient(device, adapter=adapter) as client:
        LOG.info("Connected. Querying services/characteristics...")
        services = await client.get_services()
        for service in services:
            LOG.info("\n[Service] %s | %s", service.uuid, service.description)
            for char in service.characteristics:
                props = ",".join(char.properties)
                LOG.info(
                    "  [Characteristic] %s | %s | properties: %s",
                    char.uuid,
                    char.description,
                    props,
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=("Scan BB-8 BLE GATT Characteristics"),
    )
    parser.add_argument(
        "--adapter",
        default="hci0",
        help="BLE adapter name (default: hci0)",
    )
    parser.add_argument(
        "--bb8_name",
        default="BB-8",
        help="Name fragment to identify BB-8 (default: BB-8)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    asyncio.run(main(args.adapter, args.bb8_name))
