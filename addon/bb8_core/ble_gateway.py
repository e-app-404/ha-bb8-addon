"""BLE gateway helpers: adapter selection and device scanning.

The BleGateway exposes a small async scan API and connection status
helpers used by higher-level controllers.
"""

from .logging_setup import logger

try:
    from bleak import BleakScanner
except Exception:  # pragma: no cover
    BleakScanner = None  # type: ignore

_initialized = False


def init():
    global _initialized
    if _initialized:
        return
    # existing setup...
    _initialized = True


def initialized():
    return _initialized


class BleGateway:
    def __init__(self, mode: str = "bleak", adapter: str | None = None) -> None:
        self.mode = mode
        self.adapter = adapter
        self.connected: bool = False
        logger.info(
            {
                "event": "ble_gateway_init",
                "mode": self.mode,
                "adapter": self.adapter,
            },
        )
        logger.debug(
            {
                "event": "ble_gateway_init_debug",
                "mode": self.mode,
                "adapter": str(self.adapter),
            },
        )
        logger.debug(
            {
                "event": "ble_gateway_init_state",
                "connected": self.connected,
                "class": str(type(self)),
            },
        )

    def resolve_adapter(self) -> str | None:
        logger.debug(
            {"event": "ble_gateway_resolve_adapter", "adapter": self.adapter},
        )
        return self.adapter

    async def scan(self, seconds: int = 5) -> list[dict]:
        logger.debug(
            {"event": "ble_scan_start", "mode": self.mode, "seconds": seconds},
        )
        if self.mode != "bleak" or BleakScanner is None:
            logger.debug(
                {
                    "event": "ble_scan_bypass",
                    "reason": "unsupported_or_missing_bleak",
                },
            )
            return []
        devices = await BleakScanner.discover(timeout=seconds)  # type: ignore[call-arg]
        logger.debug(
            {
                "event": "ble_scan_devices_found",
                "devices": [getattr(d, "address", None) for d in devices],
            },
        )
        result = []
        for d in devices:
            logger.debug(
                {
                    "event": "ble_scan_device_detail",
                    "name": getattr(d, "name", None),
                    "address": getattr(d, "address", None),
                    "rssi": getattr(d, "rssi", None),
                },
            )
            result.append(
                {
                    "name": getattr(d, "name", None),
                    "address": getattr(d, "address", None),
                    "rssi": getattr(d, "rssi", None),
                },
            )
        logger.info(
            {
                "event": "ble_scan_complete",
                "count": len(result),
                "devices": result,
            },
        )
        return result

    def get_connection_status(self):
        status = {"connected": getattr(self, "device", None) is not None}
        logger.debug(
            {
                "event": "ble_status",
                "status": status,
                "device": str(getattr(self, "device", None)),
            },
        )
        return status

    def shutdown(self):
        logger.info({"event": "ble_gateway_shutdown"})
        device_str = None
        try:
            device_str = str(getattr(self, "device", None))
        except Exception as e:
            # Log the exception with traceback and provide a short message
            logger.exception("ble_gateway shutdown error: %s", e)
            device_str = f"<error: {e}>"
        logger.debug(
            {
                "event": "ble_gateway_shutdown_pre",
                "device": device_str,
            },
        )
        self.device = None
        logger.debug({"event": "ble_gateway_shutdown_device_none"})
