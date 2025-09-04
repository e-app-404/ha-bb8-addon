import warnings

warnings.filterwarnings(
    "ignore", "Callback API version 1 is deprecated", DeprecationWarning, "paho"
)
import json

import pytest
from tests.helpers.fakes import FakeMQTT, FakeMessage
from tests.helpers.util import assert_json_schema, assert_contains_log


@pytest.mark.usefixtures("caplog_level")
def test_echo_publish_and_schema(monkeypatch, caplog):
    mqtt = FakeMQTT()
    published = []

    def echo_handler(client, userdata, msg):
        published.append((msg.topic, msg.payload))
        mqtt.publish("bb8/echo/state", '{"source":"device"}', retain=False)

    mqtt.message_callback_add("bb8/echo/cmd", echo_handler)
    mqtt.trigger("bb8/echo/cmd", b"ping")
    found = any(t == "bb8/echo/state" for t, _ in mqtt.published)
    assert found
    for t, p, *_ in mqtt.published:
        if t == "bb8/echo/state":
            obj = assert_json_schema(p, ["source"])
            assert obj["source"] == "device"
    assert_contains_log(caplog, "echo")


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
