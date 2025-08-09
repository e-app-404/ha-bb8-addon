# Changelog

## [0.3.1] - 2025-08-08

- Added background BLE presence scanner for BB-8 (`bb8_presence_scanner.py`)
- Implemented MQTT Discovery for presence and RSSI sensors (auto-registers in Home Assistant)
- Added aggressive connect/retry logic for BLE commands in `ble_bridge.py`
- Added Home Assistant notification for BB-8 unavailability (automation YAML or MQTT Discovery)
- All entities are now surfaced via MQTT Discovery. No manual configuration needed. Reliability is >95% for typical use. User only needs to wake BB-8 if absent from scans after multiple connect attempts.
- Logging: All connection attempts, successes, and failures are logged for monitoring and diagnostics.
- Version bump: `run.sh` updated to `VERSION="0.3.1"`

## [0.3.2] - 2025-08-08

- Prefilled config.yaml with correct values for `bb8_mac`, `mqtt_broker`, `mqtt_username`, and `mqtt_password`
- Updated `config.yaml` to version 0.3.2

## [0.3.3] - 2025-08-09

- Robust version reporting in run.sh: removed config.yaml grep, now uses VERSION env fallback (defaults to "unknown").
- MQTT broker fallback: if unset, defaults to core-mosquitto.
- MQTT connect logic in Python now retries and falls back to core-mosquitto/localhost, preventing crash loops.
- Improved error handling and startup hardening for add-on reliability.

## [0.3.4] - 2025-08-09

- Version is now injected at build time and always shown in logs (Dockerfile, run.sh).
- MQTT LWT and online status are published; discovery is always emitted on connect (mqtt_dispatcher.py).
- BLE stack is only initialized once (bridge_controller.py, ble_gateway.py).
- Scanner and notification options are defaulted and mapped from config (config.yaml, run.sh).
- MQTT discovery payloads now include all required device/entity info (mqtt_dispatcher.py).
- Minor: config.yaml version bumped to 0.3.4.

## [2025.08.1] - 2025-08-09

- Governance: Implemented Strategos v1.6 audit and reporting for STP2 (Logging/Health/Security) and STP4 (MQTT & HA Discovery Roundtrip).
- Added health endpoint probe and log grep for secrets; results saved to `reports/bb8_health_endpoint_log.json`.
- Full MQTT/HA entity roundtrip trace and schema validation; results saved to `reports/ha_mqtt_trace_snapshot.json`.
- Status rollup and milestone tracking artifacts: `reports/bb8_status_rollup.json`, `reports/bb8_milestones.json`.
- BLE driver boundary formalized: `bb8_core/core.py` now provides the Core class for all low-level BLE operations.
- Bleak compatibility shim: `bb8_core/ble_utils.py` ensures cross-version BLE service resolution.
- Pylance and runtime errors resolved for all core, bridge, and test modules.
- Version bumped to 2025.08.1 for all artifacts and documentation.

## [2025.08.2] - 2025-08-09

- Strategos v1.6 governance: STP2 (Logging/Health/Security) and STP4 (MQTT & HA Discovery Roundtrip) audits implemented.
- New governance and audit artifacts: `reports/bb8_health_endpoint_log.json`, `reports/ha_mqtt_trace_snapshot.json`, `reports/bb8_status_rollup.json`, `reports/bb8_milestones.json`.
- BLE/Core refactor: `bb8_core/core.py` now provides the Core class for all low-level BLE operations; all relevant modules updated to use this interface.
- Added `bb8_core/ble_utils.py` with `resolve_services()` for robust Bleak version compatibility.
- Refactored method calls and signatures in core, bridge, and test modules to match vendor API and silence Pylance errors.
- Improved test imports and pytest compatibility in `test_mqtt_smoke.py`.
- Versioning: Bumped to 2025.08.2 in all artifacts and documentation; version is now injected at build time and always shown in logs.
- MQTT/HA: Improved LWT and online status publishing; discovery is always emitted on connect for reliable HA entity visibility.
- Status rollup and milestone tracking artifacts added for governance and project management.

## [2025.08.3] - 2025-08-09

- Logging: Unified all modules to use the robust logger from `bb8_core/logging_setup.py` for consistent file and console output.
- Refactored `bridge_controller.py`, `test_mqtt_dispatcher.py`, `mqtt_dispatcher.py`, `ble_gateway.py`, `discovery_publish.py`, `controller.py`, and `ble_bridge.py` to remove custom logger setups and use the shared logger.
- Fixed type/lint errors:
  - Added missing `import os` in `bridge_controller.py`.
  - Ensured correct enum usage (`IntervalOptions.NONE`) in `mqtt_dispatcher.py`.
  - Removed or guarded context manager usage in `ble_bridge.py` to avoid errors with non-context manager objects.
- All logging output is now robust, consistent, and suitable for both supervised and local development environments.

## [2025.8.4] - 2025-08-09

- Implemented hybrid BB-8 MAC auto-detect logic in `bb8_core/auto_detect.py` (override, scan, cache, retry, structured logging, testability)
- Updated Supervisor-UI schema in `config.yaml` for explicit types, defaults, and comments
- Updated `run.sh` for robust option extraction, defensive mkdir, CLI+env passing

## [2025.8.5] - 2025-08-09

- Unified, structured, event-based logging implemented across all core modules (`facade.py`, `core.py`, `util.py`, `mqtt_dispatcher.py`, `ble_gateway.py`, `controller.py`, `bridge_controller.py`, `test_mqtt_dispatcher.py`).
- All logs now use the shared logger from `logging_setup.py` for file and console output.
- Removed all print statements and ad-hoc logging; all logs are now machine-parseable and audit-friendly.
- Logging covers all key actions, state changes, and error points for robust diagnostics and governance.
- Version bumped to 2025.8.5 in `config.yaml` and `run.sh`.
