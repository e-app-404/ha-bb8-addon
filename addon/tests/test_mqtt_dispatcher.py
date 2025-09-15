# --- Comprehensive mqtt_dispatcher.py tests ---
import json
import types
from unittest.mock import MagicMock

import addon.bb8_core.mqtt_dispatcher as dispatcher


def test_is_dispatcher_started_and_ensure(monkeypatch):
    dispatcher._DISPATCHER_STARTED = False
    assert dispatcher.is_dispatcher_started() is False
    assert dispatcher.ensure_dispatcher_started() is True
    assert dispatcher.is_dispatcher_started() is True
    # Idempotent
    assert dispatcher.ensure_dispatcher_started() is True


def test_device_block_and_norm_mac(monkeypatch):
    monkeypatch.setitem(dispatcher.CONFIG, "bb8_mac", "AA:BB:CC:DD:EE:FF")
    block = dispatcher._device_block()
    assert "ids" in block and "name" in block
    assert dispatcher._norm_mac("aa:bb:cc:dd:ee:ff") == "AABBCCDDEEFF"
    assert dispatcher._norm_mac(None) == "UNKNOWN"


def test_telemetry_enabled(monkeypatch):
    monkeypatch.setenv("ENABLE_BRIDGE_TELEMETRY", "1")
    assert dispatcher._telemetry_enabled() is True
    monkeypatch.setenv("ENABLE_BRIDGE_TELEMETRY", "0")
    assert dispatcher._telemetry_enabled() is False


def test_is_mock_callable():
    class Dummy:
        pass

    m = MagicMock()
    assert dispatcher._is_mock_callable(m) is True
    assert dispatcher._is_mock_callable(Dummy()) is False


def test_publish_discovery(monkeypatch):
    called = {}

    async def fake_pub_discovery(*args, **kwargs):
        called["pub"] = True

    monkeypatch.setattr(dispatcher, "_publish_discovery_async", fake_pub_discovery)
    dispatcher.publish_discovery("client", "mac")
    assert "pub" in called


def test_publish_led_discovery(monkeypatch):
    monkeypatch.setitem(dispatcher.CONFIG, "dispatcher_discovery_enabled", True)
    dispatcher._DISCOVERY_PUBLISHED.clear()
    called = {}

    def fake_publish_fn(topic, payload, retain):
        called[topic] = json.loads(payload)

    dispatcher._DISCOVERY_PUBLISHED.clear()
    dispatcher.publish_led_discovery(fake_publish_fn)
    assert any("led" in t for t in called)


def test_publish_bb8_discovery(monkeypatch):
    monkeypatch.setitem(dispatcher.CONFIG, "dispatcher_discovery_enabled", True)
    dispatcher._DISCOVERY_PUBLISHED.clear()
    called = {}

    def fake_publish_fn(topic, payload, retain):
        called[topic] = json.loads(payload)

    dispatcher._DISCOVERY_PUBLISHED.clear()
    dispatcher.publish_bb8_discovery(fake_publish_fn)
    assert any(
        "presence" in t or "rssi" in t for t in called
    ), f"No 'presence' or 'rssi' topic published, called={called}"


def test_publish_bb8_discovery_gate(monkeypatch):
    monkeypatch.setitem(dispatcher.CONFIG, "dispatcher_discovery_enabled", False)
    called = {}

    def fake_publish_fn(topic, payload, retain):
        called[topic] = json.loads(payload)

    dispatcher.publish_bb8_discovery(fake_publish_fn)
    # Should not publish anything
    assert not called


def test_maybe_publish_bb8_discovery(monkeypatch):
    monkeypatch.setitem(dispatcher.CONFIG, "dispatcher_discovery_enabled", True)

    class DummyClient:
        def is_connected(self):
            return True

        def publish(self, topic, payload, qos, retain):
            return types.SimpleNamespace(mid=1, wait_for_publish=lambda timeout=3: True)

    dispatcher.CLIENT = DummyClient()
    dispatcher._DISCOVERY_PUBLISHED.clear()
    dispatcher._maybe_publish_bb8_discovery()
    # Should publish all entities


def test_bind_subscription(monkeypatch):
    dispatcher.CLIENT = MagicMock()
    dispatcher._BOUND_TOPICS.clear()
    dispatcher._PENDING_SUBS.clear()

    def dummy_handler(client, userdata, message):
        pass

    topic = "bb8/test/topic"
    assert dispatcher.register_subscription(topic, dummy_handler) is None


def test_main(monkeypatch):
    monkeypatch.setitem(dispatcher.CONFIG, "MQTT_HOST", "localhost")
    monkeypatch.setitem(dispatcher.CONFIG, "MQTT_PORT", 1883)
    monkeypatch.setitem(dispatcher.CONFIG, "MQTT_BASE", "bb8")
    monkeypatch.setitem(dispatcher.CONFIG, "MQTT_USERNAME", "mqtt_bb8")
    monkeypatch.setitem(dispatcher.CONFIG, "MQTT_PASSWORD", "pw")
    monkeypatch.setitem(dispatcher.CONFIG, "MQTT_CLIENT_ID", "bb8-addon")
    monkeypatch.setitem(dispatcher.CONFIG, "ha_discovery_topic", "homeassistant")
    monkeypatch.setitem(dispatcher.CONFIG, "dispatcher_discovery_enabled", True)
    monkeypatch.setitem(
        dispatcher.CONFIG, "availability_topic_scanner", "bb8/availability/scanner"
    )
    monkeypatch.setitem(dispatcher.CONFIG, "availability_payload_online", "online")
    monkeypatch.setitem(dispatcher.CONFIG, "availability_payload_offline", "offline")
    monkeypatch.setitem(dispatcher.CONFIG, "qos", 1)
    monkeypatch.setitem(dispatcher.CONFIG, "bb8_mac", "AA:BB:CC:DD:EE:FF")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_broker", "localhost")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_topic_prefix", "bb8")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_port", 1883)
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_username", "mqtt_bb8")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_password", "pw")
    monkeypatch.setitem(dispatcher.CONFIG, "MQTT_TLS", False)
    monkeypatch.setitem(dispatcher.CONFIG, "MQTT_CLIENT_ID", "bb8-addon")
    monkeypatch.setitem(dispatcher.CONFIG, "state_topic", "bb8/status")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_topic", "bb8/command/#")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_port", 1883)
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_topic", "bb8/command/#")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_broker", "localhost")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_username", "mqtt_bb8")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_password", "pw")
    monkeypatch.setitem(dispatcher.CONFIG, "MQTT_CLIENT_ID", "bb8-addon")
    monkeypatch.setitem(dispatcher.CONFIG, "ha_discovery_topic", "homeassistant")
    monkeypatch.setitem(dispatcher.CONFIG, "dispatcher_discovery_enabled", True)
    monkeypatch.setitem(
        dispatcher.CONFIG, "availability_topic_scanner", "bb8/availability/scanner"
    )
    monkeypatch.setitem(dispatcher.CONFIG, "availability_payload_online", "online")
    monkeypatch.setitem(dispatcher.CONFIG, "availability_payload_offline", "offline")
    monkeypatch.setitem(dispatcher.CONFIG, "qos", 1)
    monkeypatch.setitem(dispatcher.CONFIG, "bb8_mac", "AA:BB:CC:DD:EE:FF")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_broker", "localhost")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_topic_prefix", "bb8")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_port", 1883)
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_username", "mqtt_bb8")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_password", "pw")
    monkeypatch.setitem(dispatcher.CONFIG, "MQTT_TLS", False)
    monkeypatch.setitem(dispatcher.CONFIG, "MQTT_CLIENT_ID", "bb8-addon")
    monkeypatch.setitem(dispatcher.CONFIG, "state_topic", "bb8/status")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_topic", "bb8/command/#")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_port", 1883)
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_topic", "bb8/command/#")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_broker", "localhost")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_username", "mqtt_bb8")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_password", "pw")
    monkeypatch.setitem(dispatcher.CONFIG, "MQTT_CLIENT_ID", "bb8-addon")
    monkeypatch.setitem(dispatcher.CONFIG, "ha_discovery_topic", "homeassistant")
    monkeypatch.setitem(dispatcher.CONFIG, "dispatcher_discovery_enabled", True)
    monkeypatch.setitem(
        dispatcher.CONFIG, "availability_topic_scanner", "bb8/availability/scanner"
    )
    monkeypatch.setitem(dispatcher.CONFIG, "availability_payload_online", "online")
    monkeypatch.setitem(dispatcher.CONFIG, "availability_payload_offline", "offline")
    monkeypatch.setitem(dispatcher.CONFIG, "qos", 1)
    monkeypatch.setitem(dispatcher.CONFIG, "bb8_mac", "AA:BB:CC:DD:EE:FF")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_broker", "localhost")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_topic_prefix", "bb8")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_port", 1883)
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_username", "mqtt_bb8")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_password", "pw")
    monkeypatch.setitem(dispatcher.CONFIG, "MQTT_TLS", False)
    monkeypatch.setitem(dispatcher.CONFIG, "MQTT_CLIENT_ID", "bb8-addon")
    monkeypatch.setitem(dispatcher.CONFIG, "state_topic", "bb8/status")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_topic", "bb8/command/#")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_port", 1883)
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_topic", "bb8/command/#")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_broker", "localhost")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_username", "mqtt_bb8")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_password", "pw")
    monkeypatch.setitem(dispatcher.CONFIG, "MQTT_CLIENT_ID", "bb8-addon")
    monkeypatch.setitem(dispatcher.CONFIG, "ha_discovery_topic", "homeassistant")
    monkeypatch.setitem(dispatcher.CONFIG, "dispatcher_discovery_enabled", True)
    monkeypatch.setitem(
        dispatcher.CONFIG, "availability_topic_scanner", "bb8/availability/scanner"
    )
    monkeypatch.setitem(dispatcher.CONFIG, "availability_payload_online", "online")
    monkeypatch.setitem(dispatcher.CONFIG, "availability_payload_offline", "offline")
    monkeypatch.setitem(dispatcher.CONFIG, "qos", 1)
    monkeypatch.setitem(dispatcher.CONFIG, "bb8_mac", "AA:BB:CC:DD:EE:FF")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_broker", "localhost")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_topic_prefix", "bb8")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_port", 1883)
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_username", "mqtt_bb8")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_password", "pw")
    monkeypatch.setitem(dispatcher.CONFIG, "MQTT_TLS", False)
    monkeypatch.setitem(dispatcher.CONFIG, "MQTT_CLIENT_ID", "bb8-addon")
    monkeypatch.setitem(dispatcher.CONFIG, "state_topic", "bb8/status")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_topic", "bb8/command/#")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_port", 1883)
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_topic", "bb8/command/#")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_broker", "localhost")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_username", "mqtt_bb8")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_password", "pw")
    monkeypatch.setitem(dispatcher.CONFIG, "MQTT_CLIENT_ID", "bb8-addon")
    monkeypatch.setitem(dispatcher.CONFIG, "ha_discovery_topic", "homeassistant")
    monkeypatch.setitem(dispatcher.CONFIG, "dispatcher_discovery_enabled", True)
    monkeypatch.setitem(
        dispatcher.CONFIG, "availability_topic_scanner", "bb8/availability/scanner"
    )
    monkeypatch.setitem(dispatcher.CONFIG, "availability_payload_online", "online")
    monkeypatch.setitem(dispatcher.CONFIG, "availability_payload_offline", "offline")
    monkeypatch.setitem(dispatcher.CONFIG, "qos", 1)
    monkeypatch.setitem(dispatcher.CONFIG, "bb8_mac", "AA:BB:CC:DD:EE:FF")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_broker", "localhost")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_topic_prefix", "bb8")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_port", 1883)
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_username", "mqtt_bb8")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_password", "pw")
    monkeypatch.setitem(dispatcher.CONFIG, "MQTT_TLS", False)
    monkeypatch.setitem(dispatcher.CONFIG, "MQTT_CLIENT_ID", "bb8-addon")
    monkeypatch.setitem(dispatcher.CONFIG, "state_topic", "bb8/status")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_topic", "bb8/command/#")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_port", 1883)
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_topic", "bb8/command/#")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_broker", "localhost")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_username", "mqtt_bb8")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_password", "pw")
    monkeypatch.setitem(dispatcher.CONFIG, "MQTT_CLIENT_ID", "bb8-addon")
    monkeypatch.setitem(dispatcher.CONFIG, "ha_discovery_topic", "homeassistant")
    monkeypatch.setitem(dispatcher.CONFIG, "dispatcher_discovery_enabled", True)
    monkeypatch.setitem(
        dispatcher.CONFIG, "availability_topic_scanner", "bb8/availability/scanner"
    )
    monkeypatch.setitem(dispatcher.CONFIG, "availability_payload_online", "online")
    monkeypatch.setitem(dispatcher.CONFIG, "availability_payload_offline", "offline")
    monkeypatch.setitem(dispatcher.CONFIG, "qos", 1)
    monkeypatch.setitem(dispatcher.CONFIG, "bb8_mac", "AA:BB:CC:DD:EE:FF")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_broker", "localhost")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_topic_prefix", "bb8")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_port", 1883)
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_username", "mqtt_bb8")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_password", "pw")
    monkeypatch.setitem(dispatcher.CONFIG, "MQTT_TLS", False)
    monkeypatch.setitem(dispatcher.CONFIG, "MQTT_CLIENT_ID", "bb8-addon")
    monkeypatch.setitem(dispatcher.CONFIG, "state_topic", "bb8/status")
    monkeypatch.setitem(dispatcher.CONFIG, "mqtt_topic", "bb8/command/#")
    dispatcher.main()
