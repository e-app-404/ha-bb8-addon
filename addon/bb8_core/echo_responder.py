import os
import sys
import time
import json
import logging
import threading

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

try:
    from bleak import BleakClient
except ImportError:
    BleakClient = None

MQTT_BASE = os.environ.get("MQTT_BASE", "bb8")
MQTT_ECHO_CMD = f"{MQTT_BASE}/echo/cmd"
MQTT_ECHO_ACK = f"{MQTT_BASE}/echo/ack"
MQTT_ECHO_STATE = f"{MQTT_BASE}/echo/state"
MQTT_TELEMETRY = f"{MQTT_BASE}/telemetry/echo_roundtrip"

BLE_ADDR = os.environ.get("BLE_ADDR", None)
BLE_TOUCH_CHAR = os.environ.get("BLE_TOUCH_CHAR", None)
BLE_TOUCH_VALUE = os.environ.get("BLE_TOUCH_VALUE", "01")

LOG = logging.getLogger("echo_responder")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def pub(client, topic, payload, retain=False):
    LOG.info(f"Publishing to {topic}: {payload}")
    client.publish(topic, json.dumps(payload), qos=0, retain=retain)

def on_connect(client, userdata, flags, rc, properties=None):
    LOG.info(f"Connected to MQTT broker with rc={rc}")
    client.subscribe(MQTT_ECHO_CMD)
    LOG.info(f"Subscribed to {MQTT_ECHO_CMD}")

def on_message(client, userdata, msg):
    LOG.info(f"Received message on {msg.topic}: {msg.payload}")
    try:
        payload = json.loads(msg.payload)
    except Exception:
        payload = {"raw": msg.payload.decode("utf-8", errors="replace")}
    threading.Thread(target=handle_echo, args=(client, payload)).start()

def handle_echo(client, payload):
    t0 = time.time()
    ack = {"ts": int(t0), "value": payload.get("value", None)}
    pub(client, MQTT_ECHO_ACK, ack)
    state = {"ts": int(time.time()), "state": "touched"}
    pub(client, MQTT_ECHO_STATE, state)
    ble_ok = False
    ble_latency = None
    if BLE_ADDR and BleakClient:
        try:
            ble_ok, ble_latency = BleTouch().touch()
        except Exception as e:
            LOG.error(f"BLE touch failed: {e}")
    telemetry = {
        "ts": int(time.time()),
        "rtt_ms": int((time.time() - t0) * 1000),
        "ble_ok": ble_ok,
        "ble_latency_ms": ble_latency,
    }
    pub(client, MQTT_TELEMETRY, telemetry)

class BleTouch:
    def __init__(self):
        self.addr = BLE_ADDR
        self.char = BLE_TOUCH_CHAR
        self.value = bytes.fromhex(BLE_TOUCH_VALUE)

    def touch(self):
        if not BleakClient:
            LOG.warning("bleak not available")
            return False, None
        t0 = time.time()
        try:
            with BleakClient(self.addr) as client:
                client.write_gatt_char(self.char, self.value)
            latency = int((time.time() - t0) * 1000)
            LOG.info(f"BLE touch success, latency={latency}ms")
            return True, latency
        except Exception as e:
            LOG.error(f"BLE touch error: {e}")
            return False, None

def main():
    client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_message = on_message
    mqtt_host = os.environ.get("MQTT_HOST", "localhost")
    mqtt_port = int(os.environ.get("MQTT_PORT", "1883"))
    mqtt_user = os.environ.get("MQTT_USER", None)
    mqtt_pass = os.environ.get("MQTT_PASS", None)
    if mqtt_user and mqtt_pass:
        client.username_pw_set(mqtt_user, mqtt_pass)
    client.connect(mqtt_host, mqtt_port, 60)
    LOG.info("Starting MQTT loop")
    client.loop_forever()

if __name__ == "__main__":
    main()
