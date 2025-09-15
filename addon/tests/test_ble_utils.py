import addon.bb8_core.ble_utils as ble_utils
import pytest


class DummyClientCoroutine:
    def __init__(self):
        self.called = False

    async def get_services(self):
        self.called = True
        return "coroutine_services"


class DummyClientAwaitable:
    def get_services(self):
        class Awaitable:
            def __await__(self):
                yield
                return "awaitable_services"

        return Awaitable()


class DummyClientProperty:
    def __init__(self):
        self.services = "property_services"


class DummyClientNone:
    pass


@pytest.mark.asyncio
async def test_resolve_services_coroutine():
    client = DummyClientCoroutine()
    result = await ble_utils.resolve_services(client)
    assert result == "coroutine_services"
    assert client.called is True


@pytest.mark.asyncio
async def test_resolve_services_awaitable():
    client = DummyClientAwaitable()
    result = await ble_utils.resolve_services(client)
    assert result == "awaitable_services"


@pytest.mark.asyncio
async def test_resolve_services_property():
    client = DummyClientProperty()
    result = await ble_utils.resolve_services(client)
    assert result == "property_services"


@pytest.mark.asyncio
async def test_resolve_services_none():
    client = DummyClientNone()
    result = await ble_utils.resolve_services(client)
    assert result is None
