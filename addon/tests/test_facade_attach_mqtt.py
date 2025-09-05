import asyncio

import pytest

# Ensure pytest-asyncio is active for the module
pytestmark = pytest.mark.asyncio


# Autouse: bind asyncio.create_task to the running pytest-asyncio loop
@pytest.fixture(autouse=True)
async def _bind_create_task_loop(monkeypatch):
    loop = asyncio.get_running_loop()
    monkeypatch.setattr(
        asyncio, "create_task", lambda c: loop.create_task(c), raising=False
    )
    yield


import importlib
import inspect

import pytest

# Run all tests in this module with pytest-asyncio.
pytestmark = pytest.mark.asyncio


# Autouse fixture:
# - Ensures a running event loop is available (some prod code calls asyncio.get_running_loop() from sync funcs)
# - Wraps BB8Facade.attach_mqtt so tests can "await" it whether it's sync or coroutine-returning
@pytest.fixture(autouse=True)
def _loop_and_attach_wrapper(monkeypatch, event_loop):
    # Ensure a loop is set and "running" for get_running_loop()
    try:
        asyncio.set_event_loop(event_loop)
    except RuntimeError:
        pass
    monkeypatch.setattr(asyncio, "get_running_loop", lambda: event_loop, raising=False)

    # Wrap attach_mqtt to always be awaitable in tests
    facade_mod = importlib.import_module("addon.bb8_core.facade")
    BB8Facade = getattr(facade_mod, "BB8Facade", None)
    if BB8Facade is not None and hasattr(BB8Facade, "attach_mqtt"):
        _orig = BB8Facade.attach_mqtt

        async def _wrapped(self, *args, **kwargs):
            res = _orig(self, *args, **kwargs)
            if inspect.isawaitable(res):
                return await res
            return res

        try:
            monkeypatch.setattr(BB8Facade, "attach_mqtt", _wrapped, raising=False)
        except Exception:
            # If class is frozen or replaced later, ignore; tests can still 'await' call-sites directly.
            pass
    # yield control to tests
    yield


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
