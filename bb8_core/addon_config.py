from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

# Optional dependency: PyYAML may not be present in dev test envs
try:  # pragma: no cover
    import yaml  # type: ignore
except Exception:  # noqa: BLE001
    yaml = None  # type: ignore[assignment]

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
        except Exception as exc:  # noqa: BLE001
            # Keep messages that tests expect: differentiate parse vs read
            if isinstance(exc, json.JSONDecodeError):
                logger.warning(
                    "[CONFIG] Failed to parse options.json %s: %s", path, exc
                )
            elif isinstance(exc, (OSError, UnicodeDecodeError)):
                logger.warning("[CONFIG] Failed to read options.json %s: %s", path, exc)
            else:
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
    """
    if yaml is None:
        logger.debug("[CONFIG] PyYAML not available; skipping YAML candidates")
        return {}, None
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
            except Exception as exc:  # noqa: BLE001
                # YAML parsing vs read errors: make messages explicit for tests
                if isinstance(exc, yaml.YAMLError):
                    logger.warning("[CONFIG] Failed to parse YAML %s: %s", pth, exc)
                elif isinstance(exc, (OSError, UnicodeDecodeError)):
                    logger.warning("[CONFIG] Failed to read YAML %s: %s", pth, exc)
                else:
                    logger.warning("[CONFIG] Failed to load YAML %s: %s", pth, exc)
        else:
            if "Volumes" in str(pth):
                logger.debug("[CONFIG] Dev-only path skipped: %s", pth)
            else:
                logger.debug("[CONFIG] Path not found: %s", pth)
    return {}, None


def load_config(force: bool = False) -> tuple[dict[str, Any], Path | None]:
    """
    Produce the effective configuration.
    Precedence: /data/options.json (HA) overrides YAML values.
    Returns (config_dict, primary_source_path).
    """
    global CONFIG_SOURCE

    # Cached fast-path: return existing CONFIG unless a forced reload was requested.
    if CONFIG and not force:
        return CONFIG, CONFIG_SOURCE

    # Otherwise perform a fresh init; ensure we apply whatever init_config
    # returns into the module-level CONFIG object (preserve identity).
    cfg, src = init_config()

    # If init_config returned a separate mapping (e.g., when patched in tests),
    # copy its contents into the module-level CONFIG in-place so callers that
    # hold a reference to CONFIG see the updated values.
    if cfg is not CONFIG:
        CONFIG.clear()
        CONFIG.update(cfg)

    # Always update CONFIG_SOURCE to reflect the canonical source discovered.
    CONFIG_SOURCE = src

    # Broadcast CONFIG_SOURCE to any modules that imported CONFIG by
    # reference. Tests import CONFIG (the dict) into their module namespace;
    # if a test/module holds the same CONFIG object, update its local
    # CONFIG_SOURCE binding so the imported name reflects the new value.
    for m in list(sys.modules.values()):
        try:
            if getattr(m, "__dict__", {}).get("CONFIG") is CONFIG:
                m.__dict__["CONFIG_SOURCE"] = src
        except Exception:
            # Be defensive: don't let broadcasting break config loading.
            continue
    return CONFIG, CONFIG_SOURCE


def init_config() -> tuple[dict[str, Any], Path | None]:
    """Populate module-level CONFIG & CONFIG_SOURCE and return them.

    Tests expect init_config to return (mapping, source). Keep CONFIG object
    identity by clearing/updating the module-level CONFIG and returning the
    tuple (CONFIG, CONFIG_SOURCE).
    """
    global CONFIG, CONFIG_SOURCE
    # Compute directly from disk candidates to avoid recursion with load_config()
    opts, opts_src = _load_options_json()
    yml, yml_src = _load_yaml_cfg(_candidate_paths())

    merged: dict[str, Any] = {}
    if yml:
        merged.update(yml)
    if opts:
        merged.update(opts)

    source = opts_src or yml_src
    if not merged:
        logger.error("[CONFIG] No configuration found in options.json or YAML.")
        CONFIG.clear()
        CONFIG_SOURCE = None
        return CONFIG, CONFIG_SOURCE

    CONFIG.clear()
    CONFIG.update(merged)
    CONFIG_SOURCE = source
    logger.debug("[CONFIG] Active source: %s", CONFIG_SOURCE)
    return CONFIG, CONFIG_SOURCE


__all__ = [
    "CONFIG",
    "CONFIG_SOURCE",
    "load_config",
    "init_config",
    "_load_options_json",
    "_load_yaml_cfg",
    "LOG",
]

# Initialize on import; safe for runtime and tests
init_config()
