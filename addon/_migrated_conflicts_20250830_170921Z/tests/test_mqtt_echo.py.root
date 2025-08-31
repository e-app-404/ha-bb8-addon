import json

import pytest

from bb8_core.mqtt_echo import echo_led, echo_scalar


class FakeMQTT:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload, qos=1, retain=False):
        self.published.append((topic, payload, retain))


@pytest.fixture
def mqtt():
    return FakeMQTT()


def test_echo_scalar_device(mqtt):
    echo_scalar(mqtt, "base", "speed", 42)
    topic, payload, retain = mqtt.published[-1]
    data = json.loads(payload)
    assert topic == "base/speed/state"
    assert data["source"] == "device"
    assert retain is False


def test_echo_led(mqtt):
    echo_led(mqtt, "base", 1, 2, 3)
    topic, payload, retain = mqtt.published[-1]
    data = json.loads(payload)
    assert topic == "base/led/state"
    assert "source" not in data
    assert data == {"r": 1, "g": 2, "b": 3}
    assert retain is False
