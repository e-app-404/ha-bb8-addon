from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    pass

"""
Single Source of Truth Module for loading and managing configuration for the BB-8 addon.

"""
LOG = logging.getLogger(__name__)


def _load_options_json() -> dict:
    try:
        with open("/data/options.json", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        LOG.debug(f"[CONFIG] Could not load /data/options.json: {e}")
        return {}


def _load_yaml_cfg() -> dict:
    # Add "config.yaml" to the search paths. This will be found
    # when you run `make` from the add-on's root directory on your Mac.
    for p in (
        "config.yaml",
        "/addons/local/beep_boop_bb8/config.yaml",
        "/app/config.yaml",
    ):
        try:
            with open(p, encoding="utf-8") as f:
                yml = yaml.safe_load(f) or {}
                if (
                    isinstance(yml, dict)
                    and "options" in yml
                    and isinstance(yml["options"], dict)
                ):
                    config = yml["options"]
                else:
                    config = yml
                # Validate against schema if present
                schema = yml.get("schema") if isinstance(yml, dict) else None
                if schema:
                    _validate_config_schema(config, schema)
                LOG.debug(f"[CONFIG] Loaded YAML config from {p}")
                return config
        except FileNotFoundError:
            continue  # Try the next path in the list
        except Exception as e:
            LOG.debug(f"[CONFIG] Could not load YAML config from {p}: {e}")
            continue

    LOG.debug("[CONFIG] No valid YAML config found.")
    return {}


def _validate_config_schema(cfg: dict, schema: dict):
    """Validate config dict against schema block."""
    for key, typ in schema.items():
        if key not in cfg:
            # Optional types (ending with ?) are allowed to be missing
            if not (isinstance(typ, str) and typ.endswith("?")):
                LOG.debug(
                    f"[CONFIG] Key '{key}' missing from config, expected type {typ}."
                )
            continue
        val = cfg[key]
        # Only basic type checks
        if typ in ("bool", "bool?") or typ is bool:
            if not isinstance(val, bool):
                LOG.warning(
                    f"[CONFIG] Key '{key}' expected bool, got {type(val).__name__}."
                )
        elif typ in ("int", "int?") or typ is int:
            try:
                # Accept values that are int or can be cast to int (excluding None)
                if val is None or (not isinstance(val, int) and not str(val).isdigit()):
                    raise ValueError
                int(val)
            except Exception:
                msg = (
                    f"[CONFIG] Key '{key}' expected int, got "
                    f"{type(val).__name__} value '{val}'."
                )
                LOG.warning(msg)
        elif typ in ("str", "str?") or typ is str:
            if not (isinstance(val, str) or (typ in ("str?",) and val is None)):
                msg = f"[CONFIG] Key '{key}' expected str, got {type(val).__name__}."
                LOG.warning(msg)


def _pick(
    key: str, env: dict, opt: dict, yml: dict, default, yaml_key: str | None = None
):
    """
    Pick value with precedence: env > options > yaml > default.
    If yaml_key is provided, try that key in yaml first.
    """
    # Check environment variable
    if key in env and env[key] not in ("", None):
        return env[key], "env"

    # Check options.json
    if key in opt and opt[key] not in ("", None):
        return opt[key], "options"

    # Check YAML with yaml_key mapping
    if yaml_key:
        # Case-insensitive lookup for yaml_key
        yaml_key_lc = yaml_key.lower()
        yml_keys_lc = {str(k).lower(): k for k in yml}
        if yaml_key_lc in yml_keys_lc:
            actual_key = yml_keys_lc[yaml_key_lc]
            if yml[actual_key] not in (None, ""):
                return yml[actual_key], "yaml"

    # Check YAML with original key (fallback)
    if key in yml and yml[key] not in (None, ""):
        return yml[key], "yaml"

    # Use default
    LOG.debug(
        f"[CONFIG] Key '{key}' (yaml_key='{yaml_key}') not found in env/options/yaml, "
        f"using default '{default}'."
    )
    return default, "default"


def load_config() -> tuple[dict, dict]:
    """Return (cfg, src) where src maps key -> 'env'|'options'|'yaml'|'default'."""
    env = dict(os.environ)
    opt = _load_options_json()
    yml = _load_yaml_cfg()

    cfg, src = {}, {}

    def setk(k, default, yaml_key=None, cast=None):
        """
        Set config key with precedence: env > options > yaml > default.
        Optionally cast value.
        """
        v, s = _pick(k, env, opt, yml, default, yaml_key)
        if cast and v not in (None, ""):
            try:
                v = cast(v)
            except Exception as e:
                LOG.warning(
                    f"[CONFIG] Failed to cast key '{k}' value '{v}' with {cast}: {e}"
                )
                # Don't raise, use the original value
        cfg[k], src[k] = v, s

    # Keys we care about (expanded, mapped to config.yaml user-facing keys)
    setk(
        "DISPATCHER_DISCOVERY_ENABLED",
        False,
        yaml_key="dispatcher_discovery_enabled",
        cast=lambda x: str(x).lower() in ("1", "true", "yes"),
    )
    setk("CACHE_PATH", "/data/bb8_mac_cache.json", yaml_key="cache_path")
    setk("CACHE_DEFAULT_TTL_HOURS", 24, yaml_key="cache_default_ttl_hours", cast=int)
    setk("BB8_NAME", "BB-8", yaml_key="bb8_name")
    setk("BB8_MAC", "", yaml_key="bb8_mac")
    setk("MQTT_HOST", "localhost", yaml_key="mqtt_broker")
    setk("MQTT_PORT", 1883, yaml_key="mqtt_port", cast=int)
    setk("MQTT_USERNAME", "mqtt_bb8", yaml_key="mqtt_username")
    setk("MQTT_PASSWORD", None, yaml_key="mqtt_password")
    setk("MQTT_BASE", "bb8", yaml_key="mqtt_topic_prefix")
    setk("MQTT_CLIENT_ID", "bb8_presence_scanner", yaml_key="mqtt_client_id")
    setk("KEEPALIVE", 60, yaml_key="keepalive", cast=int)
    setk("QOS", 1, yaml_key="qos", cast=int)
    setk(
        "RETAIN",
        True,
        yaml_key="discovery_retain",
        cast=lambda x: str(x).lower() in ("1", "true", "yes"),
    )
    setk(
        "ENABLE_BRIDGE_TELEMETRY",
        False,
        yaml_key="enable_bridge_telemetry",
        cast=lambda x: str(x).lower() in ("1", "true", "yes"),
    )
    setk("TELEMETRY_INTERVAL_S", 20, yaml_key="telemetry_interval_s", cast=int)
    setk("ADDON_VERSION", "unknown", yaml_key="version")
    setk(
        "DISCOVERY_RETAIN",
        False,
        yaml_key="discovery_retain",
        cast=lambda x: str(x).lower() in ("1", "true", "yes"),
    )
    setk("LOG_PATH", "", yaml_key="log_path")
    setk("SCAN_SECONDS", 5, yaml_key="scan_seconds", cast=int)
    setk(
        "RESCAN_ON_FAIL",
        True,
        yaml_key="rescan_on_fail",
        cast=lambda x: str(x).lower() in ("1", "true", "yes"),
    )
    setk("CACHE_TTL_HOURS", 24, yaml_key="cache_ttl_hours", cast=int)
    setk(
        "MQTT_TLS",
        False,
        yaml_key="mqtt_tls",
        cast=lambda x: str(x).lower() in ("1", "true", "yes"),
    )
    setk("BLE_ADAPTER", "hci0", yaml_key="ble_adapter")
    setk("HA_DISCOVERY_TOPIC", "homeassistant", yaml_key="ha_discovery_topic")
    setk("AVAIL_ON", "online")
    setk("AVAIL_OFF", "offline")
    setk("BB8_SCAN_INTERVAL", 10, yaml_key="bb8_scan_interval", cast=int)

    # Construct topics using resolved config
    cfg["COMMAND_TOPIC"] = f"{cfg['MQTT_BASE']}/command/#"
    cfg["STATUS_TOPIC"] = f"{cfg['MQTT_BASE']}/status"
    cfg["AVAILABILITY_TOPIC"] = f"{cfg['MQTT_BASE']}/status/#"

    return cfg, src


def log_config(cfg: dict, src: dict, logger: logging.Logger):
    lines = [
        "[DEBUG] Effective configuration (value ⟂ source):",
        f"  BB8_NAME='{cfg['BB8_NAME']}' ⟂ {src['BB8_NAME']}",
        f"  BB8_MAC='{cfg['BB8_MAC']}' ⟂ {src['BB8_MAC']}",
        f"  MQTT_HOST='{cfg['MQTT_HOST']}' ⟂ {src['MQTT_HOST']}",
        f"  MQTT_PORT={cfg['MQTT_PORT']} ⟂ {src['MQTT_PORT']}",
        f"  MQTT_USER='{cfg['MQTT_USERNAME']}' ⟂ {src['MQTT_USERNAME']}",
        f"  MQTT_PASSWORD={'***' if cfg['MQTT_PASSWORD'] else None} "
        f"⟂ {src['MQTT_PASSWORD']}",
        f"  MQTT_BASE='{cfg['MQTT_BASE']}' ⟂ {src['MQTT_BASE']}",
        (
            f"  ENABLE_BRIDGE_TELEMETRY={cfg['ENABLE_BRIDGE_TELEMETRY']} "
            f"⟂ {src['ENABLE_BRIDGE_TELEMETRY']}"
        ),
        (
            f"  TELEMETRY_INTERVAL_S={cfg['TELEMETRY_INTERVAL_S']} "
            f"⟂ {src['TELEMETRY_INTERVAL_S']}"
        ),
        f"  Add-on version: {cfg['ADDON_VERSION']} ⟂ {src['ADDON_VERSION']}",
    ]
    logger.debug("\n" + "\n".join(lines))
