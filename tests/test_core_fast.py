from unittest.mock import MagicMock

from addon.bb8_core.core import Core


# Test Core class basic lifecycle
def test_core_lifecycle():
    c = Core("AA:BB:CC:DD:EE:FF", adapter="hci0")
    assert c.address == "AA:BB:CC:DD:EE:FF"
    assert c.adapter == "hci0"
    assert not c._connected
    c.connect()
    assert c._connected
    c.disconnect()
    assert not c._connected


# Test context manager
def test_core_context_manager():
    c = Core("AA:BB:CC:DD:EE:FF")
    with c as core:
        assert core._connected
    assert not c._connected


# Test set_main_led
def test_core_set_main_led():
    c = Core("AA:BB:CC:DD:EE:FF")
    c.set_main_led(255, 0, 0)
    c.set_main_led(0, 255, 0, persist=True)


# Test roll
def test_core_roll():
    c = Core("AA:BB:CC:DD:EE:FF")
    c.roll(100, 90, 500)


# Test sleep
def test_core_sleep():
    c = Core("AA:BB:CC:DD:EE:FF")
    c.sleep("short", 1, 2, 3)


# Test emit_led with publisher
def test_core_emit_led_with_publisher():
    c = Core("AA:BB:CC:DD:EE:FF")
    pub = MagicMock()
    c.publish_led_rgb = pub
    c.emit_led("bridge", 1, 2, 3)
    pub.assert_called_with("bridge", 1, 2, 3)


# Test emit_led without publisher
def test_core_emit_led_without_publisher():
    c = Core("AA:BB:CC:DD:EE:FF")
    # Should not raise or call anything
    c.emit_led("bridge", 1, 2, 3)
