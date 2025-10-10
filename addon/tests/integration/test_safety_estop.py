"""
Integration tests for BB-8 safety features and emergency stop functionality.

Tests the safety layer, rate limiting, emergency stop, and telemetry features
to ensure proper motion safety controls are enforced.
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bb8_core.facade import BB8Facade
from bb8_core.safety import (
    MotionSafetyController,
    SafetyConfig,
    SafetyViolation,
)


class TestMotionSafetyController:
    """Test the core safety controller functionality."""
    
    def test_safety_config_from_env(self):
        """Test safety configuration loading from environment."""
        with patch.dict('os.environ', {
            'BB8_MIN_DRIVE_INTERVAL_MS': '75',
            'BB8_MAX_DRIVE_DURATION_MS': '3000',
            'BB8_MAX_DRIVE_SPEED': '200'
        }):
            config = SafetyConfig.from_env()
            assert config.min_drive_interval_ms == 75
            assert config.max_drive_duration_ms == 3000
            assert config.max_drive_speed == 200
            assert config.estop_latched is False
    
    def test_safety_config_defaults(self):
        """Test default safety configuration values."""
        config = SafetyConfig()
        assert config.min_drive_interval_ms == 50
        assert config.max_drive_duration_ms == 2000
        assert config.max_drive_speed == 180
        assert config.estop_latched is False
    
    def test_basic_drive_validation(self):
        """Test basic drive command validation with clamping."""
        controller = MotionSafetyController()
        controller.set_device_connected(True)
        
        # Valid command should pass through
        speed, heading, duration = controller.validate_drive_command(
            100, 90, 1500
        )
        assert speed == 100
        assert heading == 90
        assert duration == 1500
    
    def test_speed_clamping(self):
        """Test speed clamping to configured maximum."""
        config = SafetyConfig(max_drive_speed=150)
        controller = MotionSafetyController(config)
        controller.set_device_connected(True)
        
        # Speed should be clamped to max
        speed, heading, duration = controller.validate_drive_command(200, 90, 1000)
        assert speed == 150
        assert heading == 90
        assert duration == 1000
        
        # Negative speed should be clamped to 0
        speed, heading, duration = controller.validate_drive_command(-10, 90, 1000)
        assert speed == 0
    
    def test_duration_clamping(self):
        """Test duration clamping to configured maximum."""
        config = SafetyConfig(max_drive_duration_ms=1500)
        controller = MotionSafetyController(config)
        controller.set_device_connected(True)
        
        # Duration should be clamped to max
        speed, heading, duration = controller.validate_drive_command(100, 90, 3000)
        assert speed == 100
        assert heading == 90
        assert duration == 1500
        
        # None duration should default to max
        speed, heading, duration = controller.validate_drive_command(100, 90, None)
        assert duration == 1500
    
    def test_heading_wrapping(self):
        """Test heading wrapping to 0-359 range."""
        controller = MotionSafetyController()
        controller.set_device_connected(True)
        
        # Heading should wrap around
        speed, heading, duration = controller.validate_drive_command(100, 400, 1000)
        assert heading == 40  # 400 % 360
        
        speed, heading, duration = controller.validate_drive_command(100, -10, 1000)
        assert heading == 350  # -10 % 360
    
    def test_rate_limiting(self):
        """Test rate limiting enforcement."""
        config = SafetyConfig(min_drive_interval_ms=100)
        controller = MotionSafetyController(config)
        controller.set_device_connected(True)
        
        # First command should succeed
        controller.validate_drive_command(100, 90, 1000)
        
        # Immediate second command should fail rate limit
        with pytest.raises(SafetyViolation) as exc_info:
            controller.validate_drive_command(100, 90, 1000)
        
        assert exc_info.value.constraint == "rate_limit"
        assert "rate limit exceeded" in str(exc_info.value)
        
        # Wait for rate limit to expire
        time.sleep(0.11)  # 110ms > 100ms limit
        
        # Should succeed after waiting
        controller.validate_drive_command(100, 90, 1000)
    
    def test_device_offline_blocking(self):
        """Test that commands are blocked when device is offline."""
        controller = MotionSafetyController()
        controller.set_device_connected(False)
        
        with pytest.raises(SafetyViolation) as exc_info:
            controller.validate_drive_command(100, 90, 1000)
        
        assert exc_info.value.constraint == "device_offline"
        assert "not connected" in str(exc_info.value)
    
    def test_estop_activation_and_blocking(self):
        """Test emergency stop activation and motion blocking."""
        controller = MotionSafetyController()
        controller.set_device_connected(True)
        
        # Commands should work normally
        controller.validate_drive_command(100, 90, 1000)
        
        # Activate emergency stop
        controller.activate_estop("Test emergency stop")
        
        assert controller.is_estop_active()
        assert controller.get_estop_reason() == "Test emergency stop"
        
        # Commands should be blocked
        with pytest.raises(SafetyViolation) as exc_info:
            controller.validate_drive_command(100, 90, 1000)
        
        assert exc_info.value.constraint == "estop_active"
        assert "emergency stop" in str(exc_info.value)
    
    def test_estop_clear_when_safe(self):
        """Test emergency stop clearing when conditions are safe."""
        controller = MotionSafetyController()
        controller.set_device_connected(True)
        
        # Activate estop
        controller.activate_estop("Test emergency")
        assert controller.is_estop_active()
        
        # Should be able to clear when device is connected
        can_clear, reason = controller.can_clear_estop()
        assert can_clear
        assert "Safe to clear" in reason
        
        cleared, clear_reason = controller.clear_estop()
        assert cleared
        assert "Emergency stop cleared" in clear_reason
        assert not controller.is_estop_active()
        
        # Commands should work again
        controller.validate_drive_command(100, 90, 1000)
    
    def test_estop_clear_when_unsafe(self):
        """Test emergency stop clearing rejection when unsafe."""
        controller = MotionSafetyController()
        controller.set_device_connected(False)  # Device offline
        
        # Activate estop
        controller.activate_estop("Test emergency")
        
        # Should not be able to clear when device is offline
        can_clear, reason = controller.can_clear_estop()
        assert not can_clear
        assert "not connected" in reason
        
        cleared, clear_reason = controller.clear_estop()
        assert not cleared
        assert "not connected" in clear_reason
        assert controller.is_estop_active()  # Still active
    
    def test_multiple_estop_activation(self):
        """Test multiple estop activations don't interfere."""
        controller = MotionSafetyController()
        
        controller.activate_estop("First emergency")
        assert controller.get_estop_reason() == "First emergency"
        
        # Second activation should be logged but not change reason
        controller.activate_estop("Second emergency")
        assert controller.get_estop_reason() == "First emergency"
        assert controller.is_estop_active()
    
    @pytest.mark.asyncio
    async def test_auto_stop_scheduling(self):
        """Test automatic stop scheduling and cancellation."""
        controller = MotionSafetyController()
        
        stop_called = False
        async def mock_stop():
            nonlocal stop_called
            stop_called = True
        
        # Schedule auto-stop with short duration
        controller.schedule_auto_stop(100, mock_stop)  # 100ms
        
        # Should not have stopped yet
        assert not stop_called
        
        # Wait for auto-stop to trigger
        await asyncio.sleep(0.15)  # 150ms > 100ms
        assert stop_called
    
    @pytest.mark.asyncio
    async def test_auto_stop_cancellation(self):
        """Test automatic stop cancellation."""
        controller = MotionSafetyController()
        
        stop_called = False
        async def mock_stop():
            nonlocal stop_called
            stop_called = True
        
        # Schedule auto-stop
        controller.schedule_auto_stop(100, mock_stop)
        
        # Cancel before it triggers
        controller.cancel_auto_stop()
        
        # Wait past the original trigger time
        await asyncio.sleep(0.15)
        
        # Should not have been called
        assert not stop_called
    
    def test_safety_status_reporting(self):
        """Test safety status reporting for telemetry."""
        controller = MotionSafetyController()
        controller.set_device_connected(True)
        controller.activate_estop("Test status")
        
        status = controller.get_safety_status()
        
        assert status["estop_active"] is True
        assert status["estop_reason"] == "Test status"
        assert status["device_connected"] is True
        assert "last_drive_time" in status
        assert "config" in status
        assert status["config"]["min_interval_ms"] == 50
        assert status["config"]["max_duration_ms"] == 2000
        assert status["config"]["max_speed"] == 180


class TestFacadeSafetyIntegration:
    """Test safety integration with the BB8Facade."""
    
    @pytest.fixture
    def mock_facade(self):
        """Create a mock facade for testing."""
        facade = BB8Facade()
        facade._mqtt = {"client": MagicMock(), "base": "bb8", "qos": 1, "retain": True}
        
        # Mock BLE session
        mock_session = AsyncMock()
        mock_session.is_connected.return_value = True
        mock_session.roll = AsyncMock()
        mock_session.stop = AsyncMock()
        facade._ble_session = mock_session
        
        # Initialize safety controller
        facade._safety.set_device_connected(True)
        
        return facade
    
    def test_drive_command_validation(self, mock_facade):
        """Test that drive commands go through safety validation."""
        # Mock time to avoid rate limiting in test
        with patch('time.time', return_value=1000.0):
            # Valid command should work
            mock_facade.drive(100, 90, 1500)
            
            # Should have updated last command timestamp
            assert mock_facade._last_cmd_timestamp == 1000.0
    
    def test_drive_command_safety_violation(self, mock_facade):
        """Test drive command rejection on safety violations."""
        # Activate estop to trigger safety violation
        mock_facade._safety.activate_estop("Test block")
        
        # Drive command should be rejected
        mock_facade.drive(100, 90, 1500)
        
        # Should have published rejection
        mock_facade._mqtt["client"].publish.assert_called()
        call_args = mock_facade._mqtt["client"].publish.call_args
        assert "event/rejected" in call_args[0][0]
    
    def test_estop_activation(self, mock_facade):
        """Test emergency stop activation through facade."""
        mock_facade.estop("Test emergency")
        
        # Safety controller should have estop active
        assert mock_facade._safety.is_estop_active()
        assert mock_facade._safety.get_estop_reason() == "Test emergency"
    
    def test_estop_clear(self, mock_facade):
        """Test emergency stop clearing through facade."""
        # First activate estop
        mock_facade._safety.activate_estop("Test emergency")
        
        # Then clear it
        mock_facade.clear_estop()
        
        # Should be cleared
        assert not mock_facade._safety.is_estop_active()
    
    @pytest.mark.asyncio
    async def test_telemetry_publishing(self, mock_facade):
        """Test telemetry publishing functionality."""
        # Mock battery reading
        mock_facade._ble_session.battery = AsyncMock(return_value=75)
        
        # Mock time for consistent timestamps
        with patch('time.time', return_value=1000.0), \
             patch('time.gmtime', return_value=time.struct_time((2025, 10, 10, 12, 0, 0, 0, 0, 0))), \
             patch('time.strftime', return_value="2025-10-10T12:00:00.000000Z"):
            
            await mock_facade._publish_telemetry()
        
        # Should have published telemetry
        mock_facade._mqtt["client"].publish.assert_called()
        call_args = mock_facade._mqtt["client"].publish.call_args
        
        assert "status/telemetry" in call_args[0][0]
        
        # Parse published payload
        payload = json.loads(call_args[0][1])
        assert payload["connected"] is True
        assert payload["estop"] is False
        assert payload["battery_pct"] == 75
        assert "ts" in payload
    
    @pytest.mark.asyncio 
    async def test_telemetry_with_estop(self, mock_facade):
        """Test telemetry includes estop status."""
        # Activate estop
        mock_facade._safety.activate_estop("Test emergency")
        
        with patch('time.time', return_value=1000.0), \
             patch('time.gmtime', return_value=time.struct_time((2025, 10, 10, 12, 0, 0, 0, 0, 0))), \
             patch('time.strftime', return_value="2025-10-10T12:00:00.000000Z"):
            
            await mock_facade._publish_telemetry()
        
        # Parse published payload
        call_args = mock_facade._mqtt["client"].publish.call_args
        payload = json.loads(call_args[0][1])
        
        assert payload["estop"] is True


class TestRateLimitingBurstProtection:
    """Test rate limiting under burst command scenarios."""
    
    def test_burst_command_throttling(self):
        """Test that burst commands are properly throttled."""
        config = SafetyConfig(min_drive_interval_ms=50)
        controller = MotionSafetyController(config)
        controller.set_device_connected(True)
        
        success_count = 0
        violation_count = 0
        
        # Try to send 10 commands in rapid succession
        for i in range(10):
            try:
                controller.validate_drive_command(100, 90, 1000)
                success_count += 1
            except SafetyViolation as e:
                if e.constraint == "rate_limit":
                    violation_count += 1
                else:
                    raise  # Unexpected violation type
        
        # Should have 1 success and 9 rate limit violations
        assert success_count == 1
        assert violation_count == 9
    
    def test_rate_limit_recovery(self):
        """Test that rate limiting recovers after interval."""
        config = SafetyConfig(min_drive_interval_ms=50)
        controller = MotionSafetyController(config)
        controller.set_device_connected(True)
        
        # First command succeeds
        controller.validate_drive_command(100, 90, 1000)
        
        # Wait for rate limit to expire
        time.sleep(0.06)  # 60ms > 50ms limit
        
        # Second command should succeed
        controller.validate_drive_command(100, 90, 1000)


class TestSafetyConfigurability:
    """Test safety parameter configurability."""
    
    def test_configurable_speed_limit(self):
        """Test that speed limits are configurable."""
        # Test with different speed limits
        for max_speed in [100, 150, 200, 255]:
            config = SafetyConfig(max_drive_speed=max_speed)
            controller = MotionSafetyController(config)
            controller.set_device_connected(True)
            
            # Speed at limit should pass
            speed, _, _ = controller.validate_drive_command(max_speed, 90, 1000)
            assert speed == max_speed
            
            # Speed over limit should be clamped
            speed, _, _ = controller.validate_drive_command(max_speed + 50, 90, 1000)
            assert speed == max_speed
    
    def test_configurable_duration_limit(self):
        """Test that duration limits are configurable."""
        # Test with different duration limits
        for max_duration in [1000, 2000, 3000, 5000]:
            config = SafetyConfig(max_drive_duration_ms=max_duration)
            controller = MotionSafetyController(config)
            controller.set_device_connected(True)
            
            # Duration at limit should pass
            _, _, duration = controller.validate_drive_command(100, 90, max_duration)
            assert duration == max_duration
            
            # Duration over limit should be clamped
            _, _, duration = controller.validate_drive_command(100, 90, max_duration + 1000)
            assert duration == max_duration
    
    def test_configurable_rate_limit(self):
        """Test that rate limits are configurable."""
        # Test with different rate limits
        for min_interval in [25, 50, 100, 200]:
            config = SafetyConfig(min_drive_interval_ms=min_interval)
            controller = MotionSafetyController(config)
            controller.set_device_connected(True)
            
            # First command should succeed
            controller.validate_drive_command(100, 90, 1000)
            
            # Immediate second command should fail
            with pytest.raises(SafetyViolation) as exc_info:
                controller.validate_drive_command(100, 90, 1000)
            
            assert exc_info.value.constraint == "rate_limit"
            
            # Wait for interval and try again
            time.sleep((min_interval + 10) / 1000.0)  # Add 10ms buffer
            controller.validate_drive_command(100, 90, 1000)  # Should succeed