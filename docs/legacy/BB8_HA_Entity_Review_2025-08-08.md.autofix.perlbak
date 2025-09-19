# BB-8 Home Assistant Add-on: Entity & State Review

**Codebase Version:** 0.3.1 (2025-08-08)
**Artifact Purpose:** Document the current state of BB-8 add-on integration, Home Assistant entities, and identify gaps/opportunities for future investment.

---

## 1. Overview

This document reviews the Home Assistant integration for the Sphero BB-8 add-on as of version 0.3.1, following the unified background scan, MQTT Discovery, and robust error/diagnostic patch set. It provides:

- A mapping of all entities surfaced via MQTT Discovery
- A summary of which BB-8 states/actions are available to Home Assistant
- Gaps and recommendations for future development

---

## 2. Entities Surfaced via MQTT Discovery

| Entity                        | Domain         | Purpose/State                | Source Component         |
|-------------------------------|---------------|------------------------------|-------------------------|
| `binary_sensor.bb8_presence`  | binary_sensor | BLE presence (on/off)        | bb8_presence_scanner.py |
| `sensor.bb8_rssi`             | sensor        | BLE signal strength (dBm)    | bb8_presence_scanner.py |
| `sensor.bb8_error_state`      | sensor        | Last error message           | ble_bridge.py           |
| `sensor.bb8_heartbeat`        | sensor        | Heartbeat/status             | ble_bridge.py           |
| `switch.bb8_power`            | switch        | Power on/off (optimistic)    | ble_bridge.py           |
| `light.bb8_led`               | light         | RGB LED control (optimistic) | ble_bridge.py           |
| `button.bb8_roll`             | button        | Trigger roll action          | ble_bridge.py           |
| `button.bb8_stop`             | button        | Trigger stop action          | ble_bridge.py           |

---

## 3. State Feedback: What is and isn't Available

### Available (Post-Fix)

- **Presence:** Real-time BLE presence detection
- **RSSI:** Real-time signal strength
- **Error State:** Last error surfaced to HA
- **Heartbeat:** Add-on keepalive/status
- **Power, LED, Roll, Stop:** All controllable from HA via native entities

### Not Available (Gaps)

- **Rolling/Movement State:** No entity reflects if BB-8 is actively rolling
- **Direction/Heading:** No entity for current heading or direction
- **LED State Feedback:** No feedback of actual LED color from device (optimistic)
- **Power State Feedback:** No feedback of actual power state from device (optimistic)
- **Battery Level:** Not surfaced as an entity
- **Advanced Diagnostics:** No entity for firmware version, error codes, etc.

---

## 4. Recommendations & Investment Areas

1. **Rolling State:**
   - Add-on should publish a state (e.g., `bb8/state/rolling`) and surface as `binary_sensor.bb8_rolling`.
   - Enables automations and UI to reflect when BB-8 is moving.

2. **Direction/Heading:**
   - If available from the protocol, publish as `sensor.bb8_heading`.

3. **LED/Power Feedback:**
   - If device supports state readback, publish actual LED color and power state.
   - Otherwise, document as "optimistic" in UI.

4. **Battery Level:**
   - If available, surface as `sensor.bb8_battery`.

5. **Diagnostics/Version:**
   - Surface firmware version, error codes, and other diagnostics as sensors.

6. **Documentation:**
   - Keep this artifact updated with each release and major patch.
   - Reference this file in README and onboarding docs for clarity.

---

## 5. References

- Add-on codebase: `/Volumes/HA/addons/local/beep_boop_bb8/`
- Home Assistant package: `/Volumes/HA/config/packages/package_bb8.yaml`
- Main components: `bb8_presence_scanner.py`, `ble_bridge.py`
- Entities: See above table

---

**Maintainer:** GitHub Copilot (2025-08-08)
