from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)
# Back-compat alias expected by some callers/tests
LOG = logger

# Public module-level handles; populated by init_config()
CONFIG: dict[str, Any] = {}
CONFIG_SOURCE: Path | None = None


def _candidate_paths() -> list[Path]:
    """
    Ordered config locations (HA first, then add-on, then local/dev).
    The '/Volumes/...' path is dev-only and logged at DEBUG.
    """
    env_path = os.environ.get("CONFIG_PATH")
    paths: list[Path] = []
    if env_path:
        paths.append(Path(env_path))
    paths.extend(
        [
            Path("/data/config.yaml"),  # HA add-on standard
            Path("/config/config.yaml"),
            Path("/addons/docs/config.yaml"),
            Path(__file__).parent / "config.yaml",
            Path("/app/config.yaml"),
            Path("/Volumes/addons/docs/config.yaml"),
        ]
    )
    return paths


def _load_options_json(
    path: Path = Path("/data/options.json"),
) -> tuple[dict[str, Any], Path | None]:
    """
    Load Home Assistant add-on options (JSON). Returns (data, source_path).
    Catches json.JSONDecodeError and OSError if reading or parsing fails.
    """
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                logger.warning("[CONFIG] options.json root not a mapping: %s", path)
                return {}, None
            logger.info("[CONFIG] Loaded options from: %s", path)
            return data, path
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("[CONFIG] Failed reading options.json %s: %s", path, exc)
            return {}, None
    logger.debug("[CONFIG] options.json not found: %s", path)
    return {}, None


def _load_yaml_cfg(
    paths: list[Path] | None = None,
) -> tuple[dict[str, Any], Path | None]:
    """
    Load YAML config from the first available candidate path.
    Returns (data, source_path). Empty dict if none valid.
    Only yaml.YAMLError and OSError are caught during loading.
    """
    candidates = paths or _candidate_paths()
    for pth in candidates:
        if pth.exists():
            try:
                with pth.open("r", encoding="utf-8") as fh:
                    data = yaml.safe_load(fh)
                if not isinstance(data, dict):
                    logger.warning("[CONFIG] YAML root not a mapping: %s", pth)
                    continue
                logger.info("[CONFIG] Loaded YAML config from: %s", pth)
                return data, pth
            except (yaml.YAMLError, OSError) as exc:
                logger.warning("[CONFIG] Failed to load YAML %s: %s", pth, exc)
        else:
            if "Volumes" in str(pth):
                logger.debug("[CONFIG] Dev-only path skipped: %s", pth)
            else:
                logger.debug("[CONFIG] Path not found: %s", pth)
    return {}, None


def load_config() -> tuple[dict[str, Any], Path | None]:
    """
    Produce the effective configuration.
    Precedence: /data/options.json (HA) overrides YAML values.
    Returns (config_dict, primary_source_path).
    """
    opts, opts_src = _load_options_json()
    yml, yml_src = _load_yaml_cfg()

    merged: dict[str, Any] = {}
    if yml:
        merged.update(yml)
    if opts:
        merged.update(opts)

    # ---- Helper: first non-empty value ----
    def _first(*vals):
        for v in vals:
            if v is not None and v != "":
                return v
        return None

    # ---- Resolve MQTT host with precedence:
    # ENV -> options.json -> YAML -> fallback ----
    env_host = os.environ.get("MQTT_HOST")
    host_from_opts = merged.get("mqtt_broker") or merged.get("MQTT_HOST")
    host_from_yaml = (yml or {}).get("mqtt_broker") if yml else None
    final_host = _first(env_host, host_from_opts, host_from_yaml, "127.0.0.1")

    # ---- Resolve MQTT port with precedence:
    # ENV -> options.json -> YAML -> fallback ----
    def _as_int(x, default):
        if x in (None, ""):
            return default
        try:
            return int(x)
        except (ValueError, TypeError):
            LOG.warning("[CONFIG] Invalid MQTT port value: %s", x)
            return default

    env_port = os.environ.get("MQTT_PORT")
    port_from_opts = merged.get("mqtt_port") or merged.get("MQTT_PORT")
    port_from_yaml = (yml or {}).get("mqtt_port") if yml else None
    final_port = _as_int(_first(env_port, port_from_opts, port_from_yaml), 1883)

    # ---- Resolve MQTT base/topic prefix with precedence:
    # ENV -> options.json -> YAML -> fallback ----
    env_base = os.environ.get("MQTT_BASE")
    base_from_opts = merged.get("mqtt_topic_prefix") or merged.get("MQTT_BASE")
    base_from_yaml = (yml or {}).get("mqtt_topic_prefix") if yml else None
    final_base = _first(env_base, base_from_opts, base_from_yaml, "bb8")

    # ---- Credentials (env overrides if provided) ----
    final_user = _first(
        os.environ.get("MQTT_USERNAME"),
        merged.get("mqtt_username"),
        (yml or {}).get("mqtt_username") if yml else None,
    )
    final_pass = _first(
        os.environ.get("MQTT_PASSWORD"),
        merged.get("mqtt_password"),
        (yml or {}).get("mqtt_password") if yml else None,
    )

    # ---- Backfill synonyms so all callers see the same values ----
    merged["MQTT_HOST"] = final_host
    merged["mqtt_broker"] = final_host
    merged["MQTT_PORT"] = final_port
    merged["mqtt_port"] = final_port
    merged["MQTT_BASE"] = final_base
    merged["mqtt_topic_prefix"] = final_base
    if final_user is not None:
        merged["MQTT_USERNAME"] = final_user
        merged["mqtt_username"] = final_user
    if final_pass is not None:
        merged["MQTT_PASSWORD"] = final_pass
        merged["mqtt_password"] = final_pass

    # ---- Availability topic (scanner is the single owner) ----
    # Bridge must NOT advertise availability when
    # scanner_owns_telemetry is true.
    avail = f"{merged['MQTT_BASE']}/availability/scanner"
    merged["availability_topic_scanner"] = avail
    merged["availability_payload_online"] = "online"
    merged["availability_payload_offline"] = "offline"

    # (Optional) compact debug of resolved endpoints
    logger.debug(
        (
            "[CONFIG] MQTT resolved host=%s port=%s base=%s user=%s "
            "(precedence: ENV > options.json > YAML > fallback)"
        ),
        merged["MQTT_HOST"],
        merged["MQTT_PORT"],
        merged["MQTT_BASE"],
        bool(final_user),
    )
    source = opts_src or yml_src
    if not merged:
        logger.error("[CONFIG] No configuration found in options.json or YAML.")
        return {}, None

    logger.debug(
        "[CONFIG] Effective keys=%s (source=%s)",
        sorted(list(merged.keys())),
        source,
    )
    return merged, source


def init_config() -> None:
    """Populate module-level CONFIG & CONFIG_SOURCE for callers."""
    global CONFIG, CONFIG_SOURCE
    CONFIG, CONFIG_SOURCE = load_config()
    logger.debug("[CONFIG] Active source: %s", CONFIG_SOURCE)


__all__ = [
    "CONFIG",
    "CONFIG_SOURCE",
    "load_config",
    "init_config",
    "_load_options_json",
    "_load_yaml_cfg",
    "LOG",
]

# Initialize on import; safe for runtime and tests.
# To defer initialization (e.g., for testing), set the environment variable 'BB8_CONFIG_DEFER_INIT' to '1'.
if os.environ.get("BB8_CONFIG_DEFER_INIT", "0") != "1":
    init_config()
