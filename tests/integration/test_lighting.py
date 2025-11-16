"""Integration tests for lighting system with RGB clamping, cancellation, and estop interaction."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import time

from addon.bb8_core.lighting import LightingController


class TestLightingController:
    """Test lighting controller RGB clamping, cancellation, and estop interaction."""

    @pytest.fixture
    def mock_ble_session(self):
        """Mock BLE session for testing."""
        session = AsyncMock()
        session.is_connected = True
        return session

    @pytest.fixture
    def mock_toy(self):
        """Mock Spherov2 BB8 toy for LED commands."""
        toy = MagicMock()
        toy.set_led.return_value = None
        return toy

    @pytest.fixture
    def lighting_controller(self, mock_ble_session, mock_toy):
        """Create lighting controller with mocked dependencies."""
        controller = LightingController(mock_ble_session)
        controller._toy = mock_toy
        return controller

    @pytest.mark.asyncio
    async def test_rgb_clamping(self, lighting_controller, mock_toy):
        """Test RGB values are clamped to 0-255 range."""
        test_cases = [
            # (input_r, input_g, input_b, expected_r, expected_g, expected_b)
            (-10, 300, 128, 0, 255, 128),  # Negative and over 255
            (0, 0, 0, 0, 0, 0),  # Minimum values
            (255, 255, 255, 255, 255, 255),  # Maximum values
            (100, 150, 200, 100, 150, 200),  # Normal values
            (-1, 256, 127, 0, 255, 127),  # Edge cases
        ]

        for input_r, input_g, input_b, exp_r, exp_g, exp_b in test_cases:
            await lighting_controller.set_static(input_r, input_g, input_b)

            # Verify clamped values were passed to toy
            mock_toy.set_led.assert_called_with(exp_r, exp_g, exp_b)
            mock_toy.set_led.reset_mock()

    @pytest.mark.asyncio
    async def test_preset_definitions(self, lighting_controller):
        """Test that all required presets are defined."""
        required_presets = {"off", "white", "police", "sunset"}

        # Test preset existence
        for preset_name in required_presets:
            success = await lighting_controller.run_preset(preset_name)
            assert success, f"Preset '{preset_name}' should be available"

    @pytest.mark.asyncio
    async def test_invalid_preset(self, lighting_controller):
        """Test handling of invalid preset names."""
        invalid_presets = ["invalid", "nonexistent", "", None, 123]

        for invalid_preset in invalid_presets:
            success = await lighting_controller.run_preset(invalid_preset)
            assert not success, f"Invalid preset '{invalid_preset}' should fail"

    @pytest.mark.asyncio
    async def test_animation_cancellation_speed(self, lighting_controller, mock_toy):
        """Test that animations cancel within ≤100ms when new LED command issued."""
        # Start a long-running police preset (should run indefinitely)
        preset_task = asyncio.create_task(lighting_controller.run_preset("police"))

        # Let it run briefly
        await asyncio.sleep(0.01)

        # Cancel with new LED command and measure time
        start_time = time.time()
        await lighting_controller.set_static(255, 0, 0)  # Red
        cancel_time = time.time() - start_time

        # Verify cancellation was fast (≤100ms)
        assert cancel_time <= 0.1, (
            f"Cancellation took {cancel_time:.3f}s, should be ≤0.1s"
        )

        # Verify the cancellation stopped the preset
        await asyncio.sleep(0.01)
        assert preset_task.cancelled() or preset_task.done()

        # Verify final LED state is red
        mock_toy.set_led.assert_called_with(255, 0, 0)

    @pytest.mark.asyncio
    async def test_multiple_preset_cancellation(self, lighting_controller, mock_toy):
        """Test that starting new preset cancels previous one."""
        # Start sunset preset
        sunset_task = asyncio.create_task(lighting_controller.run_preset("sunset"))
        await asyncio.sleep(0.01)

        # Start police preset (should cancel sunset)
        start_time = time.time()
        police_task = asyncio.create_task(lighting_controller.run_preset("police"))
        await asyncio.sleep(0.01)
        cancel_time = time.time() - start_time

        # Verify fast cancellation
        assert cancel_time <= 0.1, f"Preset cancellation took {cancel_time:.3f}s"

        # Verify sunset was cancelled
        await asyncio.sleep(0.01)
        assert sunset_task.cancelled() or sunset_task.done()

        # Clean up
        lighting_controller.cancel_active()
        await asyncio.sleep(0.01)

    @pytest.mark.asyncio
    async def test_cancel_active_method(self, lighting_controller):
        """Test cancel_active() method stops all animations."""
        # Start multiple presets sequentially
        tasks = []
        for preset in ["police", "sunset"]:
            task = asyncio.create_task(lighting_controller.run_preset(preset))
            tasks.append(task)
            await asyncio.sleep(0.01)

        # Cancel all active animations
        start_time = time.time()
        lighting_controller.cancel_active()
        cancel_time = time.time() - start_time

        # Verify fast cancellation
        assert cancel_time <= 0.1, f"cancel_active() took {cancel_time:.3f}s"

        # Verify all tasks were cancelled
        await asyncio.sleep(0.01)
        for task in tasks:
            assert task.cancelled() or task.done()

    @pytest.mark.asyncio
    async def test_static_colors_during_estop(self, lighting_controller, mock_toy):
        """Test that static LED colors work during estop."""
        # Simulate estop condition by cancelling active animations
        lighting_controller.cancel_active()

        # Static colors should still work
        await lighting_controller.set_static(100, 150, 200)
        mock_toy.set_led.assert_called_with(100, 150, 200)

        # Test multiple static calls
        test_colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
        for r, g, b in test_colors:
            await lighting_controller.set_static(r, g, b)
            mock_toy.set_led.assert_called_with(r, g, b)

    @pytest.mark.asyncio
    async def test_estop_blocks_animated_presets(self, lighting_controller):
        """Test that animated presets are cancelled during estop."""
        # Start an animated preset
        preset_task = asyncio.create_task(lighting_controller.run_preset("police"))
        await asyncio.sleep(0.01)

        # Simulate estop by cancelling active animations
        start_time = time.time()
        lighting_controller.cancel_active()
        cancel_time = time.time() - start_time

        # Verify fast cancellation
        assert cancel_time <= 0.1, f"Estop cancellation took {cancel_time:.3f}s"

        # Verify preset was cancelled
        await asyncio.sleep(0.01)
        assert preset_task.cancelled() or preset_task.done()

    @pytest.mark.asyncio
    async def test_toy_disconnected_graceful_failure(
        self, lighting_controller, mock_ble_session
    ):
        """Test graceful handling when BLE toy is disconnected."""
        # Simulate disconnected state
        mock_ble_session.is_connected = False
        lighting_controller._toy = None

        # Static LED should fail gracefully (but not raise exceptions)
        await lighting_controller.set_static(255, 0, 0)

        # Preset should still return True (successful start) but not call hardware
        # The lighting system allows presets even when disconnected for logging/state
        success = await lighting_controller.run_preset("white")
        assert success, (
            "Preset should succeed even when disconnected (for state management)"
        )

    @pytest.mark.asyncio
    async def test_concurrent_led_commands(self, lighting_controller, mock_toy):
        """Test handling of concurrent LED commands."""
        # Start multiple LED commands concurrently
        tasks = [
            asyncio.create_task(lighting_controller.set_static(255, 0, 0)),
            asyncio.create_task(lighting_controller.set_static(0, 255, 0)),
            asyncio.create_task(lighting_controller.set_static(0, 0, 255)),
        ]

        # Wait for all to complete
        await asyncio.gather(*tasks)

        # Verify at least one LED command was made
        assert mock_toy.set_led.call_count >= 1, (
            "At least one LED command should execute"
        )

    @pytest.mark.asyncio
    async def test_preset_off_sets_black(self, lighting_controller, mock_toy):
        """Test that 'off' preset sets LED to black (0,0,0)."""
        success = await lighting_controller.run_preset("off")
        assert success

        # Wait for the preset task to complete
        await asyncio.sleep(0.01)

        # Should immediately set LED to black
        mock_toy.set_led.assert_called_with(0, 0, 0)

    @pytest.mark.asyncio
    async def test_preset_white_sets_white(self, lighting_controller, mock_toy):
        """Test that 'white' preset sets LED to white (255,255,255)."""
        success = await lighting_controller.run_preset("white")
        assert success

        # Wait for the preset task to complete
        await asyncio.sleep(0.01)

        # Should immediately set LED to white
        mock_toy.set_led.assert_called_with(255, 255, 255)
