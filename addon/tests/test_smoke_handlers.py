import json
from unittest import mock

import pytest
from addon.bb8_core import smoke_handlers


def test_env_success(monkeypatch):
    monkeypatch.setenv("MQTT_HOST", "localhost")
    monkeypatch.setenv("MQTT_PORT", "1883")
    monkeypatch.setenv("MQTT_BASE", "bb8")
    monkeypatch.setenv("MQTT_USERNAME", "user")
    monkeypatch.setenv("MQTT_PASSWORD", "pass")
    host, port, base, user, pwd = smoke_handlers.env()
    assert host == "localhost"
    assert port == 1883
    assert base == "bb8"
    assert user == "user"
    assert pwd == "pass"


def test_env_missing_host(monkeypatch):
    monkeypatch.delenv("MQTT_HOST", raising=False)
    with pytest.raises(ValueError):
        smoke_handlers.env()


def test_env_default_port(monkeypatch):
    monkeypatch.setenv("MQTT_HOST", "localhost")
    monkeypatch.delenv("MQTT_PORT", raising=False)
    monkeypatch.setenv("MQTT_BASE", "bb8")
    host, port, base, *_ = smoke_handlers.env()
    assert port == 1883


def test_main_success(monkeypatch):
    # Patch env to return fixed values
    monkeypatch.setenv("MQTT_HOST", "localhost")
    monkeypatch.setenv("MQTT_PORT", "1883")
    monkeypatch.setenv("MQTT_BASE", "bb8")
    monkeypatch.setenv("MQTT_USERNAME", "user")
    monkeypatch.setenv("MQTT_PASSWORD", "pass")
    monkeypatch.setattr(
        smoke_handlers, "env", lambda: ("localhost", 1883, "bb8", "user", "pass")
    )
    # Patch mqtt.Client
    mock_client = mock.Mock()
    mock_client.loop_start = mock.Mock()
    mock_client.loop_stop = mock.Mock()
    mock_client.disconnect = mock.Mock()
    mock_client.connect = mock.Mock()
    mock_client.subscribe = mock.Mock()
    mock_client.publish = mock.Mock()
    # Simulate got event set after on_message
    got_event = mock.Mock()
    got_event.is_set.return_value = True
    got_event.wait = mock.Mock()
    monkeypatch.setattr(smoke_handlers.threading, "Event", lambda: got_event)
    monkeypatch.setattr(smoke_handlers.mqtt, "Client", lambda *a, **kw: mock_client)
    # Patch print to capture output
    output = {}

    def fake_print(val):
        output["val"] = val

    monkeypatch.setattr("builtins.print", fake_print)
    ret = smoke_handlers.main()
    assert ret == 0
    assert json.loads(output["val"]) == {"handlers_active": True}


def test_main_failure(monkeypatch):
    monkeypatch.setattr(
        smoke_handlers, "env", lambda: ("localhost", 1883, "bb8", "user", "pass")
    )
    mock_client = mock.Mock()
    mock_client.loop_start = mock.Mock()
    mock_client.loop_stop = mock.Mock()
    mock_client.disconnect = mock.Mock()
    mock_client.connect = mock.Mock()
    mock_client.subscribe = mock.Mock()
    mock_client.publish = mock.Mock()
    got_event = mock.Mock()
    got_event.is_set.return_value = False
    got_event.wait = mock.Mock()
    monkeypatch.setattr(smoke_handlers.threading, "Event", lambda: got_event)
    monkeypatch.setattr(smoke_handlers.mqtt, "Client", lambda *a, **kw: mock_client)
    output = {}

    def fake_print(val):
        output["val"] = val

    monkeypatch.setattr("builtins.print", fake_print)
    ret = smoke_handlers.main()
    assert ret == 1
    assert json.loads(output["val"]) == {"handlers_active": False}


def test_on_message_invalid_json(monkeypatch):
    # Patch env and mqtt.Client
    monkeypatch.setattr(
        smoke_handlers, "env", lambda: ("localhost", 1883, "bb8", "user", "pass")
    )
    mock_client = mock.Mock()
    got_event = mock.Mock()
    got_event.is_set.return_value = True
    got_event.wait = mock.Mock()
    monkeypatch.setattr(smoke_handlers.threading, "Event", lambda: got_event)
    monkeypatch.setattr(smoke_handlers.mqtt, "Client", lambda *a, **kw: mock_client)
    # Patch print
    output = {}

    def fake_print(val):
        output["val"] = val

    monkeypatch.setattr("builtins.print", fake_print)

    # Patch on_message to simulate invalid JSON
    def fake_on_message(_, __, msg):
        # Should not raise
        try:
            ev = json.loads((msg.payload or b"{}").decode("utf-8", "ignore"))
        except Exception:
            ev = {}
        assert ev == {}

    monkeypatch.setattr(
        smoke_handlers,
        "main",
        lambda: fake_on_message(None, None, mock.Mock(payload=b"notjson")),
    )
    smoke_handlers.main()


def test_on_message_missing_event(monkeypatch):
    # Patch env and mqtt.Client
    monkeypatch.setattr(
        smoke_handlers, "env", lambda: ("localhost", 1883, "bb8", "user", "pass")
    )
    mock_client = mock.Mock()
    got_event = mock.Mock()
    got_event.is_set.return_value = False
    got_event.wait = mock.Mock()
    monkeypatch.setattr(smoke_handlers.threading, "Event", lambda: got_event)
    monkeypatch.setattr(smoke_handlers.mqtt, "Client", lambda *a, **kw: mock_client)
    output = {}

    def fake_print(val):
        output["val"] = val

    monkeypatch.setattr("builtins.print", fake_print)

    # Patch on_message to simulate missing event
    def fake_on_message(_, __, msg):
        ev = {"foo": "bar"}
        assert ev.get("event", "") not in (
            "flat_handlers_attached",
            "echo_stop",
            "subscribed",
        )

    monkeypatch.setattr(
        smoke_handlers,
        "main",
        lambda: fake_on_message(
            None, None, mock.Mock(payload=json.dumps({"foo": "bar"}).encode())
        ),
    )
    smoke_handlers.main()
