

import asyncio
from types import SimpleNamespace

import pytest

from bb8_core.facade import BB8Facade


class FakeClient:
    def __init__(self):
        self.calls = []

    def publish(self, t, payload, qos=0, retain=False):
        self.calls.append(("pub", t, retain))

    def subscribe(self, t, qos=0):
        self.calls.append(("sub", t, qos))

    def message_callback_add(self, t, cb):
        self.calls.append(("cb", t))

bridge = SimpleNamespace(
    connect=lambda: None,
    sleep=lambda _: None,
    stop=lambda: None,
    set_led_off=lambda: None,
    set_led_rgb=lambda r, g, b: None,
    is_connected=lambda: False,
    get_rssi=lambda: 0,
)


@pytest.mark.asyncio
async def test_attach_mqtt():
    BB8Facade(bridge).attach_mqtt(FakeClient(), "bb8", qos=1, retain=True)
    print("OK: facade.attach_mqtt bound without exceptions")

if __name__ == "__main__":
    asyncio.run(test_attach_mqtt())
