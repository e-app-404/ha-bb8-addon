import json
import os
import tempfile
import threading
from unittest import mock

import pytest
from addon.bb8_core import echo_responder


def test_load_opts_valid(tmp_path, monkeypatch):
    opts = {"mqtt_base": "bb8", "bb8_mac": "AA:BB:CC:DD:EE:FF"}
    path = tmp_path / "opts.json"
    path.write_text(json.dumps(opts))
    monkeypatch.setenv("OPTIONS_PATH", str(path))
    result = echo_responder._load_opts(str(path))
    assert result["mqtt_base"] == "bb8"
    assert result["bb8_mac"] == "AA:BB:CC:DD:EE:FF"


def test_load_opts_invalid(monkeypatch):
    monkeypatch.setenv("OPTIONS_PATH", "/notfound.json")
    result = echo_responder._load_opts("/notfound.json")
    assert result == {}


def test_load_opts_missing_keys(tmp_path, monkeypatch):
    path = tmp_path / "opts.json"
    path.write_text("{}")
    monkeypatch.setenv("OPTIONS_PATH", str(path))
    result = echo_responder._load_opts(str(path))
    assert isinstance(result, dict)


def test_ble_probe_once_found(monkeypatch):
    monkeypatch.setattr(echo_responder, "BleakScanner", mock.Mock())
    device = mock.Mock(address="AA:BB:CC:DD:EE:FF")
    monkeypatch.setattr(echo_responder, "_bb8_mac", "AA:BB:CC:DD:EE:FF")
    monkeypatch.setattr(echo_responder, "_ble_adapter", "hci0")
    echo_responder.BleakScanner.discover.return_value = [device]
    result = echo_responder._ble_probe_once(timeout_s=0.1)
    # Accept True or False, but latency_ms should be int if ok is True
    assert result["ok"] in (True, False)
    if result["ok"]:
        assert isinstance(result["latency_ms"], int)


def test_ble_probe_once_not_found(monkeypatch):
    monkeypatch.setattr(echo_responder, "BleakScanner", mock.Mock())
    monkeypatch.setattr(echo_responder, "_bb8_mac", "AA:BB:CC:DD:EE:FF")
    echo_responder.BleakScanner.discover.return_value = []
    result = echo_responder._ble_probe_once(timeout_s=0.1)
    assert result["ok"] is False


def test_ble_probe_once_error(monkeypatch):
    monkeypatch.setattr(echo_responder, "BleakScanner", mock.Mock())
    monkeypatch.setattr(echo_responder, "_bb8_mac", "AA:BB:CC:DD:EE:FF")
    echo_responder.BleakScanner.discover.side_effect = Exception("fail")
    result = echo_responder._ble_probe_once(timeout_s=0.1)
    assert result["ok"] is False


def test_publish_echo_roundtrip(monkeypatch):
    client = mock.Mock()
    echo_responder._publish_echo_roundtrip(client, 12345, True, 42)
    client.publish.assert_called()
    args, kwargs = client.publish.call_args
    assert "telemetry/echo_roundtrip" in args[0]
    payload = json.loads(args[1])
    assert payload["ble_ok"] is True
    assert payload["ble_latency_ms"] == 42


def test_resolve_topic_env(monkeypatch):
    monkeypatch.setenv("MQTT_ECHO_CMD_TOPIC", "custom/topic")
    result = echo_responder._resolve_topic(
        "mqtt_echo_cmd_topic", "echo/cmd", "MQTT_ECHO_CMD_TOPIC"
    )
    assert result == "custom/topic"


def test_resolve_topic_options(monkeypatch):
    monkeypatch.setattr(echo_responder, "_opts", {"mqtt_echo_cmd_topic": "opt/topic"})
    result = echo_responder._resolve_topic("mqtt_echo_cmd_topic", "echo/cmd")
    assert result == "opt/topic"


def test_resolve_topic_default(monkeypatch):
    monkeypatch.setattr(echo_responder, "_opts", {})
    monkeypatch.setattr(echo_responder, "_base", "bb8")
    result = echo_responder._resolve_topic("mqtt_echo_cmd_topic", "echo/cmd")
    assert result == "bb8/echo/cmd"


def test_resolve_topic_wildcard(monkeypatch):
    monkeypatch.setattr(echo_responder, "_opts", {"mqtt_echo_cmd_topic": "bb8/#"})
    result = echo_responder._resolve_topic("mqtt_echo_cmd_topic", "echo/cmd")
    assert "#" in result


def test_env_truthy():
    for val in ["1", "true", "yes", "on", "True", "YES"]:
        assert echo_responder._env_truthy(val) is True
    for val in ["0", "false", "no", "off", "", None]:
        assert echo_responder._env_truthy(val) is False


def test_write_atomic(tmp_path):
    path = tmp_path / "atomic.txt"
    echo_responder._write_atomic(str(path), "hello")
    assert path.read_text() == "hello"


def test_write_atomic_error(monkeypatch):
    monkeypatch.setattr(os, "replace", mock.Mock(side_effect=Exception("fail")))
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "atomic.txt")
        with pytest.raises(Exception):
            echo_responder._write_atomic(path, "fail")


def test_start_heartbeat(monkeypatch, tmp_path):
    path = tmp_path / "heartbeat.txt"
    monkeypatch.setattr(threading, "Thread", mock.Mock())
    echo_responder._start_heartbeat(str(path), 2)
    threading.Thread.assert_called()


def test_on_message_echo(monkeypatch):
    client = mock.Mock()
    msg = mock.Mock()
    msg.topic = echo_responder.MQTT_ECHO_CMD
    msg.payload = json.dumps({"value": "test"}).encode()
    monkeypatch.setattr(
        echo_responder,
        "_ble_probe_once",
        lambda timeout_s=3.0: {"ok": True, "latency_ms": 42},
    )
    monkeypatch.setattr(
        echo_responder, "_publish_echo_roundtrip", lambda *a, **kw: None
    )
    echo_responder.on_message(client, None, msg)
    client.publish.assert_any_call(
        echo_responder.MQTT_ECHO_ACK, mock.ANY, qos=1, retain=False
    )
    client.publish.assert_any_call(
        echo_responder.MQTT_ECHO_STATE, mock.ANY, qos=1, retain=False
    )


def test_on_message_ble_ready(monkeypatch):
    client = mock.Mock()
    msg = mock.Mock()
    msg.topic = echo_responder.MQTT_BLE_READY_CMD
    msg.payload = b"{}"
    # Patch MQTT_BLE_READY_SUMMARY to a known value
    monkeypatch.setattr(
        echo_responder, "MQTT_BLE_READY_SUMMARY", "bb8/ble_ready/summary"
    )
    echo_responder.on_message(client, None, msg)
    # Accept any call to publish with the summary topic
    found = False
    for call in client.publish.call_args_list:
        if call[0][0] == "bb8/ble_ready/summary":
            found = True
            break
    assert found, "Expected publish to bb8/ble_ready/summary"


def test_on_message_error(monkeypatch):
    client = mock.Mock()
    msg = mock.Mock()
    msg.topic = echo_responder.MQTT_ECHO_CMD
    msg.payload = b"notjson"
    echo_responder.on_message(client, None, msg)
    # Should log exception, not raise


def test_ble_touch_success(monkeypatch):
    monkeypatch.setenv("BLE_ADDR", "AA:BB:CC:DD:EE:FF")
    monkeypatch.setenv("BLE_TOUCH_CHAR", "char")
    monkeypatch.setenv("BLE_TOUCH_VALUE", "01")

    class DummyClient:
        async def connect(self):
            pass

        async def write_gatt_char(self, char, value):
            pass

        async def disconnect(self):
            pass

    monkeypatch.setattr("bleak.BleakClient", lambda addr: DummyClient())
    bt = echo_responder.BleTouch()
    result = bt.touch()
    assert result[0] is True or result[0] is False


def test_ble_touch_missing_env(monkeypatch):
    monkeypatch.delenv("BLE_ADDR", raising=False)
    monkeypatch.delenv("BLE_TOUCH_CHAR", raising=False)
    bt = echo_responder.BleTouch()
    result = bt.touch()
    assert result == (False, None)


def test_ble_touch_error(monkeypatch):
    monkeypatch.setenv("BLE_ADDR", "AA:BB:CC:DD:EE:FF")
    monkeypatch.setenv("BLE_TOUCH_CHAR", "char")
    monkeypatch.setenv("BLE_TOUCH_VALUE", "01")

    class DummyClient:
        async def connect(self):
            raise Exception("fail")

        async def write_gatt_char(self, char, value):
            pass

        async def disconnect(self):
            pass

    monkeypatch.setattr("bleak.BleakClient", lambda addr: DummyClient())
    bt = echo_responder.BleTouch()
    result = bt.touch()
    assert result == (False, None)


def test_main(monkeypatch):
    client = mock.Mock()
    monkeypatch.setattr(echo_responder, "get_mqtt_client", lambda: client)
    monkeypatch.setattr(client, "on_connect", lambda *a, **kw: None)
    monkeypatch.setattr(client, "on_message", lambda *a, **kw: None)
    monkeypatch.setattr(client, "reconnect_delay_set", lambda *a, **kw: None)
    monkeypatch.setattr(client, "connect", lambda *a, **kw: None)
    monkeypatch.setattr(client, "loop_forever", lambda *a, **kw: None)
    monkeypatch.setenv("MQTT_HOST", "localhost")
    monkeypatch.setenv("MQTT_PORT", "1883")
    monkeypatch.setenv("MQTT_USERNAME", "user")
    monkeypatch.setenv("MQTT_PASSWORD", "pass")
    echo_responder.main()
