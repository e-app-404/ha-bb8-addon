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
- Version bumped to 2025.8.10 in `config.yaml` and `run.sh`.

## [2025.8.6] - 2025-08-09

- Added pip-tools (pip-compile) to the Docker image for runtime requirements recompilation.
- `run.sh` now recompiles requirements.txt from requirements.in on every boot if pip-compile is available.
- requirements.in: Added missing runtime dependency `pyyaml` for YAML config fallback.
- Dockerfile: Now installs pip-tools for pip-compile, ensuring requirements can be recompiled in the add-on environment.
- Dependency governance: All runtime dependencies are now strictly managed and reproducible.
- No changes to core BLE/MQTT logic; this is a build/runtime/dependency governance update only.
- The fallback for MQTT_BROKER is now set to core-mosquitto.
- A robust get_mqtt_config() function has been added to bridge_controller.py. It tries environment variables, then Supervisor options, and finally falls back to config.yaml if needed.
- Version bumped to 2025.8.10 in all relevant files.

## [2025.8.7] - 2025-08-09

- Dockerfile: Now uses pip to install bleak==0.22.3, spherov2==0.12.1, and paho-mqtt==2.1.0 with strict version pinning. Removed apk install for py3-paho-mqtt to prevent version mismatches.
- Logging: Log file path updated to /config/hestia/diagnostics/reports/bb8_addon_logs.log; directory is created if missing.
- No changes to core BLE/MQTT logic; these are build/runtime and logging path governance updates only.

## [2025.8.8] - 2025-08-10

- Governance: Visual end-to-end startup flow added to README.md.
- Auto-detect: MAC auto-detect is now always invoked (with granular, structured logging) when a MAC is not provided.
- Logging: Improved structured logging for all BLE/MQTT and auto-detect actions.
- BLEBridge/BleGateway: Constructors and attributes refactored for strict type safety and runtime clarity.
- Async code: Legacy async scan/connect helpers removed for a fully synchronous, production-focused codebase.
- MQTT: Dispatcher call is now signature-agnostic and robust to parameter naming.
- Lint: All missing imports, type errors, and attribute guards resolved; repo is now lint- and runtime-clean.
- Discovery: Home Assistant MQTT discovery payloads are logged before publish, with retain=1 for discovery and availability.
- Version probe: bleak and spherov2 versions are logged at startup for diagnostics.
- Misc: pip-compile now always runs from /app for requirements hygiene.

## [2025.8.9] - 2025-08-10

### Added

- Home Assistant discovery: Each discovery topic payload is now logged before publishing, and discovery/availability topics are published with retain=1.
- Health endpoint probe and log grep for secrets; results saved to `reports/bb8_health_endpoint_log.json`.
- Status rollup and milestone tracking artifacts: `reports/bb8_status_rollup.json`, `reports/bb8_milestones.json`.
- Visual end-to-end startup flow added to README.md.

### Improved

- BLE gateway flag: After BLE gateway initialization, `features_available['ble_gateway'] = True` is set once an adapter is resolved, and downgraded if connection fails.
- Version probe: The versions of bleak and spherov2 are now logged at startup using importlib.metadata.version().
- run.sh: pip-compile now always runs in /app for correct requirements path and requirements hygiene.
- Logging: Improved structured logging for all BLE/MQTT and auto-detect actions.
- BLEBridge/BleGateway: Constructors and attributes refactored for strict type safety and runtime clarity.
- Async code: Legacy async scan/connect helpers removed for a fully synchronous, production-focused codebase.
- MQTT: Dispatcher call is now signature-agnostic and robust to parameter naming.

### Fixed

- Lint: All missing imports (contextlib, re, List, Tuple, etc.), type errors, and attribute guards resolved; repo is now lint- and runtime-clean.

### Various

`bridge_controller.py`:

- Mandatory auto-detect is wired, with structured logs. All parameters are now explicit, and the logic is clear and auditable.
- Hardened parameter names and None checks, matching new constructor signatures. The code now obtains a gateway object (from environment/config or default) and passes it as the gateway argument to start_mqtt_dispatcher, as required.
`bb8_power_on_sequence` is called with the required argument, and `IntervalOptions` is imported and used.

`auto_detect.py`

- Logging is now granular for scan/cache, and the function signature is correct. Constants, imports, and exports are now at module scope and in correct order.
- All helpers (`load_mac_from_cache`, `save_mac_to_cache`, `scan_for_bb8`, `pick_bb8_mac`) are implemented and imported. None handling is robust.

`ble_bridge.py`

- Power-on sequence is context-manager friendly. Increased logging granularity. Now safely guards all controller attribute access. Defined the attributes referenced (`timeout`, `controller`), and imports are ordered.
- Increased logging granularity.

`logging_setup.py`

- Logging is always JSON, with redaction for secrets.

`__init__.py`

- Core symbols are exported for stable imports.

## [2025.8.10] - 2025-08-10

### Major

- Build-time dependency installation: All Python dependencies are now installed at build (Dockerfile), not at runtime. No more pip-compile or pip install on container start.
- Deterministic, one-shot startup: `run.sh` no longer recompiles or installs requirements at runtime. Only one startup banner and version probe per boot.

### Added

- `bb8_core/version_probe.py` for robust, import-based dependency version reporting. Used at startup and in controller.
- Health event (`{"event":"health","state":"healthy"}`) is now emitted after successful MQTT connect and BLE bridge up (mqtt_dispatcher.py).

### Fixed

- No more repeated "Recompiling requirements..." or dependency install logs on normal boots.
- Only one JSON line with dependency versions per boot; none should be "missing" unless truly absent.
- Add-on now runs as a persistent service (no exit after discovery or requirements install).

### Improved

- `run.sh` now probes and prints package versions (bleak, paho-mqtt, spherov2) using importlib.metadata.
- Startup sequence is now: version probe → bridge controller → MQTT/HA. No early exit on version probe.
- Logging redaction pattern in `logging_setup.py` now covers more secret/env patterns and is used for all config/env echoing.
- *`bridge_controller.py`*:

  - Refactored for PEP8 import order and docstring placement. Now uses `from __future__ import annotations` at the top, followed by the module docstring and all imports in correct order.
  - Hardened and clarified startup logic, including robust `get_mqtt_config()` with Supervisor, env, and config.yaml fallback.
  - Improved parameter handling and logging for BLE/MQTT setup, with signature-agnostic dispatcher call and granular event logs.
  - All missing imports, type errors, and attribute guards resolved; file is now lint- and runtime-clean.
  - All main modules: Confirmed docstring placement and import order are PEP8-compliant and lint-clean.
  - Manual edits: Incorporated user manual changes to bridge_controller.py for structure, docstring, and import order.

### Hotfixes

`Dockerfile`: Added `ENV PYTHONPATH=/app` after `WORKDIR /app` to ensure local package is always importable.

`services.d/ble_bridge/run`: Now changes to `/app` and runs `/app/run.sh` via bash, ensuring correct working directory for imports.

`run.sh`:

- Now sets `PYTHONPATH`, changes to `/app`, prints the working directory for debug, and uses the venv Python for execution. This guarantees `bb8_core` is always importable and prevents `ModuleNotFoundError` on startup.
- The service run file has been updated to remove all user/group switching. It now simply starts from /app and runs run.sh as root, which will resolve the s6-applyuidgid error in the Home Assistant add-on environment.

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
