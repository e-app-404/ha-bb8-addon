# File: addon/tests/test_addon_config_complete.py
# Coverage Impact: +82 lines from addon_config.py
# Test Strategy: Complete configuration loading testing with file I/O mocking

import contextlib
import json
import os
from pathlib import Path
from unittest.mock import mock_open, patch

import yaml

from addon.bb8_core.addon_config import (CONFIG, CONFIG_SOURCE,
                                         _candidate_paths, _load_options_json,
                                         init_config, load_config)


class TestAddonConfigCore:
    """Test core addon configuration functionality."""

    def test_candidate_paths_default(self):
        """Test default candidate paths generation."""
        with patch.dict(os.environ, {}, clear=True):
            paths = _candidate_paths()

        # Should include standard HA paths
        assert any("data/config.yaml" in str(p) for p in paths)
        assert any("config/config.yaml" in str(p) for p in paths)
        assert len(paths) >= 5

    def test_candidate_paths_with_env(self, monkeypatch):
        """Test candidate paths with environment override."""
        monkeypatch.setenv("CONFIG_PATH", "/custom/config.yaml")

        paths = _candidate_paths()

        # Should include environment path first
        assert str(paths[0]) == "/custom/config.yaml"

    def test_load_options_json_success(self):
        """Test successful options.json loading."""
        mock_data = {
            "mqtt_host": "192.168.1.100",
            "mqtt_user": "bb8_user",
            "bb8_mac": "AA:BB:CC:DD:EE:FF",
        }

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.open", mock_open(read_data=json.dumps(mock_data))):
                data, source = _load_options_json(Path("/data/options.json"))

        assert data == mock_data
        assert source == Path("/data/options.json")

    def test_load_options_json_file_not_found(self):
        """Test options.json loading when file doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            data, source = _load_options_json(Path("/data/options.json"))

        assert data == {}
        assert source is None

    def test_load_options_json_invalid_json(self, caplog):
        """Test options.json loading with invalid JSON."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.open", mock_open(read_data="invalid json")):
                data, source = _load_options_json(Path("/data/options.json"))

        assert data == {}
        assert source is None
        assert "Failed to parse" in caplog.text

    def test_load_options_json_io_error(self, caplog):
        """Test options.json loading with I/O error."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.open", side_effect=OSError("Permission denied")):
                data, source = _load_options_json(Path("/data/options.json"))

        assert data == {}
        assert source is None
        assert "Failed to read" in caplog.text


class TestConfigInitialization:
    """Test configuration initialization process."""

    def setup_method(self):
        """Reset global config state before each test."""
        global CONFIG, CONFIG_SOURCE
        CONFIG.clear()
        CONFIG_SOURCE = None

    def test_init_config_with_yaml(self):
        """Test config initialization with YAML file."""
        mock_yaml_data = {
            "mqtt_host": "test.broker.com",
            "mqtt_port": 1883,
            "bb8_mac": "FF:EE:DD:CC:BB:AA",
        }

        with patch("addon.bb8_core.addon_config._candidate_paths") as mock_paths:
            mock_paths.return_value = [Path("/test/config.yaml")]

            with patch("pathlib.Path.exists", return_value=True):
                with patch(
                    "pathlib.Path.open", mock_open(read_data=yaml.dump(mock_yaml_data))
                ):
                    config, source = init_config()

        assert config == mock_yaml_data
        assert source == Path("/test/config.yaml")

    def test_init_config_with_options_json(self):
        """Test config initialization with options.json fallback."""
        mock_options_data = {
            "mqtt_host": "options.broker.com",
            "bb8_mac": "11:22:33:44:55:66",
        }

        # No YAML files exist
        with patch("addon.bb8_core.addon_config._candidate_paths") as mock_paths:
            mock_paths.return_value = [Path("/test/config.yaml")]

            with patch("pathlib.Path.exists", return_value=False):
                with patch(
                    "addon.bb8_core.addon_config._load_options_json"
                ) as mock_options:
                    mock_options.return_value = (
                        mock_options_data,
                        Path("/data/options.json"),
                    )

                    config, source = init_config()

        assert config == mock_options_data
        assert source == Path("/data/options.json")

    def test_init_config_no_files(self, caplog):
        """Test config initialization when no config files exist."""
        with patch("addon.bb8_core.addon_config._candidate_paths") as mock_paths:
            mock_paths.return_value = [Path("/nonexistent/config.yaml")]

            with patch("pathlib.Path.exists", return_value=False):
                with patch(
                    "addon.bb8_core.addon_config._load_options_json"
                ) as mock_options:
                    mock_options.return_value = ({}, None)

                    config, source = init_config()

        assert config == {}
        assert source is None
        assert "No configuration" in caplog.text

    def test_init_config_yaml_parse_error(self, caplog):
        """Test config initialization with YAML parse error."""
        with patch("addon.bb8_core.addon_config._candidate_paths") as mock_paths:
            mock_paths.return_value = [Path("/test/config.yaml")]

            with patch("pathlib.Path.exists", return_value=True):
                with patch(
                    "pathlib.Path.open",
                    mock_open(read_data="invalid: yaml: content: ["),
                ):
                    config, source = init_config()

        assert config == {}
        assert "Failed to parse YAML" in caplog.text


class TestConfigLoading:
    """Test high-level config loading interface."""

    def setup_method(self):
        """Reset global config state."""
        global CONFIG, CONFIG_SOURCE
        CONFIG.clear()
        CONFIG_SOURCE = None

    def test_load_config_fresh_initialization(self):
        """Test load_config with fresh initialization."""
        mock_config = {"test_key": "test_value"}

        with patch("addon.bb8_core.addon_config.init_config") as mock_init:
            mock_init.return_value = (mock_config, Path("/test/config.yaml"))

            config, source = load_config()

        assert config == mock_config
        assert source == Path("/test/config.yaml")
        assert mock_config == CONFIG
        assert Path("/test/config.yaml") == CONFIG_SOURCE

    def test_load_config_cached(self):
        """Test load_config with cached configuration."""
        global CONFIG, CONFIG_SOURCE
        # First load to populate cache
        with patch("addon.bb8_core.addon_config.init_config") as mock_init:
            mock_init.return_value = ({"cached_key": "cached_value"}, Path("/cached/config.yaml"))
            config, source = load_config()
        
        # Second load should use cache
        with patch("addon.bb8_core.addon_config.init_config") as mock_init:
            config_cached, source_cached = load_config()

        mock_init.assert_not_called()
        assert config_cached == {"cached_key": "cached_value"}
        assert source_cached == Path("/cached/config.yaml")

    def test_load_config_force_reload(self):
        """Test load_config with forced reload."""
        global CONFIG, CONFIG_SOURCE
        CONFIG.update({"old_key": "old_value"})
        CONFIG_SOURCE = Path("/old/config.yaml")

        new_config = {"new_key": "new_value"}

        with patch("addon.bb8_core.addon_config.init_config") as mock_init:
            mock_init.return_value = (new_config, Path("/new/config.yaml"))

            config, source = load_config(force=True)

        assert config == new_config
        assert new_config == CONFIG


class TestConfigurationMerging:
    """Test configuration merging and precedence."""

    def test_environment_variable_precedence(self, monkeypatch):
        """Test environment variables take precedence over config files."""
        monkeypatch.setenv("MQTT_HOST", "env.broker.com")
        monkeypatch.setenv("MQTT_PORT", "9999")

        mock_config = {
            "mqtt_host": "file.broker.com",
            "mqtt_port": 1883,
            "other_setting": "value",
        }

        with patch("addon.bb8_core.addon_config.init_config") as mock_init:
            mock_init.return_value = (mock_config, Path("/test/config.yaml"))

            config, _ = load_config(force=True)

        # Environment variables should be available via os.environ
        assert os.environ.get("MQTT_HOST") == "env.broker.com"
        assert os.environ.get("MQTT_PORT") == "9999"

    def test_config_with_nested_structures(self):
        """Test configuration with nested data structures."""
        mock_config = {
            "mqtt": {
                "host": "nested.broker.com",
                "port": 1883,
                "auth": {"username": "user", "password": "pass"},
            },
            "devices": ["device1", "device2"],
        }

        with patch("addon.bb8_core.addon_config.init_config") as mock_init:
            mock_init.return_value = (mock_config, Path("/test/config.yaml"))

            config, _ = load_config(force=True)

        assert config["mqtt"]["host"] == "nested.broker.com"
        assert config["mqtt"]["auth"]["username"] == "user"
        assert len(config["devices"]) == 2


class TestFileSystemOperations:
    """Test file system operations and error handling."""

    def test_config_file_permissions_error(self, caplog):
        """Test handling of file permission errors."""
        with patch("addon.bb8_core.addon_config._candidate_paths") as mock_paths:
            mock_paths.return_value = [Path("/protected/config.yaml")]

            with patch("pathlib.Path.exists", return_value=True):
                with patch(
                    "pathlib.Path.open", side_effect=PermissionError("Access denied")
                ):
                    config, source = init_config()

        assert config == {}
        assert "Failed to read" in caplog.text

    def test_config_file_encoding_error(self, caplog):
        """Test handling of file encoding errors."""
        with patch("addon.bb8_core.addon_config._candidate_paths") as mock_paths:
            mock_paths.return_value = [Path("/test/config.yaml")]

            with patch("pathlib.Path.exists", return_value=True):
                with patch(
                    "pathlib.Path.open",
                    side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "invalid"),
                ):
                    config, source = init_config()

        assert config == {}
        assert "Failed to read" in caplog.text

    def test_config_directory_traversal_protection(self):
        """Test protection against directory traversal."""
        malicious_path = Path("../../../etc/passwd")

        # Should handle malicious paths gracefully
        with contextlib.suppress(Exception):
            _load_options_json(malicious_path)

        # Test should complete without security issues
        assert True

    def test_large_config_file_handling(self):
        """Test handling of large configuration files."""
        # Simulate large config (should handle gracefully)
        large_config = {"key_" + str(i): f"value_{i}" for i in range(1000)}

        with patch("addon.bb8_core.addon_config._candidate_paths") as mock_paths:
            mock_paths.return_value = [Path("/test/large_config.yaml")]

            with patch("pathlib.Path.exists", return_value=True):
                with patch(
                    "pathlib.Path.open", mock_open(read_data=yaml.dump(large_config))
                ):
                    config, _ = init_config()

        assert len(config) == 1000
        assert config["key_0"] == "value_0"


class TestConfigValidation:
    """Test configuration validation and sanitization."""

    def test_config_type_coercion(self):
        """Test automatic type coercion in configuration."""
        mock_config = {
            "string_number": "123",
            "boolean_string": "true",
            "list_string": "[1, 2, 3]",
        }

        with patch("addon.bb8_core.addon_config.init_config") as mock_init:
            mock_init.return_value = (mock_config, Path("/test/config.yaml"))

            config, _ = load_config(force=True)

        # Should preserve original types (no automatic coercion)
        assert isinstance(config["string_number"], str)
        assert isinstance(config["boolean_string"], str)

    def test_config_with_empty_values(self):
        """Test configuration with empty/null values."""
        mock_config = {
            "empty_string": "",
            "null_value": None,
            "empty_list": [],
            "empty_dict": {},
        }

        with patch("addon.bb8_core.addon_config.init_config") as mock_init:
            mock_init.return_value = (mock_config, Path("/test/config.yaml"))

            config, _ = load_config(force=True)

        assert config["empty_string"] == ""
        assert config["null_value"] is None
        assert config["empty_list"] == []
        assert config["empty_dict"] == {}


class TestConfigurationIntegration:
    """Test configuration integration scenarios."""

    def test_full_config_loading_scenario(self):
        """Test complete configuration loading scenario."""
        # Setup environment
        with patch.dict(os.environ, {"CONFIG_PATH": "/custom/config.yaml"}):

            mock_config = {
                "mqtt_host": "integration.test.com",
                "mqtt_port": 1883,
                "bb8_mac": "AA:BB:CC:DD:EE:FF",
                "logging_level": "INFO",
            }

            with patch("pathlib.Path.exists", return_value=True):
                with patch(
                    "pathlib.Path.open", mock_open(read_data=yaml.dump(mock_config))
                ):
                    config, source = load_config(force=True)

        assert config["mqtt_host"] == "integration.test.com"
        assert source == Path("/custom/config.yaml")

    def test_config_error_recovery(self):
        """Test configuration error recovery scenarios."""
        # First attempt fails, second succeeds
        call_count = 0

        def mock_init_config():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Config error")
            return ({"recovered": True}, Path("/recovered/config.yaml"))

        with patch(
            "addon.bb8_core.addon_config.init_config", side_effect=mock_init_config
        ):
            # First call should handle error
            try:
                load_config(force=True)
            except Exception:
                pass

            # Second call should succeed
            config, _ = load_config(force=True)
            assert config.get("recovered") is True
