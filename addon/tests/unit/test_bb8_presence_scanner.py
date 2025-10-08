"""
Unit tests for bb8_presence_scanner module functions.
Target: +322 lines coverage from 27.3%
"""

import logging
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add addon to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from addon.bb8_core.bb8_presence_scanner import (
    _clamp,
    _device_block,
    _parse_led_payload,
    log_config,
    make_base,
    make_device_id,
    read_version_or_default,
)


class TestVersionFunctions:
    """Unit tests for version-related functions."""
    
    def test_read_version_or_default_success(self):
        """Test reading version from file."""
        with patch('pathlib.Path.read_text') as mock_read:
            mock_read.return_value = "1.2.3\n"
            
            version = read_version_or_default()
            
            assert version == "1.2.3"
    
    def test_read_version_or_default_failure(self):
        """Test version fallback on file error."""
        with patch('pathlib.Path.read_text') as mock_read:
            mock_read.side_effect = FileNotFoundError()
            
            version = read_version_or_default()
            
            assert version == "addon:dev"
    
    def test_read_version_or_default_empty_file(self):
        """Test version fallback on empty file."""
        with patch('pathlib.Path.read_text') as mock_read:
            mock_read.return_value = ""
            
            version = read_version_or_default()
            
            assert version == "addon:dev"
    
    def test_read_version_custom_path(self):
        """Test reading version from custom path."""
        with patch('pathlib.Path.read_text') as mock_read:
            mock_read.return_value = "2.0.0"
            
            version = read_version_or_default("/custom/VERSION")
            
            assert version == "2.0.0"


class TestDeviceBlock:
    """Unit tests for device block creation."""
    
    def test_device_block_basic(self):
        """Test basic device block creation."""
        mac = "AA:BB:CC:DD:EE:FF"
        
        device_block = _device_block(mac)
        
        assert "identifiers" in device_block
        assert "connections" in device_block
        assert "manufacturer" in device_block
        assert device_block["manufacturer"] == "Sphero"
        assert ["mac", mac] in device_block["connections"]


class TestDeviceIdFunctions:
    """Unit tests for device ID functions."""
    
    def test_make_device_id_standard_mac(self):
        """Test device ID creation from MAC address."""
        mac = "AA:BB:CC:DD:EE:FF"
        
        device_id = make_device_id(mac)
        
        assert device_id is not None
        assert isinstance(device_id, str)
        assert len(device_id) > 0
    
    def test_make_base_from_device_id(self):
        """Test base topic creation from device ID."""
        device_id = "bb8_test_device"
        
        base = make_base(device_id)
        
        assert base is not None
        assert isinstance(base, str)
        assert len(base) > 0


class TestLogConfig:
    """Unit tests for log configuration."""
    
    def test_log_config_basic(self):
        """Test basic log configuration."""
        cfg = {"mqtt_broker": "localhost", "base_topic": "bb8"}
        src_path = "/test/config.json"
        mock_logger = Mock(spec=logging.Logger)
        
        # Should not raise exception
        log_config(cfg, src_path, mock_logger)
        
        # Should have called logger methods
        assert (mock_logger.info.called or mock_logger.debug.called or 
                mock_logger.warning.called)


class TestLedPayloadParsing:
    """Unit tests for LED payload parsing."""
    
    def test_parse_led_payload_rgb_string(self):
        """Test parsing RGB string payload."""
        payload = "255,128,0"
        
        result = _parse_led_payload(payload)
        
        assert result is not None
        
    def test_parse_led_payload_bytes(self):
        """Test parsing bytes payload."""
        payload = b"255,128,0"
        
        result = _parse_led_payload(payload)
        
        assert result is not None


class TestClampFunction:
    """Unit tests for clamp utility function."""
    
    def test_clamp_within_range(self):
        """Test clamping value within range."""
        result = _clamp(50, 0, 100)
        
        assert result == 50
    
    def test_clamp_below_minimum(self):
        """Test clamping value below minimum."""
        result = _clamp(-10, 0, 100)
        
        assert result == 0
    
    def test_clamp_above_maximum(self):
        """Test clamping value above maximum."""
        result = _clamp(150, 0, 100)
        
        assert result == 100
    
    def test_clamp_edge_cases(self):
        """Test clamping edge cases."""
        # At minimum
        assert _clamp(0, 0, 100) == 0
        
        # At maximum  
        assert _clamp(100, 0, 100) == 100
        
        # Single value range
        assert _clamp(50, 42, 42) == 42
    
    def test_clamp_negative_range(self):
        """Test clamping with negative range."""
        result = _clamp(-50, -100, -10)
        
        assert result == -50
        
        # Below range
        assert _clamp(-150, -100, -10) == -100
        
        # Above range
        assert _clamp(0, -100, -10) == -10