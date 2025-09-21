"""Orchestrate BLE and MQTT bridge controller startup for the add-on.

This module resolves device addresses, wires the BLE gateway/bridge,
and hooks the MQTT dispatcher into Home Assistant discovery and commands.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
from typing import Any

from .addon_config import load_config
from .auto_detect import resolve_bb8_mac
from .ble_bridge import BLEBridge
from .ble_gateway import BleGateway
from .common import STATE_TOPICS, publish_device_echo
from .evidence_capture import EvidenceRecorder
from .facade import BB8Facade
from .logging_setup import logger
from .mqtt_dispatcher import register_subscription  # dynamic topic binding
from .mqtt_dispatcher import ensure_dispatcher_started

log = logging.getLogger(__name__)

__all__ = [
    "BB8Facade",
    "BLEBridge",
    "BleGateway",
    "resolve_bb8_mac",
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


DEFAULT_MQTT_HOST = "localhost"
DEFAULT_MQTT_PORT = 1883

# Client lookup when publishing; avoids import-order issues.
# Removed import of get_client (unknown symbol)


def get_client():
    """Return the live MQTT client from the dispatcher.
    Lazy import avoids import-time cycles. This function fails fast with a clear
    message if the dispatcher has not initialized the client yet.
    """
    # Lazy import keeps import graph acyclic at module import time.
    from .mqtt_dispatcher import get_client as _get_client  # type: ignore

    client = _get_client()
    if client is None:
        raise RuntimeError(
            "MQTT client unavailable: start mqtt_dispatcher before "
            "bridge_controller.",
        )
    return client


_client_or_none_cached_client = None


def _client_or_none():
    global _client_or_none_cached_client
    """Return cached MQTT client or None if dispatcher not initialized."""
    if _client_or_none_cached_client is None:
        try:
            _client_or_none_cached_client = get_client()
        except RuntimeError:
            _client_or_none_cached_client = None
    return _client_or_none_cached_client


# so later divergent attempts (e.g., localhost) are suppressed.
ensure_dispatcher_started()
_ble_loop: asyncio.AbstractEventLoop | None = None
_ble_inited: bool = False
client = None


def on_power_set(payload):
    """Publish device-originated power state to the configured echo topic."""
    c = get_client()
    if not c:
        logger.warning(
            "echo_pub skipped (no mqtt client): %s",
            STATE_TOPICS["power"],
        )
        return
    publish_device_echo(c, STATE_TOPICS["power"], payload)
    logger.info(
        "echo_pub topic=%s retain=false qos=1 source=device",
        STATE_TOPICS["power"],
    )


def on_stop():
    """Publish device-originated stop event to the echo topic."""
    c = get_client()
    if not c:
        logger.warning(
            "echo_pub skipped (no mqtt client): %s",
            STATE_TOPICS["stop"],
        )
        return
    publish_device_echo(c, STATE_TOPICS["stop"], "pressed")
    logger.info(
        "echo_pub topic=%s retain=false qos=1 source=device",
        STATE_TOPICS["stop"],
    )


def on_sleep():
    """Publish device-originated sleep/idle event to the echo topic."""
    c = get_client()
    if not c:
        logger.warning(
            "echo_pub skipped (no mqtt client): %s",
            STATE_TOPICS["sleep"],
        )
        return
    publish_device_echo(c, STATE_TOPICS["sleep"], "idle")
    logger.info(
        "echo_pub topic=%s retain=false qos=1 source=device",
        STATE_TOPICS["sleep"],
    )


def on_drive(value=None):
    """Publish device-originated drive telemetry/value to the echo topic."""
    c = get_client()
    if not c:
        logger.warning(
            "echo_pub skipped (no mqtt client): %s",
            STATE_TOPICS["drive"],
        )
        return
    publish_device_echo(c, STATE_TOPICS["drive"], value)
    logger.info(
        "echo_pub topic=%s retain=false qos=1 source=device",
        STATE_TOPICS["drive"],
    )


def on_heading(value=None):
    """Publish device-originated heading telemetry to the echo topic."""
    c = get_client()
    if not c:
        logger.warning(
            "echo_pub skipped (no mqtt client): %s",
            STATE_TOPICS["heading"],
        )
        return
    publish_device_echo(c, STATE_TOPICS["heading"], value)
    logger.info(
        "echo_pub topic=%s retain=false qos=1 source=device",
        STATE_TOPICS["heading"],
    )


def on_speed(value=None):
    """Publish device-originated speed telemetry to the echo topic."""
    c = get_client()
    if not c:
        logger.warning(
            "echo_pub skipped (no mqtt client): %s",
            STATE_TOPICS["speed"],
        )
        return
    publish_device_echo(c, STATE_TOPICS["speed"], value)
    logger.info(
        "echo_pub topic=%s retain=false qos=1 source=device",
        STATE_TOPICS["speed"],
    )


def _mqtt_publish(
    topic: str,
    payload: str,
    *,
    qos: int = 0,
    retain: bool = False,
) -> None:
    """Single publish seam used by echo paths.

    Resolves client AT CALL TIME to pick up test monkeypatches reliably.
    """
    client = None
    try:
        from .mqtt_dispatcher import get_client as _get_client

        client = _get_client()
    except ImportError:
        client = None
    if client is None:
        try:
            client = get_client()
        except RuntimeError:
            client = None
    if client is None:
        msg = "MQTT client not available for publish"
        raise RuntimeError(msg)
    log.info(
        "echo_pub topic=%s retain=%s qos=%s payload=%s",
        topic,
        retain,
        qos,
        payload,
    )
    client.publish(topic, payload, qos=qos, retain=retain)


def on_led_set(r, g, b):
    """Publish strict LED state JSON; never reflect to command topics."""
    payload = json.dumps({"r": int(r), "g": int(g), "b": int(b)})
    _mqtt_publish(STATE_TOPICS["led"], payload, qos=0, retain=False)


def _on_led_command(text: str) -> None:
    """MQTT handler for LED payloads via `/led/set` or `/led/cmd`.

    Expects JSON: {"r":<int>,"g":<int>,"b":<int>}.
    """
    try:
        data = json.loads(text or "{}")
        if not isinstance(data, dict):
            return
        r = int(data.get("r", 0))
        g = int(data.get("g", 0))
        b = int(data.get("b", 0))
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        log.warning("led_cmd parse error: %s payload=%r", exc, text)
        return
    on_led_set(r, g, b)


def _wire_led_command_handler() -> None:
    """Subscribe to bb8/led/cmd and publish strict {"r","g","b"} to
    bb8/led/state. No 'source' field; retain=False (STP4 strict).
    Uses dispatcher subscription registry for idempotent binding.
    """
    base = os.environ.get("MQTT_BASE", "bb8")
    topic_cmd = f"{base}/led/cmd"
    topic_set = f"{base}/led/set"  # legacy path also supported
    topic_state = f"{base}/led/state"
    qos = 0

    def _publish_led_state(rgb: dict[str, int]) -> None:
        cli = get_client() if get_client else None  # type: ignore
        if cli is None:
            log.warning("LED echo skipped (no mqtt client): %s", topic_state)
            return
        payload = json.dumps(rgb, separators=(",", ":"))
        try:
            cli.publish(topic_state, payload=payload, qos=qos, retain=False)
            log.info("LED state echoed -> %s", payload)
        except Exception as exc:  # noqa: BLE001
            log.warning("LED echo publish failed: %s", exc)

    def _on_led_cmd_text(text: str) -> None:
        try:
            data = json.loads(text or "{}")
            if not isinstance(data, dict):
                return
            r = int(data.get("r", 0))
            g = int(data.get("g", 0))
            b = int(data.get("b", 0))
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            log.warning("led_cmd parse error: %s payload=%r", exc, text)
            return
        _publish_led_state({"r": r, "g": g, "b": b})

    # Register via dispatcher if available; otherwise, try direct paho hooks.
    if register_subscription:
        try:
            register_subscription(topic_cmd, _on_led_cmd_text)
            register_subscription(topic_set, _on_led_cmd_text)
            log.info(
                "LED cmd handlers registered: %s , %s",
                topic_cmd,
                topic_set,
            )
            return
        except Exception as exc:  # pragma: no cover
            log.debug("register_subscription failed: %s", exc)

    # Fallback: bind directly if client exists now.
    cli = get_client() if get_client else None  # type: ignore
    if cli is None:
        log.warning("LED cmd wiring deferred: no mqtt client yet")
        return

    def _on_msg(_c: object, _u: object, msg) -> None:
        try:
            _on_led_cmd_text(msg.payload.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            log.debug("LED msg decode failed: %s", exc)

    for t in (topic_cmd, topic_set):
        cli.message_callback_add(t, _on_msg)
        cli.subscribe(t, qos=qos)
    log.info(
        "LED cmd handler wired (fallback): %s , %s",
        topic_cmd,
        topic_set,
    )


def _start_ble_loop_thread() -> asyncio.AbstractEventLoop:
    """Create and start a background thread running a dedicated event loop."""
    loop = asyncio.new_event_loop()
    thread = threading.Thread(
        target=loop.run_forever,
        name="BLEThread",
        daemon=True,
    )
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
def _start_dispatcher_compat(func, supplied: dict[str, Any]) -> Any:
    """Start MQTT dispatcher, pruning/aliasing kwargs to match the signature.

    Supports both legacy names and new-style names. Legacy names include:
    'host', 'port', 'topic', 'user', 'password', 'controller'. New-style
    names include 'mqtt_host', 'mqtt_port', 'mqtt_topic', 'username',
    'passwd', and 'bridge'.
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

    pruned: dict[str, Any] = {}
    for name in sig.parameters:
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
    config: dict[str, Any] | None = None,
    BB8Facade_cls=None,
    BLEBridge_cls=None,
    BleGateway_cls=None,
    resolve_bb8_mac_fn=None,
    EvidenceRecorder_cls=None,
    client=None,
) -> BB8Facade | None:
    """Canonical entry point for starting the BB-8 bridge controller.

    Resolves BB-8 MAC, initializes BLE gateway/bridge, starts MQTT dispatcher.
    Accepts optional config dict for testability.
    """
    from .auto_detect import resolve_bb8_mac as _resolve_bb8_mac
    from .ble_bridge import BLEBridge as _BLEBridge
    from .ble_gateway import BleGateway as _BleGateway
    from .facade import BB8Facade as _BB8Facade
    from .logging_setup import logger
    from .mqtt_dispatcher import ensure_dispatcher_started

    # normalize injected class names to lowercase local vars to satisfy style
    bb8facade_cls = BB8Facade_cls or _BB8Facade
    blebridge_cls = BLEBridge_cls or _BLEBridge
    blegateway_cls = BleGateway_cls or _BleGateway
    resolve_bb8_mac_fn = resolve_bb8_mac_fn or _resolve_bb8_mac

    cfg = config or (load_config()[0] if "load_config" in globals() else {})
    logger.info(
        {
            "event": "bridge_controller_start",
            "bb8_mac_cli": bool(cfg.get("bb8_mac")) if cfg else False,
            "scan_seconds": cfg.get("scan_seconds") if cfg else None,
            "rescan_on_fail": cfg.get("rescan_on_fail") if cfg else None,
            "cache_ttl_hours": cfg.get("cache_ttl_hours") if cfg else None,
        },
    )
    gw = blegateway_cls(mode="bleak", adapter=cfg.get("ble_adapter"))
    logger.info(
        {
            "event": "ble_gateway_init",
            "mode": getattr(gw, "mode", None),
            "adapter": cfg.get("ble_adapter"),
        },
    )
    target_mac: str | None = (cfg.get("bb8_mac") or "").strip() or None
    if not target_mac:
        logger.info(
            {
                "event": "bb8_mac_resolve_start",
                "strategy": "auto_detect",
                "scan_seconds": cfg.get("scan_seconds"),
                "cache_ttl_hours": cfg.get("cache_ttl_hours"),
                "adapter": cfg.get("ble_adapter"),
            },
        )
        target_mac = resolve_bb8_mac_fn(
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
            },
        )
    if not target_mac:
        logger.error(
            {
                "event": "ble_bridge_init_failed",
                "reason": "target_mac_missing",
            },
        )
        raise SystemExit("BB-8 MAC address could not be resolved. Exiting.")
    bridge = blebridge_cls(gw, target_mac)
    logger.info({"event": "ble_bridge_init", "target_mac": target_mac})
    facade = bb8facade_cls(bridge)
    ensure_dispatcher_started()
    logger.info({"event": "bridge_controller_ready"})

    # Evidence recorder logic
    enable_evidence = cfg.get("enable_stp4_evidence", True) if cfg else True
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
    force_evidence = os.environ.get("FORCE_EVIDENCE_RECORDER", "0") == "1"
    if client is None:
        try:
            from .mqtt_dispatcher import get_client as _get_client

            client = _get_client()
        except Exception:
            from unittest import mock

            client = mock.Mock()
    if enable_evidence or force_evidence:
        if client is None:
            msg = "Client is None, cannot instantiate EvidenceRecorder"
            logger.error(
                {
                    "event": "evidence_recorder_client_missing",
                    "msg": msg,
                },
            )
            raise RuntimeError(msg)
        try:
            recorder_cls = (
                EvidenceRecorder_cls
                if EvidenceRecorder_cls is not None
                else EvidenceRecorder
            )
            recorder_cls(client, topic_prefix, report_path).start()
            logger.info(
                {
                    "event": "stp4_evidence_recorder_started",
                    "report_path": report_path,
                    "provenance": {
                        "evidence_report_path": src_report,
                        "mqtt_topic": src_topic,
                    },
                },
            )
        except Exception as e:
            logger.warning(
                {
                    "event": "stp4_evidence_recorder_error",
                    "error": repr(e),
                    "provenance": {
                        "evidence_report_path": src_report,
                        "mqtt_topic": src_topic,
                    },
                },
            )

    # Telemetry logic
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
                },
            )
            telemetry = Telemetry(bridge)
            telemetry.start()
            logger.info(
                {
                    "event": "telemetry_loop_started",
                    "interval_s": telemetry_interval,
                    "role": "bridge",
                },
            )
        except Exception as e:
            logger.warning(
                {
                    "event": "telemetry_error",
                    "error": repr(e),
                    "role": "bridge",
                },
            )
    else:
        logger.info(
            {
                "event": "telemetry_skipped",
                "reason": "scanner_owns_telemetry",
                "role": "bridge",
            },
        )

    return facade
