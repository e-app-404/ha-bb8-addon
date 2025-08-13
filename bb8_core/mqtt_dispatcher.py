#
"""
mqtt_dispatcher.py

Connects to the MQTT broker, subscribes to command topics, dispatches commands to the BLE bridge/controller, and publishes status and discovery information for Home Assistant.
"""
# Finalized for Home Assistant runtime (2025-08-04)

from __future__ import annotations

from typing import Optional, Any
import socket
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish  # uncommented because publish.single is used
from .logging_setup import logger
from .addon_config import load_config
CFG, SRC = load_config()

REASONS = {
    0: "success",
    1: "unacceptable_protocol_version",
    2: "identifier_rejected",
    3: "server_unavailable",
    4: "bad_username_or_password",
    5: "not_authorized",
}

# Placeholder for BLE bridge import
try:
    from bb8_core.ble_bridge import BLEBridge
except ImportError:
    BLEBridge = None

def start_mqtt_dispatcher(
    mqtt_host: Optional[str] = None,
    mqtt_port: Optional[int] = None,
    mqtt_topic: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    controller: Any = None,
    client_id: Optional[str] = None,
    keepalive: Optional[int] = None,
    qos: Optional[int] = None,
    retain: Optional[bool] = None,
    status_topic: Optional[str] = None,
    tls: Optional[bool] = None,
    mqtt_user: Optional[str] = None,
    mqtt_password: Optional[str] = None,
) -> mqtt.Client:
    """
    Single entry-point used by bridge_controller via the compat shim.
    Explicit arg names (mqtt_host/mqtt_port/mqtt_topic) remove ambiguity.

    - Publishes LWT: status_topic=offline (retain)
    - On connect: status_topic=online (retain), hands the client to controller
    - Reason-logged connect/disconnect
    - Optional TLS (default False)
    """
    # Dynamic config lookups
    mqtt_host = mqtt_host or CFG.get("MQTT_HOST", "localhost")
    mqtt_port = mqtt_port or int(CFG.get("MQTT_PORT", 1883))
    mqtt_topic = mqtt_topic or f"{CFG.get('MQTT_BASE', 'bb8')}/command/#"
    username = username or CFG.get("MQTT_USERNAME", "mqtt_bb8")
    password = password or CFG.get("MQTT_PASSWORD", None)
    client_id = client_id or CFG.get("MQTT_CLIENT_ID", "bb8-addon")
    keepalive = keepalive or 60
    qos = qos if qos is not None else 1
    retain = retain if retain is not None else True
    status_topic = status_topic or f"{CFG.get('MQTT_BASE', 'bb8')}/status"
    tls = tls if tls is not None else CFG.get("MQTT_TLS", False)

    resolved = None
    try:
        resolved = socket.gethostbyname(mqtt_host)
    except Exception:
        resolved = "unresolved"

    logger.info({
        "event": "mqtt_connect_attempt",
        "host": mqtt_host,
        "port": mqtt_port,
        "resolved": resolved,
        "client_id": client_id,
        "user": bool(username),
        "tls": tls,
        "topic": mqtt_topic,
        "status_topic": status_topic,
    })

    # Paho v2 API (compatible with our version); v311 is fine for HA
    client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311, clean_session=True)

    # Auth
    if username is not None:
        client.username_pw_set(username=username, password=(password or ""))

    # TLS (optional)
    if tls:
        client.tls_set()           # customize CA/cert paths if needed
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
            # mark online
            client.publish(status_topic, payload="online", qos=qos, retain=True)

            # Always publish discovery for connected/rssi entities on connect (non-retained)
            try:
                import os
                from bb8_core.discovery_publish import publish_discovery
                dev_id = (getattr(controller, "target_mac", None) or "bb8").replace(":", "").lower()
                dbus_path = getattr(controller, "dbus_path", None) or CFG.get("BB8_DBUS_PATH", "/org/bluez/hci0")
                name = os.environ.get("BB8_NAME", "BB-8")
                publish_discovery(client, dev_id, dbus_path, name=name)
            except Exception as e:
                logger.warning({"event":"discovery_dispatcher_disabled","reason":repr(e)})
            # Hand the client to the BB-8 controller (subscribe/publish wiring)
            # Expected to implement: attach_mqtt(client, topic, qos, retain)
            if hasattr(controller, "attach_mqtt"):
                try:
                    controller.attach_mqtt(client, mqtt_topic, qos=qos, retain=retain)
                except Exception as e:
                    logger.error({"event": "controller_attach_mqtt_error", "error": repr(e)})
        else:
            logger.error({"event": "mqtt_connect_failed", "rc": rc, "reason": reason})


    def _on_disconnect(client, userdata, rc, properties=None):
        # rc==0 = clean; >0 = unexpected
        logger.warning({"event": "mqtt_disconnected", "rc": rc})

    client.on_connect = _on_connect
    client.on_disconnect = _on_disconnect

    # Async connect + network loop
    client.connect_async(mqtt_host, mqtt_port, keepalive)
    client.loop_start()

    return client


    # Discovery is published by facade.attach_mqtt(). Avoid duplicates here.


def turn_on_bb8():
    logger.info("[BB-8] Scanning for device...")
    # Lazy import to localize BLE/Sphero dependencies
    from spherov2.scanner import find_toys
    from spherov2.toy.bb8 import BB8
    from spherov2.adapter.bleak_adapter import BleakAdapter
    from spherov2.sphero_edu import SpheroEduAPI
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
    from spherov2.scanner import find_toys
    from spherov2.toy.bb8 import BB8
    from spherov2.adapter.bleak_adapter import BleakAdapter
    from spherov2.commands.core import IntervalOptions
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


def main():
    # Dynamic config lookups
    mqtt_host = CFG.get("MQTT_HOST", "localhost")
    mqtt_port = int(CFG.get("MQTT_PORT", 1883))
    mqtt_topic = f"{CFG.get('MQTT_BASE', 'bb8')}/command/#"
    username = CFG.get("MQTT_USERNAME", "mqtt_bb8")
    password = CFG.get("MQTT_PASSWORD", None)
    status_topic = f"{CFG.get('MQTT_BASE', 'bb8')}/status"

    start_mqtt_dispatcher(
        mqtt_host=mqtt_host,
        mqtt_port=mqtt_port,
        mqtt_topic=mqtt_topic,
        username=username,
        password=password,
        status_topic=status_topic,
    )


# Call this at container startup

