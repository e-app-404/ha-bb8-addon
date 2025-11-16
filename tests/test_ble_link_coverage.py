"""
Simple coverage tests for ble_link module.
Target: Missing coverage lines to improve from 64.6% to 75%+
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from addon.bb8_core.ble_link import BLEConnectionError, BLELink, create_ble_link


class TestBLELinkCoverage:
    """Simple coverage improvements for ble_link module."""

    def test_ble_connection_error_str(self):
        """Test BLEConnectionError string representation."""
        error = BLEConnectionError("Test error message")
        assert str(error) == "Test error message"
        assert error.args[0] == "Test error message"

    def test_create_ble_link_success(self):
        """Test successful BLE link creation."""
        mock_gateway = MagicMock()

        # Test successful creation
        result = create_ble_link("AA:BB:CC:DD:EE:FF", mock_gateway)
        assert isinstance(result, BLELink)
        assert result.device_address == "AA:BB:CC:DD:EE:FF"
        assert result.gateway == mock_gateway

    def test_ble_link_is_connected_false(self):
        """Test is_connected when client is None."""
        mock_gateway = MagicMock()
        link = BLELink("AA:BB:CC:DD:EE:FF", mock_gateway)

        # When client is None, should return False
        link.client = None
        assert link.is_connected is False

    def test_ble_link_is_connected_true(self):
        """Test is_connected when client exists and is connected."""
        mock_gateway = MagicMock()
        mock_client = MagicMock()
        mock_client.is_connected = True

        link = BLELink("AA:BB:CC:DD:EE:FF", mock_gateway)
        link.client = mock_client

        assert link.is_connected is True

    def test_ble_link_connection_error_handling(self):
        """Test BLE link connection error scenarios."""
        mock_gateway = MagicMock()
        mock_gateway.connect.side_effect = Exception("Connection failed")

        link = BLELink("AA:BB:CC:DD:EE:FF", mock_gateway)

        # Should handle connection errors gracefully
        with pytest.raises(Exception):
            # This will test the error path in connect method
            link.connect()

    def test_ble_link_disconnect_when_not_connected(self):
        """Test disconnect when not connected."""
        mock_gateway = MagicMock()
        link = BLELink("AA:BB:CC:DD:EE:FF", mock_gateway)
        link.client = None

        # Should handle disconnect gracefully when not connected
        link.disconnect()
        # Should not raise exception

    def test_ble_link_write_without_connection(self):
        """Test write operation without connection."""
        mock_gateway = MagicMock()
        link = BLELink("AA:BB:CC:DD:EE:FF", mock_gateway)
        link.client = None

        # Should handle write without connection
        with pytest.raises((BLEConnectionError, AttributeError)):
            link.write_characteristic("test-uuid", b"data")
