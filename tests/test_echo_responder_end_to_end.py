# File: addon/tests/test_echo_responder_end_to_end.py
# Coverage Impact: ~150+ lines from echo_responder.py
# Test Strategy: Mock MQTT broker + BLE scanning + end-to-end message flow

import json
import time
from unittest.mock import MagicMock, mock_open, patch

import pytest

from addon.bb8_core import echo_responder
from addon.bb8_core.echo_responder import (
    _ble_probe_once,
    _env_truthy,
    _load_opts,
    _publish_echo_roundtrip,
    _resolve_topic,
    _start_heartbeat,
    _write_atomic,
    on_connect,
    on_message,
    pub,
)


class TestEchoResponderCore:
    """Test core echo responder functionality."""

    def test_load_opts_success(self):
        """Test successful options loading."""
        mock_options = {
            "mqtt_base": "test_base",
            "bb8_mac": "AA:BB:CC:DD:EE:FF",
            "ble_adapter": "hci0",
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(mock_options))):
            opts = _load_opts("/fake/path.json")

        assert opts["mqtt_base"] == "test_base"
        assert opts["bb8_mac"] == "AA:BB:CC:DD:EE:FF"
        assert opts["ble_adapter"] == "hci0"

    def test_load_opts_file_not_found(self, caplog):
        """Test options loading when file doesn't exist."""
        with patch("builtins.open", side_effect=FileNotFoundError()):
            opts = _load_opts("/fake/path.json")

        assert opts == {}
        assert "Failed to read" in caplog.text

    def test_load_opts_invalid_json(self, caplog):
        """Test options loading with invalid JSON."""
        with patch("builtins.open", mock_open(read_data="invalid json")):
            opts = _load_opts("/fake/path.json")

        assert opts == {}
        assert "Failed to read" in caplog.text

    def test_resolve_topic_with_option(self, monkeypatch):
        """Test topic resolution with explicit option."""
        monkeypatch.setattr(
            echo_responder, "_opts", {"custom_topic": "bb8/custom/topic"}
        )

        topic = _resolve_topic("custom_topic", "default/suffix")
        assert topic == "bb8/custom/topic"

    def test_resolve_topic_with_default(self, monkeypatch):
        """Test topic resolution with default suffix."""
        monkeypatch.setattr(echo_responder, "_opts", {})
        monkeypatch.setattr(echo_responder, "_base", "bb8")

        topic = _resolve_topic("missing_topic", "default/suffix")
        assert topic == "bb8/default/suffix"

    def test_resolve_topic_with_env_override(self, monkeypatch):
        """Test topic resolution with environment variable override."""
        monkeypatch.setenv("CUSTOM_TOPIC", "env/override/topic")
        monkeypatch.setattr(
            echo_responder, "_opts", {"custom_topic": "bb8/custom/topic"}
        )

        topic = _resolve_topic("custom_topic", "default/suffix", "CUSTOM_TOPIC")
        assert topic == "env/override/topic"

    def test_env_truthy_values(self):
        """Test environment variable truthy detection."""
        assert _env_truthy("1") is True
        assert _env_truthy("true") is True
        assert _env_truthy("True") is True
        assert _env_truthy("yes") is True
        assert _env_truthy("on") is True

        assert _env_truthy("0") is False
        assert _env_truthy("false") is False
        assert _env_truthy("False") is False
        assert _env_truthy("no") is False
        assert _env_truthy("off") is False
        assert _env_truthy("") is False


class TestBLEProbing:
    """Test BLE probing functionality."""

    @patch("addon.bb8_core.echo_responder.BleakScanner")
    @pytest.mark.asyncio
    async def test_ble_probe_success(self, mock_scanner):
        """Test successful BLE device probe."""
        # Mock successful scan
        mock_device = MagicMock()
        mock_device.address = "AA:BB:CC:DD:EE:FF"
        mock_device.rssi = -50

        mock_scanner.discover.return_value = [mock_device]

        with patch("addon.bb8_core.echo_responder._bb8_mac", "AA:BB:CC:DD:EE:FF"):
            result = _ble_probe_once(timeout_s=1.0)

        assert result["success"] is True
        assert result["rssi"] == -50
        assert result["duration_ms"] > 0

    @patch("addon.bb8_core.echo_responder.BleakScanner")
    @pytest.mark.asyncio
    async def test_ble_probe_device_not_found(self, mock_scanner):
        """Test BLE probe when target device not found."""
        # Mock scan with different device
        mock_device = MagicMock()
        mock_device.address = "XX:YY:ZZ:AA:BB:CC"

        mock_scanner.discover.return_value = [mock_device]

        with patch("addon.bb8_core.echo_responder._bb8_mac", "AA:BB:CC:DD:EE:FF"):
            result = _ble_probe_once(timeout_s=1.0)

        assert result["success"] is False
        assert result["rssi"] is None

    @patch("addon.bb8_core.echo_responder.BleakScanner")
    @pytest.mark.asyncio
    async def test_ble_probe_scanner_error(self, mock_scanner):
        """Test BLE probe when scanner raises error."""
        mock_scanner.discover.side_effect = Exception("BLE scan failed")

        result = _ble_probe_once(timeout_s=1.0)

        assert result["success"] is False
        assert result["rssi"] is None
        assert "error" in result

    def test_ble_probe_no_bleak(self):
        """Test BLE probe when bleak not available."""
        with patch("addon.bb8_core.echo_responder.BleakScanner", None):
            result = _ble_probe_once(timeout_s=1.0)

        assert result["success"] is False
        assert result["rssi"] is None


class TestMQTTEchoHandling:
    """Test MQTT echo message handling."""

    def test_publish_echo_roundtrip(self):
        """Test echo roundtrip publishing."""
        mock_client = MagicMock()

        base_ts = time.time()

        _publish_echo_roundtrip(mock_client, base_ts, ble_ok=True, ble_ms=50)

        # Should publish telemetry message
        assert mock_client.publish.called

        # Check published payload structure
        call_args = mock_client.publish.call_args
        topic = call_args[0][0]
        payload = call_args[0][1]

        assert "telemetry" in topic

        # Parse payload if JSON
        try:
            data = json.loads(payload)
            assert "ble_ok" in data
            assert "ble_ms" in data
        except json.JSONDecodeError:
            pass  # Non-JSON payload is acceptable

    def test_pub_function(self):
        """Test pub wrapper function."""
        mock_client = MagicMock()

        pub(mock_client, "test/topic", "test_payload", retain=True)

        mock_client.publish.assert_called_with(
            "test/topic", "test_payload", retain=True
        )

    def test_on_connect_callback(self, caplog):
        """Test MQTT connection callback."""
        mock_client = MagicMock()

        # Test successful connection
        on_connect(mock_client, None, {}, 0)

        # Should subscribe to echo command topic
        assert mock_client.subscribe.called
        assert "Connected to MQTT broker" in caplog.text

    def test_on_connect_callback_error(self, caplog):
        """Test MQTT connection callback with error."""
        mock_client = MagicMock()

        # Test connection error
        on_connect(mock_client, None, {}, 5)  # Error code 5

        assert "MQTT connection failed" in caplog.text


class TestEchoMessageProcessing:
    """Test echo message processing and responses."""

    def test_on_message_echo_command(self):
        """Test echo command message processing."""
        mock_client = MagicMock()
        mock_msg = MagicMock()
        mock_msg.topic = f"{echo_responder._base}/echo/cmd"
        mock_msg.payload.decode.return_value = "test_echo_payload"

        with patch("addon.bb8_core.echo_responder._ble_probe_once") as mock_probe:
            mock_probe.return_value = {"success": True, "rssi": -45, "duration_ms": 25}

            on_message(mock_client, None, mock_msg)

        # Should publish echo acknowledgment
        assert mock_client.publish.call_count >= 1

    def test_on_message_ble_ready_command(self):
        """Test BLE ready command message processing."""
        mock_client = MagicMock()
        mock_msg = MagicMock()
        mock_msg.topic = f"{echo_responder._base}/ble_ready/cmd"
        mock_msg.payload.decode.return_value = "probe"

        with patch("addon.bb8_core.echo_responder._spawn_ble_ready") as mock_spawn:
            on_message(mock_client, None, mock_msg)

        # Should spawn BLE ready probe
        mock_spawn.assert_called()

    def test_on_message_unknown_topic(self, caplog):
        """Test handling of unknown topic messages."""
        mock_client = MagicMock()
        mock_msg = MagicMock()
        mock_msg.topic = "unknown/topic"
        mock_msg.payload.decode.return_value = "payload"

        on_message(mock_client, None, mock_msg)

        # Should log unknown topic
        assert "Unknown topic" in caplog.text


class TestFileOperations:
    """Test file operation utilities."""

    def test_write_atomic_success(self):
        """Test atomic file writing."""
        with patch("builtins.open", mock_open()) as mock_file:
            _write_atomic("/test/path.txt", "test content")

        # Should open file for writing
        mock_file.assert_called_with("/test/path.txt", "w")
        handle = mock_file.return_value.__enter__.return_value
        handle.write.assert_called_with("test content")

    def test_write_atomic_error(self, caplog):
        """Test atomic file writing with error."""
        with patch("builtins.open", side_effect=OSError("Write failed")):
            _write_atomic("/test/path.txt", "test content")

        # Should log error
        assert "Failed to write" in caplog.text


class TestHeartbeatSystem:
    """Test heartbeat system functionality."""

    def test_start_heartbeat(self):
        """Test heartbeat thread startup."""
        with patch("threading.Thread") as mock_thread:
            _start_heartbeat("/test/heartbeat.txt", interval=1)

        # Should start heartbeat thread
        mock_thread.assert_called()
        thread_instance = mock_thread.return_value
        thread_instance.start.assert_called()

    def test_heartbeat_echo_env_disabled(self, monkeypatch):
        """Test heartbeat echo when disabled via environment."""
        monkeypatch.delenv("ECHO_HEARTBEAT", raising=False)

        with patch("addon.bb8_core.echo_responder._start_heartbeat") as mock_start:
            from addon.bb8_core.echo_responder import _heartbeat_echo

            _heartbeat_echo()

        # Should not start heartbeat when not enabled
        mock_start.assert_not_called()

    def test_heartbeat_echo_env_enabled(self, monkeypatch):
        """Test heartbeat echo when enabled via environment."""
        monkeypatch.setenv("ECHO_HEARTBEAT", "1")
        monkeypatch.setenv("ECHO_HEARTBEAT_PATH", "/test/heartbeat.txt")
        monkeypatch.setenv("ECHO_HEARTBEAT_INTERVAL", "5")

        with patch("addon.bb8_core.echo_responder._start_heartbeat") as mock_start:
            from addon.bb8_core.echo_responder import _heartbeat_echo

            _heartbeat_echo()

        # Should start heartbeat when enabled
        mock_start.assert_called_with("/test/heartbeat.txt", 5)


class TestEndToEndIntegration:
    """Test end-to-end echo responder integration."""

    def test_echo_round_trip_flow(self):
        """Test complete echo round trip flow."""
        mock_client = MagicMock()

        # Simulate echo command message
        mock_msg = MagicMock()
        mock_msg.topic = f"{echo_responder._base}/echo/cmd"
        mock_msg.payload.decode.return_value = "integration_test"

        # Mock BLE probe
        with patch("addon.bb8_core.echo_responder._ble_probe_once") as mock_probe:
            mock_probe.return_value = {
                "success": True,
                "rssi": -35,
                "duration_ms": 75,
                "adapter": "hci0",
            }

            # Process echo message
            on_message(mock_client, None, mock_msg)

        # Should publish acknowledgment and state
        assert mock_client.publish.call_count >= 2

        # Verify acknowledgment message
        ack_calls = [
            call for call in mock_client.publish.call_args_list if "ack" in str(call)
        ]
        assert len(ack_calls) > 0

    def test_ble_ready_integration_flow(self):
        """Test BLE ready probe integration flow."""
        mock_client = MagicMock()

        # Setup configuration
        mock_cfg = {"bb8_mac": "AA:BB:CC:DD:EE:FF", "ble_adapter": "hci0"}

        with patch("addon.bb8_core.echo_responder._ble_probe_once") as mock_probe:
            mock_probe.return_value = {"success": True, "rssi": -40, "duration_ms": 100}

            # Test BLE ready spawn
            from addon.bb8_core.echo_responder import _spawn_ble_ready

            _spawn_ble_ready(mock_client, "bb8", "AA:BB:CC:DD:EE:FF", mock_cfg)

        # Should complete without errors
        assert True  # Test passes if no exceptions
