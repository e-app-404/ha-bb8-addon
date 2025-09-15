import json
import types

import addon.bb8_core.bb8_presence_scanner as scanner
import pytest


def test_read_version_or_default(monkeypatch, tmp_path):
    # Normal case: file exists
    version_file = tmp_path / "VERSION"
    version_file.write_text("1.2.3\n")
    assert scanner.read_version_or_default(str(version_file)) == "1.2.3"
    # Exception branch: file missing
    missing_file = tmp_path / "DOES_NOT_EXIST"
    assert scanner.read_version_or_default(str(missing_file)) == "addon:dev"


def test_device_block():
    block = scanner._device_block("AA:BB:CC:DD:EE:FF")
    assert "identifiers" in block and "connections" in block
    assert block["identifiers"][1] == "mac:AA:BB:CC:DD:EE:FF"


@pytest.mark.asyncio
async def test_publish_discovery(monkeypatch):
    calls = []

    class DummyMQTT:
        async def publish(self, topic, payload, qos, retain):
            calls.append((topic, json.loads(payload), qos, retain))

    # LED discovery branch
    monkeypatch.setenv("PUBLISH_LED_DISCOVERY", "1")
    await scanner.publish_discovery(DummyMQTT(), "AABBCCDDEEFF")
    topics = [c[0] for c in calls]
    assert any("bb8_presence" in t for t in topics)
    assert any("bb8_led" in t for t in topics)


def test_log_config():
    logs = {}

    class DummyLogger:
        def debug(self, msg):
            logs["debug"] = msg

    cfg = {"BB8_NAME": "BB-8", "MQTT_PORT": 1883, "MQTT_PASSWORD": "pw"}
    scanner.log_config(cfg, "src_path", DummyLogger())
    assert "BB8_NAME='BB-8'" in logs["debug"]


def test_cb_led_set(monkeypatch):
    # Patch BB8Facade to record calls
    called = {}

    class DummyFacade:
        def set_led_rgb(self, r, g, b):
            called["rgb"] = (r, g, b)

        def set_led_off(self):
            called["off"] = True

    monkeypatch.setattr(
        "addon.bb8_core.bb8_presence_scanner.BB8Facade", DummyFacade
    )

    class DummyClient:
        def __init__(self):
            self.published = []

        def publish(self, topic, payload, qos=1, retain=False):
            self.published.append((topic, json.loads(payload), qos, retain))

    # JSON with state ON and color
    msg = types.SimpleNamespace(
        payload=json.dumps({
            "state": "ON",
            "color": {"r": 1, "g": 2, "b": 3}
        }).encode()
    )
    c = DummyClient()
    scanner._cb_led_set(c, None, msg)
    assert called["rgb"] == (1, 2, 3)
    # JSON with hex
    msg = types.SimpleNamespace(
        payload=json.dumps({"hex": "#010203"}).encode()
    )
    called.clear()
    scanner._cb_led_set(c, None, msg)
    assert called["rgb"] == (1, 2, 3)
    # JSON with r,g,b
    msg = types.SimpleNamespace(
        payload=json.dumps({"r": 4, "g": 5, "b": 6}).encode()
    )
    called.clear()
    scanner._cb_led_set(c, None, msg)
    assert called["rgb"] == (4, 5, 6)
    # OFF string
    msg = types.SimpleNamespace(payload=b"OFF")
    called.clear()
    scanner._cb_led_set(c, None, msg)
    assert called["off"] is True
    # Invalid JSON
    msg = types.SimpleNamespace(payload=b"notjson")
    called.clear()
    scanner._cb_led_set(c, None, msg)
    # Should not raise


def test_ensure_discovery_initialized():
    # Should be idempotent
    scanner._scanner_dispatcher_initialized = False
    scanner.ensure_discovery_initialized()
    assert scanner._scanner_dispatcher_initialized is True
    scanner.ensure_discovery_initialized()
    assert scanner._scanner_dispatcher_initialized is True


def test_publish_extended_discovery():
    published = []

    class DummyClient:
        def publish(self, topic, payload=None, qos=1, retain=False):
            published.append((topic, payload, qos, retain))

    base = "bb8/test"
    device_id = "aabbccddeeff"
    device_block = {"identifiers": ["id"]}
    scanner.publish_extended_discovery(
        DummyClient(), base, device_id, device_block
    )
    topics = [t[0] for t in published]
    assert any("light" in t for t in topics)
    assert any("heading" in t for t in topics)
    assert any("speed" in t for t in topics)


def test_make_device_id_and_base():
    assert scanner.make_device_id("AA:BB:CC:DD:EE:FF") == "aabbccddeeff"
    assert scanner.make_base("aabbccddeeff") == "bb8/aabbccddeeff"


def test_extract_mac_and_dbus():
    class Device:
        def __init__(self):
            self.details = {
                "props": {"Address": "AA:BB:CC:DD:EE:FF"},
                "path": "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF",
            }
            self.address = "AA:BB:CC:DD:EE:FF"

    mac, dbus_path = scanner._extract_mac_and_dbus(Device())
    assert mac == "AA:BB:CC:DD:EE:FF"
    assert dbus_path.startswith("/org/bluez/hci0/dev_")


def test_build_device_block():
    block = scanner.build_device_block(
        "AA:BB:CC:DD:EE:FF",
        "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF",
        "S33 BB84 LE",
        "BB-8",
    )
    assert "identifiers" in block and "connections" in block
    assert block["model"] == "S33 BB84 LE"


def test_publish_discovery_old():
    published = []

    class DummyClient:
        def publish(self, topic, payload=None, qos=1, retain=False):
            published.append((topic, payload, qos, retain))

    scanner.publish_discovery_old(
        DummyClient(),
        "AA:BB:CC:DD:EE:FF",
        "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF",
        "S33 BB84 LE",
        "BB-8",
    )
    topics = [t[0] for t in published]
    assert any("binary_sensor" in t for t in topics)
    assert any("sensor" in t for t in topics)


def test_clamp():
    assert scanner._clamp(5, 0, 10) == 5
    assert scanner._clamp(-5, 0, 10) == 0
    assert scanner._clamp(15, 0, 10) == 10
    assert scanner._clamp("notanint", 0, 10) == 0


def test_parse_led_payload():
    # HA JSON schema
    payload = json.dumps({"color": {"r": 1, "g": 2, "b": 3}})
    assert scanner._parse_led_payload(payload) == ("RGB", (1, 2, 3))
    # Legacy direct
    payload = json.dumps({"r": 4, "g": 5, "b": 6})
    assert scanner._parse_led_payload(payload) == ("RGB", (4, 5, 6))
    # Hex
    payload = json.dumps({"hex": "#010203"})
    assert scanner._parse_led_payload(payload) == ("RGB", (1, 2, 3))
    # OFF
    assert scanner._parse_led_payload("OFF") == ("OFF", None)
    # Invalid
    assert scanner._parse_led_payload("notjson") == ("INVALID", None)


def test_cb_power_set(monkeypatch):
    called = {}

    class DummyFacade:
        def power(self, on):
            called["power"] = on

    monkeypatch.setattr(scanner, "FACADE", DummyFacade())

    class DummyClient:
        def __init__(self):
            self.published = []

        def publish(self, topic, payload, qos=1, retain=False):
            self.published.append((topic, payload, qos, retain))

    # ON
    msg = types.SimpleNamespace(payload=b"ON")
    c = DummyClient()
    scanner._cb_power_set(c, None, msg)
    assert called["power"] is True
    # OFF
    msg = types.SimpleNamespace(payload=b"OFF")
    scanner._cb_power_set(c, None, msg)
    assert called["power"] is False
    # Invalid
    msg = types.SimpleNamespace(payload=b"bad")
    scanner._cb_power_set(c, None, msg)


def test_cb_stop_press(monkeypatch):
    called = {}

    class DummyFacade:
        def stop(self):
            called["stop"] = True

    monkeypatch.setattr(scanner, "FACADE", DummyFacade())

    class DummyClient:
        def __init__(self):
            self.published = []

        def publish(self, topic, payload, qos=1, retain=False):
            self.published.append((topic, payload, qos, retain))

    msg = types.SimpleNamespace(payload=b"any")
    c = DummyClient()
    scanner._cb_stop_press(c, None, msg)
    assert called["stop"] is True
    # Should publish pressed and idle
    topics = [t[0] for t in c.published]
    assert any("stop/state" in t for t in topics)


def test_cb_heading_set(monkeypatch):
    called = {}

    class DummyFacade:
        def set_heading(self, deg):
            called["heading"] = deg

    monkeypatch.setattr(scanner, "FACADE", DummyFacade())

    class DummyClient:
        def __init__(self):
            self.published = []

        def publish(self, topic, payload, qos=1, retain=False):
            self.published.append((topic, payload, qos, retain))

    # Valid
    msg = types.SimpleNamespace(payload=b"123")
    c = DummyClient()
    scanner._cb_heading_set(c, None, msg)
    assert called["heading"] == 123
    # Invalid
    msg = types.SimpleNamespace(payload=b"notanumber")
    scanner._cb_heading_set(c, None, msg)


def test_cb_speed_set(monkeypatch):
    called = {}

    class DummyFacade:
        def set_speed(self, spd):
            called["speed"] = spd

    monkeypatch.setattr(scanner, "FACADE", DummyFacade())

    class DummyClient:
        def __init__(self):
            self.published = []

        def publish(self, topic, payload, qos=1, retain=False):
            self.published.append((topic, payload, qos, retain))

    # Valid
    msg = types.SimpleNamespace(payload=b"200")
    c = DummyClient()
    scanner._cb_speed_set(c, None, msg)
    assert called["speed"] == 200
    # Invalid
    msg = types.SimpleNamespace(payload=b"notanumber")
    scanner._cb_speed_set(c, None, msg)


def test_cb_drive_press(monkeypatch):
    called = {}

    class DummyFacade:
        def drive(self):
            called["drive"] = True

    monkeypatch.setattr(scanner, "FACADE", DummyFacade())

    class DummyClient:
        def __init__(self):
            self.published = []

        def publish(self, topic, payload, qos=1, retain=False):
            self.published.append((topic, payload, qos, retain))

    msg = types.SimpleNamespace(payload=b"any")
    c = DummyClient()
    scanner._cb_drive_press(c, None, msg)
    assert called["drive"] is True
    topics = [t[0] for t in c.published]
    assert any("stop/state" in t for t in topics)


def test_tick_log(capsys):
    # found True
    scanner.tick_log(True, "BB-8", "AA:BB:CC:DD:EE:FF", -60)
    out = capsys.readouterr().out
    assert "found name=BB-8" in out

    # found False, verbose
    class Args:
        verbose = True
        quiet = False
        json = False

    scanner.tick_log(False, "BB-8", None, None, Args())
    out = capsys.readouterr().out
    assert "not_found name=BB-8" in out

    # found False, json
    class Args:
        verbose = False
        quiet = False
        json = True

    scanner.tick_log(False, "BB-8", None, None, Args())
    out = capsys.readouterr().out
    assert '"found": false' in out
