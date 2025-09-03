import threading
from unittest.mock import MagicMock, patch

import addon.bb8_core.telemetry as telemetry
import pytest


class DummyMQTT:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload, qos, retain):
        self.published.append((topic, payload, qos, retain))


@pytest.fixture
def mqtt():
    return DummyMQTT()


def test_publish_metric(mqtt):
    with patch("addon.bb8_core.telemetry._now", return_value=123):
        telemetry.publish_metric(mqtt, "test", {"foo": "bar"})
    assert mqtt.published[0][0].endswith("/test")
    assert '"foo": "bar"' in mqtt.published[0][1]
    assert '"ts": 123' in mqtt.published[0][1]
    assert mqtt.published[0][2] == 0
    assert mqtt.published[0][3] is False


def test_echo_roundtrip(mqtt):
    with patch("addon.bb8_core.telemetry.publish_metric") as pm:
        telemetry.echo_roundtrip(mqtt, 42, "ok")
        pm.assert_called_once_with(mqtt, "echo_roundtrip", {"ms": 42, "outcome": "ok"})


def test_ble_connect_attempt(mqtt):
    with patch("addon.bb8_core.telemetry.publish_metric") as pm:
        telemetry.ble_connect_attempt(mqtt, 2, 1.5)
        pm.assert_called_once_with(
            mqtt, "ble_connect_attempt", {"try": 2, "backoff_s": 1.5}
        )


def test_led_discovery(mqtt):
    with patch("addon.bb8_core.telemetry.publish_metric") as pm:
        telemetry.led_discovery(mqtt, "uid", 3)
        pm.assert_called_once_with(
            mqtt, "led_discovery", {"unique_id": "uid", "duplicates": 3}
        )


class DummyBridge:
    def __init__(self, connected=True, rssi=55):
        self._connected = connected
        self._rssi = rssi
        self.presence_called = None
        self.rssi_called = None

    def is_connected(self):
        return self._connected

    def get_rssi(self):
        return self._rssi

    def publish_presence(self, online):
        self.presence_called = online

    def publish_rssi(self, dbm):
        self.rssi_called = dbm


@patch("addon.bb8_core.telemetry.logger")
def test_telemetry_start_stop(mock_logger):
    bridge = DummyBridge()
    t = telemetry.Telemetry(bridge)
    with patch.object(threading.Thread, "start") as mock_start:
        t.start()
        mock_start.assert_called_once()
    with patch.object(threading.Thread, "join") as mock_join:
        t.stop()
        mock_join.assert_called_once_with(timeout=2)
    assert mock_logger.info.call_count == 2


@patch("addon.bb8_core.telemetry.logger")
def test_telemetry_run_presence_and_rssi(mock_logger):
    bridge = DummyBridge()
    t = telemetry.Telemetry(bridge)
    t._stop = MagicMock()
    t._stop.is_set.side_effect = [False, True] + [
        True
    ] * 10  # ensure enough values for all loop calls
    with patch("time.sleep"), patch.object(
        bridge, "publish_presence"
    ) as mock_presence, patch.object(bridge, "publish_rssi") as mock_rssi:
        t._run()
        mock_presence.assert_called_once_with(True)
        mock_rssi.assert_called_once_with(55)


@patch("addon.bb8_core.telemetry.logger")
def test_telemetry_run_presence_exception(mock_logger):
    bridge = DummyBridge()

    def bad_presence(_):
        raise ValueError("fail")

    t = telemetry.Telemetry(bridge, publish_presence=bad_presence)
    t._stop = MagicMock()
    t._stop.is_set.side_effect = [False, True] + [
        True
    ] * 10  # ensure enough values for all loop calls
    with patch("time.sleep"):
        t._run()
    assert any(
        "telemetry_presence_cb_error" in str(c)
        for c in mock_logger.warning.call_args_list
    )


@patch("addon.bb8_core.telemetry.logger")
def test_telemetry_run_rssi_exception(mock_logger):
    bridge = DummyBridge()

    def bad_rssi():
        raise ValueError("fail")

    t = telemetry.Telemetry(bridge, publish_rssi=None)
    bridge.get_rssi = bad_rssi
    t._stop = MagicMock()
    t._stop.is_set.side_effect = [False, True] + [
        True
    ] * 10  # ensure enough values for all loop calls
    with patch("time.sleep"):
        t._run()
    assert any(
        "telemetry_rssi_probe_error" in str(c)
        for c in mock_logger.warning.call_args_list
    )


@patch("addon.bb8_core.telemetry.logger")
def test_telemetry_run_invalid_rssi_type(mock_logger):
    bridge = DummyBridge()
    bridge.get_rssi = lambda: ["not", "int"]
    t = telemetry.Telemetry(bridge)
    t._stop = MagicMock()
    t._stop.is_set.side_effect = [False, True] + [
        True
    ] * 10  # ensure enough values for all loop calls
    with patch("time.sleep"):
        t._run()
    assert any(
        "telemetry_invalid_rssi" in str(c) for c in mock_logger.warning.call_args_list
    )


@patch("addon.bb8_core.telemetry.logger")
def test_telemetry_run_rssi_cb_exception(mock_logger):
    bridge = DummyBridge()

    def bad_cb(dbm):
        raise ValueError("fail")

    t = telemetry.Telemetry(bridge, publish_rssi=bad_cb)
    t._stop = MagicMock()
    t._stop.is_set.side_effect = [False, True] + [
        True
    ] * 10  # ensure enough values for all loop calls
    bridge.get_rssi = lambda: 99
    with patch("time.sleep"):
        t._run()
    assert any(
        "telemetry_rssi_cb_error" in str(c) for c in mock_logger.warning.call_args_list
    )


@patch("addon.bb8_core.telemetry.logger")
def test_telemetry_run_general_exception(mock_logger):
    bridge = DummyBridge()
    t = telemetry.Telemetry(bridge)
    t._stop = MagicMock()
    t._stop.is_set.side_effect = [False, True] + [
        True
    ] * 10  # ensure enough values for all loop calls
    # Force an exception in the run loop
    t.bridge = None
    with patch("time.sleep"):
        t._run()
    assert any(
        call[0][0].get("event") == "telemetry_error"
        for call in mock_logger.warning.call_args_list
    )
