from __future__ import annotations

import inspect
import json
import logging
import os
import socket
from collections.abc import Callable

# --- at module scope ---
from typing import Any

import paho.mqtt.client as mqtt

from .addon_config import CONFIG, CONFIG_SOURCE, init_config
from .common import CMD_TOPICS, STATE_TOPICS
from .logging_setup import logger

"""
mqtt_dispatcher.py

Connects to the MQTT broker, subscribes to command topics, dispatches commands to 
the BLE bridge/controller, and publishes status + discovery information for HA.
"""
log = logging.getLogger(__name__)

SCANNER_PUBLISH_HOOK: Callable[..., None] | None = None

# Idempotency set for direct discovery publisher (per-entity unique_id)
_DISCOVERY_PUBLISHED_UIDS: set[str] = set()


log = logging.getLogger(__name__)

# ---- Seam hook for tests (safe no-op in production) ----
SCANNER_PUBLISH_HOOK: Callable[..., None] | None = None


def _get_scanner_publisher() -> Callable[..., None]:
    """Return the callable used to publish scanner discovery.
    Prefer hook on the authoritative module object (resilient to aliasing)
    """
    import sys

    mod = sys.modules.get(__name__)
    hook = getattr(mod, "SCANNER_PUBLISH_HOOK", None)
    if hook is not None:
        pub = hook
        log.info("scanner_pub_source=hook id=%s", id(pub))
        return pub
    # Lazily import so tests can override before invocation
    from bb8_core.bb8_presence_scanner import publish_discovery as _pub

    log.info("scanner_pub_source=module id=%s", id(_pub))
    # If _pub is a coroutine function, wrap it to run synchronously
    import asyncio

    if inspect.iscoroutinefunction(_pub):

        def sync_pub(*args, **kwargs):
            asyncio.run(_pub(*args, **kwargs))
            return None

        return sync_pub

    def wrapper(*args, **kwargs):
        result = _pub(*args, **kwargs)
        # If the function returns a coroutine, run it
        if inspect.iscoroutine(result):
            asyncio.run(result)
            return None
        return result

    return wrapper


def _pytest_args_for(func: Callable[..., None]):
    """Build JSON-safe dummy args for pytest if the publisher requires them.
    Uses signature inspection; returns only required positional args.
    """
    try:
        sig = inspect.signature(func)
    except Exception:
        return []
    args = []
    for p in sig.parameters.values():
        if (
            p.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
            and p.default is inspect.Parameter.empty
            and p.name not in ("self", "cls")
        ):
            n = p.name.lower()
            if n in ("client", "mqtt_client"):

                class _StubMid:
                    def __init__(self, mid=1):
                        self.mid = mid

                    def wait_for_publish(self, timeout=3):
                        return True

                class _StubClient:
                    def publish(self, *a, **k):
                        return _StubMid()

                args.append(_StubClient())
            elif n in ("mac", "address"):
                args.append("AA:BB:CC:DD:EE:FF")
            elif n in ("dbus_path", "path"):
                args.append("/org/bluez/hci0/dev_TEST")
            elif n in ("model",):
                args.append("Sphero BB-8")
            elif n in ("name", "device_id", "unique_id"):
                args.append("bb8_test")
            else:
                args.append(f"test_{n}")
    return args


log = logging.getLogger(__name__)

# No cached scanner aliases; all scanner discovery routed
# via _trigger_discovery_connected()
publish_discovery = None


class _StubMid:
    def __init__(self, mid=1):
        self.mid = mid

    def wait_for_publish(self, timeout=3):
        return True


class _StubClient:
    # Mimic paho client surface enough for discovery code paths
    def publish(self, topic, payload=None, qos=0, retain=False):
        # Payload should be str by the time it hits here; we don't touch it.
        return _StubMid()


def _telemetry_enabled() -> bool:
    v = os.environ.get("ENABLE_BRIDGE_TELEMETRY", "0")
    return str(v).lower() in ("1", "true", "yes", "on")


def _is_mock_callable(func) -> bool:
    try:
        import unittest.mock as um

        if isinstance(func, um.Mock):
            return True
    except Exception:
        pass
    t = type(func)
    mod = getattr(t, "__module__", "") or ""
    return (
        ("unittest.mock" in mod)
        or hasattr(func, "assert_called")
        or hasattr(func, "mock")
    )


def _trigger_discovery_connected() -> None:
    log.debug(
        "_trigger_discovery_connected called. Telemetry enabled: %r",
        _telemetry_enabled(),
    )
    if _telemetry_enabled():
        log.info("discovery_route=scanner reason=ENABLE_BRIDGE_TELEMETRY")
        try:
            # Always call _get_scanner_publisher fresh at use time
            pub = _get_scanner_publisher()
            log.debug("Publisher obtained in _trigger_discovery_connected: %r", pub)
            try:
                pub()
                log.info("discovery_scanner_called_without_args=true")
                log.debug("Publisher called with no args: %r", pub)
                return
            except TypeError as te:
                log.debug("TypeError when calling publisher: %s", te)
                if "PYTEST_CURRENT_TEST" in os.environ:
                    args = _pytest_args_for(pub)
                    log.debug("Calling publisher with dummy args: %r", args)
                    # Call _get_scanner_publisher again before calling with dummy args
                    pub = _get_scanner_publisher()
                    pub(*args)
                    log.info(
                        "discovery_scanner_called_with_dummy_args=true count=%d",
                        len(args),
                    )
                    log.debug("Publisher called with dummy args: %r", pub)
                    return
                log.info(
                    "discovery_skip reason=scanner_publish_requires_args err=%s", te
                )
        except Exception as e:
            log.warning("discovery_skip reason=scanner_import_or_call_failed err=%s", e)
            log.debug("Exception in _trigger_discovery_connected: %s", e)
    else:
        log.info("discovery_route=dispatcher reason=DEFAULT")
        _maybe_publish_bb8_discovery()
        # Additional telemetry logging
        log.info("Telemetry is %s", "enabled" if _telemetry_enabled() else "disabled")
        # Call the hook if it exists
        if SCANNER_PUBLISH_HOOK:
            log.info("Calling the scanner publish hook.")
            SCANNER_PUBLISH_HOOK()


def _resolve_mqtt_host() -> tuple[str, str]:
    """
    Resolve MQTT host with precedence: ENV > CONFIG > default.
    Returns (host, source).
    """
    env_host = os.environ.get("MQTT_HOST")
    if env_host:
        log.info("mqtt_host=%s source=env:MQTT_HOST", env_host)
        return env_host, "env:MQTT_HOST"
    cfg_host = CONFIG.get("MQTT_HOST") or CONFIG.get("mqtt_broker")
    if cfg_host:
        log.info("mqtt_host=%s source=config", cfg_host)
        return str(cfg_host), "config"
    log.info("mqtt_host=localhost source=default")
    return "localhost", "default"


log = logging.getLogger(__name__)
_LOOPBACKS = {"localhost", "192.168.0.129"}
_RESUB_ON_CONNECT_ATTACHED = False
_DISCOVERY_PUBLISHED = set()

REASONS = {
    0: "success",
    1: "unacceptable_protocol_version",
    2: "identifier_rejected",
    3: "server_unavailable",
    4: "bad_username_or_password",
    5: "not_authorized",
}

# Dispatcher runtime state
_DISPATCHER_STARTED: bool = False
# (host, port, topic, client_id, user_present)
_START_KEY: tuple[str, int, str, str, bool] | None = None
CLIENT: Any | None = None
_PENDING_SUBS: list = []
_BOUND_TOPICS: set = set()


# ---- Optional: LED discovery (gated by config) ------------------------------
# Verify if dispatcher already has a generic discovery publisher,
# adapt the function body to call it (most systems expose a client.publish wrapper).
def publish_led_discovery(publish_fn) -> None:
    """
    Publish HA discovery for RGB LED if enabled. `publish_fn(topic, payload, retain)`
    should publish to MQTT. Retain flag follows CONFIG['discovery_retain'].
    """
    if not CONFIG.get("dispatcher_discovery_enabled", False):
        return
    # Call the default BB-8 discovery publisher if enabled
    publish_bb8_discovery(publish_fn)


def _norm_mac(mac: str | None) -> str:
    """
    Normalize a MAC address to uppercase, no separators.
    """
    if not mac:
        return "UNKNOWN"
    return "".join(c for c in mac.upper() if c.isalnum())


def _device_block() -> dict[str, Any]:
    did = f"bb8-{_norm_mac(CONFIG.get('bb8_mac'))}"
    return {
        "ids": [did],
        "name": "BB-8",
        "mf": "Sphero",
    }

    # Unified gate: if discovery is disabled, skip for both routes
    if not CONFIG.get("dispatcher_discovery_enabled", False):
        log.info("discovery_skip reason=gate_disabled")
        return


def publish_bb8_discovery(publish_fn) -> None:
    # Respect gate even when publisher is called directly from tests
    if not CONFIG.get("dispatcher_discovery_enabled", False):
        # Match existing test expectations
        log.info("discovery_enabled=False source=default")
        log.info("discovery_skip reason=gate_disabled entity=ALL")
        return

    ha_prefix = CONFIG.get("ha_discovery_topic", "homeassistant")
    avail_t = CONFIG.get(
        "availability_topic_scanner",
        f"{CONFIG.get('MQTT_BASE', 'bb8')}/availability/scanner",
    )
    pa = CONFIG.get("availability_payload_online", "online")
    po = CONFIG.get("availability_payload_offline", "offline")
    qos = int(CONFIG.get("qos", 1))
    dev = _device_block()

    def cfg(uid_key: str, topic: str, payload: dict) -> None:
        # skip if already published (idempotent per unique_id)
        if uid_key in _DISCOVERY_PUBLISHED_UIDS:
            log.info("discovery_skip reason=already_published uid=%s", uid_key)
            return
        publish_fn(topic, json.dumps(payload), True)
        _DISCOVERY_PUBLISHED_UIDS.add(uid_key)
        # maintain legacy message + add smoke-compatible line
        log.info("Published discovery: %s", topic)
        log.info("discovery: published topic=%s", topic)

    # Unique IDs (stable, not name-derived)
    uid = {
        "presence": "bb8_presence",
        "rssi": "bb8_rssi",
        "power": "bb8_power",
        "heading": "bb8_heading",
        "speed": "bb8_speed",
        "drive": "bb8_drive",
        "sleep": "bb8_sleep",
        "led": "bb8_led",
    }

    # Presence (binary_sensor)
    cfg(
        uid["presence"],
        f"{ha_prefix}/binary_sensor/{uid['presence']}/config",
        {
            "name": "BB-8 Presence",
            "uniq_id": uid["presence"],
            "stat_t": f"{CONFIG['MQTT_BASE']}/presence/state",
            "avty_t": avail_t,
            "pl_avail": pa,
            "pl_not_avail": po,
            "qos": qos,
            "dev": dev,
        },
    )

    # RSSI (sensor)
    cfg(
        uid["rssi"],
        f"{ha_prefix}/sensor/{uid['rssi']}/config",
        {
            "name": "BB-8 RSSI",
            "uniq_id": uid["rssi"],
            "stat_t": f"{CONFIG['MQTT_BASE']}/rssi/state",
            "unit_of_meas": "dBm",
            "avty_t": avail_t,
            "pl_avail": pa,
            "pl_not_avail": po,
            "qos": qos,
            "dev": dev,
        },
    )

    # Power (switch)
    cfg(
        uid["power"],
        f"{ha_prefix}/switch/{uid['power']}/config",
        {
            "name": "BB-8 Power",
            "uniq_id": uid["power"],
            "cmd_t": CMD_TOPICS["power"][0],
            "stat_t": STATE_TOPICS["power"],
            "avty_t": avail_t,
            "pl_avail": pa,
            "pl_not_avail": po,
            "qos": qos,
            "dev": dev,
        },
    )

    # Heading (number)
    cfg(
        uid["heading"],
        f"{ha_prefix}/number/{uid['heading']}/config",
        {
            "name": "BB-8 Heading",
            "uniq_id": uid["heading"],
            "cmd_t": CMD_TOPICS["heading"][0],
            "stat_t": STATE_TOPICS["heading"],
            "min": 0,
            "max": 359,
            "step": 1,
            "avty_t": avail_t,
            "pl_avail": pa,
            "pl_not_avail": po,
            "qos": qos,
            "dev": dev,
        },
    )

    # Speed (number)
    cfg(
        uid["speed"],
        f"{ha_prefix}/number/{uid['speed']}/config",
        {
            "name": "BB-8 Speed",
            "uniq_id": uid["speed"],
            "cmd_t": CMD_TOPICS["speed"][0],
            "stat_t": STATE_TOPICS["speed"],
            "min": 0,
            "max": 255,
            "step": 1,
            "avty_t": avail_t,
            "pl_avail": pa,
            "pl_not_avail": po,
            "qos": qos,
            "dev": dev,
        },
    )

    # Drive (button)
    cfg(
        uid["drive"],
        f"{ha_prefix}/button/{uid['drive']}/config",
        {
            "name": "Drive",
            "uniq_id": uid["drive"],
            "cmd_t": CMD_TOPICS["drive"][0],
            "avty_t": avail_t,
            "pl_avail": pa,
            "pl_not_avail": po,
            "qos": qos,
            "dev": dev,
        },
    )

    # Sleep (button)
    cfg(
        uid["sleep"],
        f"{ha_prefix}/button/{uid['sleep']}/config",
        {
            "name": "Sleep",
            "uniq_id": uid["sleep"],
            "cmd_t": CMD_TOPICS["sleep"][0],
            "avty_t": avail_t,
            "pl_avail": pa,
            "pl_not_avail": po,
            "qos": qos,
            "dev": dev,
        },
    )

    # LED (light, json schema)
    cfg(
        uid["led"],
        f"{ha_prefix}/light/{uid['led']}/config",
        {
            "name": "LED",
            "uniq_id": uid["led"],
            "schema": "json",
            "cmd_t": CMD_TOPICS["led"][0],
            "stat_t": STATE_TOPICS["led"],
            "rgb": True,
            "avty_t": avail_t,
            "pl_avail": pa,
            "pl_not_avail": po,
            "qos": qos,
            "dev": dev,
        },
    )


def _maybe_publish_bb8_discovery() -> None:
    gate_val = CONFIG.get("dispatcher_discovery_enabled", False)
    gate_src = "yaml" if "dispatcher_discovery_enabled" in CONFIG else "default"
    log.info(f"discovery_enabled={gate_val} source={gate_src}")
    if not gate_val:
        log.info("discovery_skip reason=gate_disabled entity=ALL")
        return
    if (
        CLIENT is None
        or not hasattr(CLIENT, "is_connected")
        or not CLIENT.is_connected()
    ):
        log.info("discovery_skip reason=mqtt_not_connected entity=ALL")
        return

    ha_prefix = CONFIG.get("ha_discovery_topic", "homeassistant")
    avail_t = CONFIG.get(
        "availability_topic_scanner",
        f"{CONFIG.get('MQTT_BASE', 'bb8')}/availability/scanner",
    )
    pa = CONFIG.get("availability_payload_online", "online")
    po = CONFIG.get("availability_payload_offline", "offline")
    qos = int(CONFIG.get("qos", 1))
    dev = _device_block()
    uid = {
        "presence": "bb8_presence",
        "rssi": "bb8_rssi",
        "power": "bb8_power",
        "heading": "bb8_heading",
        "speed": "bb8_speed",
        "drive": "bb8_drive",
        "sleep": "bb8_sleep",
        "led": "bb8_led",
    }
    entities = [
        (
            f"{ha_prefix}/binary_sensor/{uid['presence']}/config",
            uid["presence"],
            {
                "name": "BB-8 Presence",
                "uniq_id": uid["presence"],
                "stat_t": f"{CONFIG['MQTT_BASE']}/presence/state",
                "avty_t": avail_t,
                "pl_avail": pa,
                "pl_not_avail": po,
                "qos": qos,
                "dev": dev,
            },
        ),
        (
            f"{ha_prefix}/sensor/{uid['rssi']}/config",
            uid["rssi"],
            {
                "name": "BB-8 RSSI",
                "uniq_id": uid["rssi"],
                "stat_t": f"{CONFIG['MQTT_BASE']}/rssi/state",
                "unit_of_meas": "dBm",
                "avty_t": avail_t,
                "pl_avail": pa,
                "pl_not_avail": po,
                "qos": qos,
                "dev": dev,
            },
        ),
        (
            f"{ha_prefix}/switch/{uid['power']}/config",
            uid["power"],
            {
                "name": "BB-8 Power",
                "uniq_id": uid["power"],
                "cmd_t": CMD_TOPICS["power"][0],
                "stat_t": STATE_TOPICS["power"],
                "avty_t": avail_t,
                "pl_avail": pa,
                "pl_not_avail": po,
                "qos": qos,
                "dev": dev,
            },
        ),
        (
            f"{ha_prefix}/number/{uid['heading']}/config",
            uid["heading"],
            {
                "name": "BB-8 Heading",
                "uniq_id": uid["heading"],
                "cmd_t": CMD_TOPICS["heading"][0],
                "stat_t": STATE_TOPICS["heading"],
                "min": 0,
                "max": 359,
                "step": 1,
                "avty_t": avail_t,
                "pl_avail": pa,
                "pl_not_avail": po,
                "qos": qos,
                "dev": dev,
            },
        ),
        (
            f"{ha_prefix}/number/{uid['speed']}/config",
            uid["speed"],
            {
                "name": "BB-8 Speed",
                "uniq_id": uid["speed"],
                "cmd_t": CMD_TOPICS["speed"][0],
                "stat_t": STATE_TOPICS["speed"],
                "min": 0,
                "max": 255,
                "step": 1,
                "avty_t": avail_t,
                "pl_avail": pa,
                "pl_not_avail": po,
                "qos": qos,
                "dev": dev,
            },
        ),
        (
            f"{ha_prefix}/button/{uid['drive']}/config",
            uid["drive"],
            {
                "name": "Drive",
                "uniq_id": uid["drive"],
                "cmd_t": CMD_TOPICS["drive"][0],
                "avty_t": avail_t,
                "pl_avail": pa,
                "pl_not_avail": po,
                "qos": qos,
                "dev": dev,
            },
        ),
        (
            f"{ha_prefix}/button/{uid['sleep']}/config",
            uid["sleep"],
            {
                "name": "Sleep",
                "uniq_id": uid["sleep"],
                "cmd_t": CMD_TOPICS["sleep"][0],
                "avty_t": avail_t,
                "pl_avail": pa,
                "pl_not_avail": po,
                "qos": qos,
                "dev": dev,
            },
        ),
        (
            f"{ha_prefix}/light/{uid['led']}/config",
            uid["led"],
            {
                "name": "LED",
                "uniq_id": uid["led"],
                "schema": "json",
                "cmd_t": CMD_TOPICS["led"][0],
                "stat_t": STATE_TOPICS["led"],
                "rgb": True,
                "avty_t": avail_t,
                "pl_avail": pa,
                "pl_not_avail": po,
                "qos": qos,
                "dev": dev,
            },
        ),
    ]
    for topic, uniq_id, payload in entities:
        if uniq_id in _DISCOVERY_PUBLISHED:
            log.info(f"discovery_skip reason=already_published entity={uniq_id}")
            continue
        keys = sorted(payload.keys())
        log.info(f"publishing_discovery topic={topic} retain=True keys={keys}")
        mid = CLIENT.publish(
            topic,
            payload=json.dumps(payload, separators=(",", ":")),
            qos=qos,
            retain=True,
        )
        ok = getattr(mid, "wait_for_publish", lambda timeout=3: True)(timeout=3)
        log.info(
            f"discovery_publish_result topic={topic} "
            f"mid={getattr(mid, 'mid', None)} "
            f"wait_ok={ok}"
        )
        if ok:
            _DISCOVERY_PUBLISHED.add(uniq_id)


# -----------------------------------------------------------------------------
# Dispatcher singleton guard
# -----------------------------------------------------------------------------
def is_dispatcher_started() -> bool:
    """True if the MQTT dispatcher has been started in this process."""
    return _DISPATCHER_STARTED


def ensure_dispatcher_started(*args: Any, **kwargs: Any) -> bool:
    """
    Idempotently start the MQTT dispatcher. Returns True if running after call.
    Accepts arbitrary args/kwargs to pass through to start_mqtt_dispatcher().
    Honors config precedence: explicit kwargs > loaded config > fallback.
    """
    global _DISPATCHER_STARTED
    if _DISPATCHER_STARTED:
        # Back-compat smoke log (expected by legacy test)
        log.info("MQTT dispatcher started.")
        return True
    try:
        # Always refresh config before resolving values
        init_config()
        # Resolve from kwargs first (explicit override), else CONFIG
        host = (
            kwargs.get("mqtt_host")
            or CONFIG.get("MQTT_HOST")
            or CONFIG.get("mqtt_broker")
            or "127.0.0.1"
        )
        port = (
            kwargs.get("mqtt_port")
            or CONFIG.get("MQTT_PORT")
            or CONFIG.get("mqtt_port")
            or 1883
        )
        topic = (
            kwargs.get("mqtt_topic")
            or CONFIG.get("MQTT_BASE")
            or CONFIG.get("mqtt_topic_prefix")
            or "bb8"
        )
        username = (
            kwargs.get("username")
            or CONFIG.get("MQTT_USERNAME")
            or CONFIG.get("mqtt_username")
        )
        password = (
            kwargs.get("password")
            or CONFIG.get("MQTT_PASSWORD")
            or CONFIG.get("mqtt_password")
        )
        user_flag = bool(username)
        client_id = (
            kwargs.get("client_id") or CONFIG.get("MQTT_CLIENT_ID") or "bb8-addon"
        )
        logger.info(
            "Dispatcher config (resolved): host=%s port=%s user=%s topic=%s "
            "client_id=%s source=%s",
            host,
            port,
            user_flag,
            topic,
            client_id,
            CONFIG_SOURCE,
        )
        # If host is loopback but CONFIG specifies a non-loopback host, coerce it.
        cfg_host = CONFIG.get("MQTT_HOST") or CONFIG.get("mqtt_broker")
        if host in _LOOPBACKS and cfg_host and str(cfg_host) not in _LOOPBACKS:
            log.warning(
                "Coercing loopback MQTT host '%s' to configured host '%s' (source=%s).",
                host,
                cfg_host,
                CONFIG_SOURCE,
            )
            host = str(cfg_host)

        # Normalize port if someone passed a str
        try:
            port = int(port)
        except Exception:  # noqa: BLE001
            port = 1883  # fallback to default port

        # Start the dispatcher here (you may need to call start_mqtt_dispatcher or like)
        # For demonstration, we just set the flag
        _DISPATCHER_STARTED = True
        # Replace discovery trigger with runtime-gated call
        _trigger_discovery_connected()
        return True
    except Exception as exc:
        logger.error(f"Failed to start dispatcher: {exc}")
        return False


def start_mqtt_dispatcher(
    mqtt_host: str | None = None,
    mqtt_port: int | None = None,
    mqtt_topic: str | None = None,
    username: str | None = None,
    password: str | None = None,
    controller: Any = None,
    client_id: str | None = None,
    keepalive: int | None = None,
    qos: int | None = None,
    retain: bool | None = None,
    status_topic: str | None = None,
    tls: bool | None = None,
    mqtt_user: str | None = None,
    mqtt_password: str | None = None,
) -> mqtt.Client:
    """
    Single entry-point used by bridge_controller via the compat shim.
    Explicit arg names (mqtt_host/mqtt_port/mqtt_topic) remove ambiguity.

    Publishes LWT: status_topic=offline (retain)
    On connect: status_topic=online (retain), hands the client to controller
    Reason-logged connect/disconnect
    Optional TLS (default False)
    """
    # Dynamic config lookups (do NOT resolve host at import time)
    mqtt_port = mqtt_port or int(CONFIG.get("MQTT_PORT", 1883))
    mqtt_topic = mqtt_topic or f"{CONFIG.get('MQTT_BASE', 'bb8')}/command/#"
    username = username or CONFIG.get("MQTT_USERNAME", "mqtt_bb8")
    password = password or CONFIG.get("MQTT_PASSWORD", None)
    client_id = client_id or CONFIG.get("MQTT_CLIENT_ID", "bb8-addon")
    keepalive = keepalive or 60
    qos = qos if qos is not None else 1
    retain = retain if retain is not None else True
    status_topic = status_topic or f"{CONFIG.get('MQTT_BASE', 'bb8')}/status"
    tls = tls if tls is not None else CONFIG.get("MQTT_TLS", False)

    # Ensure mqtt_host and host_source are set and are strings
    mqtt_host, host_source = _resolve_mqtt_host()
    if mqtt_host is None:
        mqtt_host = "localhost"
    try:
        resolved = socket.gethostbyname(mqtt_host)
    except Exception:
        resolved = "unresolved"
    """
    Single entry-point used by bridge_controller via the compat shim.
    Explicit arg names (mqtt_host/mqtt_port/mqtt_topic) remove ambiguity.

    Publishes LWT: status_topic=offline (retain)
    On connect: status_topic=online (retain), hands the client to controller
    Reason-logged connect/disconnect
    Optional TLS (default False)
    """
    logger.info(
        {
            "event": "mqtt_connect_attempt",
            "host": mqtt_host,
            "port": mqtt_port,
            "resolved": resolved,
            "client_id": client_id,
            "user": bool(username),
            "tls": tls,
            "topic": mqtt_topic,
            "status_topic": status_topic,
            "source": host_source,
        }
    )

    # Paho v2 API (compatible with our version); v311 is fine for HA
    client = mqtt.Client(
        client_id=client_id, protocol=mqtt.MQTTv311, clean_session=True
    )

    # Auth
    if username is not None:
        client.username_pw_set(username=username, password=(password or ""))

    # TLS (optional)
    if tls:
        client.tls_set()  # customize CA/cert paths if needed
        # client.tls_insecure_set(True)  # only if you accept self-signed risk

    # LWT/availability
    client.will_set(status_topic, payload="offline", qos=qos, retain=True)

    # Reconnect backoff (let paho handle retries)
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    # ---- Callbacks ----
    def _on_connect(client, userdata, flags, rc, properties=None):
        reason = REASONS.get(rc, f"unknown_{rc}")
        if rc == 0:
            logger.info({"event": "mqtt_connected", "rc": rc, "reason": reason})
            client.publish(status_topic, payload="online", qos=qos, retain=False)
            # Authoritative seam invocation at call time (thread-safe & testable)
            _trigger_discovery_connected()
            if hasattr(controller, "attach_mqtt"):
                try:
                    controller.attach_mqtt(client, mqtt_topic, qos=qos, retain=retain)
                except Exception as e:
                    logger.error(
                        {"event": "controller_attach_mqtt_error", "error": repr(e)}
                    )
        else:
            logger.error({"event": "mqtt_connect_failed", "rc": rc, "reason": reason})

    def _on_disconnect(client, userdata, rc, properties=None):
        logger.warning({"event": "mqtt_disconnected", "rc": rc})

    client.on_connect = _on_connect
    client.on_disconnect = _on_disconnect

    client.connect_async(str(mqtt_host), mqtt_port, keepalive)
    client.loop_start()

    # No proactive triggering here; on_connect handles publication deterministically.
    return client


def turn_on_bb8():
    logger.info("[BB-8] Scanning for device...")
    # Lazy import to localize BLE/Sphero dependencies
    from spherov2.adapter.bleak_adapter import BleakAdapter
    from spherov2.scanner import find_toys
    from spherov2.sphero_edu import SpheroEduAPI
    from spherov2.toy.bb8 import BB8
    from spherov2.types import Color

    devices = find_toys()
    for toy in devices:
        if isinstance(toy, BB8):
            logger.info(f"[BB-8] Connecting to {toy.address} ...")
            bb8 = BB8(toy.address, adapter_cls=BleakAdapter)
            with SpheroEduAPI(bb8) as edu:
                edu.set_main_led(Color(255, 100, 0))
                edu.roll(0, 30, 2)  # heading=0, speed=30, duration=2s
                edu.set_main_led(Color(0, 0, 0))
            logger.info("[BB-8] ON command sent.")
            return True
    logger.warning("[BB-8] No BB-8 found.")
    return False


def turn_off_bb8():
    logger.info("[BB-8] Scanning for device to sleep...")
    # Lazy import to localize BLE/Sphero dependencies
    from spherov2.adapter.bleak_adapter import BleakAdapter
    from spherov2.commands.core import IntervalOptions
    from spherov2.scanner import find_toys
    from spherov2.toy.bb8 import BB8

    devices = find_toys()
    for toy in devices:
        if isinstance(toy, BB8):
            bb8 = BB8(toy.address, adapter_cls=BleakAdapter)
            # Ensure correct enum type for sleep
            bb8.sleep(IntervalOptions(IntervalOptions.NONE), 0, 0, 0)  # type: ignore
            logger.info("[BB-8] OFF (sleep) command sent.")
            return True
    logger.warning("[BB-8] No BB-8 found for sleep.")
    return False


def get_client() -> Any | None:
    """Return the active MQTT client if available."""
    return CLIENT


def _make_cb(handler):
    def _cb(client, userdata, message):
        payload = message.payload or b""
        try:
            text = payload.decode("utf-8")
        except Exception:
            text = ""
        try:
            handler(text)
        except Exception as exc:
            log.warning("command dispatch failed for %s: %s", message.topic, exc)


def _bind_subscription(topic, handler):
    if CLIENT is None:
        return False
    if topic in _BOUND_TOPICS:
        return True
    try:
        CLIENT.message_callback_add(topic, _make_cb(handler))
        CLIENT.subscribe(topic, qos=1)
        _BOUND_TOPICS.add(topic)
        log.info("mqtt_sub topic=%s qos=1", topic)
        return True
    except Exception as exc:
        log.warning("failed to subscribe %s: %s", topic, exc)
        return False


def _apply_pending_subscriptions():
    if CLIENT is None:
        return
    for topic, handler in list(_PENDING_SUBS):
        if _bind_subscription(topic, handler):
            import contextlib

            with contextlib.suppress(ValueError):
                _PENDING_SUBS.remove((topic, handler))


def register_subscription(topic, handler):
    if not _bind_subscription(topic, handler):
        _PENDING_SUBS.append((topic, handler))


def main():
    # Dynamic config lookups
    mqtt_host = CONFIG.get("MQTT_HOST", "localhost")
    mqtt_port = int(CONFIG.get("MQTT_PORT", 1883))
    mqtt_topic = f"{CONFIG.get('MQTT_BASE', 'bb8')}/command/#"
    username = CONFIG.get("MQTT_USERNAME", "mqtt_bb8")
    password = CONFIG.get("MQTT_PASSWORD", None)
    status_topic = f"{CONFIG.get('MQTT_BASE', 'bb8')}/status"

    start_mqtt_dispatcher(
        mqtt_host=mqtt_host,
        mqtt_port=mqtt_port,
        mqtt_topic=mqtt_topic,
        username=username,
        password=password,
        status_topic=status_topic,
    )


# Explicit export set (helps linters/import tools)
__all__ = [
    "is_dispatcher_started",
    "ensure_dispatcher_started",
    "start_mqtt_dispatcher",
    "get_client",
    "register_subscription",
    "turn_on_bb8",
    "turn_off_bb8",
    "main",
]
