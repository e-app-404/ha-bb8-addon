import threading
import time

import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion


def test_mqtt_connect_and_message():
    events = []

    def on_connect(client, userdata, flags, rc, properties=None):
        events.append("connected")
        client.subscribe("test/topic", qos=0)
        client.publish("test/topic", "hello", qos=0)

    def on_message(client, userdata, msg):
        events.append((msg.topic, msg.payload.decode()))

    client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    # Use test broker (e.g., test.mosquitto.org) or local broker
    client.connect("test.mosquitto.org", 1883, 10)
    client.loop_start()
    time.sleep(2)
    client.loop_stop()
    assert "connected" in events
    assert any(
        isinstance(e, tuple) and e[0] == "test/topic" and e[1] == "hello"
        for e in events
    )


def test_threading_event():
    event = threading.Event()

    def worker():
        time.sleep(0.1)
        event.set()

    t = threading.Thread(target=worker)
    t.start()
    t.join(timeout=1)
    assert event.is_set()
