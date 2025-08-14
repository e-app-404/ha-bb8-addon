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

from .addon_config import load_config

# Internal imports
from .version_probe import probe
from .logging_setup import logger
from .auto_detect import resolve_bb8_mac
from .ble_gateway import BleGateway
from .ble_bridge import BLEBridge
from .facade import BB8Facade
from .mqtt_dispatcher import start_mqtt_dispatcher

from .ble_link import BLELink
import asyncio
from .evidence_capture import EvidenceRecorder


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
    # ...removed: replaced by addon_config.py...

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

    # Construct bridge and facade
    bridge = BLEBridge(gateway=gw, target_mac=target_mac, ble_adapter=cfg.get("ble_adapter"))
    logger.info({"event": "ble_bridge_init", "target_mac": target_mac})
    facade = BB8Facade(bridge)
    controller_for_mqtt = facade


    # MQTT parameters (all config and defaults handled in load_runtime_config)
    mqtt_host = cfg.get("mqtt_host") or "localhost"
    mqtt_port_raw = cfg.get("mqtt_port")
    if mqtt_port_raw is not None:
        try:
            mqtt_port = int(mqtt_port_raw)
        except Exception:
            mqtt_port = 1883
    else:
        mqtt_port = 1883
    mqtt_topic = cfg.get("mqtt_topic") or "bb8"
    mqtt_user = cfg.get("mqtt_user")
    mqtt_password = cfg.get("mqtt_password")

    _connected = False  # will be updated by BLELink
    def _emit_connected(val: bool):
        nonlocal _connected
        _connected = val
        client.publish(f"{mqtt_topic}/connected", "online" if val else "offline", qos=1, retain=True)
    def _emit_rssi(rssi):
        if rssi is not None:
            client.publish(f"{mqtt_topic}/rssi", str(int(rssi)), qos=0, retain=False)

    # Start BLE link (stable, verified)
    bb8_mac = os.environ.get("BB8_MAC") or getattr(bridge, "target_mac", None)
    if not bb8_mac:
        logger.warning({"event":"ble_link_mac_missing"})
    else:
        try:
            loop = asyncio.get_event_loop()
            ble = BLELink(bb8_mac, on_connected=_emit_connected, on_rssi=_emit_rssi)
            loop.create_task(ble.start())
            logger.info({"event":"ble_link_started", "mac": bb8_mac})
        except Exception as e:
            logger.warning({"event":"ble_link_error", "error":repr(e)})

    logger.info({
        "event": "mqtt_dispatcher_start",
        "host": mqtt_host,
        "port": mqtt_port,
        "topic": mqtt_topic,
        "user": bool(mqtt_user),
        "password_supplied": bool(mqtt_password),
    })

    # status_topic: configurable or derived from mqtt_topic
    status_topic = cfg.get("status_topic") or f"{mqtt_topic}/status"
    client = _start_dispatcher_compat(
        start_mqtt_dispatcher,
        {
            "host": mqtt_host,
            "port": mqtt_port,
            "topic": mqtt_topic,
            "user": mqtt_user,
            "password": mqtt_password,
            "status_topic": status_topic,
            "controller": controller_for_mqtt,  # now facade
            "client_id": cfg.get("client_id"),
            "keepalive": cfg.get("keepalive"),
            "qos": cfg.get("qos"),
            "retain": cfg.get("retain"),
            "tls": cfg.get("tls"),
        },
    )

    # Start evidence recorder (subscriber-only, unified config)
    # Provenance-aware config loading
    enable_evidence, src_enable = cfg.get("enable_stp4_evidence", True), cfg.get("_prov_enable_stp4_evidence", "default")
    report_path, src_report = cfg.get("evidence_report_path", "/app/reports/ha_mqtt_trace_snapshot.jsonl"), cfg.get("_prov_evidence_report_path", "default")
    topic_prefix, src_topic = cfg.get("mqtt_topic", "bb8"), cfg.get("_prov_mqtt_topic", "default")
    if enable_evidence:
        try:
            EvidenceRecorder(client, topic_prefix, report_path).start()
            logger.info({
                "event": "stp4_evidence_recorder_started",
                "report_path": report_path,
                "provenance": {
                    "enable_stp4_evidence": src_enable,
                    "evidence_report_path": src_report,
                    "mqtt_topic": src_topic,
                }
            })
        except Exception as e:
            logger.warning({
                "event": "stp4_evidence_recorder_error",
                "error": repr(e),
                "provenance": {
                    "enable_stp4_evidence": src_enable,
                    "evidence_report_path": src_report,
                    "mqtt_topic": src_topic,
                }
            })

    # Start telemetry (presence + RSSI) only if enabled
    enable_bridge_telemetry = cfg.get("enable_bridge_telemetry", True)
    telemetry_interval = cfg.get("telemetry_interval_s", 20)
    if enable_bridge_telemetry:
        try:
            from .telemetry import Telemetry
            logger.info({"event": "telemetry_start", "interval_s": telemetry_interval, "role": "bridge"})
            telemetry = Telemetry(bridge)
            telemetry.start()
            logger.info({"event": "telemetry_loop_started", "interval_s": telemetry_interval, "role": "bridge"})
        except Exception as e:
            logger.warning({"event": "telemetry_error", "error": repr(e), "role": "bridge"})
    else:
        logger.info({"event": "telemetry_skipped", "reason": "scanner_owns_telemetry", "role": "bridge"})

    # Register quick-echo handler for power/set topic inside the running controller
    def _on_power_set(_c, _u, msg):
        try:
            payload = msg.payload.decode("utf-8", "ignore").strip().upper()
            if payload not in ("ON","OFF"): return
            # Quick echo so HA has immediate feedback, but tag as "facade"
            client.publish(
                f"{mqtt_topic}/power/state",
                json.dumps({"value": payload, "source": "facade"}),
                qos=1,
                retain=False
            )
            logger.info({"event":"power_ack", "value":payload})
        except Exception as e:
            logger.warning({"event":"power_ack_error", "error":repr(e)})

    # Subscribe to power/set topic for quick-echo after client creation
    client.message_callback_add(f"{mqtt_topic}/power/set", _on_power_set)

    # ⬇️ keep the service alive; shuts down cleanly on SIGTERM/SIGINT
    _wait_forever(client, bridge)


# -------- Entry point --------
def main() -> None:
    # Single, final version probe (no preface “missing” lines)
    logging.getLogger("bb8_addon").info(probe())
    CFG, SRC = load_config()
    cfg = CFG
    # Emit one-shot INFO banner of all active config keys and their sources
    info_cfg = {k: cfg[k] for k in cfg.keys()}
    info_src = {k: SRC.get(k, None) for k in cfg.keys()}
    logger.info({
        "event": "config_effective",
        "cfg": info_cfg,
        "source": info_src
    })
    start_bridge_controller(cfg)


if __name__ == "__main__":
    main()
