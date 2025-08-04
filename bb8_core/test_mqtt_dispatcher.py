import threading
import time
import json
import logging
from unittest.mock import MagicMock, patch
import paho.mqtt.client as mqtt # pyright: ignore[reportMissingImports]

# Configure logging to stdout for test visibility
logging.basicConfig(level=logging.INFO)

# Test parameters
MQTT_HOST = "test.mosquitto.org"
MQTT_PORT = 1883
MQTT_TOPIC = "bb8/test/cmd"
STATUS_TOPIC = "bb8/test/status"

# Mock BLEBridge and its controller
class MockController:
    def handle_command(self, command, payload):
        print(f"[MOCK] handle_command called with: {command}, {payload}")
        return "mock-dispatched"

class MockBLEBridge:
    def __init__(self):
        self.controller = MockController()
    def diagnostics(self):
        return {"status": "mock_bridge_ok"}

def run_dispatcher():
    with patch("bb8_core.mqtt_dispatcher.BLEBridge", MockBLEBridge):
        from bb8_core import mqtt_dispatcher
        mqtt_dispatcher.start_mqtt_dispatcher(
            mqtt_host=MQTT_HOST,
            mqtt_port=MQTT_PORT,
            mqtt_topic=MQTT_TOPIC,
            status_topic=STATUS_TOPIC
        )

def publish_test_messages():
    client = mqtt.Client()
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()
    time.sleep(2)  # Wait for connection
    # Publish valid command
    payload = json.dumps({"command": "roll", "speed": 100})
    client.publish(MQTT_TOPIC, payload)
    print(f"[TEST] Published valid command: {payload}")
    time.sleep(1)
    # Publish malformed payload
    client.publish(MQTT_TOPIC, "{invalid_json")
    print("[TEST] Published malformed payload: {invalid_json")
    time.sleep(1)
    client.loop_stop()
    client.disconnect()

def main():
    # Start dispatcher in a background thread
    dispatcher_thread = threading.Thread(target=run_dispatcher, daemon=True)
    dispatcher_thread.start()
    time.sleep(3)  # Allow dispatcher to connect and subscribe
    publish_test_messages()
    print("[TEST] Waiting for dispatcher to process messages...")
    time.sleep(5)
    print("[TEST] Test complete. Check logs for BLE dispatch and error handling.")

if __name__ == "__main__":
    main()
