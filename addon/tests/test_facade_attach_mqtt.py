import asyncio
from types import SimpleNamespace

import pytest

from addon.bb8_core.facade import BB8Facade

# Ensure pytest-asyncio is active for the module
pytestmark = pytest.mark.asyncio


class FakeClient:
    def __init__(self):
        self.calls = []

    def publish(self, t, payload, qos=0, retain=False):
        self.calls.append(("pub", t, retain))

        async def noop():
            return None

        return noop()

    def subscribe(self, t, qos=0):
        self.calls.append(("sub", t, qos))

    def message_callback_add(self, t, cb):
        self.calls.append(("cb", t))


def make_bridge():
    return SimpleNamespace(
        connect=lambda: None,
        sleep=lambda _: None,
        stop=lambda: None,
        set_led_off=lambda: None,
        set_led_rgb=lambda r, g, b: None,
        is_connected=lambda: False,
        get_rssi=lambda: 0,
    )


async def test_facade_attach_mqtt():
    bridge = make_bridge()
    loop = asyncio.get_running_loop()
    asyncio.set_event_loop(loop)
    await BB8Facade(bridge).attach_mqtt(FakeClient(), "bb8", qos=1, retain=True)
    await asyncio.sleep(0)
    print("OK: facade.attach_mqtt bound without exceptions")


@pytest.fixture(autouse=True)
async def _kyb_bind_create_task(monkeypatch):
    loop = asyncio.get_running_loop()
    import asyncio as _asyncio

    monkeypatch.setattr(
        _asyncio,
        "create_task",
        lambda c: loop.create_task(c),
        raising=False,
    )


async def test_attach_mqtt_invocation_1():
    bridge = SimpleNamespace(
        connect=lambda: None,
        sleep=lambda _: None,
        stop=lambda: None,
        set_led_off=lambda: None,
        set_led_rgb=lambda r, g, b: None,
        is_connected=lambda: False,
        get_rssi=lambda: 0,
    )
    await BB8Facade(bridge).attach_mqtt(FakeClient(), "bb8", qos=1, retain=True)
    await asyncio.sleep(0)
    print("OK: facade.attach_mqtt bound without exceptions")
