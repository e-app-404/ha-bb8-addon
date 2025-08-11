#
"""
mqtt_dispatcher.py

Connects to the MQTT broker, subscribes to command topics, dispatches commands to the BLE bridge/controller, and publishes status and discovery information for Home Assistant.
"""
# Finalized for Home Assistant runtime (2025-08-04)

from __future__ import annotations
from typing import Optional, Any
import socket
import os
import paho.mqtt.client as mqtt
from .logging_setup import logger

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
    mqtt_host: str,
    mqtt_port: int,
    mqtt_topic: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
    controller: Any = None,
    client_id: str = "bb8-addon",
    keepalive: int = 60,
    qos: int = 1,
    retain: bool = True,
    status_topic: str = "bb8/status",
    gateway: Optional[BleGateway] = None,
    tls: bool = False,
) -> mqtt.Client:
    """
    Single entry-point used by bridge_controller via the compat shim.
    Explicit arg names (mqtt_host/mqtt_port/mqtt_topic) remove ambiguity.

    - Publishes LWT: status_topic=offline (retain)
    - On connect: status_topic=online (retain), hands the client to controller
    - Reason-logged connect/disconnect
    - Optional TLS (default False)
    """
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
    def _on_connect(c, u, flags, rc, properties=None):
        reason = REASONS.get(rc, f"unknown_{rc}")
        if rc == 0:
            logger.info({"event": "mqtt_connected", "rc": rc, "reason": reason})
            # mark online
            c.publish(status_topic, payload="online", qos=qos, retain=True)

            # Hand the client to the BB-8 controller (subscribe/publish wiring)
            # Expected to implement: attach_mqtt(client, topic, qos, retain)
            if hasattr(controller, "attach_mqtt"):
                try:
                    controller.attach_mqtt(c, mqtt_topic, qos=qos, retain=retain)
                except Exception as e:
                    logger.error({"event": "controller_attach_mqtt_error", "error": repr(e)})
                # Publish discovery if available
                try:
                    from bb8_core.controller import publish_discovery_if_available
                    publish_discovery_if_available(c, controller, mqtt_topic, qos, retain)
                except Exception as e:
                    logger.error({"event": "discovery_publish_import_error", "error": repr(e)})
        else:
            logger.error({"event": "mqtt_connect_failed", "rc": rc, "reason": reason})

    def _on_disconnect(c, u, rc, properties=None):
        # rc==0 = clean; >0 = unexpected
        logger.warning({"event": "mqtt_disconnected", "rc": rc})

    client.on_connect = _on_connect
    client.on_disconnect = _on_disconnect

    # Async connect + network loop
    client.connect_async(mqtt_host, mqtt_port, keepalive)
    client.loop_start()

    return client


def publish_mqtt_discovery(client=None):
    BB8_MAC = os.environ.get("BB8_MAC", "B8:17:C2:A8:ED:45")
    MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
    MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
    MQTT_USER = os.environ.get("MQTT_USER")
    MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD")
    mqtt_prefix = os.environ.get("MQTT_TOPIC_PREFIX", "bb8")
    device_id = f"bb8_{BB8_MAC.replace(':','').lower()}"
    def _emit(topic, payload):
        logger.debug({"event": "discovery_emit_start", "topic": topic, "payload": payload, "client": str(client)})
        logger.info({"event": "mqtt_discovery_publish", "topic": topic, "payload": payload})
        if client:
            logger.debug({"event": "discovery_emit_client_publish", "topic": topic})
            client.publish(topic, payload=payload, qos=1, retain=True)
        else:
            logger.debug({"event": "discovery_emit_single_publish", "topic": topic, "MQTT_HOST": MQTT_HOST, "MQTT_PORT": MQTT_PORT})
            publish.single(topic, payload, hostname=MQTT_HOST, port=MQTT_PORT,
                           auth={"username": MQTT_USER, "password": MQTT_PASSWORD} if MQTT_USER and MQTT_PASSWORD else None,
                           retain=True)
    # Presence sensor
    cfg_presence = {
        "name": "BB-8 Presence",
        "unique_id": f"{device_id}_presence",
        "device_class": "presence",
        "state_topic": f"{mqtt_prefix}/presence",
        "availability_topic": f"{mqtt_prefix}/status",
        "payload_on": "present",
        "payload_off": "absent",
        "device": {
            "identifiers": [device_id],
            "manufacturer": "Sphero",
            "model": "BB-8",
            "name": "BB-8"
        }
    }
    # RSSI sensor
    cfg_rssi = {
        "name": "BB-8 RSSI",
        "unique_id": f"{device_id}_rssi",
        "state_topic": f"{mqtt_prefix}/rssi",
        "availability_topic": f"{mqtt_prefix}/status",
        "unit_of_measurement": "dBm",
        "state_class": "measurement",
        "device_class": "signal_strength",
        "device": cfg_presence["device"]
    }
    # Power switch
    cfg_power = {
        "name": "BB-8 Power",
        "unique_id": f"{device_id}_power",
        "command_topic": f"{mqtt_prefix}/command/power",
        "state_topic": f"{mqtt_prefix}/state/power",
        "payload_on": "ON",
        "payload_off": "OFF",
        "availability_topic": f"{mqtt_prefix}/status",
        "device": cfg_presence["device"]
    }
    _emit(f"homeassistant/binary_sensor/{device_id}_presence/config", json.dumps(cfg_presence))
    _emit(f"homeassistant/sensor/{device_id}_rssi/config", json.dumps(cfg_rssi))
    _emit(f"homeassistant/switch/{device_id}_power/config", json.dumps(cfg_power))


def turn_on_bb8():
    logger.info("[BB-8] Scanning for device...")
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
    # Obtain gateway from config/env or instantiate default
    ble_adapter = os.environ.get("BLE_ADAPTER", "hci0")
    gateway = BleGateway(mode="bleak", adapter=ble_adapter)
    mqtt_host = os.environ.get("MQTT_HOST", "localhost")
    mqtt_port = int(os.environ.get("MQTT_PORT", "1883"))
    mqtt_topic = os.environ.get("MQTT_TOPIC", "bb8/command/#")
    mqtt_user = os.environ.get("MQTT_USER")
    mqtt_password = os.environ.get("MQTT_PASSWORD")
    status_topic = os.environ.get("STATUS_TOPIC", "bb8/status")

    start_mqtt_dispatcher(
        mqtt_host=mqtt_host,
        mqtt_port=mqtt_port,
        mqtt_topic=mqtt_topic,
        mqtt_user=mqtt_user,
        mqtt_password=mqtt_password,
        status_topic=status_topic,
        gateway=gateway,  # Pass gateway explicitly
    )


# Call this at container startup

