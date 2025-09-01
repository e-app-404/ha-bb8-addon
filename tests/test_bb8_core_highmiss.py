import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE))

# blebridge_handler_surface_check.py
from addon.bb8_core import blebridge_handler_surface_check


def test_blebridge_handler_surface_check_exists():
    assert hasattr(blebridge_handler_surface_check, "Gw")


# bridge_controller.py
from addon.bb8_core import bridge_controller


def test_bridge_controller_get_client_exists():
    assert hasattr(bridge_controller, "get_client")


# check_bridge_broker.py
from addon.bb8_core import check_bridge_broker


def test_check_bridge_broker_env():
    import os

    os.environ["MQTT_HOST"] = "localhost"
    assert isinstance(check_bridge_broker.read_mqtt_env(), tuple)


# evidence_capture.py
from addon.bb8_core import evidence_capture


def test_evidence_recorder_init():
    class DummyClient:
        pass

    rec = evidence_capture.EvidenceRecorder(DummyClient(), "topic", "report.jsonl")
    assert isinstance(rec, evidence_capture.EvidenceRecorder)


# facade.py
from addon.bb8_core import facade


def test_facade_sleep_led_pattern():
    pattern = facade._sleep_led_pattern()
    assert isinstance(pattern, list)
    assert all(isinstance(x, tuple) for x in pattern)


# smoke_handlers.py
from addon.bb8_core import smoke_handlers


def test_smoke_handlers_env(monkeypatch):
    monkeypatch.setenv("MQTT_HOST", "localhost")
    assert isinstance(smoke_handlers.env(), tuple)


# telemetry.py
from addon.bb8_core import telemetry


def test_telemetry_publish_metric():
    class DummyMQTT:
        def publish(self, topic, payload, qos=0, retain=False):
            self.called = True

    mqtt = DummyMQTT()
    telemetry.publish_metric(mqtt, "test", {"foo": "bar"})
    assert hasattr(mqtt, "called")


# types.py
from addon.bb8_core import types


def test_types_protocols():
    for symbol in getattr(types, "__all__", []):
        assert hasattr(types, symbol), f"types missing symbol: {symbol}"


# util.py
from addon.bb8_core import util


def test_util_clamp():
    assert util.clamp(5, 0, 10) == 5
    assert util.clamp(-1, 0, 10) == 0
    assert util.clamp(20, 0, 10) == 10


# verify_discovery.py
from addon.bb8_core import verify_discovery


def test_verify_discovery_get_any_synonyms():
    d = {"stat_t": "foo", "state_topic": "bar"}
    assert verify_discovery.get_any(d, "stat_t") == "foo"
    d2 = {"state_topic": "bar"}
    assert verify_discovery.get_any(d2, "stat_t") == "bar"
    d3 = {"unknown": "baz"}
    assert verify_discovery.get_any(d3, "stat_t") is None


def test_verify_discovery_first_identifiers():
    assert verify_discovery.first_identifiers(None) == []
    assert verify_discovery.first_identifiers({}) == []
    assert verify_discovery.first_identifiers({"identifiers": ["id1", "id2"]}) == [
        "id1",
        "id2",
    ]
    assert verify_discovery.first_identifiers({"identifiers": "notalist"}) == []


def test_verify_discovery_extract_cfg():
    valid = '{"foo": "bar"}'
    assert verify_discovery.extract_cfg(valid) == {"foo": "bar"}
    invalid = "{foo: bar}"
    assert isinstance(verify_discovery.extract_cfg(invalid), dict)


def test_verify_discovery_verify_configs_and_states_all_ok(monkeypatch):
    class DummyMsg:
        def __init__(self, topic, payload, retain):
            self.topic = topic
            self.payload = payload.encode("utf-8")
            self.retain = retain

    class DummyClient:
        def __init__(self):
            self.on_message = None
            self.subscribed = []
            self._msgs = []

        def subscribe(self, topic, qos=0):
            self.subscribed.append((topic, qos))

        def loop(self, timeout=0.1):
            # Simulate message for each topic
            for topic, _ in verify_discovery.CFG_TOPICS:
                msg = DummyMsg(
                    topic,
                    '{"dev": {"identifiers": ["id"]}, "stat_t": "s", "avty_t": "a"}',
                    True,
                )
                self.on_message(self, None, msg)

    client = DummyClient()
    rows, ok = verify_discovery.verify_configs_and_states(client, timeout=0.2)
    assert ok is True
    assert all(r["retained"] for r in rows)
    assert all(r["stat_t"] for r in rows)
    assert all(r["avty_t"] for r in rows)
    assert all(r["identifiers"] for r in rows)


def test_verify_discovery_verify_configs_and_states_fail(monkeypatch):
    class DummyMsg:
        def __init__(self, topic, payload, retain):
            self.topic = topic
            self.payload = payload.encode("utf-8")
            self.retain = retain

    class DummyClient:
        def __init__(self):
            self.on_message = None
            self.subscribed = []
            self._msgs = []

        def subscribe(self, topic, qos=0):
            self.subscribed.append((topic, qos))

        def loop(self, timeout=0.1):
            # Simulate missing identifiers
            for topic, _ in verify_discovery.CFG_TOPICS:
                msg = DummyMsg(topic, '{"dev": {}, "stat_t": "", "avty_t": ""}', False)
                self.on_message(self, None, msg)

    client = DummyClient()
    rows, ok = verify_discovery.verify_configs_and_states(client, timeout=0.2)
    assert ok is False
    assert all(isinstance(r, dict) for r in rows)


def test_verify_discovery_get_mqtt_client(monkeypatch):
    # Patch mqtt.Client to a dummy
    class DummyClient:
        def __init__(self, *a, **kw):
            pass

    monkeypatch.setattr("paho.mqtt.client.Client", DummyClient)
    client = verify_discovery.get_mqtt_client()
    assert isinstance(client, DummyClient)


# version_probe.py
from addon.bb8_core import version_probe


def test_version_probe_probe():
    result = version_probe.probe()
    assert isinstance(result, dict)


"""
Test stubs for highest-miss bb8_core modules (0% coverage).
Expands coverage registration for CI and future edge case tests.
"""
import types

# controller.py
from addon.bb8_core import controller


def test_controller_init():
    ctrl = controller.BB8Controller()
    assert isinstance(ctrl, controller.BB8Controller)
    assert ctrl.mode in controller.ControllerMode
    assert isinstance(ctrl.command_count, int)


# core_types.py
from addon.bb8_core import core_types


def test_core_types_protocols():
    assert hasattr(core_types, "MqttClient")
    assert hasattr(core_types, "BLELink")
    assert hasattr(core_types, "BridgeController")
    assert hasattr(core_types, "Facade")


# discovery_migrate.py
from addon.bb8_core import discovery_migrate


def test_discovery_migrate_main(monkeypatch):
    monkeypatch.setenv("BB8_MAC", "AA:BB:CC:DD:EE:FF")
    assert discovery_migrate.main() == 2


# echo_responder.py
from addon.bb8_core import echo_responder


def test_echo_responder_pub():
    class DummyClient:
        def publish(self, topic, payload, qos=0, retain=False):
            self.called = True
            return None

    client = DummyClient()
    echo_responder.pub(client, "topic", {"msg": "hi"})
    assert hasattr(client, "called")


# force_discovery_emit.py
from addon.bb8_core import force_discovery_emit


def test_force_discovery_emit_main(monkeypatch):
    monkeypatch.setenv("BB8_MAC", "AA:BB:CC:DD:EE:FF")
    assert force_discovery_emit.main() == 2


# main.py
from addon.bb8_core import main as bb8_main


def test_main_module():
    assert hasattr(bb8_main, "main")


# mqtt_helpers.py
from addon.bb8_core import mqtt_helpers


def test_mqtt_helpers_publish_retain():
    class DummyMQTT:
        def publish(self, topic, payload, qos, retain):
            self.called = True
            return None

    import asyncio

    dummy = DummyMQTT()
    asyncio.run(mqtt_helpers.publish_retain(dummy, "topic", {"msg": "hi"}))
    assert hasattr(dummy, "called")


# mqtt_probe.py
from addon.bb8_core import mqtt_probe


def test_mqtt_probe_env():
    assert mqtt_probe.env("NON_EXISTENT", default="x") == "x"


# ports.py
from addon.bb8_core import ports


def test_ports_protocols():
    assert hasattr(ports, "MqttBus")
    assert hasattr(ports, "BleTransport")
    assert hasattr(ports, "Clock")
    assert hasattr(ports, "Logger")


# scan_bb8_gatt.py
from addon.bb8_core import scan_bb8_gatt


def test_scan_bb8_gatt_main_exists():
    assert hasattr(scan_bb8_gatt, "main")


# Expanded BB8Controller edge case tests
from addon.bb8_core import controller as bb8_controller


def test_bb8controller_roll_device_none():
    ctrl = bb8_controller.BB8Controller(device=None)
    result = ctrl.roll(100, 0)
    assert result["success"] is False
    assert "No device" in result["error"]


def test_bb8controller_roll_device_no_method():
    class Dummy:
        pass

    ctrl = bb8_controller.BB8Controller(device=Dummy())
    result = ctrl.roll(100, 0)
    assert result["success"] is False
    assert "not support" in result["error"]


def test_bb8controller_roll_device_exception():
    class Dummy:
        def roll(self, **kwargs):
            raise RuntimeError("fail")

    ctrl = bb8_controller.BB8Controller(device=Dummy())
    result = ctrl.roll(100, 0)
    assert result["success"] is False
    assert "fail" in result["error"]


def test_bb8controller_stop_device_none():
    ctrl = bb8_controller.BB8Controller(device=None)
    result = ctrl.stop()
    assert result["success"] is False
    assert "No device" in result["error"]


def test_bb8controller_stop_device_no_method():
    class Dummy:
        pass

    ctrl = bb8_controller.BB8Controller(device=Dummy())
    result = ctrl.stop()
    assert result["success"] is False
    assert "not support" in result["error"]


def test_bb8controller_stop_device_exception():
    class Dummy:
        def stop(self):
            raise RuntimeError("fail")

    ctrl = bb8_controller.BB8Controller(device=Dummy())
    result = ctrl.stop()
    assert result["success"] is False
    assert "fail" in result["error"]


def test_bb8controller_set_led_device_none():
    ctrl = bb8_controller.BB8Controller(device=None)
    result = ctrl.set_led(1, 2, 3)
    assert result["success"] is False
    assert "No device" in result["error"]


def test_bb8controller_set_led_device_no_method():
    class Dummy:
        pass

    ctrl = bb8_controller.BB8Controller(device=Dummy())
    result = ctrl.set_led(1, 2, 3)
    assert result["success"] is False
    assert "Not supported" in result["error"]


def test_bb8controller_set_led_device_exception():
    class Dummy:
        def set_led(self, r, g, b):
            raise RuntimeError("fail")

    ctrl = bb8_controller.BB8Controller(device=Dummy())
    result = ctrl.set_led(1, 2, 3)
    assert result["success"] is False
    assert "fail" in result["error"]


def test_bb8controller_get_diagnostics_for_mqtt():
    ctrl = bb8_controller.BB8Controller()
    diag = ctrl.get_diagnostics_for_mqtt()
    assert "controller" in diag
    assert "timestamp" in diag


def test_bb8controller_disconnect_telemetry_none():
    ctrl = bb8_controller.BB8Controller()
    ctrl.telemetry = None
    result = ctrl.disconnect()
    assert result["success"] is True


def test_bb8controller_disconnect_telemetry_present():
    class DummyTelemetry:
        def stop(self):
            self.stopped = True

    ctrl = bb8_controller.BB8Controller()
    ctrl.telemetry = DummyTelemetry()
    result = ctrl.disconnect()
    assert result["success"] is True
    assert hasattr(ctrl.telemetry, "stopped")


def test_bb8controller_disconnect_telemetry_exception():
    class DummyTelemetry:
        def stop(self):
            raise RuntimeError("fail")

    ctrl = bb8_controller.BB8Controller()
    ctrl.telemetry = DummyTelemetry()
    result = ctrl.disconnect()
    assert result["success"] is True


def test_bb8controller_get_controller_status():
    ctrl = bb8_controller.BB8Controller()
    status = ctrl.get_controller_status()
    assert isinstance(status, bb8_controller.ControllerStatus)
    assert status.mode in bb8_controller.ControllerMode


def test_bb8controller_attach_device_none():
    ctrl = bb8_controller.BB8Controller()
    ctrl.attach_device(None)
    assert ctrl.device is None
    assert ctrl.device_connected is False


def test_publish_discovery_if_available():
    class DummyController:
        def publish_discovery(self, client, base_topic, qos, retain):
            self.called = True

    dummy = DummyController()
    bb8_controller.publish_discovery_if_available(None, dummy, "base", 1, True)
    assert hasattr(dummy, "called")


def test_publish_discovery_if_available_no_method():
    class DummyController:
        pass

    dummy = DummyController()
    bb8_controller.publish_discovery_if_available(None, dummy, "base", 1, True)
    # Should not raise


# Expanded BB8Facade edge case and logic tests
from addon.bb8_core import facade as bb8_facade


def test_facade_power_connected_on_offline():
    class Bridge:
        def is_connected(self):
            return True

        def connect(self):
            self.connected = True

        def sleep(self, _):
            self.slept = True

    class DummyMQTT:
        def publish(self, topic, payload, qos, retain):
            self.published = True

    f = bb8_facade.BB8Facade(Bridge())
    f._mqtt["client"] = DummyMQTT()
    f.power(True)
    assert hasattr(f.bridge, "connected")
    f.power(False)
    assert hasattr(f.bridge, "slept")


def test_facade_power_disconnected_on_rejected():
    class Bridge:
        def is_connected(self):
            return False

        def connect(self):
            self.connected = True

        def sleep(self, _):
            self.slept = True

    class DummyMQTT:
        def publish(self, topic, payload, qos, retain):
            self.published = True

    f = bb8_facade.BB8Facade(Bridge())
    f._mqtt["client"] = DummyMQTT()
    f.power(True)
    assert hasattr(f._mqtt["client"], "published")


def test_facade_stop_connected():
    class Bridge:
        def is_connected(self):
            return True

        def stop(self):
            self.stopped = True

    class DummyMQTT:
        def publish(self, topic, payload, qos, retain):
            self.published = True

    f = bb8_facade.BB8Facade(Bridge())
    f._mqtt["client"] = DummyMQTT()
    f.stop()
    assert hasattr(f.bridge, "stopped")


def test_facade_stop_disconnected():
    class Bridge:
        def is_connected(self):
            return False

        def stop(self):
            self.stopped = True

    class DummyMQTT:
        def publish(self, topic, payload, qos, retain):
            self.published = True

    f = bb8_facade.BB8Facade(Bridge())
    f._mqtt["client"] = DummyMQTT()
    f.stop()
    assert hasattr(f._mqtt["client"], "published")


def test_facade_set_led_off_connected():
    class Bridge:
        def is_connected(self):
            return True

        def set_led_off(self):
            self.led_off = True

    class DummyMQTT:
        def publish(self, topic, payload, qos, retain):
            self.published = True

    f = bb8_facade.BB8Facade(Bridge())
    f._mqtt["client"] = DummyMQTT()
    f.set_led_off()
    assert hasattr(f.bridge, "led_off")


def test_facade_set_led_rgb_clamp():
    class Bridge:
        pass

    f = bb8_facade.BB8Facade(Bridge())
    calls = []

    class Core:
        @staticmethod
        def emit_led(bridge, r, g, b):
            calls.append((r, g, b))

    f.Core = Core
    f._emit_led(-10, 300, 128)
    assert calls[0] == (0, 255, 128)


def test_facade_is_connected_default():
    class Bridge:
        pass

    f = bb8_facade.BB8Facade(Bridge())
    assert f.is_connected() is True


def test_facade_get_rssi_default():
    class Bridge:
        pass

    f = bb8_facade.BB8Facade(Bridge())
    assert f.get_rssi() == 0


def test_facade_sleep_emits_pattern():
    class Bridge:
        pass

    f = bb8_facade.BB8Facade(Bridge())
    calls = []

    class Core:
        @staticmethod
        def emit_led(bridge, r, g, b):
            calls.append((r, g, b))

    f.Core = Core
    bb8_facade.sleep(f)
    assert calls == bb8_facade._sleep_led_pattern()


import tempfile

# Expanded EvidenceRecorder edge case and logic tests
from addon.bb8_core import evidence_capture as bb8_evidence


def test_evidence_recorder_init_defaults():
    class DummyClient:
        pass

    rec = bb8_evidence.EvidenceRecorder(DummyClient(), "topic", "report.jsonl")
    assert rec.max_lines == 150
    assert rec.timeout_s == 2.0


def test_evidence_recorder_start_stop_thread():
    class DummyClient:
        def subscribe(self, topic, qos):
            self.subscribed = True

        def __setattr__(self, name, value):
            object.__setattr__(self, name, value)

    rec = bb8_evidence.EvidenceRecorder(
        DummyClient(), "topic", tempfile.gettempdir() + "/report.jsonl"
    )
    rec.start()
    assert rec._t.is_alive()
    rec.stop()
    assert not rec._t.is_alive()


def test_evidence_recorder_install_callbacks_chained():
    class DummyClient:
        def subscribe(self, topic, qos):
            self.subscribed = True

        def __setattr__(self, name, value):
            object.__setattr__(self, name, value)

        def on_message(self, c, u, m):
            self.called = True

    rec = bb8_evidence.EvidenceRecorder(DummyClient(), "topic", "report.jsonl")
    rec._install_callbacks()
    assert callable(rec.client.on_message)


def test_evidence_recorder_runner_queue_empty():
    class DummyClient:
        def subscribe(self, topic, qos):
            pass

    rec = bb8_evidence.EvidenceRecorder(
        DummyClient(), "topic", tempfile.gettempdir() + "/report.jsonl", max_lines=1
    )
    # Don't start thread, call runner directly
    rec._stop.set()  # Should exit immediately
    rec._runner()  # Should not raise


import time

# Expanded Telemetry edge case and logic tests
from addon.bb8_core import telemetry as bb8_telemetry


def test_publish_metric_and_helpers():
    class DummyMQTT:
        def __init__(self):
            self.calls = []

        def publish(self, topic, payload, qos=0, retain=False):
            self.calls.append((topic, payload))

    mqtt = DummyMQTT()
    bb8_telemetry.publish_metric(mqtt, "test", {"foo": "bar"})
    bb8_telemetry.echo_roundtrip(mqtt, 123, "ok")
    bb8_telemetry.ble_connect_attempt(mqtt, 1, 2.5)
    bb8_telemetry.led_discovery(mqtt, "id", 3)
    assert any("test" in c[0] for c in mqtt.calls)
    assert any("echo_roundtrip" in c[0] for c in mqtt.calls)
    assert any("ble_connect_attempt" in c[0] for c in mqtt.calls)
    assert any("led_discovery" in c[0] for c in mqtt.calls)


def test_telemetry_init_defaults():
    class Bridge:
        pass

    t = bb8_telemetry.Telemetry(Bridge())
    assert t.interval_s == 20
    assert t._cb_presence is None
    assert t._cb_rssi is None


def test_telemetry_start_stop_thread():
    class Bridge:
        pass

    t = bb8_telemetry.Telemetry(Bridge())
    t.start()
    assert t._t.is_alive()
    t.stop()
    assert not t._t.is_alive()


def test_telemetry_run_callbacks():
    class Bridge:
        def is_connected(self):
            return True

        def publish_presence(self, online):
            self.presence = online

        def get_rssi(self):
            return 42

        def publish_rssi(self, dbm):
            self.rssi = dbm

    t = bb8_telemetry.Telemetry(Bridge(), interval_s=1)
    t.start()
    time.sleep(0.5)
    t.stop()
    assert hasattr(t.bridge, "presence")
    assert hasattr(t.bridge, "rssi")


def test_telemetry_run_callbacks_exceptions():
    class Bridge:
        def is_connected(self):
            return True

        def publish_presence(self, online):
            raise RuntimeError("fail_presence")

        def get_rssi(self):
            raise RuntimeError("fail_rssi")

        def publish_rssi(self, dbm):
            raise RuntimeError("fail_rssi_cb")

    t = bb8_telemetry.Telemetry(Bridge(), interval_s=1)
    t.start()
    time.sleep(0.5)
    t.stop()
    # Should not raise


# Expanded discovery_migrate edge case and logic tests
from addon.bb8_core import discovery_migrate as bb8_discovery_migrate


def test_publish_retained_calls_publish():
    class DummyClient:
        def __init__(self):
            self.calls = []

        def publish(self, topic, payload, qos=0, retain=False):
            self.calls.append((topic, payload, qos, retain))

    c = DummyClient()
    bb8_discovery_migrate.publish_retained(c, "topic", {"foo": "bar"})
    assert c.calls[0][0] == "topic"
    assert "foo" in c.calls[0][1]
    assert c.calls[0][3] is True


def test_main_mac_missing(monkeypatch):
    monkeypatch.setenv("BB8_MAC", "")
    assert bb8_discovery_migrate.main() == 2


def test_main_mac_invalid(monkeypatch):
    monkeypatch.setenv("BB8_MAC", "AA:BB:CC:DD:EE:FF")
    assert bb8_discovery_migrate.main() == 2


def test_main_mac_valid(monkeypatch):
    monkeypatch.setenv("BB8_MAC", "00:11:22:33:44:55")
    monkeypatch.setenv("MQTT_HOST", "localhost")
    monkeypatch.setenv("MQTT_PORT", "1883")
    monkeypatch.setenv("MQTT_USERNAME", "user")
    monkeypatch.setenv("MQTT_PASSWORD", "pass")
    monkeypatch.setenv("BB8_VERSION", "2025.08.20")
    monkeypatch.setenv("PUBLISH_LED_DISCOVERY", "1")

    class DummyClient:
        def __init__(self):
            self.calls = []

        def publish(self, topic, payload, qos=0, retain=False):
            self.calls.append((topic, payload, qos, retain))

        def username_pw_set(self, user, pw):
            self.user = user
            self.pw = pw

        def connect(self, host, port, timeout):
            self.connected = True

    def get_mqtt_client():
        return DummyClient()

    monkeypatch.setattr(
        bb8_discovery_migrate,
        "mqtt",
        type("M", (), {"Client": lambda *a, **k: get_mqtt_client()})(),
    )
    monkeypatch.setattr(
        bb8_discovery_migrate, "CallbackAPIVersion", type("V", (), {"VERSION1": 1})
    )
    assert bb8_discovery_migrate.main() == 0


# Expanded force_discovery_emit edge case and logic tests
from addon.bb8_core import force_discovery_emit as bb8_force_discovery_emit


def test_find_mac_from_logs_none(monkeypatch):
    monkeypatch.setattr(bb8_force_discovery_emit, "LOG_CANDIDATES", [])
    assert bb8_force_discovery_emit.find_mac_from_logs() is None


def test_main_mac_missing(monkeypatch):
    monkeypatch.setenv("BB8_MAC", "")
    monkeypatch.setattr(bb8_force_discovery_emit, "find_mac_from_logs", lambda: None)
    assert bb8_force_discovery_emit.main() == 2


def test_main_mac_invalid(monkeypatch):
    monkeypatch.setenv("BB8_MAC", "AA:BB:CC:DD:EE:FF")
    monkeypatch.setattr(bb8_force_discovery_emit, "find_mac_from_logs", lambda: None)
    assert bb8_force_discovery_emit.main() == 2


def test_main_mac_valid(monkeypatch):
    monkeypatch.setenv("BB8_MAC", "00:11:22:33:44:55")
    monkeypatch.setenv("MQTT_HOST", "localhost")
    monkeypatch.setenv("MQTT_PORT", "1883")
    monkeypatch.setenv("MQTT_USERNAME", "user")
    monkeypatch.setenv("MQTT_PASSWORD", "pass")
    monkeypatch.setenv("BB8_VERSION", "2025.08.20")

    class DummyClient:
        def __init__(self):
            self.calls = []

        def publish(self, topic, payload, qos=0, retain=False):
            self.calls.append((topic, payload, qos, retain))

        def username_pw_set(self, user, pw):
            self.user = user
            self.pw = pw

        def connect(self, host, port, keepalive):
            self.connected = True

    def get_mqtt_client():
        return DummyClient()

    monkeypatch.setattr(
        bb8_force_discovery_emit,
        "mqtt",
        type("M", (), {"Client": lambda *a, **k: get_mqtt_client()})(),
    )
    monkeypatch.setattr(
        bb8_force_discovery_emit, "CallbackAPIVersion", type("V", (), {"VERSION1": 1})
    )
    assert bb8_force_discovery_emit.main() == 0


# Expanded smoke_handlers edge case and logic tests
from addon.bb8_core import smoke_handlers as bb8_smoke_handlers


def test_env_valid(monkeypatch):
    monkeypatch.setenv("MQTT_HOST", "localhost")
    monkeypatch.setenv("MQTT_PORT", "1883")
    monkeypatch.setenv("MQTT_BASE", "bb8")
    monkeypatch.setenv("MQTT_USERNAME", "user")
    monkeypatch.setenv("MQTT_PASSWORD", "pass")
    result = bb8_smoke_handlers.env()
    assert result[0] == "localhost"
    assert result[1] == 1883
    assert result[2] == "bb8"
    assert result[3] == "user"
    assert result[4] == "pass"


def test_env_missing_host(monkeypatch):
    monkeypatch.delenv("MQTT_HOST", raising=False)
    try:
        bb8_smoke_handlers.env()
        assert False, "Should raise ValueError"
    except ValueError:
        pass


def test_main_valid(monkeypatch):
    monkeypatch.setenv("MQTT_HOST", "localhost")
    monkeypatch.setenv("MQTT_PORT", "1883")
    monkeypatch.setenv("MQTT_BASE", "bb8")
    monkeypatch.setenv("MQTT_USERNAME", "user")
    monkeypatch.setenv("MQTT_PASSWORD", "pass")

    class DummyClient:
        def __init__(self):
            self.subscribed = False
            self.published = False
            self.loop_started = False
            self.loop_stopped = False
            self.disconnected = False
            self.connected = False

        def subscribe(self, topic, qos):
            self.subscribed = True

        def publish(self, topic, payload, qos, retain):
            self.published = True

        def connect(self, host, port, keepalive):
            self.connected = True

        def loop_start(self):
            self.loop_started = True

        def loop_stop(self):
            self.loop_stopped = True

        def disconnect(self):
            self.disconnected = True

    def get_mqtt_client():
        return DummyClient()

    monkeypatch.setattr(
        bb8_smoke_handlers,
        "mqtt",
        type("M", (), {"Client": lambda *a, **k: get_mqtt_client(), "MQTTv5": 5})(),
    )
    monkeypatch.setattr(
        bb8_smoke_handlers, "CallbackAPIVersion", type("V", (), {"VERSION1": 1})
    )
    assert bb8_smoke_handlers.main() in (0, 1)
