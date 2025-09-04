"""
ble_gateway.py

Handles BLE adapter selection, device scanning, and connection status for BB-8
device management.
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
        self.device = None
        logger.info(
            {"event": "ble_gateway_init", "mode": self.mode, "adapter": self.adapter}
        )
        logger.debug(
            {
                "event": "ble_gateway_init_debug",
                "mode": self.mode,
                "adapter": str(self.adapter),
            }
        )
        logger.debug(
            {
                "event": "ble_gateway_init_state",
                "connected": self.connected,
                "class": str(type(self)),
            }
        )

    def resolve_adapter(self) -> str | None:  # pragma: no cover
        logger.debug({"event": "ble_gateway_resolve_adapter", "adapter": self.adapter})
        return self.adapter

    async def scan(self, seconds: int = 5) -> list[dict]:  # pragma: no cover
        logger.debug({"event": "ble_scan_start", "mode": self.mode, "seconds": seconds})
        if self.mode != "bleak" or BleakScanner is None:
            logger.debug(
                {"event": "ble_scan_bypass", "reason": "unsupported_or_missing_bleak"}
            )
            return []
        devices = await BleakScanner.discover(timeout=seconds)  # type: ignore[call-arg]  # pragma: no cover
        logger.debug(
            {
                "event": "ble_scan_devices_found",
                "devices": [getattr(d, "address", None) for d in devices],
            }
        )
        result = []
        for d in devices:
            logger.debug(
                {
                    "event": "ble_scan_device_detail",
                    "name": getattr(d, "name", None),
                    "address": getattr(d, "address", None),
                    "rssi": getattr(d, "rssi", None),
                }
            )
            result.append(
                {
                    "name": getattr(d, "name", None),
                    "address": getattr(d, "address", None),
                    "rssi": getattr(d, "rssi", None),
                }
            )
        logger.info(
            {"event": "ble_scan_complete", "count": len(result), "devices": result}
        )
        return result

    def get_connection_status(self):  # pragma: no cover
        status = {"connected": getattr(self, "device", None) is not None}
        logger.debug(
            {
                "event": "ble_status",
                "status": status,
                "device": str(getattr(self, "device", None)),
            }
        )
        return status

    def shutdown(self):  # pragma: no cover
        logger.info({"event": "ble_gateway_shutdown"})
        try:
            logger.debug(
                {
                    "event": "ble_gateway_shutdown_pre",
                    "device": str(getattr(self, "device", None)),
                }
            )
            self.device = None
            logger.debug({"event": "ble_gateway_shutdown_device_none"})
        except Exception as e:
            logger.error(
                {"event": "ble_gateway_shutdown_error", "error": str(e)}, exc_info=True
            )
