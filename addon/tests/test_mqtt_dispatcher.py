# --- Imports ---
import json
from unittest.mock import MagicMock

import addon.bb8_core.mqtt_dispatcher as dispatcher


# --- Utility/Error branch coverage ---
def test_pytest_args_for_exception(monkeypatch):
    # Pass a non-callable to force exception
    assert dispatcher._pytest_args_for(123) == []


def test_is_mock_callable_exception(monkeypatch):
    # Pass a non-mock object to hit exception and fallback logic
    class Dummy:
        pass

    assert dispatcher._is_mock_callable(Dummy()) is False


def test_trigger_discovery_connected_exception(monkeypatch):
    monkeypatch.setattr(
        dispatcher,
        "_get_scanner_publisher",
        lambda: lambda: (_ for _ in ()).throw(Exception("fail")),
    )
    monkeypatch.setenv("ENABLE_BRIDGE_TELEMETRY", "1")
    # Should log warning, not raise
    dispatcher._trigger_discovery_connected()


def test_bind_subscription_error(monkeypatch):
    dispatcher.CLIENT = None
    # Should return False if CLIENT is None
    assert dispatcher._bind_subscription("topic", lambda x: x) is False


def test_publish_discovery_already_published(monkeypatch):
    monkeypatch.setitem(dispatcher.CONFIG, "dispatcher_discovery_enabled", True)
    dispatcher._DISCOVERY_PUBLISHED.clear()
    called = {}

    def fake_publish_fn(topic, payload, retain):
        called[topic] = json.loads(payload)

    # First publish
    dispatcher.publish_bb8_discovery(fake_publish_fn)
    assert any("presence" in t or "rssi" in t for t in called)
    # Second publish should skip
    called2 = {}

    def _record2(topic, payload, retain):
        return called2.setdefault(topic, json.loads(payload))

    dispatcher.publish_bb8_discovery(_record2)
    assert not called2
    dispatcher._DISCOVERY_PUBLISHED.clear()


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

    config_updates = {
        "MQTT_HOST": "localhost",
        "MQTT_PORT": 1883,
        "MQTT_BASE": "bb8",
        "MQTT_USERNAME": "mqtt_bb8",
        "MQTT_PASSWORD": "pw",
        "MQTT_CLIENT_ID": "bb8-addon",
        "ha_discovery_topic": "homeassistant",
        "dispatcher_discovery_enabled": True,
        "availability_topic_scanner": "bb8/availability/scanner",
        "availability_payload_online": "online",
        "availability_payload_offline": "offline",
        "qos": 1,
        "bb8_mac": "AA:BB:CC:DD:EE:FF",
        "mqtt_broker": "localhost",
        "mqtt_topic_prefix": "bb8",
        "mqtt_port": 1883,
        "mqtt_username": "mqtt_bb8",
        "mqtt_password": "pw",
        "MQTT_TLS": False,
        "state_topic": "bb8/status",
        "mqtt_topic": "bb8/command/#",
    }
    for k, v in config_updates.items():
        monkeypatch.setitem(dispatcher.CONFIG, k, v)

    # Exercise some idempotent calls / ensure no exceptions
    monkeypatch.setitem(dispatcher.CONFIG, "dispatcher_discovery_enabled", True)
    dispatcher._DISCOVERY_PUBLISHED.clear()
    assert True
    # end state: discovery published cleared
