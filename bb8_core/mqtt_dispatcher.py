# MQTT Dispatcher: Core MQTT event handling for Home Assistant add-on
# Finalized for Home Assistant runtime (2025-08-04)

import logging
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

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)

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
    """Blocking MQTT dispatcher for BB-8 BLE bridge with robust connect/retry."""
    import socket
    bridge = BLEBridge() if BLEBridge else None
    client = mqtt.Client()
    if mqtt_user and mqtt_password:
        client.username_pw_set(mqtt_user, mqtt_password)
    # Optional: Enable TLS if needed
    # client.tls_set()

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Connected to MQTT broker at {mqtt_host}:{mqtt_port}")
            client.subscribe(mqtt_topic)
            client.subscribe("bb8/command/power")  # Subscribe to power command topic
            logger.info(f"Subscribed to topic: {mqtt_topic} and bb8/command/power")
            if status_topic:
                publish_status(client, status_topic, bridge)
        else:
            logger.error(f"Failed to connect to MQTT broker: {rc}")

    def on_message(client, userdata, msg):
        try:
            logger.debug(f"[DISPATCH] on_message called. Raw msg: {msg}")
            topic = msg.topic
            logger.debug(f"[DISPATCH] Message topic: {topic}")
            try:
                payload = msg.payload.decode('utf-8').strip()
                logger.debug(f"[DISPATCH] Decoded payload: '{payload}' (type: {type(payload)})")
            except Exception as e:
                logger.error(f"[DISPATCH][ERROR] Payload decode error: {e}")
                return
            print(f"[MQTT] Received message on {topic}: {payload}")
            logger.info(f"Received message on {topic}: {payload}")
            # Power command handler for Home Assistant switch
            if topic == "bb8/command/power":
                logger.debug(f"[DISPATCH] Power command topic matched. Payload: '{payload}'")
                print(f"[MQTT] Power command received: {payload}")
                logger.info(f"[MQTT] Power command received: {payload}")
                if payload == "ON":
                    logger.debug(f"[DISPATCH] Entered ON handler. Function ref: {bb8_power_on_sequence}")
                    print(f"[DEBUG] About to call bb8_power_on_sequence(), function ref: {bb8_power_on_sequence}")
                    try:
                        bb8_power_on_sequence()
                        logger.debug(f"[DISPATCH] bb8_power_on_sequence() call completed.")
                    except Exception as e:
                        logger.error(f"[DISPATCH][ERROR] Exception in bb8_power_on_sequence: {e}", exc_info=True)
                        print(f"[MQTT][ERROR] Exception when calling bb8_power_on_sequence: {e}")
                elif payload == "OFF":
                    logger.debug(f"[DISPATCH] Entered OFF handler. Function ref: {bb8_power_off_sequence}")
                    print(f"[DEBUG] Entered OFF handler, about to call bb8_power_off_sequence()")
                    print(f"[DEBUG] About to call bb8_power_off_sequence(), function ref: {bb8_power_off_sequence}")
                    try:
                        bb8_power_off_sequence()
                        logger.debug(f"[DISPATCH] bb8_power_off_sequence() call completed.")
                    except Exception as e:
                        logger.error(f"[DISPATCH][ERROR] Exception in bb8_power_off_sequence: {e}", exc_info=True)
                        print(f"[MQTT][ERROR] Exception when calling bb8_power_off_sequence: {e}")
                else:
                    logger.warning(f"[DISPATCH] Unknown power command payload: '{payload}'")
                    print(f"[MQTT] Unknown power command: {payload}")
                return
            try:
                payload_json = json.loads(payload)
                command = payload_json.get("command")
                if not command:
                    logger.error("No 'command' in payload")
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
                        logger.error(f"Unknown or unsupported command: {command}")
                        result = {"success": False, "error": f"Unknown command: {command}"}
                    logger.info(f"Dispatched command '{command}': {result}")
                else:
                    logger.warning("BLEBridge not available; command not dispatched.")
            except json.JSONDecodeError as e:
                logger.error(f"Malformed JSON: {e}")
            except Exception as e:
                logger.error(f"Error handling message: {e}")
        except Exception as e:
            logger.error(f"[DISPATCH][ERROR] Unhandled exception in on_message: {e}", exc_info=True)
            print(f"[MQTT][ERROR] Unhandled exception in on_message: {e}")

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


def publish_mqtt_discovery():
    BB8_MAC = os.environ.get("BB8_MAC", "B8:17:C2:A8:ED:45")
    MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
    MQTT_USER = os.environ.get("MQTT_USER")
    MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD")
    payload = {
        "name": "BB-8 Power",
        "unique_id": "bb8_power_switch",
        "command_topic": "bb8/command/power",
        "state_topic": "bb8/state/power",
        "payload_on": "ON",
        "payload_off": "OFF",
        "device": {
            "identifiers": [f"bb8_{BB8_MAC}"],
            "name": "Sphero BB-8",
            "model": "BB-8",
            "manufacturer": "Sphero"
        }
    }
    auth = None
    if MQTT_USER and MQTT_PASSWORD:
        auth = {'username': MQTT_USER, 'password': MQTT_PASSWORD}
    publish.single(
        "homeassistant/switch/bb8_power/config",
        json.dumps(payload),
        hostname=MQTT_HOST,
        auth=auth
    )


def turn_on_bb8():
    logger.info("[BB-8] Scanning for device...")
    devices = find_toys()
    for toy in devices:
        if isinstance(toy, BB8):
            logger.info(f"[BB-8] Connecting to {toy.address} ...")
            bb8 = BB8(toy.address, adapter_cls=BleakAdapter)
            bb8.set_main_led(255, 100, 0)
            bb8.roll(0, 30)
            bb8.set_main_led(0, 0, 0)
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
            bb8.sleep()
            logger.info("[BB-8] OFF (sleep) command sent.")
            return True
    logger.warning("[BB-8] No BB-8 found for sleep.")
    return False


# Call this at container startup
publish_mqtt_discovery()
