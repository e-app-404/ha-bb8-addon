"""
Integration tests for BLE session layer.

Tests connection handling, retry logic, timeouts, and error conditions
with mocked spherov2 and bleak components.
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

# Provide a BB8 stub when spherov2 is not installed to allow isinstance checks
try:  # pragma: no cover - environment dependent
    from spherov2.toy.bb8 import BB8  # type: ignore
except Exception:  # noqa: BLE001

    class BB8:  # type: ignore
        pass


from addon.bb8_core.ble_session import (
    BleSession,
    BleSessionError,
    ConnectionError,
    DeviceNotConnectedError,
    ValidationError,
)


class TestBleSessionConnection:
    """Test BLE session connection logic."""

    @pytest.fixture
    def mock_bb8_toy(self):
        """Mock BB8 toy instance."""
        toy = MagicMock()
        toy.__enter__ = MagicMock(return_value=toy)
        toy.__exit__ = MagicMock(return_value=None)
        toy.set_main_led = MagicMock()
        return toy

    @pytest.fixture
    def mock_find_toys(self, mock_bb8_toy):
        """Mock spherov2 find_toys function."""
        mock_bb8_toy.__class__ = BB8
        with patch("addon.bb8_core.ble_session.find_toys") as mock:
            mock.return_value = [mock_bb8_toy]
            yield mock

    @pytest.fixture
    def ble_session(self):
        """Create BLE session instance."""
        return BleSession("AA:BB:CC:DD:EE:FF")

    @pytest.mark.asyncio
    async def test_connect_success_with_mac(
        self, ble_session, mock_find_toys, mock_bb8_toy
    ):
        """Test successful connection with provided MAC."""
        with patch("addon.bb8_core.ble_session.BB8") as mock_bb8_class:
            mock_bb8_class.return_value = mock_bb8_toy

            start_time = time.time()
            await ble_session.connect()
            connect_time = time.time() - start_time

            assert ble_session.is_connected()
            assert ble_session._connect_attempts == 1
            assert ble_session._last_connect_time < 5.0  # Should be fast in mock
            mock_find_toys.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_timeout(self, ble_session, mock_find_toys):
        """Test connection timeout handling."""

        # Mock slow connection
        async def slow_enter():
            await asyncio.sleep(6)  # Longer than 5s timeout

        mock_toy = MagicMock()
        mock_toy.__enter__ = slow_enter

        with patch("addon.bb8_core.ble_session.BB8") as mock_bb8_class:
            mock_bb8_class.return_value = mock_toy

            with pytest.raises(ConnectionError, match="Connection timeout"):
                await ble_session.connect()

            assert not ble_session.is_connected()

    @pytest.mark.asyncio
    async def test_connect_retry_logic(self, ble_session, mock_find_toys, mock_bb8_toy):
        """Test retry logic with backoff."""
        connect_attempts = []

        def track_connect():
            connect_attempts.append(time.time())
            if len(connect_attempts) == 1:
                raise Exception("First attempt fails")
            return mock_bb8_toy

        with patch("addon.bb8_core.ble_session.BB8", side_effect=track_connect):
            await ble_session.connect()

        assert len(connect_attempts) == 2
        assert ble_session._connect_attempts == 2

        # Check backoff delay (should be at least 0.4s * 0.8 = 0.32s)
        delay = connect_attempts[1] - connect_attempts[0]
        assert delay >= 0.3

    @pytest.mark.asyncio
    async def test_connect_max_attempts(self, ble_session, mock_find_toys):
        """Test connection fails after max attempts."""
        with patch(
            "addon.bb8_core.ble_session.BB8",
            side_effect=Exception("Always fails"),
        ):
            with pytest.raises(
                ConnectionError, match="Failed to connect after 2 attempts"
            ):
                await ble_session.connect()

            assert not ble_session.is_connected()

    @pytest.mark.asyncio
    async def test_auto_discovery(self, mock_find_toys, mock_bb8_toy):
        """Test auto-discovery when no MAC provided."""
        # Mock toy with address attribute
        mock_bb8_toy.address = "AA:BB:CC:DD:EE:FF"

        session = BleSession(None)  # No MAC provided

        with patch("addon.bb8_core.ble_session.BB8") as mock_bb8_class:
            mock_bb8_class.return_value = mock_bb8_toy

            await session.connect()

            assert session.is_connected()
            assert session._target_mac == "AA:BB:CC:DD:EE:FF"


class TestBleSessionOperations:
    """Test BLE session operations."""

    @pytest.fixture
    async def connected_session(self, mock_find_toys, mock_bb8_toy):
        """Create connected BLE session."""
        session = BleSession("AA:BB:CC:DD:EE:FF")

        with patch("addon.bb8_core.ble_session.BB8") as mock_bb8_class:
            mock_bb8_class.return_value = mock_bb8_toy
            await session.connect()

        return session, mock_bb8_toy

    @pytest.mark.asyncio
    async def test_wake_success(self, connected_session):
        """Test successful wake operation."""
        session, mock_toy = connected_session

        await session.wake()

        # Should call LED commands for wake indication
        assert mock_toy.set_main_led.call_count >= 2

    @pytest.mark.asyncio
    async def test_wake_not_connected(self):
        """Test wake fails when not connected."""
        session = BleSession("AA:BB:CC:DD:EE:FF")

        with pytest.raises(DeviceNotConnectedError):
            await session.wake()

    @pytest.mark.asyncio
    async def test_sleep_success(self, connected_session):
        """Test successful sleep operation."""
        session, mock_toy = connected_session

        with patch.object(session, "_disconnect") as mock_disconnect:
            await session.sleep()

        # Should call LED fade and disconnect
        assert mock_toy.set_main_led.call_count >= 4  # Fade steps
        mock_disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_battery_success(self, connected_session):
        """Test battery reading."""
        session, mock_toy = connected_session

        battery_pct = await session.battery()

        # Should return default value (simplified implementation)
        assert isinstance(battery_pct, int)
        assert 0 <= battery_pct <= 100

    @pytest.mark.asyncio
    async def test_battery_not_connected(self):
        """Test battery reading when not connected."""
        session = BleSession("AA:BB:CC:DD:EE:FF")

        with pytest.raises(DeviceNotConnectedError):
            await session.battery()

    @pytest.mark.asyncio
    async def test_set_led_validation(self, connected_session):
        """Test LED color validation."""
        session, mock_toy = connected_session

        # Valid colors
        await session.set_led(255, 128, 0)
        mock_toy.set_main_led.assert_called_with(255, 128, 0, None)

        # Test clamping
        await session.set_led(300, -10, 0)
        mock_toy.set_main_led.assert_called_with(255, 0, 0, None)

        # Invalid types
        with pytest.raises(ValidationError):
            await session.set_led("red", "green", "blue")

    @pytest.mark.asyncio
    async def test_roll_validation(self, connected_session):
        """Test roll parameter validation."""
        session, mock_toy = connected_session

        # Valid roll (uses LED indication in simplified implementation)
        await session.roll(100, 90, 1000)

        # Test clamping
        await session.roll(300, 450, 6000)  # Should clamp speed and wrap heading

        # Invalid types
        with pytest.raises(ValidationError):
            await session.roll("fast", "north", "long")

    @pytest.mark.asyncio
    async def test_stop_success(self, connected_session):
        """Test stop operation."""
        session, mock_toy = connected_session

        await session.stop()

        # Should call LED indication for stop
        mock_toy.set_main_led.assert_called()

    @pytest.mark.asyncio
    async def test_operation_retry_logic(self, connected_session):
        """Test retry logic for operations."""
        session, mock_toy = connected_session

        # Mock LED to fail first time
        call_count = 0

        def failing_led(*args):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First call fails")

        mock_toy.set_main_led.side_effect = failing_led

        await session.set_led(255, 0, 0)

        # Should retry and succeed
        assert call_count == 2


class TestBleSessionMetrics:
    """Test BLE session metrics and monitoring."""

    @pytest.mark.asyncio
    async def test_connection_metrics(self, mock_find_toys, mock_bb8_toy):
        """Test connection metrics collection."""
        session = BleSession("AA:BB:CC:DD:EE:FF")

        with patch("addon.bb8_core.ble_session.BB8") as mock_bb8_class:
            mock_bb8_class.return_value = mock_bb8_toy

            # Test initial metrics
            metrics = session.get_connection_metrics()
            assert metrics["connected"] is False
            assert metrics["connect_attempts"] == 0

            # Connect and check metrics
            await session.connect()

            metrics = session.get_connection_metrics()
            assert metrics["connected"] is True
            assert metrics["connect_attempts"] == 1
            assert metrics["last_connect_time"] > 0
            assert metrics["target_mac"] == "AA:BB:CC:DD:EE:FF"

    @pytest.mark.asyncio
    async def test_connect_timing(self, mock_find_toys, mock_bb8_toy):
        """Test connection timing is captured correctly."""
        session = BleSession("AA:BB:CC:DD:EE:FF")

        # Mock slow connection
        async def slow_enter():
            await asyncio.sleep(0.1)  # 100ms delay
            return mock_bb8_toy

        with patch("addon.bb8_core.ble_session.BB8") as mock_bb8_class:
            mock_bb8_class.return_value = mock_bb8_toy

            # Mock asyncio.to_thread to simulate connection time
            with patch("asyncio.to_thread", side_effect=slow_enter):
                start_time = time.time()
                await session.connect()
                actual_time = time.time() - start_time

                metrics = session.get_connection_metrics()
                # Should capture timing (allowing some variance)
                assert 0.05 <= metrics["last_connect_time"] <= actual_time + 0.05


@pytest.mark.integration
class TestBleSessionIntegration:
    """Integration tests that test full workflows."""

    @pytest.mark.asyncio
    async def test_full_connect_wake_sleep_cycle(self, mock_find_toys, mock_bb8_toy):
        """Test complete connect->wake->sleep cycle."""
        session = BleSession("AA:BB:CC:DD:EE:FF")

        with patch("addon.bb8_core.ble_session.BB8") as mock_bb8_class:
            mock_bb8_class.return_value = mock_bb8_toy

            # Full cycle
            start_time = time.time()

            # Connect
            await session.connect()
            assert session.is_connected()

            # Wake
            await session.wake()

            # Get battery
            battery = await session.battery()
            assert 0 <= battery <= 100

            # Sleep
            with patch.object(session, "_disconnect"):
                await session.sleep()

            cycle_time = time.time() - start_time

            # Should complete in reasonable time
            assert cycle_time < 5.0

            # Check metrics
            metrics = session.get_connection_metrics()
            assert metrics["last_connect_time"] < 5.0

    @pytest.mark.asyncio
    async def test_error_handling_preserves_state(self, mock_find_toys, mock_bb8_toy):
        """Test that errors don't corrupt session state."""
        session = BleSession("AA:BB:CC:DD:EE:FF")

        # Connect successfully
        with patch("addon.bb8_core.ble_session.BB8") as mock_bb8_class:
            mock_bb8_class.return_value = mock_bb8_toy
            await session.connect()

        assert session.is_connected()

        # Cause operation to fail
        mock_bb8_toy.set_main_led.side_effect = Exception("Device error")

        with pytest.raises(BleSessionError):
            await session.set_led(255, 0, 0)

        # Session should still report connected
        assert session.is_connected()

        # Metrics should be preserved
        metrics = session.get_connection_metrics()
        assert metrics["connected"] is True
