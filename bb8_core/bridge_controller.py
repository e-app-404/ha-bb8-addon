"""
bridge_controller.py

Orchestrates BLE and MQTT setup for the BB-8 add-on:
- Resolves BB-8 MAC (env/options.json/auto-detect).
- Initializes BLE gateway + BLE bridge.
- Starts the MQTT dispatcher for Home Assistant integration.
- Emits a single version probe and structured logs.

All code lives inside functions; only the __main__ guard executes main().
"""
from __future__ import annotations

from typing import Optional, Tuple, Dict, Any
import signal
import time
import threading
import os
import json
import logging

try:
    import yaml  # PyYAML
except Exception:  # pragma: no cover
    yaml = None  # handled gracefully; options.json is valid JSON which yaml.safe_load can parse too

# Internal imports
from .version_probe import probe
from .logging_setup import logger
from .auto_detect import resolve_bb8_mac
from .ble_gateway import BleGateway
from .ble_bridge import BLEBridge
from .mqtt_dispatcher import start_mqtt_dispatcher


# -------- Config helpers --------
def _as_bool(v: Any, default: bool) -> bool:
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    s = str(v).strip().lower()
    return s in {"1", "true", "yes", "y", "on"}


def _read_options(path: str) -> Dict[str, Any]:
    """Read /data/options.json (JSON, but YAML loader also accepts it). Return {} on failure."""
    try:
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        # Prefer yaml.safe_load to accept both JSON and YAML
        if yaml is not None:
            return yaml.safe_load(text) or {}
        return json.loads(text or "{}")
    except Exception as e:
        logger.warning({"event": "options_read_failed", "path": path, "error": repr(e)})
        return {}


def load_runtime_config() -> Dict[str, Any]:
    """
    Coalesce runtime config from env -> /data/options.json -> safe defaults.
    Returns a dict with normalized keys used by the controller.
    """
    opts_path = "/data/options.json"
    opts = _read_options(opts_path)

    # BLE / BB-8
    bb8_mac = (os.environ.get("BB8_MAC_OVERRIDE") or opts.get("bb8_mac") or "").strip() or None
    ble_adapter = os.environ.get("BLE_ADAPTER") or opts.get("ble_adapter") or "hci0"

    # MQTT
    mqtt_host = os.environ.get("MQTT_BROKER") or opts.get("mqtt_broker") or "core-mosquitto"
    mqtt_port_raw = os.environ.get("MQTT_PORT") or opts.get("mqtt_port") or "1883"
    try:
        mqtt_port = int(mqtt_port_raw)
    except Exception:
        mqtt_port = 1883

    mqtt_user = os.environ.get("MQTT_USERNAME") or opts.get("mqtt_username")
    mqtt_password = os.environ.get("MQTT_PASSWORD") or opts.get("mqtt_password")
    mqtt_topic = os.environ.get("MQTT_TOPIC_PREFIX") or opts.get("mqtt_topic_prefix") or "bb8"

    # Behavior
    scan_seconds = int(os.environ.get("SCAN_SECONDS") or opts.get("scan_seconds") or 5)
    rescan_on_fail = _as_bool(os.environ.get("RESCAN_ON_FAIL") or opts.get("rescan_on_fail"), True)
    cache_ttl_hours = int(os.environ.get("CACHE_TTL_HOURS") or opts.get("cache_ttl_hours") or 24)

    # Dispatcher tuning
    client_id = os.environ.get("MQTT_CLIENT_ID") or opts.get("mqtt_client_id") or "bb8-addon"
    keepalive = int(os.environ.get("MQTT_KEEPALIVE") or opts.get("mqtt_keepalive") or 60)
    qos = int(os.environ.get("MQTT_QOS") or opts.get("mqtt_qos") or 1)
    retain = _as_bool(os.environ.get("MQTT_RETAIN") or opts.get("mqtt_retain"), True)
    tls = _as_bool(os.environ.get("MQTT_TLS") or opts.get("mqtt_tls"), False)

    cfg: Dict[str, Any] = {
        "bb8_mac": bb8_mac,
        "ble_adapter": ble_adapter,
        "mqtt_host": mqtt_host,
        "mqtt_port": mqtt_port,
        "mqtt_user": mqtt_user,
        "mqtt_password": mqtt_password,
        "mqtt_topic": mqtt_topic,
        "scan_seconds": scan_seconds,
        "rescan_on_fail": rescan_on_fail,
        "cache_ttl_hours": cache_ttl_hours,
        "client_id": client_id,
        "keepalive": keepalive,
        "qos": qos,
        "retain": retain,
        "tls": tls,
    }
    logger.debug({"event": "runtime_config_loaded", **{k: (v if k not in {"mqtt_password"} else bool(v)) for k, v in cfg.items()}})
    return cfg


# -------- Dispatcher compatibility shim --------
def _start_dispatcher_compat(func, supplied: Dict[str, Any]) -> Any:
    """
    Start MQTT dispatcher, pruning/aliasing kwargs to match the function signature.
    Supports both legacy ('host','port','topic','user','password','controller')
    and new-style ('mqtt_host','mqtt_port','mqtt_topic','username','passwd','bridge') names.
    """
    import inspect
    sig = inspect.signature(func)

    # canonical values we derive once
    offered = {
        "host":        supplied.get("host"),
        "port":        supplied.get("port"),
        "topic":       supplied.get("topic"),
        "user":        supplied.get("user"),
        "password":    supplied.get("password"),
        "controller":  supplied.get("controller"),
        "status_topic": supplied.get("status_topic", "bb8/status"),
        "client_id":   supplied.get("client_id"),
        "keepalive":   supplied.get("keepalive", 60),
        "qos":         supplied.get("qos", 1),
        "retain":      supplied.get("retain", True),
        "tls":         supplied.get("tls", False),
    }

    # map dispatcher param names -> keys in offered
    aliases = {
        "mqtt_host": "host",
        "mqtt_port": "port",
        "mqtt_topic": "topic",
        "username":  "user",
        "passwd":    "password",
        "bridge":    "controller",
        "topic_prefix": "topic",
    }

    pruned: Dict[str, Any] = {}
    for name in sig.parameters.keys():
        if name in offered:
            pruned[name] = offered[name]
        elif name in aliases and aliases[name] in offered:
            pruned[name] = offered[aliases[name]]

    # redact password for debug
    dbg = {k: (bool(v) if k == "password" else v) for k, v in pruned.items()}
    try:
        from .logging_setup import logger
        logger.debug({"event": "dispatcher_call_args", **dbg})
    except Exception:
        pass

    return func(**pruned)


# -------- Core orchestration --------
def _wait_forever(client, bridge) -> None:
    """Block the main thread until SIGTERM/SIGINT; then shutdown cleanly."""
    stop = threading.Event()

    def _handle(sig, _frame):
        try:
            from .logging_setup import logger
            logger.info({"event": "shutdown_signal", "signal": int(sig)})
        except Exception:
            pass
        stop.set()

    for s in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        try:
            signal.signal(s, _handle)
        except Exception:
            # Some platforms may not allow setting SIGHUP; ignore
            pass

    try:
        while not stop.is_set():
            time.sleep(1.0)
    finally:
        # orderly teardown
        try:
            client.loop_stop()
            client.disconnect()
        except Exception:
            pass
        try:
            if hasattr(bridge, "shutdown"):
                bridge.shutdown()
        except Exception:
            pass

def start_bridge_controller(cfg: Dict[str, Any]) -> None:
    """
    Bring up BLE gateway + bridge, resolve target MAC if needed, and start MQTT dispatcher.
    """
    logger.info({
        "event": "bridge_controller_start",
        "bb8_mac_cli": bool(cfg.get("bb8_mac")),
        "scan_seconds": cfg.get("scan_seconds"),
        "rescan_on_fail": cfg.get("rescan_on_fail"),
        "cache_ttl_hours": cfg.get("cache_ttl_hours"),
    })

    # Initialize BLE gateway
    gw = BleGateway(mode="bleak", adapter=cfg.get("ble_adapter"))
    logger.info({"event": "ble_gateway_init", "mode": gw.mode, "adapter": cfg.get("ble_adapter")})

    # Resolve BB-8 MAC if not provided
    target_mac: Optional[str] = (cfg.get("bb8_mac") or "").strip() or None
    if not target_mac:
        logger.info({
            "event": "bb8_mac_resolve_start",
            "strategy": "auto_detect",
            "scan_seconds": cfg.get("scan_seconds"),
            "cache_ttl_hours": cfg.get("cache_ttl_hours"),
            "adapter": cfg.get("ble_adapter"),
        })
        target_mac = resolve_bb8_mac(
            scan_seconds=cfg.get("scan_seconds", 5),
            cache_ttl_hours=cfg.get("cache_ttl_hours", 24),
            rescan_on_fail=cfg.get("rescan_on_fail", True),
            adapter=cfg.get("ble_adapter"),
        )
        logger.info({"event": "bb8_mac_resolve_success", "bb8_mac": target_mac})
    else:
        logger.info({"event": "bb8_mac_resolve_bypass", "reason": "env_or_options", "bb8_mac": target_mac})

    # Construct bridge
    bridge = BLEBridge(gateway=gw, target_mac=target_mac, ble_adapter=cfg.get("ble_adapter"))
    logger.info({"event": "ble_bridge_init", "target_mac": target_mac})

    # MQTT parameters
    mqtt_host = cfg.get("mqtt_host") or "localhost"
    mqtt_port = int(cfg.get("mqtt_port") or 1883)
    mqtt_topic = cfg.get("mqtt_topic") or "bb8"
    mqtt_user = cfg.get("mqtt_user")
    mqtt_password = cfg.get("mqtt_password")

    logger.info({
        "event": "mqtt_dispatcher_start",
        "host": mqtt_host,
        "port": mqtt_port,
        "topic": mqtt_topic,
        "user": bool(mqtt_user),
        "password_supplied": bool(mqtt_password),
    })


    client = _start_dispatcher_compat(
        start_mqtt_dispatcher,
        {
            "host": mqtt_host,
            "port": mqtt_port,
            "topic": mqtt_topic,
            "user": mqtt_user,
            "password": mqtt_password,
            "status_topic": "bb8/status",
            "controller": bridge,
            "client_id": cfg.get("client_id"),
            "keepalive": cfg.get("keepalive", 60),
            "qos": cfg.get("qos", 1),
            "retain": cfg.get("retain", True),
            "tls": cfg.get("tls", False),
        },
    )

    # ⬇️ keep the service alive; shuts down cleanly on SIGTERM/SIGINT
    _wait_forever(client, bridge)


# -------- Entry point --------
def main() -> None:
    # Single, final version probe (no preface “missing” lines)
    logging.getLogger("bb8_addon").info(probe())
    cfg = load_runtime_config()
    start_bridge_controller(cfg)


if __name__ == "__main__":
    main()
