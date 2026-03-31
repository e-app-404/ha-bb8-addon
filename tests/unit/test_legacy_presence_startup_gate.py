from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from addon.bb8_core import bridge_controller
from addon.bb8_core.facade import BB8Facade


class _FakeBridgeClient:
    def publish(self, *args, **kwargs):
        return None

    def subscribe(self, *args, **kwargs):
        return None

    def message_callback_add(self, *args, **kwargs):
        return None


class _DummyFacade:
    def __init__(self, bridge):
        self.bridge = bridge
        self.target_mac = None

    def set_target_mac(self, mac: str) -> None:
        self.target_mac = mac


def _close_coro(coro):
    coro.close()
    return Mock()


def test_start_bridge_controller_disables_legacy_presence_monitor_by_default(monkeypatch):
    start_presence_monitor = Mock()

    monkeypatch.setattr(
        "addon.bb8_core.auto_detect.start_presence_monitor",
        start_presence_monitor,
    )
    monkeypatch.setattr(
        "addon.bb8_core.auto_detect.resolve_bb8_mac",
        lambda **kwargs: "AA:BB:CC:DD:EE:FF",
    )
    monkeypatch.setattr("addon.bb8_core.ble_gateway.BleGateway", lambda *args, **kwargs: Mock())
    monkeypatch.setattr("addon.bb8_core.ble_bridge.BLEBridge", lambda *args, **kwargs: Mock())
    monkeypatch.setattr("addon.bb8_core.ble_session.BleSession", lambda *args, **kwargs: Mock())
    monkeypatch.setattr(bridge_controller, "BB8Facade", _DummyFacade)
    monkeypatch.setattr(bridge_controller, "_propagate_ble_session_to_facade", lambda *args: None)
    monkeypatch.setattr(bridge_controller.asyncio, "create_task", _close_coro)

    facade = bridge_controller.start_bridge_controller(config={"bb8_mac": "AA:BB:CC:DD:EE:FF"})

    assert isinstance(facade, _DummyFacade)
    start_presence_monitor.assert_not_called()


def test_attach_mqtt_skips_legacy_presence_discovery_by_default(monkeypatch):
    create_task = Mock(side_effect=_close_coro)

    monkeypatch.setattr(
        "addon.bb8_core.facade.load_config",
        lambda: (
            {
                "MQTT_BASE": "bb8",
                "MQTT_CLIENT_ID": "bb8_presence_scanner",
                "BB8_NAME": "S33 BB84 LE",
                "QOS": 1,
                "RETAIN": True,
            },
            None,
        ),
    )
    monkeypatch.setattr("asyncio.create_task", create_task)

    facade = BB8Facade(SimpleNamespace())
    facade.attach_mqtt(_FakeBridgeClient(), "bb8")

    create_task.assert_not_called()


def test_attach_mqtt_can_enable_legacy_presence_discovery(monkeypatch):
    create_task = Mock(side_effect=_close_coro)

    monkeypatch.setattr(
        "addon.bb8_core.facade.load_config",
        lambda: (
            {
                "MQTT_BASE": "bb8",
                "MQTT_CLIENT_ID": "bb8_presence_scanner",
                "BB8_NAME": "S33 BB84 LE",
                "QOS": 1,
                "RETAIN": True,
            },
            None,
        ),
    )
    monkeypatch.setattr("asyncio.create_task", create_task)
    monkeypatch.setattr(
        "addon.bb8_core.facade.publish_discovery",
        lambda *args, **kwargs: _noop_publish_discovery(),
    )

    facade = BB8Facade(SimpleNamespace())
    facade.attach_mqtt(
        _FakeBridgeClient(),
        "bb8",
        enable_presence_discovery=True,
    )

    create_task.assert_called_once()


async def _noop_publish_discovery():
    return None