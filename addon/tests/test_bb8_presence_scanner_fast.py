import pytest
import json
from unittest.mock import MagicMock, patch
from addon.bb8_core import bb8_presence_scanner

# Test _device_block
@pytest.mark.parametrize("mac_upper", ["AA:BB:CC:DD:EE:FF", ""])
def test_device_block(mac_upper):
    block = bb8_presence_scanner._device_block(mac_upper)
    assert "identifiers" in block
    assert block["manufacturer"] == "Sphero"
    assert block["model"] == "S33 BB84 LE"
    assert block["sw_version"]

# Test publish_discovery
@pytest.mark.asyncio
async def test_publish_discovery_basic(monkeypatch):
    mqtt = MagicMock()
    mac_upper = "AA:BB:CC:DD:EE:FF"
    # LED discovery off
    monkeypatch.setenv("PUBLISH_LED_DISCOVERY", "0")
    await bb8_presence_scanner.publish_discovery(mqtt, mac_upper)
    assert mqtt.publish.call_count == 2
    calls = [call[0][0] for call in mqtt.publish.call_args_list]
    assert "homeassistant/binary_sensor/bb8_presence/config" in calls
    assert "homeassistant/sensor/bb8_rssi/config" in calls

@pytest.mark.asyncio
async def test_publish_discovery_led(monkeypatch):
    mqtt = MagicMock()
    mac_upper = "AA:BB:CC:DD:EE:FF"
    monkeypatch.setenv("PUBLISH_LED_DISCOVERY", "1")
    await bb8_presence_scanner.publish_discovery(mqtt, mac_upper)
    assert mqtt.publish.call_count == 3
    calls = [call[0][0] for call in mqtt.publish.call_args_list]
    assert "homeassistant/light/bb8_led/config" in calls

# Test log_config
def test_log_config(capsys):
    cfg = {"BB8_NAME": "BB-8", "MQTT_HOST": "localhost", "MQTT_PORT": 1883, "MQTT_USERNAME": "user", "MQTT_PASSWORD": "pass", "MQTT_BASE": "bb8", "ENABLE_BRIDGE_TELEMETRY": True, "TELEMETRY_INTERVAL_S": 10, "ADDON_VERSION": "1.0.0"}
    logger = MagicMock()
    bb8_presence_scanner.log_config(cfg, "src_path", logger)
    logger.debug.assert_called()

# Test _cb_led_set
@pytest.mark.parametrize("payload,state", [
    (json.dumps({"state": "ON", "color": {"r": 255, "g": 0, "b": 0}}), "OFF"),
    (json.dumps({"state": "OFF"}), "OFF"),
    ("", "OFF"),
])
def test_cb_led_set(payload, state):
    msg = MagicMock()
    msg.payload = payload.encode("utf-8")
    result = bb8_presence_scanner._cb_led_set(None, None, msg)
    assert result is None  # Function does not return, just side effects

# Test read_version_or_default
@patch("addon.bb8_core.bb8_presence_scanner.Path.read_text", return_value="1.2.3")
def test_read_version_or_default_success(mock_read):
    assert bb8_presence_scanner.read_version_or_default() == "1.2.3"

@patch("addon.bb8_core.bb8_presence_scanner.Path.read_text", side_effect=Exception)
def test_read_version_or_default_fallback(mock_read):
    assert bb8_presence_scanner.read_version_or_default() == "addon:dev"
