import asyncio
from unittest.mock import MagicMock

import pytest

from addon.bb8_core import common


def test_mqtt_base_env(monkeypatch):
    monkeypatch.delenv("MQTT_BASE", raising=False)
    assert common._mqtt_base() == "bb8"
    monkeypatch.setenv("MQTT_BASE", "custom")
    assert common._mqtt_base() == "custom"


def test_cmd_and_state_topics(monkeypatch):
    monkeypatch.setenv("MQTT_BASE", "testbase")
    # Re-import to refresh topics
    import importlib

    importlib.reload(common)
    for _k, v in common.CMD_TOPICS.items():
        assert isinstance(v, list)
        assert all(isinstance(t, str) for t in v)
    for _k, v in common.STATE_TOPICS.items():
        assert isinstance(v, str)
        assert v.startswith("testbase/")


@pytest.mark.parametrize(
    "val,expected",
    [
        (5, 5),
        (3.14, 3.14),
        ("foo", "foo"),
        ([1, 2], "[1, 2]"),
        ({"a": 1}, "{'a': 1}"),
    ],
)
def test_coerce_raw(val, expected):
    result = common._coerce_raw(val)
    if isinstance(val, int | float | str):
        assert result == val
    else:
        assert isinstance(result, str)


def test_publish_device_echo():
    client = MagicMock()
    # Should publish raw and JSON echo
    common.publish_device_echo(client, "topic", 42)
    calls = [c[0] for c in client.publish.call_args_list]
    assert any("topic" in str(a) for a in calls)
    # Should publish both raw and JSON
    assert client.publish.call_count == 2


def test_command_handlers():
    client = MagicMock()
    # on_power_set
    common.on_power_set(client, "ON")
    # on_stop
    common.on_stop(client)
    # on_sleep
    common.on_sleep(client)
    # on_drive
    common.on_drive(client, "drive")
    # on_heading
    common.on_heading(client, 123)
    # on_speed
    common.on_speed(client, 255)
    # on_led_set
    common.on_led_set(client, 1, 2, 3)
    # All should call publish
    assert client.publish.call_count >= 8


def test_ble_loop_thread():
    loop = common.ble_loop
    assert isinstance(loop, asyncio.AbstractEventLoop)
