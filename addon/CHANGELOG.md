
<!-- markdownlint-disable MD022 MD032 MD024 -->
<!-- Refer to meta schema section at the end of this document for changelog entry format guidance -->
# Changelog
<!-- Version [2025.8.21.1] for updating starts here -->

<!-- Current version for updating ends here -->
## [2025.8.21] — 2025-08-21

### Summary
ADR-0001 “Canonical Topology — Dual-Clone via Git Remote” implemented. Workspace and runtime now follow a dual-clone model (no symlinks/submodules), ops tooling reorganized by domain, CI/templates consolidated, and deployment/verification are fully automated with green gates.

### Added
- ADR-0001 receipt + governance tokens emitted on deploy (`STRUCTURE_OK`, `DEPLOY_OK`, `VERIFY_OK`, `WS_READY`).
- `ops/deploy_dual_clone.sh` one-step deploy + runtime realign.
- Domain folders under `ops/`: `audit/`, `workspace/`, `deploy/`, `qa/`, `diagnostics/`, `maintenance/`, `artifacts/`.

### Changed
- **Topology**: Two real git clones of the same remote (workspace `addon/` and HA runtime), deploy = push → fetch + hard reset.
- **Ops structure**: Scripts regrouped by functional domain for maintainability.
- **Wrappers**: `scripts/` are the canonical wrappers; they now export `WORKSPACE_ROOT` and `REPORT_ROOT`.
- **Git**: Ignore Python caches (`__pycache__/`, `*.pyc`) and local-only clutter; `.gitignore` unified.
- **Tests**: All tests live under `addon/tests/`; suite passes locally.
- **BLE/MQTT**: `publish_discovery(...)` now accepts optional `dbus_path` kwarg to preserve backward compatibility.

### Fixed
- Resolved rebase conflicts and orphan `HEAD`.
- Removed stray runtime symlinks (`addon` → self, `docs` → external), preventing HA confusion.
- Eliminated duplicate/ambiguous `.github` + workflows; ensured the single root workflow runs.

### Removed
- `addon/.github/`, `addon/.vscode/`, `addon/tools/`, `addon/reports/` (superseded by root `.github`, `ops/`, and `reports/`).
- Repo-tracked Python cache artifacts.

### CI / Templates
- Consolidated PR templates and `addon-audit.yml` workflow at repo root `.github/`.

### Migration notes
- Pull latest `main`; use **only** `scripts/` wrappers for local actions.
- Any tooling that assumed old `ops/*` flat paths should be updated to new domain subpaths.
- HA runtime is now aligned by deploy script; restart add-on after deploy if needed.

### Evidence
- `DEPLOY_OK runtime_head=243c989 branch=main`
- `VERIFY_OK ws_head=243c989 runtime_head=243c989 remote=git@github.com:e-app-404/ha-bb8-addon.git`
- `STRUCTURE_OK`
- `WS_READY addon_ws=git_clone_ok runtime=git_clone_ok reports=ok wrappers=ok ops=ok`

---

## v2025.08.20

### Highlights
- **STP4 (strict) graduation — PASS**  
  Device-originated scalar echoes verified; LED RGB JSON shape enforced; command→state pairing clean.

### Added
- **Tools:** `tools/env_sanity.py`, `tools/check_configs.py`, `tools/stp4_diagnose.py`, `tools/audit_addon_tree.py`.
- **CI Gate:** `addon-audit` GitHub Action to prevent stray tooling/config inside `addon/`.
- **Build Context Control:** `addon/.dockerignore` to minimize image context.
- **Evidence Receipt:** `reports/strict_accept_<ts>.status` stamped after strict acceptance.

### Changed
- **Editable Packaging:** `addon/pyproject.toml` now auto-discovers `bb8_core*`; repo installs via `pip install -e addon`.
- **Import Hygiene:** Removed all repo-level `PYTHONPATH` usage; editable install is the sole import mechanism.
- **Tooling Single-Source:** Root-level `pytest.ini`, `ruff.toml`, and `mypy.ini` are authoritative; duplicate sections removed from `pyproject.toml`.
- **Ruff Isort Hint:** `known-first-party = ["bb8_core"]`.
- **Add-on Tree Cleanliness:** Forbidden dev files relocated to `docs/addon_legacy/`.

### Fixed / Validated
- **Shim Hard-Disable in Strict:** `REQUIRE_DEVICE_ECHO=1` guarantees no facade echoes.
- **BLE Loop Robustness:** Dedicated asyncio loop thread validated (no `get_event_loop` warnings in strict run).
- **Discovery Scope:** Scanner remains single source; discovery dump validated during evidence.
- **Retain Policy:** Commandable echoes publish with `retain=false`; sensors may retain as configured.

### Ops Notes
- **MQTT Namespace:** Flat `bb8/<signal>/{set|state}`; scalars accept raw or `{"value": ...}`, LED must be `{"r","g","b"}`.
- **Env Toggles:** `REQUIRE_DEVICE_ECHO=1`, `ENABLE_BRIDGE_TELEMETRY=1`, `MQTT_BASE=bb8`.
- **Artifacts:** Strict evidence stored under `addon/reports/stp4_<ts>/` with `diagnose.txt` and `evidence_manifest.json`.

### Migration
- If any automation referenced the old package name `beep_boop_bb8`, switch imports to **`bb8_core`**.
- Local dev: use the workspace **.venv** and `pip install -e addon`; no `PYTHONPATH` needed.

---

## [2025.08.19] - 2025-08-16

### PATCH-BUNDLE-STP4-20250816-H

#### Major
- Refactored scanner discovery logic for deterministic, thread-safe, and idempotent operation.
- Finalized robust test coverage for dispatcher and facade, with all seam/hook integration tests passing reliably.

#### Added
- Explicit seam and test hooks in the MQTT dispatcher.
- Exported `start_bridge_controller` and other key entry points for explicit import and modularity.
- Dispatcher smoke test log lines for telemetry and discovery.

#### Improved
- Sleep/LED mapping instrumentation in the facade, enabling robust test patching and reliable assertions.
- Test instrumentation with StubCore and monkeypatching for sleep/LED and dispatcher logic.
- Code clarity by cleaning up unused globals/locals and addressing legacy test failures.

#### Fixed
- Import order and compliance with `from __future__ import annotations`, resolving circular import and syntax errors.
- Deduplicated and clamped LED emits, ensuring single-path emission and correct test recording.
- Updated integration tests to use dual seam injection (module-level hook and patched seam function), ensuring deterministic invocation of stubs in threaded MQTT callbacks.

#### Result
The codebase is now deterministic, testable, and robust for scanner discovery, sleep/LED mapping, and MQTT dispatcher integration, with all critical tests passing and instrumentation in place for future development.

---

## [2025.08.18] - 2025-08-16

### bb8: deterministic discovery seam + race fix

Refactored MQTT dispatcher to resolve scanner publisher at call time (no cached aliases).
Added stable seam (SCANNER_PUBLISH_HOOK) for deterministic, thread-safe test injection.
Updated tests for robust coverage of discovery and seam logic.
No public API changes; all changes are internal and covered by focused tests.

---

## [2025.08.17] - 2025-08-15

### Major Patch to Improve Device Discovery Logic

#### Race fix & idempotency

- `_DISCOVERY_PUBLISHED` is now a set of per-entity keys (using `uniq_id`).
- In `maybe_publish_bb8_discovery()`, discovery only runs if the client is connected; otherwise, logs and returns without marking published.
- Each entity is marked as published only after a successful publish (`wait_for_publish()`).
- All config publishes use `retain=True` and `json.dumps(..., separators=(",", ":"))`.

#### High-signal logs

**At gate**: `discovery_enabled=<bool> source=<yaml|env|default>`
**Before each publish**: `publishing_discovery topic=<topic> retain=True keys=<sorted_keys>`
**After publish**: `discovery_publish_result topic=<topic> mid=<mid> wait_ok=<bool>`
**On skip**: `discovery_skip reason=<reason> entity=<uniq_id>`

#### Tests

- **Added** `test_mqtt_discovery.py`
- Tests use only the real API, with a stub publish_fn and `wait_for_publish()`.
- **Assert**: valid JSON payloads, correct HA domains, `retain=True`, idempotency

- `_DISCOVERY_PUBLISHED` is now a set of per-entity keys (using uniq_id).
- `In_maybe_publish_bb8_discovery()`, discovery only runs if the client is connected; otherwise, logs and returns without marking published.
- Each entity is marked as published only after a successful publish `(wait_for_publish())`.
- All config publishes use `retain=True` and `json.dumps(..., separators=(",", ":"))`.

#### High-signal logs

- **At gate**: `discovery_enabled=<bool> source=<yaml|env|default>`
- **Before each publish**: `publishing_discovery topic=<topic> retain=True keys=<sorted_keys>`
- **After publish**: `discovery_publish_result topic=<topic> mid=<mid> wait_ok=<bool>`
- **On skip**: `discovery_skip reason=<reason> entity=<uniq_id>`

#### Tests

- **Added** `test_mqtt_discovery.py`
- Tests use only the real API, with a stub publish_fn and `wait_for_publish()`.
- **Assert**: valid JSON payloads, correct HA domains, `retain=True`, idempotency

#### No API changes

- `publish_bb8_discovery(publish_fn)` and entity construction are unchanged.
`_maybe_publish_bb8_discovery()` is still callable from all current sites.

## [2025.08.16] - 2025-08-15

### Major

#### Device Echo and Topic Split
- Migrated all MQTT topic usage to split `CMD_TOPICS` (commands) and `STATE_TOPICS` (state/echo) in `common.py`.
- Updated all device echo handlers in `bridge_controller.py` and related modules to use strict echo publishing (raw and JSON) on state topics.
- Added detailed echo logging for all device state publications.

#### Home Assistant Discovery and LED Support
- Added Home Assistant discovery publishing for RGB LED entity, gated by config.
- Improved discovery payloads for drive, sleep, and presence entities; fixed missing/invalid discovery for some entities.

#### BLE Shutdown and Loop Management
- Enhanced BLE link runner with clean shutdown logic, draining pending tasks and logging exceptions.
- Added BLELink class facade for compatibility with legacy callers/tests.
- Improved type hints and coroutine scheduling for BLE operations.

#### Config Loader and Environment Overlay
- Refactored config loader for strict precedence: Home Assistant options.json > YAML > environment > defaults.
- Added environment variable overlay for MQTT config keys, with type-safe parsing and logging.
- Improved error handling and logging for config resolution and loading failures.

#### Dispatcher and Collector Guards
- Added singleton guard to `mqtt_dispatcher.py` to ensure only one dispatcher instance per process.
- Updated evidence collector to use environment fallback for MQTT host/port, with improved error reporting.

#### Lint, Type, and Test Config
- Updated and enforced ruff.toml, mypy.ini, and pytest.ini for consistent linting, type checking, and test discovery.
- All import sorting, line length, and type hints are now enforced.
- Pytest config stabilizes asyncio mode and narrows test discovery to avoid errors and recursion.

#### Miscellaneous
- Removed deprecated topic symbols and files, cleaned up circular imports and duplicate code blocks.
- Improved logging and error reporting throughout the codebase.
- All modules now use shared constants and helpers from `common.py`.
- Config precedence for MQTT host/port/base/user/pass now follows: ENV > options.json > YAML > fallback. User-provided YAML fallback is respected if not overridden.

#### Patches Applied
- PATCH-STP4-250814-config-path
- PATCH-STP4-250814-device-echo
- PATCH-STP4-250814-device-echo-v2
- PATCH-STP4-250815-addon-config-api-compat
- PATCH-STP4-250815-addon-config-lint-fixes
- PATCH-STP4-250815-addon-config-order-fix
- PATCH-STP4-250815-dispatcher-singleton
- PATCH-STP4-250815-mypy-config
- PATCH-STP4-250815-mypy-root-config
- PATCH-STP4-250815-pytest-root-config
- PATCH-STP4-250815-pytest-stabilize
- PATCH-STP4-250815-ruff-config
- PATCH-STP4-250815-topic-split-and-echo-fix
- PATCH-STP4-250815-echo-logging
- PATCH-STP4-250815-led-discovery
- PATCH-STP4-250815-mqtt-config-binding
- PATCH-STP4-250815-ble-init-guard
- PATCH-STP4-250815-ble-loop-runner-v2
- PATCH-STP4-250815-ble-shutdown-cleanup
- PATCH-STP4-250815-blelink-class-facade
- PATCH-STP4-250815-blelink-type-hints
- PATCH-STP4-250815-collector-connect-guard
- PATCH-STP4-250815-config-precedence-mqtt-host

## [2025.08.15] - 2025-08-13

### Major

Patch to resolve static fallbacks and hardcoded config variables:

#### `bb8_presence_scanner.py`

- All hardcoded "bb8/" topic prefixes replaced with dynamic MQTT_TOPIC_PREFIX from config.
- All references to MQTT_BASE changed to MQTT_TOPIC_PREFIX for clarity.
- DISCOVERY_RETAIN now loaded from config (options.discovery_retain).
- MQTT client ID is now dynamic (CFG.get("MQTT_CLIENT_ID", "bb8_presence_scanner")).
- Model hint is now dynamic (CFG.get("BB8_NAME", "S33 BB84 LE")).
- Added HA_DISCOVERY_TOPIC as a configurable value for Home Assistant discovery topics.
- All Home Assistant discovery topic prefixes now use HA_DISCOVERY_TOPIC.
- Added a TODO to store and map "device_defaults" from facade_mapping_table.json for future dynamic mapping.
- Ensured all CLI defaults and static values are loaded from config or have config fallbacks.
- Fixed function signature for publish_discovery to avoid type errors (never passes None for model/name).

All hardcoded topic prefixes, static config fallbacks, and inconsistent config keys in bb8_presence_scanner.py have been unified to use the dynamic config loader in addon_config.py. All MQTT topics now use MQTT_BASE, and config keys like MQTT_USERNAME, MQTT_CLIENT_ID, AVAIL_ON, and AVAIL_OFF are resolved via the loader. No errors remain.

- Added support for the scanner to respect the `ENABLE_SCANNER_TELEMETRY` toggle. Telemetry publishing and related log events will only occur if enabled, and all telemetry logs include "role": "scanner" for clarity.
- `ENABLE_SCANNER_TELEMETRY` is loaded via the shared config loader (CFG/SRC), not directly from environment variables.

#### `facade.py`

- MQTT QoS, retain, and D-Bus path defaults are now loaded dynamically from config (`addon_config.py`).
- Uses `MQTT_TOPIC_PREFIX` and `HA_DISCOVERY_TOPIC` from config for topic construction and discovery.
- All helper functions and config lookups are now properly scoped within the attach_mqtt method.
- Added a TODO to store and map "device_defaults" from facade_mapping_table.json for future dynamic mapping.
- Removed static defaults and fixed indentation/scoping errors.
- Resolved a broken `from .discovery_publish` import to import publish_discovery directly from `bb8_presence_scanner.py`, matching the current codebase

- Refactored `BB8Facade.attach_mqtt` to remove duplicate local function definitions.
- Eliminated redundant second block of `_pub`, `_parse_color`, `_handle_power`, `_handle_led`, and `_handle_stop` functions.
- Removed duplicate telemetry publisher bindings, subscriptions, and logger.info calls.
- Ensured only one definition of each local function and one block of subscriptions remain for correct scoping.
- No changes to logic; patch restores maintainability and eliminates lint errors.

#### `ble_bridge.py`

All static values and topic prefixes in `ble_bridge.py` are now loaded dynamically from `addon_config.py`, using all available config keys.

#### `addon_config.py`

Now loads all relevant config keys from config.yaml, including discovery_retain, log_path, scan_seconds, rescan_on_fail, cache_ttl_hours, mqtt_tls, ble_adapter, and ha_discovery_topic.

Now supports dynamic lookups for command_topic, status_topic, availability_topic, keepalive, qos, and retain as config keys with sensible defaults

Optimized the `load_config()` function:

- All MQTT topics are constructed using the resolved config value for MQTT_BASE.
- Type safety is added for booleans and integers (e.g., RETAIN, QOS, KEEPALIVE, etc.).
- The precedence order is clarified and maintainable.
- The code is more robust and consistent for all config keys.

Toggles:

Config source toggles in `addon_config.py` are now directly mapped to user-facing boolean toggles in `config.yaml`. This ensures all runtime config values (including telemetry, retain, and other booleans) are consistently loaded from the options UI and YAML schema, with correct precedence and type safety.

#### `bridge_controller.py` and `auto_detect.py`

- Unified config loading in `auto_detect.py` and `bridge_controller.py` to use addon_config.py, and added support for CACHE_PATH and CACHE_DEFAULT_TTL_HOURS in the config loader. All config values are now resolved via load_config().

- The evidence recorder section in `bridge_controller.py` is now refactored for full config unification and provenance logging.

- Telemetry in the bridge will now only start if the `enable_bridge_telemetry` toggle is on, and all related log events will include the `"role": "bridge"` field for clarity. If telemetry is not started due to the config toggle, the following will be logged with a log statement.

- The config banner now emits a one-shot INFO log at startup, showing all available active config keys and their sources at startup. This makes it easy to verify the active configuration without second-guessing.

#### `config.yaml`

The options and schema in config.yaml are now logically structured into clear sections:

- Telemetry & Logging
- Device Identification
- MQTT Configuration

#### README

The `README.md` directory structure is now fully up-to-date, reflecting all current components, scripts, and config systems. It also includes a summary of the unified configuration and evidence collection systems.

### Hotfixes

Updated `PYTHONPATH` to include the correct folder paths for the current structure and ensure add-on imports work as expected.

<!-- Current version for updating ends here -->
## [2025.08.14] - 2025-08-12

### Major

Exposed all BB-8 actuator bridge hooks (power, stop, LED, heading, speed, drive) via MQTT in `bb8_presence_scanner.py`, centralizing all Home Assistant discovery and actuator control logic in the scanner and retiring legacy `discovery*.py` logic.
Scanner now subscribes to both flat and legacy MQTT command topics for all actuators (LED, stop, drive, heading, speed, power), and state publishing now echoes to both flat and legacy state topics, ensuring full backward compatibility and eliminating topic mismatches.
Unified all extended Home Assistant discovery topics and command/state handlers to use the flat namespace (`bb8/led`, `bb8/speed`, `bb8/heading`, `bb8/drive`, etc.) for all entities, with consistent payloads and topic formatting for future-proof, device-specific support (e.g., `bb8/<device_id>/led/set`).
Home Assistant MQTT JSON light compliance: LED entity now uses `schema: json` and publishes state in the HA-compatible format (`{"state":"ON","color":{"r":..,"g":..,"b":..},"color_mode":"rgb"}` and `{"state":"OFF"}`), with support for `brightness` (discovery advertises `supported_color_modes: ["rgb", "brightness"]`, and handlers accept/publish a `brightness` field).
Scanner supports direct robot control from Home Assistant entities (light/button/number), not just state echo, and all changes are backward-compatible and future-proofed for multi-device and brightness support.
Added flat alias for power command (`bb8/power/set`), subscribing and routing to the power handler for consistency with other flat topics.

### Fixed

- Guarded call to `is_connected` with `callable()` in `TelemetryLoop` to prevent `TypeError: 'NoneType' object is not callable` in telemetry error logs.

### Improved

### Config Unification & Provenance Logging

- **Unified Configuration Loader:** All configuration for the scanner is now loaded via a single-source-of-truth config loader (`bb8_core.addon_config.load_config`). This loader merges environment variables, YAML, and options.json, and tracks provenance for each setting.
- **Provenance-Aware Debug Logging:** The scanner now logs the provenance (source) of each config value at startup, making it easy to audit and debug configuration issues.
- **Removed Legacy Config Logic:** All legacy config loading functions, environment variable fallbacks, and debug banners have been removed from `bb8_presence_scanner.py`. All references now use the unified config loader (`CFG`).
- **CLI Defaults Unified:** All CLI argument defaults and device block logic now use values from the unified config loader, ensuring consistency and maintainability.
- **Error Handling Improved:** Lint and runtime errors caused by legacy config references have been resolved. The scanner is now robust against missing or malformed config sources.

### Deprecation notice
- `discovery.py` and `discovery_publish.py` are now thin shims that re-export `publish_discovery` from `bb8_presence_scanner.py`. All Home Assistant discovery logic is unified in the scanner.

### Major update: Unified Scanner & Discovery Logic

`bb8_presence_scanner.py` now subsumes `discovery.py` and `discovery_publish.py`:

Publishes full Home Assistant MQTT discovery payloads for Presence and RSSI sensors.
Adds complete device block with MAC, D-Bus path, and add-on version (sw_version).
Availability (birth and last-will) now handled automatically.
Improved BLE device metadata extraction:
Extracts MAC and D-Bus path directly from BLE scan details.
Uses MAC in identifiers and connections to ensure uniqueness.

Simplified deployment:

Older discovery scripts are now redundant; scanner handles telemetry + discovery in one process.

Telemetry updates:

`bb8/sensor/presence` publishes on/off (retained).
`bb8/sensor/rssi` publishes integer dBm values (retained).

- Integrated extended Home Assistant discovery/entities (LED, sleep, drive, heading, speed) into `bb8_presence_scanner.py`.
  - Scanner now publishes all discovery configs and echoes state for extended entities.
  - Extended entities enabled by default; can be toggled via `--extended/--no-extended` CLI or `BB8_EXTENDED` env var.
  - Device/topic helpers and unified extended discovery publisher added.
- Deprecated `discovery.py` and `discovery_publish.py` (now raise `DeprecationWarning`).
- No changes to BLE scanning, presence/RSSI telemetry, or availability topics.

## [2025.08.12] - 2025-08-11

### Added
- New `bb8_core/ble_link.py`: Implements a minimal, observable BLE link class with connection and RSSI callbacks for device observability.
- BLE link is now wired into `bridge_controller.py`, publishing MQTT observability topics for connection status and RSSI.
- Home Assistant discovery now publishes new entities for `connected` (binary_sensor) and `rssi` (sensor) on every MQTT connect, ensuring these are always available and discoverable.

### Changed
- Evidence collector script (`ops/evidence/collect_stp4.py`) updated to implement strict ordering, prestate, source, and device-echo logic. Annotates commands, checks for device-originated state echoes, and enforces stricter roundtrip validation.
- Power quick-echo in MQTT publish for `power/state` is now tagged as `"source": "facade"` in `facade.py`, allowing the evidence collector to distinguish façade-originated echoes.
- Discovery is now published on every MQTT connect, ensuring all entities are visible and retained in Home Assistant.

### Fixed
- Fixed bug in `bb8_core/ble_link.py`: `is_connected` is now accessed as a property, not awaited as a coroutine, resolving the "Object of type 'bool' is not callable" error.
- Fixed indentation and parameter issues in `bridge_controller.py` for BLE link and MQTT observability publishing; all lint errors addressed.
### Changed

- MQTT/HA controller is now always the `BB8Facade` (not the bridge), ensuring all MQTT and Home Assistant logic is centralized and device-agnostic.
- `bridge_controller.py` now passes the facade to the dispatcher, keeping BLEBridge device-only and simplifying teardown.
- `mqtt_dispatcher.py` no longer publishes Home Assistant discovery; this is now handled exclusively by the facade, preventing duplicate retained configs.
- `facade.py` discovery call is now explicit and correct (no unsupported `qos` argument).
- `bridge_controller.py` now starts the `EvidenceRecorder` (if enabled) and telemetry loop after MQTT connect, with configuration via environment variables.
- Updated import in `bridge_controller.py` to use local `evidence_capture.py` for compatibility with Home Assistant add-on/container environments.

### Added

- Logging now supports the `BB8_LOG_PATH` environment variable and a robust fallback: if the configured log path is unwritable (e.g., read-only `/config`), logs are written to `/tmp/bb8_addon.log` with a one-time warning. This is controlled by the new logic in `logging_setup.py`.
- `config.yaml` and `run.sh` now support an optional `log_path` override, plumbed through to the environment for flexible deployment.
- STP4 evidence automation: Added Makefile targets `evidence-stp4` and `evidence-clean` for automated evidence bundle generation and cleanup.
- New script `ops/evidence/collect_stp4.py` to collect MQTT/HA roundtrip evidence, outputting discovery and trace artifacts for compliance.
- New module `bb8_core/evidence_capture.py` with `EvidenceRecorder` class for in-process MQTT roundtrip evidence capture.

### Fixed

- YAML schema in `config.yaml` is now valid and deduplicated; schema and options are separate and error-free.
- All facade and dispatcher changes are Pylance/static-analysis clean, and all discovery publishing is idempotent and non-duplicated.
- Fixed `ModuleNotFoundError: No module named 'ops'` by moving `evidence_capture.py` into `bb8_core/` and updating the import path.

### Developer Notes

- To test logging fallback, set `BB8_LOG_PATH` to an unwritable location and confirm a fallback warning and log output in `/tmp`.
- To test discovery, ensure only one `discovery_published` event appears after connect, and that all entities are visible in Home Assistant.
- To generate an STP4 evidence bundle, run `make evidence-stp4` (or invoke the collector script directly if `make` is unavailable).
- The evidence collector and recorder require `paho-mqtt` and `PyYAML` (add to requirements if missing).

### Added

- Public handler surface (`power`, `stop`, `set_led_off`, `set_led_rgb`, `sleep`, `is_connected`, `get_rssi`, `attach_mqtt`) is now exposed on both `BB8Facade` and `BLEBridge`.
- `BLEBridge` now provides thin, typed delegates for all handler methods, ensuring interface compatibility and silencing Pylance/IDE warnings. All methods are safe no-ops until real Sphero BLE logic is implemented.
- `attach_mqtt` method added to `BLEBridge` class: wires up MQTT command handlers and telemetry publishers for Home Assistant integration. Supports power, stop, and LED commands, and exposes presence/RSSI publishers.
- Home Assistant MQTT Discovery publishing is now called automatically after MQTT connect (in `start_mqtt_dispatcher`), ensuring all entities are visible and retained in Home Assistant. Uses `publish_discovery` from `bb8_core/discovery_publish.py`.
- Home Assistant discovery is now always re-published after MQTT connect, using `publish_discovery` directly after `controller.attach_mqtt` in the dispatcher.
- Telemetry loop (`TelemetryLoop` in `bb8_core/telemetry.py`) is now started after BLE connect and stopped on shutdown in the controller, providing periodic presence and RSSI updates to Home Assistant.

### Improved

- All handler methods are now available on both the facade and bridge, so any code (now or future) can call either interface safely. This keeps the bridge device-focused but compatible with handler contracts.

- Cleaned up imports in `bb8_core/mqtt_dispatcher.py`: only modules actually used are imported at the top level.
- Dispatcher now supports both `username`/`password` and legacy `mqtt_user`/`mqtt_password` parameters (with internal unification and deprecation warning).
- BLE/Sphero dependencies are now lazy-imported inside the minimal functions that require them, keeping the dispatcher module transport-focused and lightweight.
- `paho.mqtt.publish` import is now only enabled if `publish.single` is actually used; otherwise, all MQTT publishing is done via the connected client.
- Discovery publishing is now idempotent and safe to re-publish on reconnect; all configs are retained for Home Assistant auto-entity creation.

### Fixed

- All dispatcher import errors and legacy parameter issues resolved; file is now clean, error-free, and back-compatible.

### Development

- Facade and bridge handler surfaces are now fully interface-compatible. Pylance and static analysis are satisfied for all handler method signatures.

- Dispatcher code and API are now fully back-compatible and ready for further refactor or migration away from legacy argument names.

---
## [2025.08.14] - 2025-08-12

### Major
- Exposed all BB-8 actuator bridge hooks (power, stop, LED, heading, speed, drive) via MQTT in `bb8_presence_scanner.py`.
- Retired legacy `discovery*.py` logic; all Home Assistant discovery and actuator control is now centralized in the scanner.
- Scanner now supports direct robot control from Home Assistant entities (light/button/number), not just state echo.

### Added
- Optional bridge integration: scanner auto-loads `BB8Facade` with a `BLEBridge` if available, or falls back to a safe no-op facade if not.
- Subscribes to new command topics:
  - `bb8/cmd/power_set` ("ON"|"OFF")
  - `bb8/cmd/stop_press` (momentary)
  - `bb8/cmd/led_set` ({r,g,b}|{"hex":...}|"OFF")
  - `bb8/cmd/heading_set` (0..359)
  - `bb8/cmd/speed_set` (0..255)
  - `bb8/cmd/drive_press` (momentary)
- Publishes state echoes for all actuators:
  - `bb8/state/led` (retained)
  - `bb8/state/heading` (retained)
  - `bb8/state/speed` (retained)
  - `bb8/state/stop` (pressed→idle, non-retained)
- Minimal JSON/hex parsing and clamping helpers for robust command handling.
- All command handling and bridge calls are guarded; scanner runs and logs cleanly even if the bridge is not present.

### Improved
- Home Assistant extended entities (light/button/number) now operate the robot through MQTT, not just echo state.
- All actuator commands are validated, clamped, and logged for traceability and safety.
- Retained/non-retained state echoes match Home Assistant expectations for UI and automation feedback.

### Fixed
- Fixed all runtime and lint errors related to missing bridge/facade methods and payload parsing.
- Fixed memoryview/bytes payload handling for MQTT command callbacks.
- All scanner command handlers are now robust to missing bridge/facade and invalid payloads.

## [2025.08.11] - 2025-08-11

### Major

- Fixed repeated add-on restart loop: main process now blocks in foreground and shuts down cleanly on SIGTERM/SIGINT (`bridge_controller.py`).
- MQTT dispatcher fully modernized: legacy dispatcher code removed, new implementation supports explicit connect arguments, TLS passthrough, and granular connect reason logging.
- Add-on manifest and config hardened for Home Assistant: DBus, udev, AppArmor, and minimal privileges set in `config.yaml`.
- Dockerfile now uses `ARG BUILD_FROM` for multi-arch builds; venv and requirements install are deterministic.

### Added

- `publish_discovery_if_available` helper function: allows the dispatcher to call controller-based discovery publishing if available, with error logging fallback.
- `/data/options.json` explainer and actual discovery entity list added to README for user clarity.
- Example Home Assistant automation using 2024.8+ `action: mqtt.publish` syntax in README.

### Improved

- Add-on now logs a `shutdown_signal` event and performs orderly teardown on Supervisor stop/restart.
- Dispatcher lifecycle is now managed at the controller level for robust process control.
- Only a single version probe is logged at startup (removed duplicate from `run.sh`).
- Dev-only requirements recompilation: `pip-compile` now runs only if `BB8_DEV_DEPS=1` (`run.sh`).
- Cleaned up unused/duplicate imports in `mqtt_dispatcher.py` for clarity and lint compliance.
- Dispatcher now logs all connect/disconnect reasons and supports both legacy and new argument names for maximum compatibility.
- All legacy/duplicate dispatcher code removed from `bb8_core/mqtt_dispatcher.py` for clarity and maintainability.
- Manifest and config.yaml now have aligned defaults and schema for first-run success.
- README and config.yaml now accurately reflect only the entities and options actually shipped.

### Fixed
- No more repeated s6 startup banners; add-on stays up after `mqtt_connect_attempt`.
- No more duplicate or conflicting dispatcher definitions; file is now clean and top-level only.
- All test imports now reference `mqtt_dispatcher` (not removed dispatcher class); smoke test uses correct dispatcher signature.
- All jq usage removed from `run.sh`; all config is parsed in Python.

### Development
- Added `_wait_forever()` to pin process in foreground and handle shutdown signals.
- All changes are non-invasive: no behavior change for BLE or MQTT logic—only lifecycle management and polish.
- Refactored dispatcher for explicit parameter handling and robust logging, with clear separation from legacy code.
- Dockerfile, config, and test polish for Home Assistant add-on builder and multi-arch support.

---

## [2025.08.10] - 2025-08-10

### Major

- Build-time dependency installation: All Python dependencies are now installed at build (Dockerfile), not at runtime
- Deterministic, one-shot startup: `run.sh` no longer recompiles or installs requirements at runtime

### Added

- `bb8_core/version_probe.py` for robust, import-based dependency version reporting
- Health event (`{"event":"health","state":"healthy"}`) emitted after successful MQTT connect and BLE bridge up (`mqtt_dispatcher.py`)

### Improved

- Startup sequence is now: version probe → bridge controller → MQTT/HA with no early exit on version probe
- Logging redaction pattern in `logging_setup.py` now covers more secret/env patterns for all config/env echoing
- `bridge_controller.py` refactored for PEP8 import order and docstring placement with `from __future__ import annotations`
- Hardened startup logic including robust `get_mqtt_config()` with Supervisor, env, and config.yaml fallback
- Parameter handling and logging for BLE/MQTT setup with signature-agnostic dispatcher call and granular event logs

### Fixed

- No more repeated "Recompiling requirements..." or dependency install logs on normal boots
- Only one JSON line with dependency versions per boot; none should be "missing" unless truly absent
- Add-on now runs as persistent service (no exit after discovery or requirements install)
- All missing imports, type errors, and attribute guards resolved; file is now lint- and runtime-clean
- ModuleNotFoundError resolved by setting `PYTHONPATH=/app` in Dockerfile and updating service run scripts
- `bb8_core/bridge_controller.py` fully rewritten: all code now lives inside functions, with a single `main()` and `if __name__ == "__main__": main()` guard at the end. File is now clean, deduplicated, and free of trailing/duplicate code blocks. Lint- and runtime-clean.

### Development

- `run.sh` now probes and prints package versions (bleak, paho-mqtt, spherov2) using importlib.metadata
- Services run file updated to remove user/group switching, resolving s6-applyuidgid error in HA add-on environment

---

## [2025.08.9] - 2025-08-10

### Added

- Home Assistant discovery: Each discovery topic payload is now logged before publishing
- Health endpoint probe and log grep for secrets with results saved to `reports/bb8_health_endpoint_log.json`
- Status rollup and milestone tracking artifacts: `reports/bb8_status_rollup.json`, `reports/bb8_milestones.json`
- Visual end-to-end startup flow documentation in README.md

### Improved

- BLE gateway initialization: `features_available['ble_gateway'] = True` set once adapter is resolved, downgraded if connection fails
- Discovery/availability topics now published with retain=1 for better persistence
- Structured logging for all BLE/MQTT and auto-detect actions
- BLEBridge/BleGateway constructors and attributes refactored for strict type safety and runtime clarity
- MQTT dispatcher call is now signature-agnostic and robust to parameter naming

### Fixed

- All missing imports (contextlib, re, List, Tuple, etc.), type errors, and attribute guards resolved
- Repository is now lint- and runtime-clean

### Changed

- Legacy async scan/connect helpers removed for fully synchronous, production-focused codebase

### Development

- Version probe: bleak and spherov2 versions now logged at startup using importlib.metadata.version()
- pip-compile now always runs in /app for correct requirements path and requirements hygiene

## [2025.08.8] - 2025-08-10

### Added

- Visual end-to-end startup flow documentation in README.md
- Version probe: bleak and spherov2 versions logged at startup for diagnostics

### Improved

- Auto-detect: MAC auto-detect is now always invoked with granular, structured logging when MAC not provided
- Structured logging for all BLE/MQTT and auto-detect actions
- BLEBridge/BleGateway: Constructors and attributes refactored for strict type safety and runtime clarity
- MQTT: Dispatcher call is now signature-agnostic and robust to parameter naming
- Home Assistant MQTT discovery payloads are logged before publish, with retain=1 for discovery and availability

### Fixed

- All missing imports, type errors, and attribute guards resolved; repo is now lint- and runtime-clean

### Changed

- Legacy async scan/connect helpers removed for fully synchronous, production-focused codebase

### Development

- pip-compile now always runs from /app for requirements hygiene

## [2025.08.7] - 2025-08-09

### Changed

- Dockerfile now uses pip to install bleak==0.22.3, spherov2==0.12.1, and paho-mqtt==2.1.0 with strict version pinning
- Log file path updated to `/config/hestia/diagnostics/reports/bb8_addon_logs.log`
- Directory creation added if log path missing

### Removed

- apk install for py3-paho-mqtt to prevent version mismatches

## [2025.08.6] - 2025-08-09

### Added

- Robust `get_mqtt_config()` function in `bridge_controller.py` with environment variables, Supervisor options, and config.yaml fallback

### Improved

- Dependency governance: All runtime dependencies are now strictly managed and reproducible
- MQTT_BROKER fallback now set to core-mosquitto

### Major

- Logging covers all key actions, state changes, and error points for robust diagnostics and governance

### Fixed

- Removed all print statements and ad-hoc logging throughout codebase

### Changed

- All modules now use structured logging: `facade.py`, `core.py`, `util.py`, `mqtt_dispatcher.py`, `ble_gateway.py`, `controller.py`, `bridge_controller.py`, `test_mqtt_dispatcher.py`

## [2025.08.4] - 2025-08-09

### Added

- Hybrid BB-8 MAC auto-detect logic in `bb8_core/auto_detect.py` with override, scan, cache, retry, structured logging, and testability

### Improved

- Supervisor-UI schema in `config.yaml` with explicit types, defaults, and comments
- `run.sh` with robust option extraction, defensive mkdir, CLI+env passing

## [2025.08.3] - 2025-08-09

### Major

- Unified logging system: All modules now use robust logger from `bb8_core/logging_setup.py`

### Improved

- Consistent file and console output across all modules
- All logging output is now robust and suitable for both supervised and local development environments

### Fixed

- Added missing `import os` in `bridge_controller.py`
- Ensured correct enum usage (`IntervalOptions.NONE`) in `mqtt_dispatcher.py`
- Removed or guarded context manager usage in `ble_bridge.py` to avoid errors with non-context manager objects

### Changed

- Refactored `bridge_controller.py`, `test_mqtt_dispatcher.py`, `mqtt_dispatcher.py`, `ble_gateway.py`, `discovery_publish.py`, `controller.py`, and `ble_bridge.py` to remove custom logger setups

## [2025.08.2] - 2025-08-09

### Added

- Strategos v1.6 governance: STP2 (Logging/Health/Security) and STP4 (MQTT & HA Discovery Roundtrip) audits implemented
- Governance and audit artifacts: `reports/bb8_health_endpoint_log.json`, `reports/ha_mqtt_trace_snapshot.json`, `reports/bb8_status_rollup.json`, `reports/bb8_milestones.json`
- `bb8_core/ble_utils.py` with `resolve_services()` for robust Bleak version compatibility
- Status rollup and milestone tracking artifacts for governance and project management

### Major

- BLE/Core refactor: `bb8_core/core.py` now provides Core class for all low-level BLE operations

### Improved

- MQTT/HA: LWT and online status publishing; discovery always emitted on connect for reliable HA entity visibility
- Test imports and pytest compatibility in `test_mqtt_smoke.py`
- Version is now injected at build time and always shown in logs

### Fixed

- Refactored method calls and signatures in core, bridge, and test modules to match vendor API and silence Pylance errors

### Changed

- All relevant modules updated to use Core class interface
- Versioning bumped to 2025.08.2 in all artifacts and documentation

## [2025.08.1] - 2025-08-09

### Added

- Strategos v1.6 audit and reporting for STP2 (Logging/Health/Security) and STP4 (MQTT & HA Discovery Roundtrip)
- Health endpoint probe and log grep for secrets with results saved to `reports/bb8_health_endpoint_log.json`
- Full MQTT/HA entity roundtrip trace and schema validation with results saved to `reports/ha_mqtt_trace_snapshot.json`
- Status rollup and milestone tracking artifacts: `reports/bb8_status_rollup.json`, `reports/bb8_milestones.json`
- Bleak compatibility shim: `bb8_core/ble_utils.py` ensures cross-version BLE service resolution

### Major

- BLE driver boundary formalized: `bb8_core/core.py` now provides Core class for all low-level BLE operations

### Fixed

- Pylance and runtime errors resolved for all core, bridge, and test modules

### Changed

- Version bumped to 2025.08.1 for all artifacts and documentation

## [0.3.4] - 2025-08-09 (Legacy Format)

### Added

- Version injection at build time, always shown in logs (Dockerfile, run.sh)
- MQTT LWT and online status publishing
- MQTT discovery payloads now include all required device/entity info (`mqtt_dispatcher.py`)

### Improved

- Discovery always emitted on connect (`mqtt_dispatcher.py`)
- BLE stack only initialized once (`bridge_controller.py`, `ble_gateway.py`)
- Scanner and notification options defaulted and mapped from config (`config.yaml`, `run.sh`)

### Changed

- Config.yaml version bumped to 0.3.4

## [0.3.3] - 2025-08-09 (Legacy Format)

### Improved

- Robust version reporting in run.sh: removed config.yaml grep, now uses VERSION env fallback (defaults to "unknown")
- MQTT connect logic in Python now retries and falls back to core-mosquitto/localhost, preventing crash loops
- Error handling and startup hardening for add-on reliability

### Changed

- MQTT broker fallback: if unset, defaults to core-mosquitto

## [0.3.2] - 2025-08-08 (Legacy Format)

### Added

- Prefilled config.yaml with correct values for `bb8_mac`, `mqtt_broker`, `mqtt_username`, and `mqtt_password`

### Changed

- Updated `config.yaml` to version 0.3.2

## [0.3.1] - 2025-08-08 (Legacy Format)

### Added

- Background BLE presence scanner for BB-8 (`bb8_presence_scanner.py`)
- MQTT Discovery for presence and RSSI sensors (auto-registers in Home Assistant)
- Aggressive connect/retry logic for BLE commands in `ble_bridge.py`
- Home Assistant notification for BB-8 unavailability (automation YAML or MQTT Discovery)

### Improved

- All entities now surfaced via MQTT Discovery with no manual configuration needed
- Reliability >95% for typical use
- All connection attempts, successes, and failures are logged for monitoring and diagnostics

### Changed

- Version bump: `run.sh` updated to `VERSION="0.3.1"`

### Documentation

- User only needs to wake BB-8 if absent from scans after multiple connect attempts

<!-- # BB-8 Add-on Changelog Schema

## Version Format Standard
**Use semantic versioning with date-based major versions:**
- `YYYY.MM.PATCH` for major releases (e.g., `2025.08.1`, `2025.08.2`)
- Include release date in ISO format: `YYYY-MM-DD`

## Entry Structure Template

```markdown
## [YYYY.MM.PATCH] - YYYY-MM-DD

### Major
- High-impact architectural changes
- Breaking changes or major refactors
- New core features or capabilities

### Added
- New features, endpoints, or functionality
- New configuration options
- New dependencies or tools
- New documentation or artifacts

### Improved
- Performance enhancements
- Code quality improvements (refactoring, type safety)
- Enhanced error handling or logging
- Better user experience or reliability
- Dependency updates or optimizations

### Fixed
- Bug fixes
- Security vulnerabilities resolved
- Compatibility issues resolved
- Error handling improvements

### Changed
- Modifications to existing behavior
- Configuration changes
- API changes (non-breaking)
- Default value changes

### Deprecated
- Features marked for future removal
- Configuration options being phased out

### Removed
- Deleted features, files, or functionality
- Removed dependencies
- Discontinued support for something

### Security
- Security-related fixes or improvements
- Vulnerability patches
- Security hardening measures

### Development
- Build system changes
- CI/CD improvements
- Development tooling updates
- Test improvements

### Documentation
- Documentation updates
- README changes
- Schema updates
- Comment improvements
```

## Writing Guidelines

### Entry Content Rules

1. **Use action-oriented language**: Start with verbs (Added, Fixed, Improved, etc.)
2. **Be specific**: Include module/file names when relevant
3. **Include impact**: Mention user-facing benefits when applicable
4. **Reference issues**: Link to tickets/issues when available
5. **Order by importance**: Most significant changes first within each section

### Section Priority Order

When multiple sections are used, order them as:
1. Major
2. Added
3. Improved
4. Fixed
5. Changed
6. Security
7. Development
8. Documentation
9. Deprecated
10. Removed

### Content Examples

**Good entries:**
```markdown
### Added
- Background BLE presence scanner (`bb8_presence_scanner.py`) with MQTT Discovery auto-registration
- Health endpoint probe with secret detection and JSON reporting (`reports/bb8_health_endpoint_log.json`)

### Improved
- MQTT connection reliability with automatic fallback to core-mosquitto broker
- BLE stack initialization now occurs only once, preventing resource conflicts (`bridge_controller.py`, `ble_gateway.py`)

### Fixed
- Resolved ModuleNotFoundError by setting PYTHONPATH=/app in Dockerfile and run scripts
- Corrected type errors and missing imports across all core modules for lint compliance
```

**Avoid:**
- Vague descriptions: "Various improvements"
- Missing file references when specific
- Duplicate information across sections

### Version Numbering Rules

- **Major version (YYYY.MM)**: New year/month, significant feature releases
- **Patch version**: Bug fixes, minor improvements, documentation updates
- **Example progression**: `2025.08.1` → `2025.08.2` → `2025.08.3` → `2025.09.1`

### Special Considerations

- **Governance entries**: Include audit results, compliance measures, and reporting artifacts in "Added" or "Development" sections
- **Dependencies**: List version changes with rationale in "Improved" or "Changed" sections
- **Configuration**: Note schema changes and migration steps in "Changed" section
- **Breaking changes**: Always include in "Major" section with migration guidance

## Validation Checklist

Before publishing a changelog entry:

- [ ] Version follows YYYY.MM.PATCH format
- [ ] Date is in YYYY-MM-DD format
- [ ] Each bullet point is specific and actionable
- [ ] File/module names are included where relevant
- [ ] Sections are ordered by priority
- [ ] No duplicate information across sections
- [ ] Breaking changes are clearly marked in "Major"
- [ ] Grammar and spelling are correct
- [ ] Technical accuracy is verified

## Migration Notes

**For existing entries:** Previous semantic versions (0.3.x) should be considered legacy. New entries should follow the YYYY.MM.PATCH format going forward.

**Consolidation:** Consider grouping minor patches when preparing release summaries or major version documentation. -->

## 2025-08-23
- deps: pin **paho-mqtt >= 2,<3** and update code to pass  on client construction.
- deps: ensure **PyYAML >= 6.0.1** present.
- docs: add MQTT Version Policy to README.
- ADR: add **ADR-0002** for dependency & runtime compatibility.

## 2025-08-23
- deps: pin **paho-mqtt >= 2,<3** and update code to pass  on client construction.
- deps: ensure **PyYAML >= 6.0.1** present.
- docs: add MQTT Version Policy to README.
- ADR: add **ADR-0002** for dependency & runtime compatibility.
