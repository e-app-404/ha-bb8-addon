import json
import threading
import time
from unittest.mock import patch

import paho.mqtt.client as mqtt  # pyright: ignore[reportMissingImports]
from addon.bb8_core.logging_setup import logger
from addon.bb8_core.mqtt_dispatcher import start_mqtt_dispatcher

# Test parameters
MQTT_HOST = "test.mosquitto.org"
MQTT_PORT = 1883
MQTT_TOPIC = "bb8/test/cmd"
STATUS_TOPIC = "bb8/test/status"


# Mock BLEBridge and its controller
class MockController:
    def handle_command(self, command, payload):
        logger.info(
            {
                "event": "test_mock_handle_command",
                "command": command,
                "payload": payload,
            }
        )
        return "mock-dispatched"


class MockBLEBridge:
    def __init__(self):
        self.controller = MockController()

    def diagnostics(self):
        return {"status": "mock_bridge_ok"}


def run_dispatcher():
    with patch("addon.bb8_core.mqtt_dispatcher.BLEBridge", MockBLEBridge):
        start_mqtt_dispatcher(
            mqtt_host=MQTT_HOST,
            mqtt_port=MQTT_PORT,
            mqtt_topic=MQTT_TOPIC,
            status_topic=STATUS_TOPIC,
        )


def publish_test_messages():
    client = mqtt.Client()
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()
    time.sleep(2)  # Wait for connection
    # Publish valid command
    payload = json.dumps({"command": "roll", "speed": 100})
    client.publish(MQTT_TOPIC, payload)
    logger.info({"event": "test_publish_valid_command", "payload": payload})
    time.sleep(1)
    # Publish malformed payload
    client.publish(MQTT_TOPIC, "{invalid_json")
    logger.info(
        {
            "event": "test_publish_malformed_payload",
            "payload": "{invalid_json",
        }
    )
    time.sleep(1)
    client.loop_stop()
    client.disconnect()


def main():
    # Start dispatcher in a background thread
    dispatcher_thread = threading.Thread(target=run_dispatcher, daemon=True)
    dispatcher_thread.start()
    time.sleep(3)  # Allow dispatcher to connect and subscribe
    publish_test_messages()
    logger.info({"event": "test_waiting_for_dispatcher"})
    time.sleep(5)
    logger.info("[TEST] Test complete. Check logs for BLE dispatch and error handling.")


if __name__ == "__main__":
    main()
