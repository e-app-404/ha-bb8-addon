import time

import addon.bb8_core.facade as facade


class StubCore:
    calls: list[tuple] = []

    @staticmethod
    def sleep(_unused_toy, interval_option, unk, unk2, _unused_proc=None):
        # Parameters intentionally unused
        StubCore.calls.append(("sleep", interval_option, unk, unk2))
        _ = _unused_toy
        _ = _unused_proc

    def set_main_led(_unused_toy, r, g, b, _unused_proc=None):
        # Parameters intentionally unused
        StubCore.calls.append(("led", r, g, b))
        _ = _unused_toy
        _ = _unused_proc

    def set_heading(_unused_toy, h, _unused_proc=None):
        # Parameters intentionally unused
        StubCore.calls.append(("heading", h))
        _ = _unused_toy
        _ = _unused_proc

    @staticmethod
    def dummy_decorator():
        pass


def test_sleep_mapping(monkeypatch):
    StubCore.calls.clear()
    facade.BB8Facade.Core = StubCore  # Patch before instantiation
    f = facade.BB8Facade(bridge=object())
    f.set_led_rgb(300, -5, 10)
    # clamped to 255,0,10
    assert ("led", 255, 0, 10) in StubCore.calls

    monkeypatch.setattr(facade, "Core", StubCore, raising=False)
    StubCore.calls.clear()
    slept = {"ms": 0}
    monkeypatch.setattr(
        time,
        "sleep",
        lambda s: slept.__setitem__("ms", slept["ms"] + int(s * 1000)),
        raising=False,
    )

    # --- Comprehensive BB8Facade tests ---
    from unittest import mock

    class DummyBridge:
        def __init__(self):
            self.powered = False
            self.led_state = None
            self.sleeping = False
            self.mqtt_client = None

        def set_power(self, value):
            self.powered = value

        def set_led(self, r, g, b):
            self.led_state = (r, g, b)

        def sleep(self):
            self.sleeping = True

        def attach_mqtt(self, client):
            self.mqtt_client = client

    class DummyMQTT:
        def __init__(self):
            self.published = []
            self.connected = True

        def publish(self, topic, payload, qos=0, retain=False):
            self.published.append((topic, payload, qos, retain))

    @mock.patch("addon.bb8_core.facade.publish_device_echo")
    def test_power_publish(mock_pub):
        bridge = DummyBridge()
        f = facade.BB8Facade(bridge)
        f.power(True)
        mock_pub.assert_called()
        f.power(False)
        mock_pub.assert_called()

    def test_stop_publish(monkeypatch):
        bridge = DummyBridge()
        f = facade.BB8Facade(bridge)
        called = {}

        def fake_pub(client, topic, payload):
            called["topic"] = topic
            called["payload"] = payload

        monkeypatch.setattr(facade, "publish_device_echo", fake_pub)
        f.stop()
        assert "stop" in called["topic"]

    def test_set_led_off(monkeypatch):
        bridge = DummyBridge()
        f = facade.BB8Facade(bridge)
        called = {}

        def fake_pub(client, topic, payload):
            called["topic"] = topic
            called["payload"] = payload

        monkeypatch.setattr(facade, "publish_device_echo", fake_pub)
        f.set_led_off()
        assert called["payload"] == {"r": 0, "g": 0, "b": 0}

    def test_set_led_rgb(monkeypatch):
        bridge = DummyBridge()
        f = facade.BB8Facade(bridge)
        called = {}

        def fake_pub(client, topic, payload):
            called["topic"] = topic
            called["payload"] = payload

        monkeypatch.setattr(facade, "publish_device_echo", fake_pub)
        f.set_led_rgb(10, 20, 30)
        assert called["payload"] == {"r": 10, "g": 20, "b": 30}

    def test_sleep_publish(monkeypatch):
        bridge = DummyBridge()
        f = facade.BB8Facade(bridge)
        called = {}

        def fake_pub(client, topic, payload):
            called["topic"] = topic
            called["payload"] = payload

        monkeypatch.setattr(facade, "publish_device_echo", fake_pub)
        f.sleep()
        assert "sleep" in called["topic"]

    def test_attach_mqtt(monkeypatch):
        bridge = DummyBridge()
        f = facade.BB8Facade(bridge)
        client = DummyMQTT()
        monkeypatch.setattr(facade, "publish_device_echo", lambda c, t, p: None)
        f.attach_mqtt(client)
        assert bridge.mqtt_client == client

    def test_color_parsing(monkeypatch):
        bridge = DummyBridge()
        f = facade.BB8Facade(bridge)
        called = {}

        def fake_pub(client, topic, payload):
            called["payload"] = payload

        monkeypatch.setattr(facade, "publish_device_echo", fake_pub)
        # Valid color
        f.set_led_rgb("255", "128", "64")
        assert called["payload"] == {"r": 255, "g": 128, "b": 64}
        # Invalid color
        f.set_led_rgb("notanint", "0", "0")
        assert called["payload"] == {"r": 0, "g": 0, "b": 0}

    def test_rejected_publish(monkeypatch):
        bridge = DummyBridge()
        f = facade.BB8Facade(bridge)

        def fake_pub(client, topic, payload):
            raise Exception("Publish failed")

        monkeypatch.setattr(facade, "publish_device_echo", fake_pub)
        # Should not raise
        f.set_led_rgb(1, 2, 3)
        f.set_led_off()
        f.sleep()
        f.stop()
        f.power(True)

    def test_telemetry_publish(monkeypatch):
        bridge = DummyBridge()
        f = facade.BB8Facade(bridge)
        called = {}

        def fake_pub(client, topic, payload):
            called["topic"] = topic
            called["payload"] = payload

        monkeypatch.setattr(facade, "publish_device_echo", fake_pub)
        # Simulate telemetry
        f.publish_telemetry({"rssi": -60, "mac": "AA:BB:CC:DD:EE:FF"})
        assert "rssi" in called["payload"]
        assert "mac" in called["payload"]
