from __future__ import annotations

# Explicit export set (helps linters/import tools)
__all__ = [
    "start_bridge_controller",
    # add other public symbols here as needed
]
"""
bridge_controller.py

Orchestrates BLE and MQTT setup for the BB-8 add-on:
- Resolves BB-8 MAC (env/options.json/auto-detect)
- Initializes BLE gateway + BLE bridge
- Starts the MQTT dispatcher for Home Assistant integration
- Emits a single version probe and structured logs

All code lives inside functions; only the __main__ guard executes main().
"""
import asyncio
import json
import os  # Needed for os.environ
import threading
from typing import Any, Dict, Optional

from .addon_config import load_config
from .auto_detect import resolve_bb8_mac
from .ble_bridge import BLEBridge
from .ble_gateway import BleGateway
from .ble_link import BLELink
from .common import CMD_TOPICS, STATE_TOPICS, publish_device_echo
from .evidence_capture import EvidenceRecorder
from .facade import BB8Facade
from .logging_setup import logger

DEFAULT_MQTT_HOST = "localhost"
DEFAULT_MQTT_PORT = 1883

# Client lookup when publishing; avoids import-order issues.
# Removed import of get_client (unknown symbol)


# Client lookup when publishing; avoids import-order issues.
# Define get_client as a stub or import from the correct module
def get_client():
    # TODO: Replace with actual client getter logic
    return None


def _client_or_none():
    c = get_client()
    return c


# so later divergent attempts (e.g., localhost) are suppressed.
from .mqtt_dispatcher import ensure_dispatcher_started

ensure_dispatcher_started()
_ble_loop: Optional[asyncio.AbstractEventLoop] = None
_ble_inited: bool = False
client = None


def on_power_set(payload):
    c = _client_or_none()
    if not c:
        logger.warning("echo_pub skipped (no mqtt client): %s", STATE_TOPICS["power"])
        return
    publish_device_echo(c, STATE_TOPICS["power"], payload)
    logger.info(
        "echo_pub topic=%s retain=false qos=1 source=device", STATE_TOPICS["power"]
    )


def on_stop():
    c = _client_or_none()
    if not c:
        logger.warning("echo_pub skipped (no mqtt client): %s", STATE_TOPICS["stop"])
        return
    publish_device_echo(c, STATE_TOPICS["stop"], "pressed")
    logger.info(
        "echo_pub topic=%s retain=false qos=1 source=device", STATE_TOPICS["stop"]
    )


def on_sleep():
    c = _client_or_none()
    if not c:
        logger.warning("echo_pub skipped (no mqtt client): %s", STATE_TOPICS["sleep"])
        return
    publish_device_echo(c, STATE_TOPICS["sleep"], "idle")
    logger.info(
        "echo_pub topic=%s retain=false qos=1 source=device", STATE_TOPICS["sleep"]
    )


def on_drive(value=None):
    c = _client_or_none()
    if not c:
        logger.warning("echo_pub skipped (no mqtt client): %s", STATE_TOPICS["drive"])
        return
    publish_device_echo(c, STATE_TOPICS["drive"], value)
    logger.info(
        "echo_pub topic=%s retain=false qos=1 source=device", STATE_TOPICS["drive"]
    )


def on_heading(value=None):
    c = _client_or_none()
    if not c:
        logger.warning("echo_pub skipped (no mqtt client): %s", STATE_TOPICS["heading"])
        return
    publish_device_echo(c, STATE_TOPICS["heading"], value)
    logger.info(
        "echo_pub topic=%s retain=false qos=1 source=device", STATE_TOPICS["heading"]
    )


def on_speed(value=None):
    c = _client_or_none()
    if not c:
        logger.warning("echo_pub skipped (no mqtt client): %s", STATE_TOPICS["speed"])
        return
    publish_device_echo(c, STATE_TOPICS["speed"], value)
    logger.info(
        "echo_pub topic=%s retain=false qos=1 source=device", STATE_TOPICS["speed"]
    )


def on_led_set(r, g, b):
    payload = json.dumps({"r": r, "g": g, "b": b})
    c = _client_or_none()
    if not c:
        logger.warning("echo_pub skipped (no mqtt client): %s", STATE_TOPICS["led"])
        return
    c.publish(CMD_TOPICS["led"][0], payload=payload, qos=1, retain=False)
    c.publish(STATE_TOPICS["led"], payload=payload, qos=1, retain=False)
    logger.info(
        "echo_pub topic=%s retain=false qos=1 payload=%s", STATE_TOPICS["led"], payload
    )


def _start_ble_loop_thread() -> asyncio.AbstractEventLoop:
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, name="BLEThread", daemon=True)
    thread.start()
    return loop


def _init_ble_once() -> None:
    """Idempotent BLE init: loop + link runner."""
    global _ble_loop, _ble_inited
    if _ble_inited:
        return
    _ble_loop = _start_ble_loop_thread()
    from . import ble_link

    ble_link.set_loop(_ble_loop)
    ble_link.start()
    _ble_inited = True


# initialize on import
_init_ble_once()


def shutdown_ble() -> None:
    """Called on process termination to avoid pending tasks."""
    from . import ble_link

    ble_link.stop()
    # Note: the loop thread can remain running for process lifetime; if you
    # explicitly stop it, ensure all tasks are cancelled first.


# -------- Config helpers --------
# Removed unused function _as_bool


# -------- Dispatcher compatibility shim --------
def _start_dispatcher_compat(func, supplied: Dict[str, Any]) -> Any:
    """
    Start MQTT dispatcher, pruning/aliasing kwargs to match the function signature.
    Supports both legacy ('host','port','topic','user','password','controller') and new-style ('mqtt_host','mqtt_port','mqtt_topic','username','passwd','bridge') names.
    """
    import inspect

    sig = inspect.signature(func)

    # canonical values we derive once
    offered = {
        "host": supplied.get("host"),
        "port": supplied.get("port"),
        "topic": supplied.get("topic"),
        "user": supplied.get("user"),
        "password": supplied.get("password"),
        "controller": supplied.get("controller"),
        "status_topic": supplied.get("status_topic", "bb8/status"),
        "client_id": supplied.get("client_id"),
        "keepalive": supplied.get("keepalive", 60),
        "qos": supplied.get("qos", 1),
        "retain": supplied.get("retain", True),
        "tls": supplied.get("tls", False),
    }

    # map dispatcher param names -> keys in offered
    aliases = {
        "mqtt_host": "host",
        "mqtt_port": "port",
        "mqtt_topic": "topic",
        "username": "user",
        "passwd": "password",
        "bridge": "controller",
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
# Canonical entry point for controller startup
def start_bridge_controller(
    config: Optional[Dict[str, Any]] = None,
) -> Optional[BB8Facade]:
    """
    Canonical entry point for starting the BB-8 bridge controller.
    Resolves BB-8 MAC, initializes BLE gateway/bridge, starts MQTT dispatcher.
    Accepts optional config dict for testability.
    """
    from .addon_config import load_config
    from .auto_detect import resolve_bb8_mac
    from .ble_bridge import BLEBridge
    from .ble_gateway import BleGateway
    from .facade import BB8Facade
    from .logging_setup import logger
    from .mqtt_dispatcher import ensure_dispatcher_started

    cfg = config or (load_config()[0] if "load_config" in globals() else {})
    logger.info(
        {
            "event": "bridge_controller_start",
            "bb8_mac_cli": bool(cfg.get("bb8_mac")) if cfg else False,
            "scan_seconds": cfg.get("scan_seconds") if cfg else None,
            "rescan_on_fail": cfg.get("rescan_on_fail") if cfg else None,
            "cache_ttl_hours": cfg.get("cache_ttl_hours") if cfg else None,
        }
    )
    gw = BleGateway(mode="bleak", adapter=cfg.get("ble_adapter"))
    logger.info(
        {
            "event": "ble_gateway_init",
            "mode": gw.mode,
            "adapter": cfg.get("ble_adapter"),
        }
    )
    target_mac: Optional[str] = (cfg.get("bb8_mac") or "").strip() or None
    if not target_mac:
        logger.info(
            {
                "event": "bb8_mac_resolve_start",
                "strategy": "auto_detect",
                "scan_seconds": cfg.get("scan_seconds"),
                "cache_ttl_hours": cfg.get("cache_ttl_hours"),
                "adapter": cfg.get("ble_adapter"),
            }
        )
        target_mac = resolve_bb8_mac(
            scan_seconds=cfg.get("scan_seconds", 5),
            cache_ttl_hours=cfg.get("cache_ttl_hours", 24),
            rescan_on_fail=cfg.get("rescan_on_fail", True),
            adapter=cfg.get("ble_adapter"),
        )
        logger.info({"event": "bb8_mac_resolve_success", "bb8_mac": target_mac})
    else:
        logger.info(
            {
                "event": "bb8_mac_resolve_bypass",
                "reason": "env_or_options",
                "bb8_mac": target_mac,
            }
        )
    if not target_mac:
        logger.error(
            {"event": "ble_bridge_init_failed", "reason": "target_mac_missing"}
        )
        raise SystemExit("BB-8 MAC address could not be resolved. Exiting.")
    bridge = BLEBridge(gw, target_mac)
    logger.info({"event": "ble_bridge_init", "target_mac": target_mac})
    facade = BB8Facade(bridge)
    ensure_dispatcher_started()
    logger.info({"event": "bridge_controller_ready"})
    return facade


# Only one canonical definition below (with correct return type)


def _wait_forever(client, bridge, ble=None) -> None:
    """Block the main thread until SIGTERM/SIGINT; then shutdown cleanly."""
    stop = threading.Event()

    def _handle(sig, _frame):
        try:
            from .logging_setup import logger

            logger.info({"event": "shutdown_signal", "signal": int(sig)})
        except Exception:
            pass

    # Example config loading (replace with actual config logic)
    cfg, _ = load_config() if "load_config" in globals() else ({}, None)

    logger.info(
        {
            "event": "bridge_controller_start",
            "bb8_mac_cli": bool(cfg.get("bb8_mac")) if cfg else False,
            "scan_seconds": cfg.get("scan_seconds") if cfg else None,
            "rescan_on_fail": cfg.get("rescan_on_fail") if cfg else None,
            "cache_ttl_hours": cfg.get("cache_ttl_hours") if cfg else None,
        }
    )
    # Initialize BLE gateway
    gw = BleGateway(mode="bleak", adapter=cfg.get("ble_adapter"))
    logger.info(
        {
            "event": "ble_gateway_init",
            "mode": gw.mode,
            "adapter": cfg.get("ble_adapter"),
        }
    )

    # Resolve BB-8 MAC if not provided
    target_mac: Optional[str] = (cfg.get("bb8_mac") or "").strip() or None
    if not target_mac:
        logger.info(
            {
                "event": "bb8_mac_resolve_start",
                "strategy": "auto_detect",
                "scan_seconds": cfg.get("scan_seconds"),
                "cache_ttl_hours": cfg.get("cache_ttl_hours"),
                "adapter": cfg.get("ble_adapter"),
            }
        )
        target_mac = resolve_bb8_mac(
            scan_seconds=cfg.get("scan_seconds", 5),
            cache_ttl_hours=cfg.get("cache_ttl_hours", 24),
            rescan_on_fail=cfg.get("rescan_on_fail", True),
            adapter=cfg.get("ble_adapter"),
        )
        logger.info({"event": "bb8_mac_resolve_success", "bb8_mac": target_mac})
    else:
        logger.info(
            {
                "event": "bb8_mac_resolve_bypass",
                "reason": "env_or_options",
                "bb8_mac": target_mac,
            }
        )

    # Construct bridge and facade (requires target_mac to be non-None)
    if not target_mac:
        logger.error(
            {"event": "ble_bridge_init_failed", "reason": "target_mac_missing"}
        )
        raise SystemExit("BB-8 MAC address could not be resolved. Exiting.")
    bridge = BLEBridge(gw, target_mac)
    logger.info({"event": "ble_bridge_init", "target_mac": target_mac})
    # Removed unused facade assignment
    mqtt_port_val = cfg.get("mqtt_port")
    if mqtt_port_val is not None:
        try:
            mqtt_port = int(mqtt_port_val)
        except Exception:
            mqtt_port = 1883
    else:
        mqtt_port = 1883

    MQTT_TOPIC_DEFAULT = "bb8"
    mqtt_topic = cfg.get("mqtt_topic") or MQTT_TOPIC_DEFAULT
    mqtt_user = cfg.get("mqtt_user")
    mqtt_host = (
        cfg.get("mqtt_host") or DEFAULT_MQTT_HOST
    )  # Added definition for mqtt_host

    # BLE loop thread setup
    ble_loop = asyncio.new_event_loop()
    threading.Thread(target=ble_loop.run_forever, name="BLEThread", daemon=True).start()

    # Start BLE link (all BLE calls must use run_coroutine_threadsafe)
    bb8_mac = (os.environ.get("BB8_MAC") or "").strip() or getattr(
        bridge, "target_mac", None
    )
    ble = None
    try:
        ble = BLELink(bb8_mac)
        try:
            ble.start()
            logger.info(
                {
                    "event": "ble_link_started",
                    "mac": bb8_mac,
                    "adapter": cfg.get("ble_adapter") if cfg else None,
                    "source": "device",
                }
            )
        except Exception as e:
            logger.error(
                {
                    "event": "ble_link_start_failed",
                    "mac": bb8_mac,
                    "error": str(e),
                }
            )
    except Exception as e:
        logger.error({"event": "ble_link_error", "error": str(e)})
    logger.info(
        {
            "event": "mqtt_dispatcher_start",
            "host": mqtt_host,
            "port": mqtt_port,
            "topic": mqtt_topic,
            "user": bool(mqtt_user),
        }
    )
    # Removed unused status_topic assignment
    status_topic = cfg.get("status_topic") if cfg else f"{mqtt_topic}/status"
    # Example usage of dispatcher (replace with actual call)
    # If you need to use dispatcher_args, ensure you reference it later in the code.
    # For now, start the dispatcher directly if needed:
    # start_mqtt_dispatcher(
    #     host=mqtt_host,
    #     port=mqtt_port,
    #     topic=mqtt_topic,
    #     user=mqtt_user,
    #     password=mqtt_password,  # Now uses cfg.get("password")
    #     status_topic=status_topic,
    #     controller=facade,
    #     client_id=cfg.get("client_id") if cfg else None,
    #     keepalive=cfg.get("keepalive") if cfg else None,
    #     qos=cfg.get("qos") if cfg else None,
    #     retain=cfg.get("retain") if cfg else None,
    #     tls=cfg.get("tls") if cfg else None,
    # )
    # start_mqtt_dispatcher(**dispatcher_args)  # Uncomment if dispatcher is needed

    enable_evidence, src_enable = (
        cfg.get("enable_stp4_evidence", True) if cfg else True,
        cfg.get("_prov_enable_stp4_evidence", "default") if cfg else "default",
    )
    report_path, src_report = (
        (
            cfg.get("report_path", "/app/reports/ha_mqtt_trace_snapshot.jsonl")
            if cfg
            else "/app/reports/ha_mqtt_trace_snapshot.jsonl"
        ),
        cfg.get("_prov_evidence_report_path", "default") if cfg else "default",
    )
    topic_prefix, src_topic = (
        cfg.get("mqtt_topic", "bb8") if cfg else "bb8",
        cfg.get("_prov_mqtt_topic", "default") if cfg else "default",
    )
    if enable_evidence:
        try:
            EvidenceRecorder(client, topic_prefix, report_path).start()
            logger.info(
                {
                    "event": "stp4_evidence_recorder_started",
                    "report_path": report_path,
                    "provenance": {
                        "enable_stp4_evidence": src_enable,
                        "evidence_report_path": src_report,
                        "mqtt_topic": src_topic,
                    },
                }
            )
        except Exception as e:
            logger.warning(
                {
                    "event": "stp4_evidence_recorder_error",
                    "error": repr(e),
                    "provenance": {
                        "enable_stp4_evidence": src_enable,
                        "evidence_report_path": src_report,
                        "mqtt_topic": src_topic,
                    },
                }
            )

    # Start telemetry (presence + RSSI) only if enabled
    enable_bridge_telemetry = cfg.get("enable_bridge_telemetry", True)
    telemetry_interval = cfg.get("telemetry_interval_s", 20)
    if enable_bridge_telemetry:
        try:
            from .telemetry import Telemetry

            logger.info(
                {
                    "event": "telemetry_start",
                    "interval_s": telemetry_interval,
                    "role": "bridge",
                }
            )
            telemetry = Telemetry(bridge)
            telemetry.start()
            logger.info(
                {
                    "event": "telemetry_loop_started",
                    "interval_s": telemetry_interval,
                    "role": "bridge",
                }
            )
        except Exception as e:
            logger.warning(
                {"event": "telemetry_error", "error": repr(e), "role": "bridge"}
            )
    else:
        logger.info(
            {
                "event": "telemetry_skipped",
                "reason": "scanner_owns_telemetry",
                "role": "bridge",
            }
        )

    # Removed unused device echo handler functions


# Removed import of register_subscription (unknown symbol)
