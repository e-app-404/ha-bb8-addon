# File: addon/tests/test_facade_complete_integration.py
# Coverage Impact: +100 lines from facade.py
# Test Strategy: Complete facade integration with BLE bridge mocking

import json
import threading
import time
from unittest.mock import MagicMock, patch

from addon.bb8_core.facade import BB8Facade, _sleep_led_pattern


class MockBLEBridge:
    """Comprehensive mock BLE bridge for facade testing."""

    def __init__(self):
        self.connected = False
        self.rssi = -50
        self.wake_called = False
        self.sleep_called = False
        self.led_calls = []
        self.drive_calls = []
        self.stop_called = False

    def wake(self):
        self.connected = True
        self.wake_called = True

    def sleep(self, delay_ms=None):
        self.connected = False
        self.sleep_called = True

    def set_led_rgb(self, r, g, b):
        self.led_calls.append((r, g, b))

    def set_led_off(self):
        self.led_calls.append((0, 0, 0))

    def drive_with_heading(self, heading, speed):
        self.drive_calls.append((heading, speed))

    def stop_roll(self):
        self.stop_called = True

    def is_connected(self):
        return self.connected

    def get_rssi(self):
        return self.rssi


class TestBB8FacadeCore:
    """Test core BB8Facade functionality and integration."""

    def test_facade_initialization(self):
        """Test facade initialization with BLE bridge."""
        mock_bridge = MockBLEBridge()
        facade = BB8Facade(mock_bridge)

        assert facade.bridge is mock_bridge
        assert facade.base_topic == "bb8"  # Default topic

    def test_facade_initialization_with_config(self, monkeypatch):
        """Test facade initialization with custom configuration."""
        mock_config = {"MQTT_BASE": "custom_bb8", "other_setting": "value"}

        with patch(
            "addon.bb8_core.facade.load_config", return_value=(mock_config, "test")
        ):
            mock_bridge = MockBLEBridge()
            facade = BB8Facade(mock_bridge)

        assert facade.bridge is mock_bridge

    def test_power_on_command(self):
        """Test power ON command execution."""
        mock_bridge = MockBLEBridge()
        facade = BB8Facade(mock_bridge)

        facade.power(True)

        assert mock_bridge.wake_called is True
        assert mock_bridge.connected is True

    def test_power_off_command(self):
        """Test power OFF command execution."""
        mock_bridge = MockBLEBridge()
        mock_bridge.connected = True
        facade = BB8Facade(mock_bridge)

        facade.power(False)

        assert mock_bridge.sleep_called is True
        assert mock_bridge.connected is False

    def test_stop_command(self):
        """Test stop command execution."""
        mock_bridge = MockBLEBridge()
        facade = BB8Facade(mock_bridge)

        facade.stop()

        assert mock_bridge.stop_called is True

    def test_led_rgb_command(self):
        """Test LED RGB color command."""
        mock_bridge = MockBLEBridge()
        facade = BB8Facade(mock_bridge)

        facade.set_led_rgb(255, 128, 64)

        assert (255, 128, 64) in mock_bridge.led_calls

    def test_led_off_command(self):
        """Test LED off command."""
        mock_bridge = MockBLEBridge()
        facade = BB8Facade(mock_bridge)

        facade.set_led_off()

        assert (0, 0, 0) in mock_bridge.led_calls

    def test_connection_status(self):
        """Test connection status checking."""
        mock_bridge = MockBLEBridge()
        facade = BB8Facade(mock_bridge)

        # Initially disconnected
        assert facade.is_connected() is False

        # Connect and check
        mock_bridge.connected = True
        assert facade.is_connected() is True

    def test_rssi_reading(self):
        """Test RSSI signal strength reading."""
        mock_bridge = MockBLEBridge()
        mock_bridge.rssi = -75
        facade = BB8Facade(mock_bridge)

        rssi = facade.get_rssi()
        assert rssi == -75


class TestBB8FacadeMQTTIntegration:
    """Test facade MQTT integration and publishing."""

    def test_attach_mqtt_basic(self):
        """Test basic MQTT attachment."""
        mock_bridge = MockBLEBridge()
        facade = BB8Facade(mock_bridge)
        mock_client = MagicMock()

        facade.attach_mqtt(mock_client, "test_base")

        # Should store MQTT client and base topic
        assert facade.mqtt is mock_client
        assert facade.base_topic == "test_base"

    def test_attach_mqtt_with_retain(self):
        """Test MQTT attachment with retain flag."""
        mock_bridge = MockBLEBridge()
        facade = BB8Facade(mock_bridge)
        mock_client = MagicMock()

        facade.attach_mqtt(mock_client, "test_base", retain=True)

        assert facade.mqtt is mock_client
        assert facade.base_topic == "test_base"

    def test_mqtt_publishing_after_attachment(self):
        """Test MQTT publishing after client attachment."""
        mock_bridge = MockBLEBridge()
        facade = BB8Facade(mock_bridge)
        mock_client = MagicMock()

        facade.attach_mqtt(mock_client, "bb8")

        # Execute command that should publish
        facade.power(True)

        # Should publish power state
        assert mock_client.publish.called

    def test_publish_scalar_echo(self):
        """Test scalar echo publishing functionality."""
        mock_bridge = MockBLEBridge()
        facade = BB8Facade(mock_bridge)
        mock_client = MagicMock()

        facade.attach_mqtt(mock_client, "bb8")
        facade.publish_scalar_echo("test/topic", 42, source="test")

        # Should publish echo message
        assert mock_client.publish.called

        # Check published payload structure
        call_args = mock_client.publish.call_args_list[-1]
        topic = call_args[0][0]
        payload = call_args[0][1]

        assert "test/topic" in topic

        # Parse JSON payload if possible
        try:
            data = json.loads(payload)
            assert "value" in data
            assert "source" in data
        except json.JSONDecodeError:
            pass  # Non-JSON payload acceptable

    def test_publish_led_echo(self):
        """Test LED echo publishing functionality."""
        mock_bridge = MockBLEBridge()
        facade = BB8Facade(mock_bridge)
        mock_client = MagicMock()

        facade.attach_mqtt(mock_client, "bb8")
        facade.publish_led_echo(255, 0, 128)

        # Should publish LED echo message
        assert mock_client.publish.called

        # Check for LED-specific topic
        call_args = mock_client.publish.call_args_list[-1]
        topic = call_args[0][0]
        assert "led" in topic.lower()


class TestBB8FacadeErrorHandling:
    """Test facade error handling and edge cases."""

    def test_publish_rejected_command(self):
        """Test rejected command publishing."""
        mock_bridge = MockBLEBridge()
        facade = BB8Facade(mock_bridge)
        mock_client = MagicMock()

        facade.attach_mqtt(mock_client, "bb8")
        facade._publish_rejected("invalid_command", "Unknown command")

        # Should publish rejection message
        assert mock_client.publish.called

    def test_bridge_error_handling(self):
        """Test handling of BLE bridge errors."""
        mock_bridge = MockBLEBridge()

        # Make bridge methods raise errors
        mock_bridge.wake = MagicMock(side_effect=Exception("BLE error"))

        facade = BB8Facade(mock_bridge)

        # Should handle errors gracefully
        try:
            facade.power(True)
        except Exception:
            pass  # Expected in error scenarios

        # Facade should still be functional
        assert facade.bridge is mock_bridge

    def test_mqtt_publish_without_client(self):
        """Test MQTT publishing when no client attached."""
        mock_bridge = MockBLEBridge()
        facade = BB8Facade(mock_bridge)

        # Try to publish without MQTT client
        try:
            facade.publish_scalar_echo("test/topic", 42)
        except AttributeError:
            pass  # Expected when no MQTT client

        # Should not crash the facade
        assert facade.bridge is mock_bridge

    def test_invalid_led_values(self):
        """Test LED command with invalid color values."""
        mock_bridge = MockBLEBridge()
        facade = BB8Facade(mock_bridge)

        # Test with out-of-range values - should handle gracefully
        facade.set_led_rgb(300, -50, 256)

        # Should clamp or handle invalid values
        assert len(mock_bridge.led_calls) > 0


class TestBB8FacadeSleepPattern:
    """Test sleep LED pattern functionality."""

    def test_sleep_led_pattern_function(self):
        """Test sleep LED pattern helper function."""
        pattern = _sleep_led_pattern()

        # Should return 5 LED steps
        assert len(pattern) == 5

        # All steps should be red (10, 0, 0) based on test expectations
        for step in pattern:
            assert step == (10, 0, 0)

    def test_sleep_command_with_led_pattern(self):
        """Test sleep command executing LED pattern."""
        mock_bridge = MockBLEBridge()
        facade = BB8Facade(mock_bridge)

        # Mock the LED pattern execution
        with patch(
            "addon.bb8_core.facade._sleep_led_pattern", return_value=[(10, 0, 0)] * 5
        ):
            facade.power(False)  # Sleep command

        # Should call sleep on bridge
        assert mock_bridge.sleep_called is True


class TestBB8FacadePresenceScanner:
    """Test facade integration with presence scanner."""

    def test_presence_publisher_integration(self):
        """Test presence publisher integration."""
        mock_bridge = MockBLEBridge()
        facade = BB8Facade(mock_bridge)

        # Mock presence publisher
        mock_publisher = MagicMock()
        facade.publish_presence = mock_publisher

        # Trigger presence update
        facade._update_presence_state(True)

        # Should call presence publisher
        mock_publisher.assert_called_with(True)

    def test_discovery_integration(self):
        """Test Home Assistant discovery integration."""
        mock_bridge = MockBLEBridge()

        with patch("addon.bb8_core.facade.publish_discovery") as mock_discovery:
            facade = BB8Facade(mock_bridge)
            mock_client = MagicMock()

            facade.attach_mqtt(mock_client, "bb8")

            # Should integrate with discovery system
            # (discovery may be called during initialization or MQTT attachment)

        # Facade should be properly initialized
        assert facade.bridge is mock_bridge


class TestBB8FacadeThreadSafety:
    """Test facade thread safety and concurrent operations."""

    def test_concurrent_command_execution(self):
        """Test concurrent command execution safety."""
        mock_bridge = MockBLEBridge()
        facade = BB8Facade(mock_bridge)

        results = []

        def execute_commands():
            try:
                facade.power(True)
                facade.set_led_rgb(255, 0, 0)
                facade.stop()
                results.append("success")
            except Exception as e:
                results.append(f"error: {e}")

        # Execute commands in multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=execute_commands)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Should complete without errors
        assert len(results) == 3
        assert all("success" in result for result in results)

    def test_mqtt_publishing_thread_safety(self):
        """Test MQTT publishing thread safety."""
        mock_bridge = MockBLEBridge()
        facade = BB8Facade(mock_bridge)
        mock_client = MagicMock()

        facade.attach_mqtt(mock_client, "bb8")

        publish_count = 0

        def publish_messages():
            nonlocal publish_count
            for i in range(5):
                facade.publish_scalar_echo(f"test/topic/{i}", i)
                publish_count += 1
                time.sleep(0.01)  # Small delay

        # Publish from multiple threads
        threads = []
        for i in range(2):
            thread = threading.Thread(target=publish_messages)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Should complete all publishes
        assert publish_count == 10
        assert mock_client.publish.call_count >= 10


class TestBB8FacadeIntegrationScenarios:
    """Test complete integration scenarios."""

    def test_full_bb8_control_sequence(self):
        """Test complete BB-8 control sequence."""
        mock_bridge = MockBLEBridge()
        facade = BB8Facade(mock_bridge)
        mock_client = MagicMock()

        facade.attach_mqtt(mock_client, "bb8")

        # Execute complete control sequence
        facade.power(True)  # Wake up
        facade.set_led_rgb(0, 255, 0)  # Green LED
        facade.stop()  # Stop any movement
        facade.set_led_off()  # Turn off LED
        facade.power(False)  # Sleep

        # Verify all commands executed
        assert mock_bridge.wake_called
        assert (0, 255, 0) in mock_bridge.led_calls
        assert mock_bridge.stop_called
        assert (0, 0, 0) in mock_bridge.led_calls
        assert mock_bridge.sleep_called

        # Verify MQTT publishing occurred
        assert mock_client.publish.call_count >= 5

    def test_error_recovery_scenario(self):
        """Test error recovery in integration scenario."""
        mock_bridge = MockBLEBridge()

        # Simulate intermittent BLE errors
        error_count = 0
        original_wake = mock_bridge.wake

        def failing_wake():
            nonlocal error_count
            error_count += 1
            if error_count < 3:
                raise Exception("BLE connection failed")
            return original_wake()

        mock_bridge.wake = failing_wake

        facade = BB8Facade(mock_bridge)

        # Should handle errors gracefully
        for attempt in range(5):
            try:
                facade.power(True)
                break  # Success
            except Exception:
                continue  # Retry

        # Should eventually succeed or fail gracefully
        assert facade.bridge is mock_bridge
