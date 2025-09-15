import logging
import time

import addon.bb8_core.facade as facade

# --- Comprehensive facade.py tests ---
import pytest


class DummyBridge:
    def __init__(self):
        self.connected = True
        self.rssi = -60
        self.calls = []
        self.powered = None
        self.led_state = None
        self.sleeping = False

    def connect(self):
        self.calls.append("connect")
        self.connected = True

    def sleep(self, arg):
        self.calls.append(("sleep", arg))
        self.sleeping = True

    def stop(self):
        self.calls.append("stop")

    def set_led_off(self):
        self.calls.append("led_off")

    def set_led_rgb(self, r, g, b):
        self.calls.append(("led_rgb", r, g, b))

    def set_heading(self, deg):
        self.calls.append(("heading", deg))

    def set_speed(self, v):
        self.calls.append(("speed", v))

    def drive(self):
        self.calls.append("drive")

    def is_connected(self):
        return self.connected

    def get_rssi(self):
        return self.rssi


class DummyClient:
    def __init__(self):
        self.published = []
        self.subscribed = []
        self.callbacks = {}

    def publish(self, topic, payload=None, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))

    def subscribe(self, topic, qos=0):
        self.subscribed.append((topic, qos))

    def message_callback_add(self, topic, handler):
        self.callbacks[topic] = handler


def test_sleep_led_pattern():
    pattern = facade._sleep_led_pattern()
    assert isinstance(pattern, list)
    assert len(pattern) == 5
    assert all(isinstance(t, tuple) and len(t) == 3 for t in pattern)


def test_emit_led_paths(monkeypatch):
    # Test Core.emit_led path
    class CoreEmit:
        @staticmethod
        def emit_led(bridge, r, g, b):
            bridge.calls.append(("core_emit", r, g, b))

    f = facade.BB8Facade(DummyBridge())
    f.Core = CoreEmit
    f._emit_led(1, 2, 3)
    assert ("core_emit", 1, 2, 3) in f.bridge.calls

    # Test Core.publish_led_rgb path
    class CorePub:
        @staticmethod
        def publish_led_rgb(bridge, r, g, b):
            bridge.calls.append(("core_pub", r, g, b))

    f.Core = CorePub
    f._emit_led(4, 5, 6)
    assert ("core_pub", 4, 5, 6) in f.bridge.calls

    # Test Core.calls list path
    class CoreCalls:
        calls = []

    f.Core = CoreCalls
    f._emit_led(7, 8, 9)
    assert ("led", 7, 8, 9) in CoreCalls.calls


def test_power_connected_and_disconnected(monkeypatch):
    bridge = DummyBridge()
    f = facade.BB8Facade(bridge)
    # Connected, power on
    bridge.connected = True
    f.power(True)
    assert "connect" in bridge.calls
    # Connected, power off
    f.power(False)
    assert any(c == ("sleep", None) for c in bridge.calls)
    # Disconnected, power on
    bridge.connected = False
    f.power(True)
    # Should call _publish_rejected
    bridge.connected = False
    f.power(False)


def test_stop_connected_and_disconnected(monkeypatch):
    bridge = DummyBridge()
    f = facade.BB8Facade(bridge)
    bridge.connected = True
    f.stop()
    assert "stop" in bridge.calls
    bridge.connected = False
    f.stop()


def test_set_led_off_connected_and_disconnected(monkeypatch):
    bridge = DummyBridge()
    f = facade.BB8Facade(bridge)
    bridge.connected = True
    f.set_led_off()
    assert "led_off" in bridge.calls
    bridge.connected = False
    f.set_led_off()


def test_set_led_rgb_clamping(monkeypatch):
    bridge = DummyBridge()
    f = facade.BB8Facade(bridge)
    # Should clamp values
    f.set_led_rgb(300, -5, 10)
    # Should not raise


def test_is_connected_and_get_rssi():
    bridge = DummyBridge()
    f = facade.BB8Facade(bridge)
    assert f.is_connected() is True
    assert f.get_rssi() == -60

    # Bridge without methods
    class NoBridge:
        pass

    f2 = facade.BB8Facade(NoBridge())
    assert f2.is_connected() is True
    assert f2.get_rssi() == 0


@pytest.mark.asyncio
async def test_attach_mqtt(monkeypatch):
    bridge = DummyBridge()
    f = facade.BB8Facade(bridge)
    client = DummyClient()
    # Patch publish_discovery to record call
    called = {}

    async def fake_publish_discovery(
        client_, mac_upper, dbus_path=None, model=None, name=None
    ):
        called["discovery"] = (mac_upper, dbus_path, model, name)

    monkeypatch.setattr(facade, "publish_discovery", fake_publish_discovery)
    await f.attach_mqtt(client, "bb8/test", qos=1, retain=True)
    assert "discovery" in called
    # Should set up subscriptions
    assert any("power/set" in t[0] for t in client.subscribed)
    assert any("led/set" in t[0] for t in client.subscribed)
    assert any("stop/press" in t[0] for t in client.subscribed)


def test_publish_rejected():
    bridge = DummyBridge()
    f = facade.BB8Facade(bridge)
    client = DummyClient()
    f._mqtt = {"client": client, "base": "bb8/test", "qos": 1, "retain": True}
    f._publish_rejected("power", "offline")
    assert any("rejected" in t[0] for t in client.published)


def test_sleep_function(monkeypatch):
    bridge = DummyBridge()
    f = facade.BB8Facade(bridge)
    # Patch _emit_led to record calls
    calls = []
    monkeypatch.setattr(f, "_emit_led", lambda r, g, b: calls.append((r, g, b)))
    # Patch time.sleep to avoid delay
    monkeypatch.setattr(time, "sleep", lambda s: None)
    # Patch logging
    logger = logging.getLogger(__name__)
    monkeypatch.setattr(logger, "info", lambda *a, **k: None)
    facade.sleep(f)
    assert len(calls) == 5


def test_sleep_mapping(monkeypatch):
    class StubCore:
        calls = []

        @staticmethod
        def emit_led(bridge, r, g, b):
            StubCore.calls.append(("led", r, g, b))

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
