import json
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import bb8_core.facade as facade_mod  # type: ignore[import-not-found]


class FakeClient:
    def __init__(self):
        self.calls = []

    def publish(self, topic, payload=None, qos=0, retain=False):
        self.calls.append(
            {
                "topic": topic,
                "payload": payload,
                "qos": qos,
                "retain": retain,
            }
        )


class FakeLighting:
    def __init__(self):
        self.static_calls = []
        self.cancel_calls = 0

    async def cancel_active(self):
        self.cancel_calls += 1

    def clamp_rgb(self, r, g, b):
        return int(r), int(g), int(b)

    async def set_static(self, r, g, b):
        self.static_calls.append((r, g, b))
        return True


class FakeSession:
    def __init__(self, connected=True):
        self._connected = connected

    def is_connected(self):
        return self._connected


def test_led_deferred_during_post_connect_holdoff(monkeypatch):
    monkeypatch.setattr(
        facade_mod,
        "load_config",
        lambda *args, **kwargs: ({"post_connect_delay_s": 15}, "test"),
    )

    facade = facade_mod.BB8Facade(bridge=SimpleNamespace())
    facade._lighting = FakeLighting()
    facade._ble_session = FakeSession(connected=True)
    facade._mqtt = {"client": FakeClient(), "base": "bb8/test", "qos": 1, "retain": False}

    facade.mark_post_connect_holdoff(now_monotonic=100.0)
    monkeypatch.setattr(facade_mod.time, "monotonic", lambda: 100.2)

    result = asyncio.run(facade.set_led_async(1, 2, 3, cid="cid-holdoff"))

    assert facade._lighting.static_calls == []
    assert result is False
    ack = next(c for c in facade._mqtt["client"].calls if c["topic"].endswith("/ack/led"))
    rej = next(
        c for c in facade._mqtt["client"].calls if c["topic"].endswith("/event/rejected")
    )

    ack_payload = json.loads(ack["payload"])
    rej_payload = json.loads(rej["payload"])

    assert ack_payload["ok"] is False
    assert ack_payload["reason"] == "post_connect_holdoff"
    assert ack_payload["remaining_s"] == 15
    assert rej_payload["cmd"] == "led"
    assert rej_payload["reason"] == "post_connect_holdoff"
    assert rej_payload["remaining_s"] == 15


def test_led_succeeds_after_holdoff(monkeypatch):
    monkeypatch.setattr(
        facade_mod,
        "load_config",
        lambda *args, **kwargs: ({"post_connect_delay_s": 15}, "test"),
    )

    facade = facade_mod.BB8Facade(bridge=SimpleNamespace())
    facade._lighting = FakeLighting()
    facade._ble_session = FakeSession(connected=True)
    facade._mqtt = {"client": FakeClient(), "base": "bb8/test", "qos": 1, "retain": False}

    facade.mark_post_connect_holdoff(now_monotonic=100.0)
    monkeypatch.setattr(facade_mod.time, "monotonic", lambda: 120.0)

    result = asyncio.run(facade.set_led_async(7, 8, 9, cid="cid-ready"))

    assert facade._lighting.static_calls == [(7, 8, 9)]
    assert result is True
    ack = next(c for c in facade._mqtt["client"].calls if c["topic"].endswith("/ack/led"))
    ack_payload = json.loads(ack["payload"])
    assert ack_payload["ok"] is True
    assert all(not c["topic"].endswith("/event/rejected") for c in facade._mqtt["client"].calls)


def test_delay_override_affects_remaining_seconds(monkeypatch):
    monkeypatch.setattr(
        facade_mod,
        "load_config",
        lambda *args, **kwargs: ({"post_connect_delay_s": 3}, "test"),
    )

    facade = facade_mod.BB8Facade(bridge=SimpleNamespace())
    facade._lighting = FakeLighting()
    facade._ble_session = FakeSession(connected=True)
    facade._mqtt = {"client": FakeClient(), "base": "bb8/test", "qos": 1, "retain": False}

    facade.mark_post_connect_holdoff(now_monotonic=10.0)
    monkeypatch.setattr(facade_mod.time, "monotonic", lambda: 12.0)

    result = asyncio.run(facade.set_led_async(10, 11, 12, cid="cid-delay"))

    assert result is False
    ack = next(c for c in facade._mqtt["client"].calls if c["topic"].endswith("/ack/led"))
    payload = json.loads(ack["payload"])
    assert payload["reason"] == "post_connect_holdoff"
    assert payload["remaining_s"] == 1


def test_propagated_session_drives_led_path(monkeypatch):
    monkeypatch.setattr(
        facade_mod,
        "load_config",
        lambda *args, **kwargs: ({"post_connect_delay_s": 15}, "test"),
    )

    facade = facade_mod.BB8Facade(bridge=SimpleNamespace())
    session = MagicMock()
    session.is_connected = MagicMock(return_value=True)
    session.set_led = AsyncMock(return_value=None)
    session._target_mac = "C9:5A:63:6B:B5:4A"
    facade._mqtt = {"client": FakeClient(), "base": "bb8/test", "qos": 1, "retain": False}

    facade.set_ble_session(session)

    result = asyncio.run(facade.set_led_async(7, 8, 9, cid="cid-propagated"))

    assert result is True
    assert facade._ble_session is session
    assert facade._lighting._ble_session is session
    session.set_led.assert_awaited_once_with(7, 8, 9)
