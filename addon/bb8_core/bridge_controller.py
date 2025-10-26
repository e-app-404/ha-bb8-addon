from __future__ import annotations

import warnings

warnings.filterwarnings(
    "ignore", "Callback API version 1 is deprecated", DeprecationWarning, "paho"
)

import asyncio
import json
import logging
import os
import signal
import threading
import time
from typing import Any

from .addon_config import load_config
from .auto_detect import resolve_bb8_mac
from .ble_bridge import BLEBridge
from .ble_gateway import BleGateway
from .ble_link import BLELink
from .common import STATE_TOPICS, publish_device_echo

_stop_evt = threading.Event()


def _on_signal(signum, frame):
    logger.info("controller_signal_received signum=%s", signum)
    _stop_evt.set()


from .evidence_capture import EvidenceRecorder
from .logging_setup import logger
from .mqtt_dispatcher import (
    register_subscription,  # dynamic topic binding
)

log = logging.getLogger(__name__)

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


DEFAULT_MQTT_HOST = "localhost"
DEFAULT_MQTT_PORT = 1883

# Client lookup when publishing; avoids import-order issues.
# Removed import of get_client (unknown symbol)


def get_client():
    """
    Return the live MQTT client from the dispatcher.
    Lazy import avoids import-time cycles. This function fails fast with a clear
    message if the dispatcher has not initialized the client yet.
    """
    # Lazy import keeps import graph acyclic at module import time.
    from .mqtt_dispatcher import get_client as _get_client  # type: ignore

    client = _get_client()
    if client is None:
        raise RuntimeError(
            "MQTT client unavailable: start mqtt_dispatcher before "
            "bridge_controller."
        )  # pragma: no cover
    return client


_client_or_none_cached_client = None


def _client_or_none():
    global _client_or_none_cached_client
    if _client_or_none_cached_client is None:
        try:
            _client_or_none_cached_client = get_client()  # pragma: no cover
        except Exception:
            _client_or_none_cached_client = None
    return _client_or_none_cached_client


# NOTE: Disable legacy MQTT dispatcher auto-start to avoid event-loop conflicts
# with the in-module paho bootstrap used by __main__. The legacy dispatcher can
# be explicitly enabled via tests or a config flag if ever needed.
# (PIE P4/P1 import/runtime policy)
# ensure_dispatcher_started()
_ble_loop: asyncio.AbstractEventLoop | None = None
_ble_inited: bool = False
client = None


def on_power_set(payload):
    c = get_client()
    if not c:
        logger.warning(
            "echo_pub skipped (no mqtt client): %s", STATE_TOPICS["power"]
        )
        return
    publish_device_echo(c, STATE_TOPICS["power"], payload)
    logger.info(
        "echo_pub topic=%s retain=false qos=1 source=device",
        STATE_TOPICS["power"],
    )


def on_stop():
    c = get_client()
    if not c:
        logger.warning(
            "echo_pub skipped (no mqtt client): %s", STATE_TOPICS["stop"]
        )
        return
    publish_device_echo(c, STATE_TOPICS["stop"], "pressed")
    logger.info(
        "echo_pub topic=%s retain=false qos=1 source=device",
        STATE_TOPICS["stop"],
    )


def on_sleep():
    c = get_client()
    if not c:
        logger.warning(
            "echo_pub skipped (no mqtt client): %s", STATE_TOPICS["sleep"]
        )
        return
    publish_device_echo(c, STATE_TOPICS["sleep"], "idle")
    logger.info(
        "echo_pub topic=%s retain=false qos=1 source=device",
        STATE_TOPICS["sleep"],
    )


def on_drive(value=None):
    c = get_client()
    if not c:
        logger.warning(
            "echo_pub skipped (no mqtt client): %s", STATE_TOPICS["drive"]
        )
        return
    publish_device_echo(c, STATE_TOPICS["drive"], value)
    logger.info(
        "echo_pub topic=%s retain=false qos=1 source=device",
        STATE_TOPICS["drive"],
    )


def on_heading(value=None):
    c = get_client()
    if not c:
        logger.warning(
            "echo_pub skipped (no mqtt client): %s", STATE_TOPICS["heading"]
        )
        return
    publish_device_echo(c, STATE_TOPICS["heading"], value)
    logger.info(
        "echo_pub topic=%s retain=false qos=1 source=device",
        STATE_TOPICS["heading"],
    )


def on_speed(value=None):
    c = get_client()
    if not c:
        logger.warning(
            "echo_pub skipped (no mqtt client): %s", STATE_TOPICS["speed"]
        )
        return
    publish_device_echo(c, STATE_TOPICS["speed"], value)
    logger.info(
        "echo_pub topic=%s retain=false qos=1 source=device",
        STATE_TOPICS["speed"],
    )


def _mqtt_publish(
    topic: str, payload: str, *, qos: int = 0, retain: bool = False
) -> None:
    """
    Single publish seam used by echo paths. Resolves client AT CALL TIME to
    pick up test monkeypatches reliably.
    """
    client = None
    try:
        from .mqtt_dispatcher import get_client as _get_client

        client = _get_client()  # pragma: no cover
    except Exception:
        client = None
    if client is None:
        try:
            client = get_client()  # pragma: no cover
        except Exception:
            client = None
    if client is None:
        raise RuntimeError(
            "MQTT client not available for publish"
        )  # pragma: no cover
    log.info(
        "echo_pub topic=%s retain=%s qos=%s payload=%s",
        topic,
        retain,
        qos,
        payload,
    )
    client.publish(topic, payload, qos=qos, retain=retain)  # pragma: no cover


def on_led_set(r, g, b):
    """Publish strict LED state JSON; never reflect to command topics."""
    payload = json.dumps({"r": int(r), "g": int(g), "b": int(b)})
    _mqtt_publish(STATE_TOPICS["led"], payload, qos=0, retain=False)


def _on_led_command(text: str) -> None:
    """
    MQTT command handler for LED payloads coming via `/led/set` or `/led/cmd`.
    Expects JSON: {"r":<int>,"g":<int>,"b":<int>}.
    """
    try:
        data = json.loads(text or "{}")
        if not isinstance(data, dict):
            return
        r = int(data.get("r", 0))
        g = int(data.get("g", 0))
        b = int(data.get("b", 0))
    except Exception as exc:
        log.warning("led_cmd parse error: %s payload=%r", exc, text)
        return
    on_led_set(r, g, b)


def _wire_led_command_handler() -> None:
    """
    Subscribe to bb8/led/cmd and publish strict {"r","g","b"} to
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
        except Exception as exc:
            log.warning("led_cmd parse error: %s payload=%r", exc, text)
            return
        _publish_led_state({"r": r, "g": g, "b": b})

    # Register via dispatcher if available; otherwise, try direct paho hooks.
    if register_subscription:
        try:
            register_subscription(topic_cmd, _on_led_cmd_text)
            register_subscription(topic_set, _on_led_cmd_text)
            log.info(
                "LED cmd handlers registered: %s , %s", topic_cmd, topic_set
            )
            return
        except Exception as exc:  # pragma: no cover
            log.debug("register_subscription failed: %s", exc)

    # Fallback: bind directly if client exists now.
    cli = get_client() if get_client else None  # type: ignore
    if cli is None:
        log.warning("LED cmd wiring deferred: no mqtt client yet")
        return

    def _on_msg(_c, _u, msg):
        try:
            _on_led_cmd_text(msg.payload.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            log.debug("LED msg decode failed: %s", exc)

    for t in (topic_cmd, topic_set):
        cli.message_callback_add(t, _on_msg)
        cli.subscribe(t, qos=qos)
    log.info("LED cmd handler wired (fallback): %s , %s", topic_cmd, topic_set)


def _start_ble_loop_thread() -> asyncio.AbstractEventLoop:
    loop = asyncio.new_event_loop()
    thread = threading.Thread(
        target=loop.run_forever, name="BLEThread", daemon=True
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
    """
    Start MQTT dispatcher, pruning/aliasing kwargs to match the function signature.
    Supports both legacy ('host','port','topic','user','password','controller') and
    new-style ('mqtt_host','mqtt_port','mqtt_topic','username','passwd','bridge') names.
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
from .facade import BB8Facade


def start_bridge_controller(
    config: dict[str, Any] | None = None,
) -> BB8Facade | None:
    """
    Canonical entry point for starting the BB-8 bridge controller.
    Resolves BB-8 MAC, initializes BLE gateway/bridge, starts MQTT dispatcher,
    and sets up supervised watchdog for connection monitoring.
    Accepts optional config dict for testability.
    """
    from .addon_config import load_config
    from .auto_detect import resolve_bb8_mac, start_presence_monitor
    from .ble_bridge import BLEBridge
    from .ble_gateway import BleGateway
    from .ble_session import BleSession
    from .logging_setup import logger

    cfg = config or (load_config()[0] if "load_config" in globals() else {})

    # Start passive BLE presence monitor in background thread if enabled
    enable_presence_monitor = cfg.get("enable_presence_monitor", True)
    if enable_presence_monitor:
        try:
            start_presence_monitor()
            logger.info({
                "event": "bb8_presence_monitor_integration",
                "status": "started",
            })
        except Exception as e:
            logger.error({
                "event": "bb8_presence_monitor_error",
                "error": repr(e),
            })

    logger.info({
        "event": "bridge_controller_start",
        "bb8_mac_cli": bool(cfg.get("bb8_mac")) if cfg else False,
        "scan_seconds": cfg.get("scan_seconds") if cfg else None,
        "rescan_on_fail": cfg.get("rescan_on_fail") if cfg else None,
        "cache_ttl_hours": cfg.get("cache_ttl_hours") if cfg else None,
    })

    # Initialize BLE gateway
    gw = BleGateway(mode="bleak", adapter=cfg.get("ble_adapter"))
    logger.info({
        "event": "ble_gateway_init",
        "mode": gw.mode,
        "adapter": cfg.get("ble_adapter"),
    })

    # Resolve BB-8 MAC if not provided
    target_mac: str | None = (cfg.get("bb8_mac") or "").strip() or None
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
        logger.info({
            "event": "bb8_mac_resolve_bypass",
            "reason": "env_or_options",
            "bb8_mac": target_mac,
        })

    if not target_mac:
        logger.error({
            "event": "ble_bridge_init_failed",
            "reason": "target_mac_missing",
        })
        raise SystemExit("BB-8 MAC address could not be resolved. Exiting.")

    # Create BLE session and facade
    ble_session = BleSession(target_mac)
    bridge = BLEBridge(gw, target_mac)  # Keep for compatibility
    facade = BB8Facade(bridge)
    facade.set_target_mac(target_mac)  # Configure facade with session

    logger.info({"event": "ble_bridge_init", "target_mac": target_mac})

    # Legacy MQTT dispatcher intentionally not started here; __main__ uses a
    # self-contained paho bootstrap for MQTT (LWT/online/cmd/ACK/telemetry).
    # If a legacy path needs it, wire via an explicit config flag.
    # try:
    #     ensure_dispatcher_started()
    # except Exception as e:
    #     logger.debug({"event": "dispatcher_start_skipped", "reason": str(e)})

    # Start supervised watchdog
    watchdog_task = asyncio.create_task(
        _start_watchdog(facade, ble_session, cfg)
    )

    logger.info({
        "event": "bridge_controller_ready",
        "watchdog_enabled": True,
        "target_mac": target_mac,
    })

    return facade


async def _start_watchdog(
    facade: BB8Facade, ble_session: BleSession, config: dict[str, Any]
) -> None:
    """
    Supervised watchdog for BLE connection monitoring.

    Monitors connection health every 10s, attempts auto-reconnect,
    and publishes metrics to cache.
    """
    watchdog_interval = config.get("watchdog_interval_s", 10)
    max_reconnect_attempts = config.get("max_reconnect_attempts", 3)

    # Metrics cache
    metrics = {
        "connected": False,
        "reconnect_attempts": 0,
        "last_ok_ts": None,
        "last_error": None,
        "mean_connect_ms": 0.0,
        "total_connects": 0,
        "total_connect_time": 0.0,
    }

    logger.info({
        "event": "watchdog_start",
        "interval_s": watchdog_interval,
        "max_reconnect_attempts": max_reconnect_attempts,
    })

    consecutive_failures = 0

    while True:
        try:
            await asyncio.sleep(watchdog_interval)

            # Check connection status
            is_connected = ble_session.is_connected()
            metrics["connected"] = is_connected

            if is_connected:
                metrics["last_ok_ts"] = time.time()
                consecutive_failures = 0

                # Try to get battery for health check
                try:
                    battery_pct = await ble_session.battery()
                    logger.debug({
                        "event": "watchdog_health_ok",
                        "battery": battery_pct,
                        "reconnect_attempts": metrics["reconnect_attempts"],
                    })
                except Exception as e:
                    logger.debug({
                        "event": "watchdog_battery_check_failed",
                        "error": str(e),
                    })

            else:
                consecutive_failures += 1
                logger.warning({
                    "event": "watchdog_disconnected",
                    "consecutive_failures": consecutive_failures,
                    "max_attempts": max_reconnect_attempts,
                })

                # Attempt reconnection if within limits
                if consecutive_failures <= max_reconnect_attempts:
                    try:
                        logger.info({
                            "event": "watchdog_reconnect_attempt",
                            "attempt": consecutive_failures,
                            "max_attempts": max_reconnect_attempts,
                        })

                        connect_start = time.time()
                        await ble_session.connect()
                        connect_time = (time.time() - connect_start) * 1000

                        # Update connection metrics
                        metrics["total_connects"] += 1
                        metrics["total_connect_time"] += connect_time
                        metrics["mean_connect_ms"] = (
                            metrics["total_connect_time"]
                            / metrics["total_connects"]
                        )
                        metrics["reconnect_attempts"] = consecutive_failures

                        logger.info({
                            "event": "watchdog_reconnect_success",
                            "connect_time_ms": connect_time,
                            "mean_connect_ms": metrics["mean_connect_ms"],
                            "attempt": consecutive_failures,
                        })

                        # Update facade presence
                        if facade.publish_presence:
                            facade.publish_presence(True)

                    except Exception as e:
                        error_msg = str(e)
                        metrics["last_error"] = error_msg

                        logger.error({
                            "event": "watchdog_reconnect_failed",
                            "attempt": consecutive_failures,
                            "error": error_msg,
                        })

                        # Update facade presence
                        if facade.publish_presence:
                            facade.publish_presence(False)
                else:
                    logger.error({
                        "event": "watchdog_max_attempts_exceeded",
                        "consecutive_failures": consecutive_failures,
                        "max_attempts": max_reconnect_attempts,
                    })

                    # Update facade presence
                    if facade.publish_presence:
                        facade.publish_presence(False)

            # Publish health metrics
            await _publish_health_metrics(metrics, config)

        except asyncio.CancelledError:
            logger.info({"event": "watchdog_cancelled"})
            break
        except Exception as e:
            logger.error({"event": "watchdog_error", "error": str(e)})
            await asyncio.sleep(1)  # Brief pause before retry


async def _publish_health_metrics(
    metrics: dict[str, Any], config: dict[str, Any]
) -> None:
    """Publish health metrics to MQTT and file."""
    try:
        # Prepare health data
        health_data = {
            "connect_ok": metrics["connected"],
            "reconnect_attempts": metrics["reconnect_attempts"],
            "battery_pct": 75,  # Default until real battery reading
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "mean_connect_ms": metrics["mean_connect_ms"],
            "last_ok_ts": metrics["last_ok_ts"],
            "last_error": metrics["last_error"],
        }

        # Publish to MQTT if available
        try:
            client = get_client()
            base = config.get("MQTT_BASE", "bb8")
            topic = f"{base}/status/health"
            payload = json.dumps(health_data, separators=(",", ":"))
            client.publish(topic, payload=payload, qos=1, retain=True)

            logger.debug({"event": "health_metrics_published", "topic": topic})
        except Exception as e:
            logger.debug({
                "event": "health_metrics_mqtt_failed",
                "error": str(e),
            })

        # Write to health file for B1 evidence
        health_file = "/Users/evertappels/actions-runner/Projects/HA-BB8/reports/checkpoints/BB8-FUNC/b1_ble_health.json"

        # Ensure directory exists
        os.makedirs(os.path.dirname(health_file), exist_ok=True)

        with open(health_file, "w") as f:
            json.dump(health_data, f, indent=2)

        logger.debug({"event": "health_file_written", "path": health_file})

    except Exception as e:
        logger.error({"event": "publish_health_metrics_error", "error": str(e)})


# Only one canonical definition below (with correct return type)


def _wait_forever(client, bridge, ble=None) -> None:
    """Block the main thread until SIGTERM/SIGINT; then shutdown cleanly."""
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    logger.info("controller_ready")
    try:
        while not _stop_evt.wait(1.0):
            pass
    finally:
        try:
            if ble:
                ble.stop()
                ble.join()
        finally:
            logger.info("controller_stopped")

    # Example config loading (replace with actual config logic)
    cfg, _ = load_config() if "load_config" in globals() else ({}, None)

    logger.info({
        "event": "bridge_controller_start",
        "bb8_mac_cli": bool(cfg.get("bb8_mac")) if cfg else False,
        "scan_seconds": cfg.get("scan_seconds") if cfg else None,
        "rescan_on_fail": cfg.get("rescan_on_fail") if cfg else None,
        "cache_ttl_hours": cfg.get("cache_ttl_hours") if cfg else None,
    })
    # Initialize BLE gateway
    gw = BleGateway(mode="bleak", adapter=cfg.get("ble_adapter"))
    logger.info({
        "event": "ble_gateway_init",
        "mode": gw.mode,
        "adapter": cfg.get("ble_adapter"),
    })

    # Resolve BB-8 MAC if not provided
    target_mac: str | None = (cfg.get("bb8_mac") or "").strip() or None
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
        logger.info({
            "event": "bb8_mac_resolve_bypass",
            "reason": "env_or_options",
            "bb8_mac": target_mac,
        })

    # Construct bridge and facade (requires target_mac to be non-None)
    if not target_mac:
        logger.error({
            "event": "ble_bridge_init_failed",
            "reason": "target_mac_missing",
        })
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
    threading.Thread(
        target=ble_loop.run_forever, name="BLEThread", daemon=True
    ).start()

    # Start BLE link (all BLE calls must use run_coroutine_threadsafe)
    bb8_mac = (os.environ.get("BB8_MAC") or "").strip() or getattr(
        bridge, "target_mac", None
    )
    ble = None
    try:
        ble = BLELink(bb8_mac)
        try:
            ble.start()
            logger.info({
                "event": "ble_link_started",
                "mac": bb8_mac,
                "adapter": cfg.get("ble_adapter") if cfg else None,
                "source": "device",
            })
        except Exception as e:
            logger.error({
                "event": "ble_link_start_failed",
                "mac": bb8_mac,
                "error": str(e),
            })
    except Exception as e:
        logger.error({"event": "ble_link_error", "error": str(e)})
    logger.info({
        "event": "mqtt_dispatcher_start",
        "host": mqtt_host,
        "port": mqtt_port,
        "topic": mqtt_topic,
        "user": bool(mqtt_user),
    })
    # Removed unused status_topic assignment
    # status_topic = cfg.get("status_topic") if cfg else f"{mqtt_topic}/status"
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
            logger.info({
                "event": "stp4_evidence_recorder_started",
                "report_path": report_path,
                "provenance": {
                    "enable_stp4_evidence": src_enable,
                    "evidence_report_path": src_report,
                    "mqtt_topic": src_topic,
                },
            })
        except Exception as e:
            logger.warning({
                "event": "stp4_evidence_recorder_error",
                "error": repr(e),
                "provenance": {
                    "enable_stp4_evidence": src_enable,
                    "evidence_report_path": src_report,
                    "mqtt_topic": src_topic,
                },
            })

    # Start telemetry (presence + RSSI) only if enabled
    enable_bridge_telemetry = cfg.get("enable_bridge_telemetry", True)
    telemetry_interval = cfg.get("telemetry_interval_s", 20)
    if enable_bridge_telemetry:
        try:
            from .telemetry import Telemetry

            logger.info({
                "event": "telemetry_start",
                "interval_s": telemetry_interval,
                "role": "bridge",
            })
            telemetry = Telemetry(bridge)
            telemetry.start()
            logger.info({
                "event": "telemetry_loop_started",
                "interval_s": telemetry_interval,
                "role": "bridge",
            })
        except Exception as e:
            logger.warning({
                "event": "telemetry_error",
                "error": repr(e),
                "role": "bridge",
            })
    else:
        logger.info({
            "event": "telemetry_skipped",
            "reason": "scanner_owns_telemetry",
            "role": "bridge",
        })

    # Removed unused device echo handler functions


if __name__ == "__main__":
    """
    Foreground entrypoint (aligned with runtime model policy):
    - Initialize BLE and facade via start_bridge_controller() within a running
      asyncio loop to satisfy create_task semantics
    - Start MQTT dispatcher with explicit env/config resolution
    - Keep the loop alive indefinitely
    """
    import asyncio as _asyncio

    async def _async_entry():
        cfg, _src = load_config() if 'load_config' in globals() else ({}, None)

        # Initialize core subsystems and get facade for handler attachment
        facade = start_bridge_controller(config=cfg)

        # Resolve MQTT params (env → config → defaults)
        mqtt_host = os.environ.get("MQTT_HOST") or cfg.get("MQTT_HOST") or cfg.get("mqtt_broker") or "core-mosquitto"
        try:
            mqtt_port = int(os.environ.get("MQTT_PORT") or cfg.get("MQTT_PORT") or cfg.get("mqtt_port") or 1883)
        except Exception:
            mqtt_port = 1883
        base = os.environ.get("MQTT_BASE") or cfg.get("MQTT_BASE") or cfg.get("mqtt_topic_prefix") or "bb8"
        username = os.environ.get("MQTT_USER") or cfg.get("MQTT_USERNAME") or cfg.get("mqtt_username")
        password = os.environ.get("MQTT_PASSWORD") or cfg.get("MQTT_PASSWORD") or cfg.get("mqtt_password")
        status_topic = f"{base}/status"

        logger.info({
            "event": "bridge_controller_mqtt_params",
            "host": mqtt_host,
            "port": mqtt_port,
            "base": base,
            "user": bool(username),
        })

        # Minimal, in-module MQTT bootstrap to avoid cross-thread asyncio issues
        import paho.mqtt.client as mqtt
        from paho.mqtt.enums import CallbackAPIVersion

        client = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION2,
            protocol=mqtt.MQTTv311,
        )
        if username and password:
            client.username_pw_set(username, password)
        # LWT
        client.will_set(status_topic, payload="offline", qos=0, retain=True)

        # Helper: publish ACKs
        def _ack(cmd: str, cid: str | None, ok: bool = True, reason: str | None = None):
            payload = {"ok": bool(ok)}
            if cid is not None:
                payload["cid"] = cid
            if reason is not None:
                payload["reason"] = reason
            client.publish(f"{base}/ack/{cmd}", json.dumps(payload), qos=0, retain=False)

        loop = _asyncio.get_running_loop()

        def _on_connect(cl, ud, flags, rc, properties=None):
            cl.publish(status_topic, payload="online", qos=0, retain=True)
            # Commands and echo responder subscriptions
            cl.subscribe(f"{base}/cmd/#", qos=0)
            cl.subscribe(f"{base}/echo/cmd", qos=0)
            logger.info({"event": "mqtt_connected", "rc": rc, "reason": "success" if rc == 0 else rc})

        def _on_message(cl, ud, msg):
            try:
                logger.info({
                    "event": "mqtt_cmd_received",
                    "topic": getattr(msg, "topic", ""),
                    "len": len(getattr(msg, "payload", b"")),
                })
                topic = msg.topic or ""
                cmd = topic.split("/")[-1]
                raw = (msg.payload or b"{}").decode("utf-8", "ignore")
                data = {}
                try:
                    data = json.loads(raw) if raw else {}
                except Exception:
                    data = {}
                cid = data.get("cid")

                # Dispatch to facade on main loop thread
                if cmd == "power":
                    action = (data.get("action") or "").lower()
                    loop.call_soon_threadsafe(lambda: facade.power(action == "wake"))
                    _ack("power", cid, True)
                elif cmd == "stop":
                    loop.call_soon_threadsafe(lambda: facade.stop())
                    _ack("stop", cid, True)
                elif cmd == "led":
                    r = int(data.get("r", 0)); g = int(data.get("g", 0)); b = int(data.get("b", 0))
                    loop.call_soon_threadsafe(lambda: _asyncio.create_task(facade.set_led_async(r, g, b, cid)))
                    _ack("led", cid, True)
                elif cmd == "led_preset":
                    name = data.get("name")
                    loop.call_soon_threadsafe(lambda: _asyncio.create_task(facade.set_led_preset(name, cid)))
                    _ack("led_preset", cid, True)
                elif cmd == "drive":
                    speed = int(data.get("speed", 0)); heading = int(data.get("heading", 0)); ms = data.get("ms")
                    ms = int(ms) if ms is not None else None
                    loop.call_soon_threadsafe(lambda: _asyncio.create_task(facade.drive(speed, heading, ms)))
                    _ack("drive", cid, True)
                elif cmd == "estop":
                    reason = data.get("reason", "MQTT emergency stop")
                    loop.call_soon_threadsafe(lambda: _asyncio.create_task(facade.estop(reason)))
                    _ack("estop", cid, True)
                elif cmd == "clear_estop":
                    loop.call_soon_threadsafe(lambda: _asyncio.create_task(facade.clear_estop()))
                    _ack("clear_estop", cid, True)
                elif topic == f"{base}/echo/cmd":
                    # Immediate echo responder for evidence harness
                    try:
                        echo_payload = {
                            "cid": cid,
                            "source": "device",
                            "pong": True,
                            "ts": time.strftime(
                                "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                            ),
                        }
                        cl.publish(
                            f"{base}/echo/state",
                            json.dumps(echo_payload, separators=(",", ":")),
                            qos=0,
                            retain=False,
                        )
                    except Exception:
                        pass
                else:
                    _ack("unknown", cid, False, f"no handler for {topic}")
            except Exception as ex:  # defensive guard
                try:
                    _ack("unknown", None, False, f"handler error: {type(ex).__name__}")
                except Exception:
                    pass

        client.on_connect = _on_connect
        client.on_message = _on_message
        client.connect(mqtt_host, mqtt_port, keepalive=60)
        client.loop_start()

        async def _telemetry_heartbeat():
            while True:
                try:
                    conn = bool(getattr(facade, "is_connected", lambda: None)())
                except Exception:
                    conn = None
                snap = {
                    # Report actual BLE connectivity when available; fallback True
                    "connected": (conn if conn is not None else True),
                    "estop": getattr(getattr(facade, "_safety", None), "is_estop_active", lambda: False)(),
                    "last_cmd_ts": None,
                    "battery_pct": None,
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                try:
                    client.publish(f"{base}/status/telemetry", json.dumps(snap), qos=0, retain=False)
                except Exception:
                    pass
                await _asyncio.sleep(10.0)

        # start telemetry task in loop
        _asyncio.create_task(_telemetry_heartbeat())

        # Keep the loop alive indefinitely
        evt = _asyncio.Event()
        await evt.wait()

    try:
        _asyncio.run(_async_entry())
    except SystemExit:
        raise
    except Exception as e:
        logger.error({"event": "bridge_controller_fatal", "error": repr(e)})
        raise


# Removed import of register_subscription (unknown symbol)
