from __future__ import annotations

"""
auto_detect.py

Device discovery and auto-detection logic, scans for BB-8 and caches MAC address.
"""
import asyncio
import contextlib
import json
import os
import re
import threading
import time
from typing import Any, Iterable, List, Optional, Tuple

from .addon_config import load_config
from .ble_gateway import BleGateway
from .logging_setup import logger

# Lazy import for testability
with contextlib.suppress(ImportError):
    from bleak import BleakClient, BleakScanner  # type: ignore

CFG, SRC = load_config()
CACHE_PATH: str = CFG.get("CACHE_PATH", "/data/bb8_mac_cache.json")
CACHE_DEFAULT_TTL_HOURS: int = CFG.get("CACHE_DEFAULT_TTL_HOURS", 24)

__all__ = [
    "resolve_bb8_mac",
    "load_mac_from_cache",
    "save_mac_to_cache",
    "scan_for_bb8",
    "pick_bb8_mac",
    "CACHE_PATH",
    "CACHE_DEFAULT_TTL_HOURS",
]


class Candidate:
    def __init__(self, mac: str, name: str = "", rssi: Any = None):
        self.mac = mac
        self.name = name
        self.rssi = rssi


def _valid_mac(mac: str) -> bool:
    return bool(re.fullmatch(r"([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", mac or ""))


def _now() -> float:
    return time.time()


def load_cache(now: float, ttl_hours: int, cache_path: str) -> Optional[Candidate]:
    if not cache_path or not os.path.exists(cache_path):
        return None
    try:
        with open(cache_path, "r") as f:
            data = json.load(f)
        if ttl_hours > 0:
            age_hours = (now - data.get("last_seen_epoch", 0)) / 3600.0
            if age_hours > ttl_hours:
                return None
        if not _valid_mac(data.get("mac", "")):
            return None
        return Candidate(
            mac=data["mac"], name=data.get("advertised_name", ""), rssi=None
        )
    except Exception:
        return None


def save_cache(mac: str, name: str, cache_path: str) -> None:
    payload = {
        "mac": mac,
        "advertised_name": name or "",
        "last_seen_epoch": int(_now()),
        "source": "discovery",
    }
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(payload, f)


def is_probable_bb8(name: Optional[str]) -> bool:
    if not name:
        return False
    name_l = name.lower()
    return any(t in name_l for t in ("bb-8", "droid", "sphero"))


async def async_scan_for_bb8(scan_seconds: int) -> List[Candidate]:
    devices = await BleakScanner.discover(timeout=scan_seconds)  # type: ignore[name-defined]
    out: List[Candidate] = []
    for d in devices:
        name = getattr(d, "name", None)
        if is_probable_bb8(name):
            out.append(
                Candidate(
                    mac=getattr(d, "address", ""),
                    name=name or "",
                    rssi=getattr(d, "rssi", None),
                )
            )

    # Sort: exact name first, stronger RSSI, then MAC
    def score(c: Candidate) -> Tuple[int, int, str]:
        exact = 1 if c.name.lower() == "bb-8" else 0
        rssi = c.rssi if isinstance(c.rssi, int) else -999
        return (exact, rssi, c.mac)

    out.sort(key=score, reverse=True)
    return out


def resolve_bb8_mac(
    scan_seconds: int,
    cache_ttl_hours: int,
    rescan_on_fail: bool,
    adapter: Optional[str] = None,
) -> str:
    mac = load_mac_from_cache(ttl_hours=cache_ttl_hours)
    if mac:
        logger.info({"event": "auto_detect_cache_hit", "bb8_mac": mac})
        return mac
    logger.info({"event": "auto_detect_cache_miss"})
    devices = scan_for_bb8(scan_seconds=scan_seconds, adapter=adapter)
    logger.info({"event": "auto_detect_scan_complete", "count": len(devices)})
    mac = pick_bb8_mac(devices)
    if not mac:
        logger.warning({"event": "auto_detect_scan_no_match"})
        if not rescan_on_fail:
            raise RuntimeError("BB-8 not found during scan and rescan_on_fail is False")
        logger.info({"event": "auto_detect_rescan_retry"})
        devices = scan_for_bb8(scan_seconds=scan_seconds, adapter=adapter)
        mac = pick_bb8_mac(devices)
        logger.info({"event": "auto_detect_rescan_complete", "count": len(devices)})
        if not mac:
            raise RuntimeError("BB-8 not found after rescan")
    save_mac_to_cache(mac)
    logger.info({"event": "auto_detect_cache_write", "bb8_mac": mac})
    return mac


def load_mac_from_cache(ttl_hours: int = CACHE_DEFAULT_TTL_HOURS) -> Optional[str]:
    cache_path = CFG.get("CACHE_PATH", CACHE_PATH)
    try:
        st = os.stat(cache_path)
        age_hours = (time.time() - st.st_mtime) / 3600.0
        if age_hours > max(1, ttl_hours):
            logger.debug({"event": "auto_detect_cache_stale", "age_hours": age_hours})
            return None
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        mac = data.get("bb8_mac")
        return mac
    except FileNotFoundError:
        return None
    except Exception as e:
        logger.warning({"event": "auto_detect_cache_error", "error": repr(e)})
        return None


def save_mac_to_cache(mac: str) -> None:
    cache_path = CFG.get("CACHE_PATH", CACHE_PATH)
    try:
        os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump({"bb8_mac": mac, "saved_at": time.time()}, f)
    except Exception as e:
        logger.warning({"event": "auto_detect_cache_write_error", "error": repr(e)})


def scan_for_bb8(scan_seconds: int, adapter: Optional[str]) -> list[dict]:
    gw = BleGateway(mode="bleak", adapter=adapter)
    try:
        loop = asyncio.new_event_loop()
        t = threading.Thread(target=loop.run_forever, name="BB8ScanThread", daemon=True)
        t.start()
        fut = asyncio.run_coroutine_threadsafe(gw.scan(seconds=scan_seconds), loop)
        result = fut.result()
        loop.call_soon_threadsafe(loop.stop)
        return result
    except RuntimeError:
        return asyncio.run(gw.scan(seconds=scan_seconds))
    except Exception as e:
        logger.warning({"event": "auto_detect_scan_error", "error": repr(e)})
        return []


def pick_bb8_mac(devices: Iterable[dict]) -> Optional[str]:
    candidates = []
    for d in devices:
        name = (d.get("name") or "").upper()
        addr = d.get("address")
        if not addr:
            continue
        if "BB-8" in name or "SPHERO" in name:
            candidates.append(addr)
    if candidates:
        return candidates[0]
    for d in devices:
        addr = d.get("address")
        if isinstance(addr, str) and len(addr.split(":")) == 6:
            return addr
    return None


# Minimal Options class for async connect_bb8
class Options:
    def __init__(
        self,
        scan_seconds,
        cache_ttl_hours,
        rescan_on_fail,
        adapter=None,
        cache_path=None,
    ):
        self.scan_seconds = scan_seconds
        self.cache_ttl_hours = cache_ttl_hours
        self.rescan_on_fail = rescan_on_fail
        self.adapter = adapter
        self.cache_path = cache_path or CACHE_PATH


async def connect_bb8(opts: Options):
    mac = resolve_bb8_mac(
        scan_seconds=opts.scan_seconds,
        cache_ttl_hours=opts.cache_ttl_hours,
        rescan_on_fail=opts.rescan_on_fail,
        adapter=getattr(opts, "adapter", None),
    )

    async def _try(mac_addr: str):
        logger.info({"event": "connect_attempt", "mac": mac_addr})
        async with BleakClient(mac_addr) as client:  # type: ignore[name-defined]
            if not client.is_connected:
                raise RuntimeError("Connected=False after context enter")
            return client

    try:
        return await _try(mac)
    except Exception as e:
        logger.warning({"event": "connect_fail", "error": str(e)})
        if not opts.rescan_on_fail:
            raise
        logger.info({"event": "rescan_trigger"})
        candidates = await async_scan_for_bb8(opts.scan_seconds)
        if not candidates:
            raise RuntimeError("Rescan found no BB-8 candidates.") from e
        winner = candidates[0]
        save_cache(winner.mac, winner.name, opts.cache_path)
        return await _try(winner.mac)
