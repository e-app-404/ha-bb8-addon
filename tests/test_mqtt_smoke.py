import json
import pytest
from bb8_core.mqtt_dispatcher import start_mqtt_dispatcher
from bb8_core.discovery_publish import publish_discovery

class FakeMQTT:
    def __init__(self):
        self.published = []
        self.subscriptions = {}
    def publish(self, topic, payload, retain=False, qos=1):
        self.published.append((topic, payload, retain, qos))
    def subscribe(self, topic, handler):
        self.subscriptions[topic] = handler
    def trigger(self, topic, payload):
        if topic in self.subscriptions:
            self.subscriptions[topic](topic, payload)

class FakeLog:
    def __init__(self):
        self.entries = []
    def info(self, msg):
        self.entries.append(("info", msg))
    def error(self, msg):
        self.entries.append(("error", msg))

class FakeToy: pass

def test_discovery_and_dispatcher_smoke():
    mqtt = FakeMQTT()
    log = FakeLog()
    device_id = "testbb8"
    name = "Test BB-8"
    # Publish discovery
    publish_discovery(mqtt, device_id, name, log)
    assert any("discovery: published" in e[1] for e in log.entries)
    # Start dispatcher
    from bb8_core.facade import Bb8Facade, Rgb
    from bb8_core.dispatcher import Bb8Dispatcher
    disp = Bb8Dispatcher(FakeToy(), mqtt, device_id, log)
    disp.start()
    # Simulate LED set
    mqtt.trigger(f"bb8/{device_id}/cmd/led/set", json.dumps({"r": 1, "g": 2, "b": 3}))
    # Simulate sleep
    mqtt.trigger(f"bb8/{device_id}/cmd/sleep", json.dumps({"after_ms": 0}))
    # Simulate drive
    mqtt.trigger(f"bb8/{device_id}/cmd/drive", json.dumps({"heading_deg": 90, "speed": 100, "duration_ms": 10}))
    # Validate state echo
    assert any(f"bb8/{device_id}/state/led" in t for t, *_ in mqtt.published)
    assert any(f"bb8/{device_id}/event/slept" in t for t, *_ in mqtt.published)
    assert any(f"bb8/{device_id}/state/motion" in t for t, *_ in mqtt.published)
