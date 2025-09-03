# BB-8 Passive BLE Presence Monitor

This document provides a comprehensive overview of the BB-8 passive BLE presence monitor implementation, including architecture, configuration, usability, debugging, error handling, and extension points. It is intended for developers, integrators, and maintainers working with the Home Assistant BB-8 add-on.

---

## 1. Overview

The passive BLE presence monitor continuously scans for BB-8 devices via Bluetooth Low Energy (BLE), updates a central registry with device signals, and publishes presence state changes to MQTT. It is designed for robust, configurable, and testable operation in Home Assistant environments.

---

## 2. Architecture & Implementation

- **Core File:** `addon/bb8_core/auto_detect.py`
- **Main Functions:**
  - `monitor_bb8_presence`: Synchronous monitor loop for standard environments.
  - `async_monitor_bb8_presence`: Asynchronous monitor loop for async environments.
  - `atomic_write_yaml`: Thread-safe, atomic registry updates.
  - `publish_presence_mqtt`: Publishes state changes to MQTT.
  - Test hooks/mocks for BLE scan, registry write, and MQTT publish.
- **Registry:** YAML file at `REGISTRY_PATH`, keyed by MAC address, containing all surfaced device signals.
- **MQTT:** Publishes to topic `MQTT_PRESENCE_TOPIC_BASE/<mac>` (configurable).

---

## 3. Configuration

All operational parameters are loaded from `config.yaml`:

- `SCAN_INTERVAL_SEC`: BLE scan interval (seconds)
- `ABSENCE_TIMEOUT_SEC`: Absence timeout before marking device absent (seconds)
- `DEBOUNCE_COUNT`: Consecutive misses before marking absent
- `CACHE_PATH`: Path for MAC cache file
- `CACHE_DEFAULT_TTL_HOURS`: Cache TTL (hours)
- `REGISTRY_PATH`: Path for device registry YAML
- `MQTT_PRESENCE_TOPIC_BASE`: Base MQTT topic for presence notifications (default: `bb8/presence`)

**To change behavior:** Edit `config.yaml` and restart the add-on. All config keys are documented in the module docstring and this document.

---

## 4. Usability & Integration

- **Entrypoint:**
  - Synchronous: `start_presence_monitor()` (runs in background thread)
  - Asynchronous: `await async_monitor_bb8_presence(...)`
- **Registry Format:**
  ```yaml
  <mac>:
    bb8_mac: <mac>
    advertised_name: <name>
    last_seen_epoch: <timestamp>
    last_checked_epoch: <timestamp>
    rssi: <rssi>
    present: <bool>
    absence_timeout_sec: <int>
    source: "presence_monitor"
  ```
- **MQTT Payload:**
  ```json
  {
    "state": "present"|"absent",
    "mac": <mac>,
    "rssi": <rssi>,
    "absence_timeout_sec": <int>,
    "timestamp": <float>
  }
  ```
- **Test Hooks:**
  - All major functions accept optional overrides for BLE scan, registry write, and MQTT publish.
  - Example mocks are provided for CI/unit testing.

---

## 5. Debugging & Error Handling

- **Error Handling Strategy:**
  - All long-running loops and I/O operations use try/except blocks to prevent crashes and surface actionable errors.
  - All exceptions are logged with event type, error details, and relevant context.
  - Monitor loops are designed to continue running after recoverable errors, with state logged for diagnostics.
- **Common Failure Modes:**
  - BLE scan errors (hardware, permissions, adapter issues)
  - Registry write errors (filesystem, permissions, atomicity)
  - MQTT publish errors (network, broker, payload format)
  - Cache read/write errors (corruption, permissions)
- **Debugging Tips:**
  - Check logs for events like `bb8_presence_monitor_error`, `bb8_registry_atomic_write_error`, and `bb8_presence_mqtt_publish_error`.
  - Use test hooks/mocks to simulate error conditions and validate error handling in CI.
  - Inspect the registry YAML and MQTT payloads for expected values.
  - Validate config changes by restarting the add-on and observing log output.

---

## 6. Extension & Customization

- **Adding New Device Types:**
  - Extend `is_probable_bb8` and registry format as needed.
- **Changing MQTT Topic Structure:**
  - Update `MQTT_PRESENCE_TOPIC_BASE` in `config.yaml`.
- **Registry Format Changes:**
  - Update registry payload construction in monitor functions.
- **Advanced Testing:**
  - Inject custom test hooks/mocks for BLE, registry, and MQTT to simulate edge cases and failures.

---

## 7. Best Practices

- Always use atomic writes for registry updates to prevent corruption.
- Use thread-safe constructs (`registry_lock`) for concurrent access.
- Keep config values in `config.yaml` up to date and document any changes.
- Monitor logs for error events and address issues promptly.
- Use provided test hooks for robust CI and integration testing.

---

## 8. References

- Source: `addon/bb8_core/auto_detect.py`
- Config: `addon/config.yaml`
- Registry: `addon/bb8_core/bb8_device_registry.yaml`
- MQTT: Home Assistant MQTT integration

---

For further questions or troubleshooting, consult the module docstring in `auto_detect.py` or reach out to the project maintainers.
