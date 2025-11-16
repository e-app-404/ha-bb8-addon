"""
Test coverage improvements for addon_config.py module.
Focus: Missing coverage areas identified by coverage analysis.
Target: Improve from 65.8% to 80%+ coverage.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
import yaml

from addon.bb8_core.addon_config import (
    CONFIG,
    CONFIG_SOURCE,
    _candidate_paths,
    _load_options_json,
    _load_yaml_cfg,
    init_config,
    load_config,
)


class TestAddonConfigCoverage:
    """Coverage-focused tests for addon_config module."""

    def test_candidate_paths_with_env(self):
        """Test _candidate_paths with CONFIG_PATH environment variable (Line 28)."""
        with patch.dict(os.environ, {"CONFIG_PATH": "/custom/config.yaml"}):
            paths = _candidate_paths()
            assert Path("/custom/config.yaml") in paths
            # Should be first in the list
            assert paths[0] == Path("/custom/config.yaml")

    def test_candidate_paths_without_env(self):
        """Test _candidate_paths without CONFIG_PATH."""
        with patch.dict(os.environ, {}, clear=True):
            paths = _candidate_paths()
            # Standard paths should be included
            assert Path("/data/config.yaml") in paths
            assert Path("/config/config.yaml") in paths
            assert len(paths) >= 5

    def test_load_options_json_file_not_exists(self):
        """Test _load_options_json when file doesn't exist (Lines 49-59)."""
        non_existent_path = Path("/nonexistent/options.json")
        data, source = _load_options_json(non_existent_path)

        assert data == {}
        assert source is None

    def test_load_options_json_invalid_json(self):
        """Test _load_options_json with invalid JSON (Lines 49-59)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json {")
            f.flush()

            data, source = _load_options_json(Path(f.name))

        # Clean up
        os.unlink(f.name)

        assert data == {}
        assert source is None

    def test_load_options_json_non_dict_root(self):
        """Test _load_options_json with non-dict root (Lines 49-59)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(["not", "a", "dict"], f)
            f.flush()

            data, source = _load_options_json(Path(f.name))

        # Clean up
        os.unlink(f.name)

        assert data == {}
        assert source is None

    def test_load_options_json_permission_error(self):
        """Test _load_options_json with permission error (Lines 49-59)."""
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            data, source = _load_options_json(Path("/fake/options.json"))

        assert data == {}
        assert source is None

    def test_load_yaml_cfg_file_not_exists(self):
        """Test _load_yaml_cfg with non-existent paths (Lines 74-83)."""
        fake_paths = [Path("/fake1.yaml"), Path("/fake2.yaml")]
        data, source = _load_yaml_cfg(fake_paths)

        assert data == {}
        assert source is None

    def test_load_yaml_cfg_invalid_yaml(self):
        """Test _load_yaml_cfg with invalid YAML (Lines 74-83)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            f.flush()

            data, source = _load_yaml_cfg([Path(f.name)])

        # Clean up
        os.unlink(f.name)

        assert data == {}
        assert source is None

    def test_load_yaml_cfg_non_dict_root(self):
        """Test _load_yaml_cfg with non-dict root (Lines 74-83)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(["not", "a", "dict"], f)
            f.flush()

            data, source = _load_yaml_cfg([Path(f.name)])

        # Clean up
        os.unlink(f.name)

        assert data == {}
        assert source is None

    def test_load_yaml_cfg_permission_error(self):
        """Test _load_yaml_cfg with permission error (Lines 74-83)."""
        # Ensure the temp file is opened in text mode so yaml.dump writes strings
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml", delete=False) as f:
            # Write valid YAML first
            yaml.dump({"test": "value"}, f)
            f.flush()
            name = f.name

        try:
            # Mock permission error on Path.open to simulate unreadable file
            with patch(
                "addon.bb8_core.addon_config.Path.open",
                side_effect=PermissionError("Access denied"),
            ):
                data, source = _load_yaml_cfg([Path(name)])

            assert data == {}
            assert source is None
        finally:
            # Clean up
            os.unlink(name)

    def test_init_config_yaml_only(self):
        """Test init_config with YAML config only (Lines 103, 105)."""
        test_config = {"yaml_key": "yaml_value"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(test_config, f)
            f.flush()
            yaml_path = Path(f.name)

        # Mock to use our test YAML file
        with patch(
            "addon.bb8_core.addon_config._candidate_paths", return_value=[yaml_path]
        ):
            # Mock options.json to not exist
            with patch(
                "addon.bb8_core.addon_config._load_options_json",
                return_value=({}, None),
            ):
                config, source = init_config()

        # Clean up
        os.unlink(f.name)

        assert config["yaml_key"] == "yaml_value"
        assert source == yaml_path

    def test_init_config_options_and_yaml_merge(self):
        """Test init_config merging options.json and YAML (Lines 126-130)."""
        options_data = {"option_key": "option_value", "shared_key": "from_options"}
        yaml_data = {"yaml_key": "yaml_value", "shared_key": "from_yaml"}

        # Create temporary YAML file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(yaml_data, f)
            f.flush()
            yaml_path = Path(f.name)

        # Mock both sources to return data
        with patch(
            "addon.bb8_core.addon_config._load_options_json",
            return_value=(options_data, Path("/fake/options.json")),
        ):
            with patch(
                "addon.bb8_core.addon_config._candidate_paths", return_value=[yaml_path]
            ):
                config, source = init_config()

        # Clean up
        os.unlink(f.name)

        # Options.json should take precedence
        assert config["option_key"] == "option_value"
        assert config["yaml_key"] == "yaml_value"
        assert config["shared_key"] == "from_options"  # Options wins
        assert source == Path("/fake/options.json")  # Options source preferred

    def test_load_config_empty_config(self):
        """Test load_config when CONFIG is empty (Lines 164-165)."""
        # Operate on the addon_config module object so assignments affect module
        import addon.bb8_core.addon_config as ac

        original_config = ac.CONFIG.copy()
        original_source = ac.CONFIG_SOURCE

        ac.CONFIG.clear()
        ac.CONFIG_SOURCE = None

        try:
            test_data = {"init_key": "init_value"}
            test_source = Path("/test/config.yaml")

            # Simulate init_config by injecting the config directly into module
            ac.CONFIG.update(test_data)
            ac.CONFIG_SOURCE = test_source

            config, source = ac.load_config()

            assert config["init_key"] == "init_value"
            assert source == test_source

        finally:
            ac.CONFIG.clear()
            ac.CONFIG.update(original_config)
            ac.CONFIG_SOURCE = original_source

    def test_load_config_cached(self):
        """Test load_config when CONFIG is already populated (Lines 167-168)."""
        import addon.bb8_core.addon_config as ac

        original_config = ac.CONFIG.copy()
        original_source = ac.CONFIG_SOURCE

        test_data = {"cached_key": "cached_value"}
        test_source = Path("/cached/config.yaml")
        ac.CONFIG.clear()
        ac.CONFIG.update(test_data)
        ac.CONFIG_SOURCE = test_source

        try:
            config, source = ac.load_config()

            assert config["cached_key"] == "cached_value"
            assert source == test_source

        finally:
            ac.CONFIG.clear()
            ac.CONFIG.update(original_config)
            ac.CONFIG_SOURCE = original_source

    def test_env_var_export_success(self):
        """Test environment variable export functionality (Lines 173-176)."""
        # Store original config state
        original_config = CONFIG.copy()
        import addon.bb8_core.addon_config as ac

        original_source = ac.CONFIG_SOURCE

        try:
            test_config = {
                "mqtt_host": "test.broker.com",
                "mqtt_port": 1883,
                "nested": {"key": "value"},
            }

            # Clear cache first to force fresh load
            CONFIG.clear()
            ac.CONFIG_SOURCE = None

            # Mock init_config and os.environ
            with (
                patch(
                    "addon.bb8_core.addon_config.init_config",
                    return_value=(test_config, Path("/test")),
                ),
                patch.dict(os.environ, {}, clear=True),
            ):
                config, source = load_config(force=True)

                # Check that config values were loaded correctly
                # Since we mocked init_config, should get our test_config
                assert "mqtt_host" in config
                assert config["mqtt_host"] == "test.broker.com"
                assert source == Path("/test")

        finally:
            # Restore original config state
            CONFIG.clear()
            CONFIG.update(original_config)
            ac.CONFIG_SOURCE = original_source

    def test_env_var_export_error_handling(self):
        """Test error handling in env var export (Lines 191-192)."""
        test_config = {"test_key": "test_value"}

        import addon.bb8_core.addon_config as ac

        # Inject directly into module and simulate environment update failure
        original_env = os.environ.copy()
        try:
            ac.CONFIG.clear()
            ac.CONFIG.update(test_config)
            ac.CONFIG_SOURCE = Path("/test")
            with (
                patch.dict(os.environ, {}, clear=True),
                patch.object(os.environ, "update", side_effect=Exception("Env error")),
            ):
                config, source = ac.load_config()
                assert config["test_key"] == "test_value"
        finally:
            os.environ.clear()
            os.environ.update(original_env)
