"""
Single Source of Truth Module for loading and managing configuration for the BB-8 addon.

"""
from __future__ import annotations
import os, json, yaml, logging
from typing import Dict, Tuple

LOG = logging.getLogger(__name__)

def _load_options_json() -> Dict:
    try:
        with open("/data/options.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _load_yaml_cfg() -> Dict:
    for p in ("/addons/local/beep_boop_bb8/config.yaml", "/app/config.yaml"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            continue
    return {}

def _pick(key: str, env: Dict, opt: Dict, yml: Dict, default):
    if key in env and env[key] not in ("", None):
        return env[key], "env"
    if key in opt and opt[key] not in ("", None):
        return opt[key], "options"
    if key in yml and yml[key] not in ("", None):
        return yml[key], "yaml"
    return default, "default"

def load_config() -> Tuple[Dict, Dict]:
    """Return (cfg, src) where src maps key -> 'env'|'options'|'yaml'|'default'."""
    env = dict(os.environ)
    opt = _load_options_json()
    yml = _load_yaml_cfg()

    cfg, src = {}, {}
    def setk(k, default, yaml_key=None, cast=None):
        """Set config key with precedence: yaml_key (top-level YAML) > env > options > yaml > default. Optionally cast value."""
        v, s = None, None
        if yaml_key and yaml_key in yml and yml[yaml_key] not in (None, ""):
            v, s = yml[yaml_key], "yaml"
        else:
            v, s = _pick(k, env, opt, yml, default)
        if cast and v not in (None, ""):
            try:
                v = cast(v)
            except Exception:
                pass
        cfg[k], src[k] = v, s

    # Keys we care about (expanded, mapped to config.yaml user-facing keys)
    setk("CACHE_PATH", "/data/bb8_mac_cache.json")
    setk("CACHE_DEFAULT_TTL_HOURS", 24, cast=int)
    setk("BB8_NAME", "BB-8", yaml_key="bb8_name")
    setk("BB8_MAC", "", yaml_key="bb8_mac")
    setk("MQTT_HOST", "localhost", yaml_key="mqtt_broker")
    setk("MQTT_PORT", 1883, yaml_key="mqtt_port", cast=int)
    setk("MQTT_USERNAME", "mqtt_bb8", yaml_key="mqtt_username")
    setk("MQTT_PASSWORD", None, yaml_key="mqtt_password")
    setk("MQTT_BASE", "bb8", yaml_key="mqtt_topic_prefix")
    setk("MQTT_CLIENT_ID", "bb8_presence_scanner")
    setk("KEEPALIVE", 60, cast=int)
    setk("QOS", 1, cast=int)
    setk("RETAIN", True, yaml_key="discovery_retain", cast=lambda x: str(x).lower() in ("1", "true", "yes"))
    setk("ENABLE_BRIDGE_TELEMETRY", "0", yaml_key="enable_bridge_telemetry", cast=lambda x: str(x).lower() in ("1", "true", "yes"))
    setk("TELEMETRY_INTERVAL_S", 20, cast=int)
    setk("ADDON_VERSION", "unknown", yaml_key="version")
    setk("DISCOVERY_RETAIN", False, yaml_key="discovery_retain", cast=lambda x: str(x).lower() in ("1", "true", "yes"))
    setk("LOG_PATH", "", yaml_key="log_path")
    setk("SCAN_SECONDS", 5, yaml_key="scan_seconds", cast=int)
    setk("RESCAN_ON_FAIL", True, yaml_key="rescan_on_fail", cast=lambda x: str(x).lower() in ("1", "true", "yes"))
    setk("CACHE_TTL_HOURS", 24, yaml_key="cache_ttl_hours", cast=int)
    setk("MQTT_TLS", False, yaml_key="mqtt_tls", cast=lambda x: str(x).lower() in ("1", "true", "yes"))
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

def log_config(cfg: Dict, src: Dict, logger: logging.Logger):
    lines = [
        "[DEBUG] Effective configuration (value ⟂ source):",
        f"  BB8_NAME='{cfg['BB8_NAME']}' ⟂ {src['BB8_NAME']}",
        f"  BB8_MAC='{cfg['BB8_MAC']}' ⟂ {src['BB8_MAC']}",
        f"  MQTT_HOST='{cfg['MQTT_HOST']}' ⟂ {src['MQTT_HOST']}",
        f"  MQTT_PORT={cfg['MQTT_PORT']} ⟂ {src['MQTT_PORT']}",
        f"  MQTT_USER='{cfg['MQTT_USERNAME']}' ⟂ {src['MQTT_USERNAME']}",
        f"  MQTT_PASSWORD={'***' if cfg['MQTT_PASSWORD'] else None} ⟂ {src['MQTT_PASSWORD']}",
        f"  MQTT_BASE='{cfg['MQTT_BASE']}' ⟂ {src['MQTT_BASE']}",
        f"  ENABLE_BRIDGE_TELEMETRY={cfg['ENABLE_BRIDGE_TELEMETRY']} ⟂ {src['ENABLE_BRIDGE_TELEMETRY']}",
        f"  TELEMETRY_INTERVAL_S={cfg['TELEMETRY_INTERVAL_S']} ⟂ {src['TELEMETRY_INTERVAL_S']}",
        f"  Add-on version: {cfg['ADDON_VERSION']} ⟂ {src['ADDON_VERSION']}",
    ]
    logger.debug("\n" + "\n".join(lines))
