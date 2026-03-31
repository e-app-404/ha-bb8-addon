import asyncio
from unittest.mock import AsyncMock, MagicMock

from bb8_core.lighting import LightingController


def test_set_static_uses_ble_session_write_path():
    session = MagicMock()
    session.is_connected = MagicMock(return_value=True)
    session.set_led = AsyncMock(return_value=None)

    controller = LightingController(session)

    result = asyncio.run(controller.set_static(1, 2, 3))

    assert result is True
    session.set_led.assert_awaited_once_with(1, 2, 3)


def test_set_static_off_uses_same_ble_session_path():
    session = MagicMock()
    session.is_connected = MagicMock(return_value=True)
    session.set_led = AsyncMock(return_value=None)

    controller = LightingController(session)

    result = asyncio.run(controller.set_static(0, 0, 0))

    assert result is True
    session.set_led.assert_awaited_once_with(0, 0, 0)


def test_set_static_returns_false_when_not_connected():
    session = MagicMock()
    session.is_connected = MagicMock(return_value=False)
    session.set_led = AsyncMock(return_value=None)

    controller = LightingController(session)

    result = asyncio.run(controller.set_static(9, 8, 7))

    assert result is False
    session.set_led.assert_not_called()


def test_set_static_propagates_hardware_failure():
    session = MagicMock()
    session.is_connected = MagicMock(return_value=True)
    session.set_led = AsyncMock(side_effect=RuntimeError("boom"))

    controller = LightingController(session)

    try:
        asyncio.run(controller.set_static(4, 5, 6))
    except RuntimeError as exc:
        assert str(exc) == "boom"
    else:
        raise AssertionError("Expected set_static to propagate hardware failure")