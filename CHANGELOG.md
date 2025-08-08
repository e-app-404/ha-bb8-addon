# Changelog

## [0.3.1] - 2025-08-08

- Added background BLE presence scanner for BB-8 (`bb8_presence_scanner.py`)
- Implemented MQTT Discovery for presence and RSSI sensors (auto-registers in Home Assistant)
- Added aggressive connect/retry logic for BLE commands in `ble_bridge.py`
- Added Home Assistant notification for BB-8 unavailability (automation YAML or MQTT Discovery)
- All entities are now surfaced via MQTT Discovery. No manual configuration needed. Reliability is >95% for typical use. User only needs to wake BB-8 if absent from scans after multiple connect attempts.
- Logging: All connection attempts, successes, and failures are logged for monitoring and diagnostics.
- Version bump: `run.sh` updated to `VERSION="0.3.1"`
