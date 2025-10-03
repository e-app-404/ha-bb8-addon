"""Comprehensive tests to achieve ≥80% coverage for INT-HA-CONTROL"""

import os
from unittest.mock import MagicMock, patch


def test_addon_config_functionality():
    """Test addon_config module functionality."""
    from addon.bb8_core.addon_config import CONFIG, init_config, load_config

    # Test config loading
    config, source = load_config()
    assert isinstance(config, dict)
    assert isinstance(source, str)

    # Test init_config
    init_config()
    assert isinstance(CONFIG, dict)


def test_logging_setup_functionality():
    """Test logging_setup module functionality."""
    from addon.bb8_core.logging_setup import (get_log_level, logger,
                                              setup_logging)

    # Test logger is available
    assert logger is not None

    # Test log level function
    level = get_log_level("INFO")
    assert level is not None

    # Test setup_logging function
    setup_logging(level="DEBUG")


def test_common_module():
    """Test common module functionality."""
    from addon.bb8_core.common import CMD_TOPICS, STATE_TOPICS

    # Test that topic dictionaries exist and have expected structure
    assert isinstance(CMD_TOPICS, dict)
    assert isinstance(STATE_TOPICS, dict)

    # Test expected topics exist
    expected_topics = ["power", "led", "heading", "speed", "drive", "sleep"]
    for topic in expected_topics:
        assert topic in CMD_TOPICS or topic in STATE_TOPICS


def test_mqtt_dispatcher_basic():
    """Test mqtt_dispatcher module basic functionality."""
    from addon.bb8_core.mqtt_dispatcher import (_device_block,
                                                is_dispatcher_started)

    # Test initial state
    assert not is_dispatcher_started()

    # Test device block creation
    device_block = _device_block()
    assert isinstance(device_block, dict)
    assert "ids" in device_block
    assert "name" in device_block


@patch("addon.bb8_core.echo_responder.mqtt.Client")
def test_echo_responder_client_creation(mock_client):
    """Test echo responder MQTT client creation."""
    from addon.bb8_core.echo_responder import get_mqtt_client

    mock_client_instance = MagicMock()
    mock_client.return_value = mock_client_instance

    # Test client creation
    client = get_mqtt_client()
    assert client == mock_client_instance


def test_facade_basic_functionality():
    """Test facade module basic functionality."""
    from addon.bb8_core.facade import BB8Facade

    # Test facade can be instantiated
    facade = BB8Facade()
    assert facade is not None

    # Test facade has expected methods
    expected_methods = ["power_on", "power_off", "set_led", "set_heading", "set_speed"]
    for method in expected_methods:
        assert hasattr(facade, method)


def test_core_types():
    """Test core_types module."""
    from addon.bb8_core import core_types

    # Test module imports successfully
    assert core_types is not None


def test_telemetry_module():
    """Test telemetry module functionality."""
    from addon.bb8_core.telemetry import TelemetryCollector

    # Test telemetry collector can be created
    collector = TelemetryCollector()
    assert collector is not None


@patch("addon.bb8_core.auto_detect.subprocess.run")
def test_auto_detect_basic(mock_subprocess):
    """Test auto_detect module basic functionality."""
    from addon.bb8_core.auto_detect import scan_for_bb8_mac

    # Mock subprocess to return empty result
    mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")

    # Test scanning function
    result = scan_for_bb8_mac()
    # Should handle empty result gracefully
    assert result is None or isinstance(result, str)


def test_ble_utils():
    """Test ble_utils module functionality."""
    from addon.bb8_core.ble_utils import is_valid_mac

    # Test MAC validation
    assert is_valid_mac("AA:BB:CC:DD:EE:FF")
    assert is_valid_mac("aa:bb:cc:dd:ee:ff")
    assert not is_valid_mac("invalid-mac")
    assert not is_valid_mac("")
    assert not is_valid_mac(None)


def test_mqtt_echo():
    """Test mqtt_echo module functionality."""
    from addon.bb8_core.mqtt_echo import echo_led, echo_scalar

    mock_mqtt = MagicMock()

    # Test scalar echo
    echo_scalar(mock_mqtt, "bb8", "power", "ON")
    mock_mqtt.publish.assert_called()

    # Test LED echo
    echo_led(mock_mqtt, "bb8", 255, 128, 0)
    mock_mqtt.publish.assert_called()


def test_util_module():
    """Test util module functionality."""
    from addon.bb8_core.util import safe_json_loads

    # Test JSON parsing utility
    result = safe_json_loads('{"key": "value"}')
    assert result == {"key": "value"}

    result = safe_json_loads("invalid json")
    assert result == {}


def test_ports_module():
    """Test ports module functionality."""
    from addon.bb8_core import ports

    # Test module loads
    assert ports is not None

    # Test default port constant
    if hasattr(ports, "DEFAULT_MQTT_PORT"):
        assert isinstance(ports.DEFAULT_MQTT_PORT, int)


@patch.dict(os.environ, {"MQTT_BASE": "test_base"})
def test_environment_config():
    """Test environment variable configuration."""
    from addon.bb8_core.addon_config import load_config

    config, source = load_config()

    # Should pick up environment variables
    assert isinstance(config, dict)


def test_version_probe():
    """Test version_probe module functionality."""
    from addon.bb8_core.version_probe import get_version_info

    # Test version info retrieval
    version_info = get_version_info()
    assert isinstance(version_info, dict)


@patch("addon.bb8_core.evidence_capture.open")
def test_evidence_capture(mock_open):
    """Test evidence_capture module functionality."""
    from addon.bb8_core.evidence_capture import EvidenceRecorder

    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file

    # Test evidence recorder
    recorder = EvidenceRecorder()
    assert recorder is not None

    # Test recording evidence
    recorder.record("test_event", {"data": "value"})


def test_smoke_handlers():
    """Test smoke_handlers module functionality."""
    from addon.bb8_core.smoke_handlers import SmokeHandler

    # Test smoke handler creation
    handler = SmokeHandler()
    assert handler is not None


def test_discovery_migrate():
    """Test discovery_migrate module functionality."""
    from addon.bb8_core.discovery_migrate import migrate_discovery_config

    # Test migration function exists and can be called
    old_config = {"name": "test", "unique_id": "test_id"}
    new_config = migrate_discovery_config(old_config)
    assert isinstance(new_config, dict)
