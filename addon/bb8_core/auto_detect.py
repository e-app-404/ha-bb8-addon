# Async passive BLE presence monitor for async environments
import asyncio
import contextlib
import json
import os
import tempfile
import threading
import time
from typing import Any

import yaml

# from .addon_config import load_config  # Duplicate import removed
from .logging_setup import logger

# Centralized config loading
with contextlib.suppress(ImportError):
    pass  # type: ignore
# BleakClient import removed since it's not used


async def async_monitor_bb8_presence(
    scan_interval=30,
    absence_timeout=300,
    debounce_count=2,
    async_ble_scan_fn=None,
    registry_write_fn=None,
    mqtt_publish_fn=None,
):
    """
    Async passive BLE presence monitor loop.
    Args are the same as monitor_bb8_presence, but uses async BLE scan and async sleep.
    """
    last_state = None
    absent_since = None
    consecutive_misses = 0
    registry_data = {}
    mac = None
    name = None
    rssi = None
    while True:
        try:
            if async_ble_scan_fn:
                devices = await async_ble_scan_fn(scan_seconds=5, adapter=None)
            else:
                devices = await scan_for_bb8(scan_seconds=5)
            found = False
            now = time.time()
            for d in devices:
                if is_probable_bb8(d.get("name")):
                    found = True
                    mac = d.get("address")
                    name = d.get("name")
                    rssi = d.get("rssi")
                    break
            if found:
                consecutive_misses = 0
                absent_since = None
            else:
                consecutive_misses += 1
                if consecutive_misses >= debounce_count and absent_since is None:
                    absent_since = now
            present = found or consecutive_misses < debounce_count
            absence_duration = int(now - absent_since) if absent_since else 0
            payload = {
                "bb8_mac": mac or "",
                "advertised_name": name or "",
                "last_seen_epoch": (
                    int(now)
                    if found
                    else registry_data.get(mac, {}).get("last_seen_epoch", 0)
                ),
                "last_checked_epoch": int(now),
                "rssi": rssi if found else None,
                "present": bool(present),
                "absence_timeout_sec": absence_duration,
                "source": "presence_monitor",
            }
            if mac:
                registry_data[mac] = payload
                atomic_write_yaml(
                    REGISTRY_PATH, registry_data, write_fn=registry_write_fn
                )
            if present != last_state:
                logger.info(
                    {
                        "event": "bb8_presence_change",
                        "state": "present" if present else "absent",
                        "timestamp": now,
                        "mac": mac,
                        "rssi": rssi,
                        "absence_timeout_sec": absence_duration,
                    }
                )
                publish_presence_mqtt(
                    "present" if present else "absent",
                    mac,
                    rssi,
                    absence_timeout,
                    mqtt_publish_fn=mqtt_publish_fn,
                )
            last_state = present
        # Log registry write errors for diagnostics and recovery
        except Exception as e:
            logger.error({"event": "bb8_presence_monitor_error", "error": repr(e)})
        await asyncio.sleep(scan_interval)


# Example async BLE scan mock for CI/unit testing
async def mock_async_ble_scan(scan_seconds=5, adapter=None):
    await asyncio.sleep(0.01)
    return [{"address": "00:11:22:33:44:55", "name": "BB-8", "rssi": -60}]


# Usage in async tests:
# await async_monitor_bb8_presence(
#     async_ble_scan_fn=mock_async_ble_scan,
#     registry_write_fn=mock_registry_write,
#     mqtt_publish_fn=mock_mqtt_publish,
# )
"""
auto_detect.py
----------------
Passive BLE presence tracking and registry automation for BB-8 Home Assistant add-on.

Features:
- Continuously monitors BLE presence of BB-8 devices.
- Updates central YAML registry with all surfaced device signals (MAC, name, RSSI, etc.).
- Publishes presence state changes to MQTT (configurable topic).
- Config-driven operation: scan interval, absence timeout, debounce count, cache/registry paths.
- Thread-safe, atomic registry writes.
- Robust error handling and logging.

Integration:
- Entrypoint: passive monitor runs in background thread.
- Registry: YAML file at REGISTRY_PATH, keyed by MAC.
- MQTT: publishes to topic 'bb8/presence/<mac>' (configurable in future).

Config keys (from config.yaml):
    SCAN_INTERVAL_SEC: BLE scan interval (seconds)
    ABSENCE_TIMEOUT_SEC: Absence timeout before marking device absent (seconds)
    DEBOUNCE_COUNT: Consecutive misses before marking absent
    CACHE_PATH: Path for MAC cache file
    CACHE_DEFAULT_TTL_HOURS: Cache TTL (hours)
    REGISTRY_PATH: Path for device registry YAML
    MQTT_PRESENCE_TOPIC_BASE: Base MQTT topic for presence notifications (default: "bb8/presence")

Registry format (YAML):
    <mac>:
        bb8_mac: <mac>
        advertised_name: <name>
        last_seen_epoch: <timestamp>
        last_checked_epoch: <timestamp>
        rssi: <rssi>
        present: <bool>
        absence_timeout_sec: <int>
        source: "presence_monitor"

MQTT topic/payload:
    Topic: bb8/presence/<mac>
    Payload: {
        "state": "present"|"absent",
        "mac": <mac>,
        "rssi": <rssi>,
        "absence_timeout_sec": <int>,
        "timestamp": <float>
    }

Error handling/logging:
- All major operations log events and errors with context for diagnostics.
- Try/except blocks are used in all long-running loops and I/O operations to prevent crashes and surface actionable errors.
- Failure modes include:
    * BLE scan errors (hardware, permissions, adapter issues)
    * Registry write errors (filesystem, permissions, atomicity)
    * MQTT publish errors (network, broker, payload format)
    * Cache read/write errors (corruption, permissions)
- All exceptions are logged with event type, error details, and relevant context.
- Monitor loops are designed to continue running after recoverable errors, with state logged for diagnostics.
- For CI and testing, hooks/mocks can be injected to simulate error conditions and validate error handling.

Usage Example:
    # Entrypoint: starts passive monitor in background thread
    if __name__ == "__main__":
            start_presence_monitor()
            while True:
                    time.sleep(60)
"""

# Centralized imports

from .addon_config import load_config

CFG, SRC = load_config()
SCAN_INTERVAL_SEC = int(CFG.get("SCAN_INTERVAL_SEC", 30))
ABSENCE_TIMEOUT_SEC = int(CFG.get("ABSENCE_TIMEOUT_SEC", 300))
DEBOUNCE_COUNT = int(CFG.get("DEBOUNCE_COUNT", 2))
CACHE_PATH: str = CFG.get("CACHE_PATH", "/data/bb8_mac_cache.json")
CACHE_DEFAULT_TTL_HOURS: int = CFG.get("CACHE_DEFAULT_TTL_HOURS", 24)
REGISTRY_PATH: str = CFG.get("REGISTRY_PATH", "addon/bb8_core/bb8_device_registry.yaml")
MQTT_PRESENCE_TOPIC_BASE: str = CFG.get("MQTT_PRESENCE_TOPIC_BASE", "bb8/presence")


def publish_presence_mqtt(state, mac, rssi, absence_timeout_sec, mqtt_publish_fn=None):
    """
    Publish BB-8 presence state change to MQTT. Replace with your actual MQTT publish utility.
    """
    topic_base = MQTT_PRESENCE_TOPIC_BASE or "bb8/presence"
    topic = f"{topic_base}/{mac or 'unknown'}"
    payload = {
        "state": state,
        "mac": mac,
        "rssi": rssi,
        "absence_timeout_sec": absence_timeout_sec,
        "timestamp": time.time(),
    }
    try:
        if mqtt_publish_fn:
            mqtt_publish_fn(topic, payload)
        else:
            # TODO: Replace with your actual MQTT publish function
            # mqtt_publish(topic, json.dumps(payload))
            logger.info(
                {
                    "event": "bb8_presence_mqtt_publish",
                    "topic": topic,
                    "payload": payload,
                }
            )
    except Exception as e:
        logger.error(
            {
                "event": "bb8_presence_mqtt_publish_error",
                "error": repr(e),
                "topic": topic,
            }
        )


registry_lock = threading.Lock()


# Entrypoint integration: start passive presence monitor in a background thread
def start_presence_monitor():
    t = threading.Thread(
        target=monitor_bb8_presence, name="BB8PresenceMonitor", daemon=True
    )
    t.start()
    logger.info({"event": "bb8_presence_monitor_started"})
    return t


# Atomic YAML write utility for registry updates
def atomic_write_yaml(path, data, write_fn=None):
    """
    Atomically write YAML data to a file, optionally using a custom write function.

    Args:
        path (str): File path
        data (dict): Data to write
        write_fn (callable, optional): Custom write function
    """
    dirpath = os.path.dirname(path)
    try:
        with registry_lock:
            if write_fn:
                write_fn(path, data)
            else:
                with tempfile.NamedTemporaryFile("w", dir=dirpath, delete=False) as tf:
                    yaml.safe_dump(data, tf)
                    tempname = tf.name
                os.replace(tempname, path)
    except Exception as e:
        logger.error(
            {
                "event": "bb8_registry_atomic_write_error",
                "error": repr(e),
                "path": path,
            }
        )


def monitor_bb8_presence(
    scan_interval=SCAN_INTERVAL_SEC,
    absence_timeout=ABSENCE_TIMEOUT_SEC,
    debounce_count=DEBOUNCE_COUNT,
    ble_scan_fn=None,
    registry_write_fn=None,
    mqtt_publish_fn=None,
):
    """
    Passive BLE presence monitor loop (threaded).
    """
    last_state = None
    consecutive_misses = 0
    registry_data = {}
    mac = None
    name = None
    rssi = None
    absent_since = None  # Initialize absent_since to avoid UnboundLocalError
    shutdown_event = threading.Event()
    while not shutdown_event.is_set():
        try:
            if ble_scan_fn:
                devices = ble_scan_fn(scan_seconds=5, adapter=None)
            else:
                import asyncio

                devices = asyncio.run(scan_for_bb8(scan_seconds=5, adapter=None))
            found = False
            now = time.time()
            for d in devices:
                if is_probable_bb8(d.get("name")):
                    found = True
                    mac = d.get("address")
                    name = d.get("name")
                    rssi = d.get("rssi")
                    break
            if found:
                consecutive_misses = 0
                absent_since = None
            else:
                consecutive_misses += 1
                if consecutive_misses >= debounce_count and absent_since is None:
                    absent_since = now
            present = found or consecutive_misses < debounce_count
            absence_duration = int(now - absent_since) if absent_since else 0
            # Build registry payload
            payload = {
                "bb8_mac": mac or "",
                "advertised_name": name or "",
                "last_seen_epoch": (
                    int(now)
                    if found
                    else registry_data.get(mac, {}).get("last_seen_epoch", 0)
                ),
                "last_checked_epoch": int(now),
                "rssi": rssi if found else None,
                "present": bool(present),
                "absence_timeout_sec": absence_duration,
                "source": "presence_monitor",
            }
            if mac:
                registry_data[mac] = payload
                atomic_write_yaml(
                    REGISTRY_PATH, registry_data, write_fn=registry_write_fn
                )
            # State change logging
            if present != last_state:
                logger.info(
                    {
                        "event": "bb8_presence_change",
                        "state": "present" if present else "absent",
                        "timestamp": now,
                        "mac": mac,
                        "rssi": rssi,
                        "absence_timeout_sec": absence_duration,
                    }
                )
                publish_presence_mqtt(
                    "present" if present else "absent",
                    mac,
                    rssi,
                    absence_duration,
                    mqtt_publish_fn=mqtt_publish_fn,
                )
            last_state = present
        except Exception as e:
            logger.error({"event": "bb8_presence_monitor_error", "error": repr(e)})
        # Responsive sleep: check for shutdown every 0.5 seconds
        for _ in range(int(scan_interval * 2)):
            if shutdown_event.is_set():
                break
            time.sleep(0.5)
        time.sleep(scan_interval)


# The following code block was incorrectly indented and merged into monitor_bb8_presence.
# It should be a separate function, which already exists below as update_bb8_registry.
# Remove the duplicate and misplaced code.
def update_bb8_registry(
    mac: str, name: str = "", rssi: Any = None, registry_path: str = REGISTRY_PATH
) -> None:
    """
    Write BB-8 device info to the central registry YAML file.
    Idempotent: overwrites previous entry for this MAC.

    Args:
        mac (str): Device MAC address
        name (str): Advertised name
        rssi (Any): RSSI value
        registry_path (str): Registry file path
    """
    try:
        payload = {
            "bb8_mac": mac,
            "advertised_name": name or "",
            "last_seen_epoch": int(time.time()),
            "rssi": rssi,
            "source": "auto_detect",
        }
        os.makedirs(os.path.dirname(registry_path), exist_ok=True)
        # If registry exists, load and update
        if os.path.exists(registry_path):
            with open(registry_path) as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}
        data[mac] = payload
        with open(registry_path, "w") as f:
            yaml.safe_dump(data, f)
    except Exception as e:
        logger.warning({"event": "bb8_registry_update_error", "error": repr(e)})


def is_probable_bb8(name: str | None) -> bool:
    """
    Heuristic: is this device likely a BB-8?
    Args:
        name (str|None): BLE device name
    Returns:
        bool: True if probable BB-8
    """
    if not name:
        return False
    name_l = name.lower()
    return any(t in name_l for t in ("bb-8", "droid", "sphero"))


def resolve_bb8_mac(
    scan_seconds: int,
    cache_ttl_hours: int,
    rescan_on_fail: bool,
    adapter: str | None = None,
) -> str:
    mac = load_mac_from_cache(ttl_hours=cache_ttl_hours)
    if mac:
        logger.info({"event": "auto_detect_cache_hit", "bb8_mac": mac})
        return mac
    logger.info({"event": "auto_detect_cache_miss"})
    devices = asyncio.run(scan_for_bb8(scan_seconds=scan_seconds, adapter=adapter))
    logger.info({"event": "auto_detect_scan_complete", "count": len(devices)})
    mac = pick_bb8_mac(devices)
    if not mac:
        logger.warning({"event": "auto_detect_scan_no_match"})
        if not rescan_on_fail:
            raise RuntimeError("BB-8 not found during scan and rescan_on_fail is False")
        logger.info({"event": "auto_detect_rescan_retry"})
        import asyncio

        devices = asyncio.run(scan_for_bb8(scan_seconds=scan_seconds, adapter=adapter))
        mac = pick_bb8_mac(devices)
        logger.info(
            {
                "event": "auto_detect_rescan_complete",
                "count": len(devices),
            }
        )
        if not mac:
            raise RuntimeError("BB-8 not found after rescan")
    save_mac_to_cache(mac)
    logger.info({"event": "auto_detect_cache_write", "bb8_mac": mac})
    return mac


def save_mac_to_cache(mac: str, cache_path: str = CACHE_PATH) -> None:
    """
    Save the BB-8 MAC address to the cache file.
    Args:
        mac (str): MAC address to save
        cache_path (str): Path to cache file
    """
    try:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump({"bb8_mac": mac}, f)
    except Exception as e:
        logger.warning({"event": "auto_detect_cache_save_error", "error": repr(e)})


def load_mac_from_cache(ttl_hours: int = CACHE_DEFAULT_TTL_HOURS) -> str | None:
    cache_path = CFG.get("CACHE_PATH", CACHE_PATH)
    try:
        st = os.stat(cache_path)
        age_hours = (time.time() - st.st_mtime) / 3600.0
        if age_hours > max(1, ttl_hours):
            logger.debug(
                {
                    "event": "auto_detect_cache_stale",
                    "age_hours": age_hours,
                }
            )
        with open(cache_path, encoding="utf-8") as f:
            data = json.load(f)
            return data.get("bb8_mac")
    except FileNotFoundError:
        return None
    except Exception as e:
        logger.warning({"event": "auto_detect_cache_error", "error": repr(e)})
        return None


# (Removed outdated comment about missing scan_for_bb8, pick_bb8_mac, and Options class)


async def scan_for_bb8(scan_seconds: int = 5, adapter: str | None = None) -> list[dict]:
    """
    Async scan for BLE devices and return a list of dicts with keys: address, name, rssi

    Args:
        scan_seconds (int): Scan duration
        adapter (str|None): BLE adapter (optional)
    Returns:
        list[dict]: Devices found
    """
    try:
        from bleak import BleakScanner  # type: ignore

        devices = await BleakScanner.discover(timeout=scan_seconds)
        out = []
        for d in devices:
            out.append(
                {
                    "address": getattr(d, "address", ""),
                    "name": getattr(d, "name", ""),
                    "rssi": getattr(d, "rssi", None),
                }
            )
        return out
    except Exception as e:
        logger.warning({"event": "scan_for_bb8_error", "error": repr(e)})
        return []


def pick_bb8_mac(devices: list[dict]) -> str:
    """
    Pick the most probable BB-8 MAC from scanned devices.

    Args:
        devices (list[dict]): Devices from scan
    Returns:
        str: MAC address of best candidate
    """
    candidates = [d for d in devices if is_probable_bb8(d.get("name"))]
    if not candidates:
        return ""
    # Prefer exact name, then strongest RSSI
    candidates.sort(
        key=lambda d: (d.get("name", "").lower() == "bb-8", d.get("rssi", -999)),
        reverse=True,
    )
    return candidates[0].get("address", "")
