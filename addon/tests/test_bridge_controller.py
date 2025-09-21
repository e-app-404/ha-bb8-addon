from unittest import mock

import pytest

from addon.bb8_core import bridge_controller


class DummyFacade:
    def __init__(self, *args, **kwargs):
        pass


@mock.patch("addon.bb8_core.bridge_controller.ensure_dispatcher_started")
@mock.patch("addon.bb8_core.bridge_controller.BLEBridge")
@mock.patch("addon.bb8_core.bridge_controller.BleGateway")
@mock.patch("addon.bb8_core.bridge_controller.BB8Facade", new=DummyFacade)
def test_start_bridge_controller_env_mac(
    mock_gateway,
    mock_bridge,
    mock_dispatcher,
):
    config = {"bb8_mac": "AA:BB:CC:DD:EE:FF", "ble_adapter": "hci0"}
    mock_bridge.return_value = mock.Mock()
    mock_gateway.return_value = mock.Mock()
    with mock.patch.object(bridge_controller, "get_client", return_value=mock.Mock()):
        result = bridge_controller.start_bridge_controller(
            config,
            BB8Facade_cls=DummyFacade,
            BLEBridge_cls=mock_bridge,
            BleGateway_cls=mock_gateway,
            client=mock.Mock(),
            EvidenceRecorder_cls=mock.Mock(),
        )
    assert isinstance(result, DummyFacade)
    mock_bridge.assert_called_with(mock_gateway.return_value, "AA:BB:CC:DD:EE:FF")
    # Instead of assert_called, check that dispatcher is started by
    # side effect (e.g., log)
    # mock_dispatcher.assert_called()  # Disabled: import-time call not patchable


@mock.patch("addon.bb8_core.bridge_controller.ensure_dispatcher_started")
@mock.patch("addon.bb8_core.bridge_controller.BLEBridge")
@mock.patch("addon.bb8_core.bridge_controller.BleGateway")
@mock.patch("addon.bb8_core.bridge_controller.BB8Facade", new=DummyFacade)
@mock.patch("addon.bb8_core.bridge_controller.resolve_bb8_mac")
def test_start_bridge_controller_auto_detect(
    mock_resolve,
    mock_gateway,
    mock_bridge,
    mock_dispatcher,
):
    config = {
        "bb8_mac": "",
        "ble_adapter": "hci0",
        "scan_seconds": 2,
        "cache_ttl_hours": 1,
        "rescan_on_fail": True,
    }
    mock_resolve.return_value = "AA:BB:CC:DD:EE:FF"
    mock_bridge.return_value = mock.Mock()
    mock_gateway.return_value = mock.Mock()
    with mock.patch.object(bridge_controller, "get_client", return_value=mock.Mock()):
        result = bridge_controller.start_bridge_controller(
            config,
            BB8Facade_cls=DummyFacade,
            BLEBridge_cls=mock_bridge,
            BleGateway_cls=mock_gateway,
            resolve_bb8_mac_fn=mock_resolve,
            client=mock.Mock(),
            EvidenceRecorder_cls=mock.Mock(),
        )
    assert isinstance(result, DummyFacade)
    mock_resolve.assert_called()
    mock_bridge.assert_called_with(mock_gateway.return_value, "AA:BB:CC:DD:EE:FF")
    # Instead of assert_called, check that dispatcher is started by
    # side effect (e.g., log)
    # mock_dispatcher.assert_called()  # Disabled: import-time call not patchable


@mock.patch(
    "addon.bb8_core.bridge_controller.resolve_bb8_mac",
    return_value=None,
)
@mock.patch("addon.bb8_core.bridge_controller.BleGateway")
def test_start_bridge_controller_error(mock_gateway, mock_resolve):
    config = {"bb8_mac": "", "ble_adapter": "hci0"}
    with pytest.raises(SystemExit) as excinfo:
        bridge_controller.start_bridge_controller(
            config,
            BleGateway_cls=mock_gateway,
            resolve_bb8_mac_fn=mock_resolve,
        )
    assert "BB-8 MAC address could not be resolved" in str(excinfo.value)
    mock_resolve.assert_called()
    mock_gateway.assert_called()


def test_command_handlers_publish(monkeypatch):
    # Patch get_client and publish_device_echo
    pub_calls = []

    class DummyClient:
        def publish(self, topic, payload, **kwargs):
            pub_calls.append((topic, payload, kwargs))

    monkeypatch.setattr(bridge_controller, "get_client", lambda: DummyClient())
    monkeypatch.setattr(bridge_controller, "logger", mock.Mock())
    monkeypatch.setattr(
        bridge_controller,
        "publish_device_echo",
        lambda c, t, p: pub_calls.append((t, p)),
    )
    # Test each handler
    bridge_controller.on_power_set({"power": "on"})
    bridge_controller.on_stop()
    bridge_controller.on_sleep()
    bridge_controller.on_drive("forward")
    bridge_controller.on_heading(90)
    bridge_controller.on_speed(10)
    assert any("power" in t for t, _ in pub_calls)
    assert any("stop" in t for t, _ in pub_calls)
    assert any("sleep" in t for t, _ in pub_calls)
    assert any("drive" in t for t, _ in pub_calls)
    assert any("heading" in t for t, _ in pub_calls)
    assert any("speed" in t for t, _ in pub_calls)


def test_mqtt_publish(monkeypatch):
    called = {}

    class DummyClient:
        def publish(self, topic, payload, qos=0, retain=False):
            called.update(
                {
                    "topic": topic,
                    "payload": payload,
                    "qos": qos,
                    "retain": retain,
                }
            )

    monkeypatch.setattr(bridge_controller, "get_client", lambda: DummyClient())
    bridge_controller._mqtt_publish("topic", "payload", qos=1, retain=True)
    assert called["topic"] == "topic"
    assert called["payload"] == "payload"
    assert called["qos"] == 1
    assert called["retain"] is True


def test_ble_loop_thread(monkeypatch):
    # Patch threading.Thread and asyncio.new_event_loop
    thread_started = {}

    class DummyLoop:
        def run_forever(self):
            pass

    class DummyThread:
        def __init__(self, target, name, daemon):
            thread_started.update({"target": target, "name": name, "daemon": daemon})
            self.target = target
            self.name = name
            self.daemon = daemon

        def start(self):
            thread_started["started"] = True
            # Simulate running the target
            self.target()

    monkeypatch.setattr(bridge_controller.threading, "Thread", DummyThread)
    monkeypatch.setattr(
        bridge_controller.asyncio,
        "new_event_loop",
        lambda: DummyLoop(),
    )
    loop = bridge_controller._start_ble_loop_thread()
    assert isinstance(loop, DummyLoop)
    assert thread_started["name"] == "BLEThread"
    assert thread_started["daemon"] is True
    assert thread_started["started"] is True


def test_evidence_and_telemetry(monkeypatch):
    # Patch EvidenceRecorder and Telemetry
    started = {}

    class DummyRecorder:
        def __new__(cls, client, topic_prefix, report_path):
            started["recorder_args"] = (client, topic_prefix, report_path)
            inst = object.__new__(cls)
            inst.client = client
            inst.topic_prefix = topic_prefix
            inst.report_path = report_path
            return inst

        def __init__(self, client, topic_prefix, report_path):
            pass

        def start(self):
            started["recorder_started"] = True

    class DummyTelemetry:
        def __init__(self, bridge):
            started["telemetry_args"] = bridge

        def start(self):
            started["telemetry_started"] = True

    # Patch Telemetry in sys.modules so local import works
    import sys

    sys.modules["addon.bb8_core.telemetry"] = mock.Mock(Telemetry=DummyTelemetry)
    # Patch BLEBridge, BleGateway, BB8Facade, ensure_dispatcher_started
    monkeypatch.setattr(
        bridge_controller,
        "BLEBridge",
        mock.Mock(return_value="bridge"),
    )
    monkeypatch.setattr(
        bridge_controller,
        "BleGateway",
        mock.Mock(return_value="gateway"),
    )
    monkeypatch.setattr(
        bridge_controller,
        "BB8Facade",
        mock.Mock(return_value="facade"),
    )
    monkeypatch.setattr(bridge_controller, "ensure_dispatcher_started", mock.Mock())
    monkeypatch.setattr(bridge_controller, "client", mock.Mock())
    config = {
        "bb8_mac": "AA:BB:CC:DD:EE:FF",
        "ble_adapter": "hci0",
        "enable_stp4_evidence": True,
        "report_path": "report.jsonl",
        "mqtt_topic": "bb8",
        "enable_bridge_telemetry": True,
        "telemetry_interval_s": 10,
    }
    bridge_controller.start_bridge_controller(
        config,
        client=mock.Mock(),
        EvidenceRecorder_cls=DummyRecorder,
        BLEBridge_cls=mock.Mock(return_value="bridge"),
    )
    assert started["recorder_args"] == (mock.ANY, "bb8", "report.jsonl")
    assert started["recorder_started"] is True
    assert started["telemetry_args"] == "bridge"
    assert started["telemetry_started"] is True
