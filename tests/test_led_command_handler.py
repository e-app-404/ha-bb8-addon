import asyncio
import importlib
import logging
import sys
import types
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _install_bridge_controller_import_stubs():
    logger = logging.getLogger("test_bridge_controller")

    def _stub_module(name, **attrs):
        module = types.ModuleType(name)
        for key, value in attrs.items():
            setattr(module, key, value)
        sys.modules[name] = module
        return module

    async def _probe_bluez_health(*args, **kwargs):
        return {"healthy": True, "reason": "ok", "metadata": {}}

    class _NoOpRecorder:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            return None

    _stub_module("bb8_core.addon_config", load_config=lambda: ({}, None))
    _stub_module("bb8_core.auto_detect", resolve_bb8_mac=lambda *args, **kwargs: None)
    _stub_module("bb8_core.ble_bridge", BLEBridge=type("BLEBridge", (), {}))
    _stub_module("bb8_core.ble_gateway", BleGateway=type("BleGateway", (), {}))
    _stub_module(
        "bb8_core.ble_link",
        BLELink=type("BLELink", (), {}),
        set_loop=lambda *args, **kwargs: None,
        start=lambda *args, **kwargs: None,
        stop=lambda *args, **kwargs: None,
    )
    _stub_module("bb8_core.bluez_health", probe_bluez_health=_probe_bluez_health)
    _stub_module(
        "bb8_core.common",
        STATE_TOPICS={"led": "bb8/led/state"},
        publish_device_echo=lambda *args, **kwargs: None,
    )
    _stub_module("bb8_core.evidence_capture", EvidenceRecorder=_NoOpRecorder)
    _stub_module("bb8_core.logging_setup", logger=logger)
    _stub_module(
        "bb8_core.mqtt_dispatcher",
        register_subscription=lambda *args, **kwargs: None,
    )
    _stub_module("bb8_core.ble_session", BleSession=type("BleSession", (), {}))
    _stub_module("bb8_core.facade", BB8Facade=type("BB8Facade", (), {}))


_install_bridge_controller_import_stubs()

bridge_controller = importlib.import_module("bb8_core.bridge_controller")


class FakeMQTTClient:
    def __init__(self):
        self.publishes = []

    def publish(self, topic, payload=None, qos=0, retain=False):
        self.publishes.append((topic, payload, qos, retain))


class RecordingFacade:
    def __init__(self):
        self.calls = []

    async def set_led_async(self, r, g, b, cid=None):
        self.calls.append((r, g, b, cid))
        return True


class FailingFacade:
    def __init__(self):
        self.calls = []

    async def set_led_async(self, r, g, b, cid=None):
        self.calls.append((r, g, b, cid))
        return False


def _run_led_command(*, facade, mqtt_client, raw_payload, payload, cid=None, last_color=None):
    return asyncio.run(
        bridge_controller._process_led_command(
            facade=facade,
            mqtt_client=mqtt_client,
            raw_payload=raw_payload,
            payload=payload,
            cid=cid,
            last_commanded_color=last_color or [255, 255, 255],
            led_state_topic="bb8/state/led",
        )
    )


def test_led_on_with_rgb():
    facade = RecordingFacade()
    mqtt_client = FakeMQTTClient()
    last_color = [255, 255, 255]

    ok = _run_led_command(
        facade=facade,
        mqtt_client=mqtt_client,
        raw_payload='{"state":"ON","color":{"r":0,"g":255,"b":0}}',
        payload={"state": "ON", "color": {"r": 0, "g": 255, "b": 0}},
        cid="cid-1",
        last_color=last_color,
    )

    assert ok is True
    assert facade.calls == [(0, 255, 0, "cid-1")]
    assert mqtt_client.publishes == [
        (
            "bb8/state/led",
            '{"state":"ON","color_mode":"rgb","color":{"r":0,"g":255,"b":0}}',
            0,
            True,
        )
    ]
    assert last_color == [0, 255, 0]


def test_led_off():
    facade = RecordingFacade()
    mqtt_client = FakeMQTTClient()
    last_color = [10, 20, 30]

    ok = _run_led_command(
        facade=facade,
        mqtt_client=mqtt_client,
        raw_payload='{"state":"OFF"}',
        payload={"state": "OFF"},
        last_color=last_color,
    )

    assert ok is True
    assert facade.calls == [(0, 0, 0, None)]
    assert mqtt_client.publishes == [("bb8/state/led", '{"state":"OFF"}', 0, True)]
    assert last_color == [10, 20, 30]


def test_led_on_without_color_uses_default_or_last():
    facade = RecordingFacade()
    mqtt_client = FakeMQTTClient()
    last_color = [255, 255, 255]

    first_ok = _run_led_command(
        facade=facade,
        mqtt_client=mqtt_client,
        raw_payload='{"state":"ON"}',
        payload={"state": "ON"},
        last_color=last_color,
    )
    second_ok = _run_led_command(
        facade=facade,
        mqtt_client=mqtt_client,
        raw_payload='{"state":"ON","color":{"r":4,"g":5,"b":6}}',
        payload={"state": "ON", "color": {"r": 4, "g": 5, "b": 6}},
        last_color=last_color,
    )
    third_ok = _run_led_command(
        facade=facade,
        mqtt_client=mqtt_client,
        raw_payload='{"state":"ON"}',
        payload={"state": "ON"},
        last_color=last_color,
    )

    assert first_ok is True
    assert second_ok is True
    assert third_ok is True
    assert facade.calls == [
        (255, 255, 255, None),
        (4, 5, 6, None),
        (4, 5, 6, None),
    ]
    assert mqtt_client.publishes[0] == (
        "bb8/state/led",
        '{"state":"ON","color_mode":"rgb","color":{"r":255,"g":255,"b":255}}',
        0,
        True,
    )
    assert mqtt_client.publishes[2] == (
        "bb8/state/led",
        '{"state":"ON","color_mode":"rgb","color":{"r":4,"g":5,"b":6}}',
        0,
        True,
    )


def test_led_malformed_payload(caplog):
    facade = RecordingFacade()
    mqtt_client = FakeMQTTClient()

    with caplog.at_level(logging.ERROR):
        ok = _run_led_command(
            facade=facade,
            mqtt_client=mqtt_client,
            raw_payload="{bad-json",
            payload={},
        )

    assert ok is False
    assert facade.calls == []
    assert mqtt_client.publishes == []
    assert any("led_cmd malformed payload" in record.message for record in caplog.records)


def test_led_facade_failure_no_state_publish():
    """Bridge controller suppresses retained state publish when the facade reports failure."""
    facade = FailingFacade()
    mqtt_client = FakeMQTTClient()
    last_color = [255, 255, 255]

    ok = _run_led_command(
        facade=facade,
        mqtt_client=mqtt_client,
        raw_payload='{"state":"ON","color":{"r":7,"g":8,"b":9}}',
        payload={"state": "ON", "color": {"r": 7, "g": 8, "b": 9}},
        last_color=last_color,
    )

    assert ok is False
    assert facade.calls == [(7, 8, 9, None)]
    assert mqtt_client.publishes == []
    assert last_color == [255, 255, 255]


def test_led_state_payload_structure():
    assert bridge_controller._build_ha_led_state_payload((1, 2, 3)) == (
        '{"state":"ON","color_mode":"rgb","color":{"r":1,"g":2,"b":3}}'
    )
    assert bridge_controller._build_ha_led_state_payload((0, 0, 0)) == '{"state":"OFF"}'


def test_propagate_ble_session_to_facade():
    session = object()

    class SessionAwareFacade:
        def __init__(self):
            self.calls = []

        def set_ble_session(self, value):
            self.calls.append(value)

    facade = SessionAwareFacade()

    bridge_controller._propagate_ble_session_to_facade(facade, session)

    assert facade.calls == [session]


def test_propagate_ble_session_to_facade_missing_method_is_noop():
    bridge_controller._propagate_ble_session_to_facade(object(), object())


def test_led_backward_compat_payload():
    facade = RecordingFacade()
    mqtt_client = FakeMQTTClient()
    last_color = [255, 255, 255]

    ok = _run_led_command(
        facade=facade,
        mqtt_client=mqtt_client,
        raw_payload="1,2,3",
        payload={},
        last_color=last_color,
    )

    assert ok is True
    assert facade.calls == [(1, 2, 3, None)]
    assert mqtt_client.publishes == [
        (
            "bb8/state/led",
            '{"state":"ON","color_mode":"rgb","color":{"r":1,"g":2,"b":3}}',
            0,
            True,
        )
    ]
    assert last_color == [1, 2, 3]
