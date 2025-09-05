import asyncio
import pytest

# Ensure a running event loop for all tests in this module (no-op if one already exists).
@pytest.fixture(autouse=True)
def _ensure_running_loop():
    created = False
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        created = True
    try:
        yield
    finally:
        # Do not close the loop here to avoid interfering with other tests.
        # (pytest will handle loop lifecycle across tests if configured.)
        if created:
            pass

pytestmark = pytest.mark.asyncio
from types import SimpleNamespace

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

async def test_facade_attach_mqtt():
    BB8Facade(bridge).attach_mqtt(FakeClient(), "bb8", qos=1, retain=True)
    print("OK: facade.attach_mqtt bound without exceptions")
import asyncio
import pytest

# Ensure a running event loop for all tests in this module (no-op if one already exists).
@pytest.fixture(autouse=True)
def _ensure_running_loop():
    created = False
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        created = True
    try:
        yield
    finally:
        # Do not close the loop here to avoid interfering with other tests.
        # (pytest will handle loop lifecycle across tests if configured.)
        if created:
            pass
import pytest
# Mark all tests in this module as asyncio to ensure a running loop is available.
pytestmark = pytest.mark.asyncio
from types import SimpleNamespace

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
BB8Facade(bridge).attach_mqtt(FakeClient(), "bb8", qos=1, retain=True)
print("OK: facade.attach_mqtt bound without exceptions")
