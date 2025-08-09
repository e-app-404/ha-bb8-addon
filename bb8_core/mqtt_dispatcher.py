# MQTT Dispatcher: Core MQTT event handling for Home Assistant add-on
# Finalized for Home Assistant runtime (2025-08-04)

import json
import time
from typing import Optional
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import os
from spherov2.scanner import find_toys
from spherov2.toy.bb8 import BB8
from spherov2.adapter.bleak_adapter import BleakAdapter
from bb8_core.ble_bridge import bb8_power_on_sequence, bb8_power_off_sequence
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color
from spherov2.commands.core import IntervalOptions
from bb8_core.logging_setup import logger

# Placeholder for BLE bridge import
try:
    from bb8_core.ble_bridge import BLEBridge
except ImportError:
    BLEBridge = None


def start_mqtt_dispatcher(
    mqtt_host: str,
    mqtt_port: int,
    mqtt_topic: str,
    mqtt_user: Optional[str] = None,
    mqtt_password: Optional[str] = None,
    status_topic: Optional[str] = None,
) -> None:
    """Blocking MQTT dispatcher for BB-8 BLE bridge with robust connect/retry and LWT/discovery."""
    import socket
    bridge = BLEBridge() if BLEBridge else None
    client = mqtt.Client(client_id="bb8-addon", clean_session=True)
    # LWT for Home Assistant availability
    mqtt_prefix = os.environ.get("MQTT_TOPIC_PREFIX", "bb8")
    client.will_set(f"{mqtt_prefix}/status", payload="offline", qos=1, retain=True)
    if mqtt_user and mqtt_password:
        client.username_pw_set(mqtt_user, mqtt_password)
    # Optional: Enable TLS if needed
    # client.tls_set()

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Connected to MQTT broker at {mqtt_host}:{mqtt_port}")
            client.subscribe(mqtt_topic)
            client.subscribe("bb8/command/power")
            logger.info(f"Subscribed to topic: {mqtt_topic} and bb8/command/power")
            if status_topic:
                publish_status(client, status_topic, bridge)
            # Publish online status and emit discovery
            client.publish(f"{mqtt_prefix}/status", "online", qos=1, retain=True)
            try:
                publish_mqtt_discovery(client)
            except Exception as e:
                logger.warning(f"Discovery emit failed: {e}")
        else:
            logger.error(f"Failed to connect to MQTT broker: {rc}")

    def on_message(client, userdata, msg):
        try:
            logger.debug(f"[DISPATCH] on_message called. Raw msg: {msg}")
            topic = msg.topic
            logger.debug(f"[DISPATCH] Message topic: {topic}")
            try:
                payload = msg.payload.decode('utf-8').strip()
                logger.debug({"event": "mqtt_payload_decoded", "payload": payload, "type": str(type(payload))})
            except Exception as e:
                logger.error({"event": "mqtt_payload_decode_error", "error": str(e)})
                return
            logger.info({"event": "mqtt_message_received", "topic": topic, "payload": payload})
            # Power command handler for Home Assistant switch
            if topic == "bb8/command/power":
                logger.debug({"event": "mqtt_power_command", "payload": payload})
                if payload == "ON":
                    logger.debug({"event": "mqtt_power_on_handler", "function": str(bb8_power_on_sequence)})
                    try:
                        bb8_power_on_sequence()
                        logger.debug({"event": "mqtt_power_on_sequence_completed"})
                    except Exception as e:
                        logger.error({"event": "mqtt_power_on_sequence_error", "error": str(e)}, exc_info=True)
                elif payload == "OFF":
                    logger.debug({"event": "mqtt_power_off_handler", "function": str(bb8_power_off_sequence)})
                    try:
                        bb8_power_off_sequence()
                        logger.debug({"event": "mqtt_power_off_sequence_completed"})
                    except Exception as e:
                        logger.error({"event": "mqtt_power_off_sequence_error", "error": str(e)}, exc_info=True)
                else:
                    logger.warning({"event": "mqtt_power_command_unknown", "payload": payload})
                return
            try:
                payload_json = json.loads(payload)
                command = payload_json.get("command")
                if not command:
                    logger.error({"event": "mqtt_command_missing", "payload": payload})
                    return
                if bridge:
                    # Accepts 'roll', 'stop', 'set_led' commands
                    if hasattr(bridge.controller, 'roll') and command == 'roll':
                        result = bridge.controller.roll(**payload_json)
                    elif hasattr(bridge.controller, 'stop') and command == 'stop':
                        result = bridge.controller.stop()
                    elif hasattr(bridge.controller, 'set_led') and command == 'set_led':
                        result = bridge.controller.set_led(
                            payload_json.get('r', 0), payload_json.get('g', 0), payload_json.get('b', 0)
                        )
                    else:
                        logger.error({"event": "mqtt_command_unknown", "command": command})
                        result = {"success": False, "error": f"Unknown command: {command}"}
                    logger.info({"event": "mqtt_command_dispatched", "command": command, "result": result})
                else:
                    logger.warning({"event": "mqtt_bridge_unavailable", "command": command})
            except json.JSONDecodeError as e:
                logger.error({"event": "mqtt_json_decode_error", "error": str(e)})
            except Exception as e:
                logger.error({"event": "mqtt_message_handle_error", "error": str(e)})
        except Exception as e:
            logger.error({"event": "mqtt_on_message_unhandled_exception", "error": str(e)}, exc_info=True)

    def on_disconnect(client, userdata, rc):
        logger.warning(f"MQTT disconnected (rc={rc}). Attempting reconnect in 5s...")
        time.sleep(5)
        try:
            client.reconnect()
        except Exception as e:
            logger.error(f"Reconnect failed: {e}")

    def publish_status(client, topic, bridge):
        try:
            status = bridge.diagnostics() if bridge else {"status": "no_bridge"}
            client.publish(topic, json.dumps(status))
            logger.info(f"Published status to {topic}")
        except Exception as e:
            logger.error(f"Failed to publish status: {e}")

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    # Robust connect/retry loop with host fallback
    hosts_to_try = [mqtt_host, "core-mosquitto", "localhost"]
    connected = False
    while not connected:
        for host in hosts_to_try:
            try:
                resolved_host = socket.gethostbyname(host)
                logger.info(f"Attempting MQTT connect to {host}:{mqtt_port} (resolved: {resolved_host})")
                client.connect(host, mqtt_port, keepalive=60)
                connected = True
                break
            except Exception as e:
                logger.error(f"MQTT connect failed for {host}:{mqtt_port}: {e}")
        if not connected:
            logger.warning("All MQTT broker hosts failed. Retrying in 10 seconds...")
            time.sleep(10)
    client.loop_forever()


def publish_mqtt_discovery(client=None):
    BB8_MAC = os.environ.get("BB8_MAC", "B8:17:C2:A8:ED:45")
    MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
    MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
    MQTT_USER = os.environ.get("MQTT_USER")
    MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD")
    mqtt_prefix = os.environ.get("MQTT_TOPIC_PREFIX", "bb8")
    device_id = f"bb8_{BB8_MAC.replace(':','').lower()}"
    def _emit(topic, payload):
        if client:
            client.publish(topic, payload=payload, qos=1, retain=True)
        else:
            publish.single(topic, payload, hostname=MQTT_HOST, port=MQTT_PORT,
                           auth={"username": MQTT_USER, "password": MQTT_PASSWORD} if MQTT_USER and MQTT_PASSWORD else None)
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
            bb8.sleep(IntervalOptions.NONE, 0, 0, 0)
            logger.info("[BB-8] OFF (sleep) command sent.")
            return True
    logger.warning("[BB-8] No BB-8 found for sleep.")
    return False


# Call this at container startup
publish_mqtt_discovery()
