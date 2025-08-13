from __future__ import annotations
import asyncio
from typing import Optional, Callable
from bleak import BleakClient, BleakScanner

class BLELink:
    def __init__(self, mac: str, on_connected: Callable[[bool], None], on_rssi: Callable[[Optional[int]], None]):
        self.mac, self.on_connected, self.on_rssi = mac, on_connected, on_rssi
        self._stop = False

    async def start(self):
        backoff = [1,2,5,5,5]; i = 0
        while not self._stop:
            try:
                dev = await BleakScanner.find_device_by_address(self.mac, timeout=5.0)
                self.on_rssi(getattr(dev, "rssi", None) if dev else None)
                if not dev: await asyncio.sleep(backoff[min(i,4)]); i+=1; continue
                async with BleakClient(self.mac) as cl:
                    self.on_connected(True); i = 0
                    # minimal verification: confirm connected; extend later with char read
                    _ = cl.is_connected  # property access, not await
                    while cl.is_connected and not self._stop:
                        dev = await BleakScanner.find_device_by_address(self.mac, timeout=3.0)
                        self.on_rssi(getattr(dev, "rssi", None) if dev else None)
                        await asyncio.sleep(5)
            except Exception:
                pass
            finally:
                self.on_connected(False)
                await asyncio.sleep(backoff[min(i,4)]); i+=1

    async def stop(self): self._stop = True
