from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Tuple, Any
import json, time, os, re, contextlib, logging
import logging_setup  # type: ignore

# Lazy import for testability
with contextlib.suppress(ImportError):
    from bleak import BleakScanner, BleakClient  # type: ignore

logger = logging_setup.logger

DEFAULT_CACHE_PATH = os.getenv("BB8_CACHE_PATH", "/data/bb8_cache.json")

@dataclass
class Options:
    bb8_mac: Optional[str] = ""
    scan_seconds: int = 5
    rescan_on_fail: bool = True
    cache_ttl_hours: int = 720
    cache_path: str = DEFAULT_CACHE_PATH

@dataclass
class Candidate:
    mac: str
    name: str
    rssi: Optional[int]

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
        return Candidate(mac=data["mac"], name=data.get("advertised_name", ""), rssi=None)
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

async def scan_for_bb8(scan_seconds: int) -> List[Candidate]:
    devices = await BleakScanner.discover(timeout=scan_seconds)  # type: ignore[name-defined]
    out: List[Candidate] = []
    for d in devices:
        name = getattr(d, "name", None)
        if is_probable_bb8(name):
            out.append(Candidate(
                mac=getattr(d, "address", ""),
                name=name or "",
                rssi=getattr(d, "rssi", None),
            ))
    # Sort: exact name first, stronger RSSI, then MAC
    def score(c: Candidate) -> Tuple[int, int, str]:
        exact = 1 if c.name.lower() == "bb-8" else 0
        rssi = c.rssi if isinstance(c.rssi, int) else -999
        return (exact, rssi, c.mac)
    out.sort(key=score, reverse=True)
    return out

async def resolve_bb8_mac(opts: Options) -> str:
    now = _now()
    # 1) Override
    if opts.bb8_mac and _valid_mac(opts.bb8_mac.strip()):
        logger.info({"event": "mac_override", "mac": opts.bb8_mac.strip()})
        return opts.bb8_mac.strip()

    # 2) Cache
    cached = load_cache(now, opts.cache_ttl_hours, opts.cache_path)
    if cached:
        logger.info({"event": "cache_hit", "mac": cached.mac, "name": cached.name})
        return cached.mac

    # 3) Scan
    logger.info({"event": "scan_start", "seconds": opts.scan_seconds})
    candidates = await scan_for_bb8(opts.scan_seconds)
    if not candidates:
        raise RuntimeError("No BB-8 devices found. Check adapter, permissions, and RF environment.")
    winner = candidates[0]
    save_cache(winner.mac, winner.name, opts.cache_path)
    logger.info({"event": "scan_winner", "mac": winner.mac, "name": winner.name, "rssi": winner.rssi})
    return winner.mac

async def connect_bb8(opts: Options):
    mac = await resolve_bb8_mac(opts)

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
        candidates = await scan_for_bb8(opts.scan_seconds)
        if not candidates:
            raise RuntimeError("Rescan found no BB-8 candidates.") from e
        winner = candidates[0]
        save_cache(winner.mac, winner.name, opts.cache_path)
        return await _try(winner.mac)
