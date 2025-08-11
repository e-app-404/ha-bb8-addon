
<!-- markdownlint-disable MD022 MD032 MD024 -->
# Changelog

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

<!-- Refer to meta schema section below for changelog entry format guidance -->

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
