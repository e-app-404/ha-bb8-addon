# MQTT Dispatcher: Core MQTT event handling for Home Assistant add-on
# Finalized for Home Assistant runtime (2025-08-04)

import logging
import json
import time
from typing import Optional
import paho.mqtt.client as mqtt # pyright: ignore[reportMissingImports]

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
    """Blocking MQTT dispatcher for BB-8 BLE bridge."""
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
            logger.info(f"Subscribed to topic: {mqtt_topic}")
            if status_topic:
                publish_status(client, status_topic, bridge)
        else:
            logger.error(f"Failed to connect to MQTT broker: {rc}")

    def on_message(client, userdata, msg):
        logger.info(f"Received message on {msg.topic}: {msg.payload}")
        try:
            payload = json.loads(msg.payload.decode())
            command = payload.get("command")
            if not command:
                logger.error("No 'command' in payload")
                return
            if bridge:
                result = bridge.controller.handle_command(command, payload)
                logger.info(f"Dispatched command '{command}': {result}")
            else:
                logger.warning("BLEBridge not available; command not dispatched.")
        except json.JSONDecodeError as e:
            logger.error(f"Malformed JSON: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

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

    logger.info(f"Connecting to MQTT broker at {mqtt_host}:{mqtt_port}")
    client.connect(mqtt_host, mqtt_port, keepalive=60)
    client.loop_forever()
