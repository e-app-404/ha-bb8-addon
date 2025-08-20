## BB-8 Add-on End-to-End Startup Flow

1. **Container Startup**
   - S6 supervisor starts the add-on container.
   - `run.sh` is executed as the entrypoint.

2. **Shell Entrypoint (`run.sh`)**
   - Loads config from `/data/options.json`.
   - Exports environment variables for all options (including `BB8_MAC_OVERRIDE`).
   - Prints startup diagnostics and environment.
   - Runs BLE adapter check.
   - Starts the main Python service:
     - `python -m bb8_core.bridge_controller ...`

3. **Python Entrypoint (`bb8_core/bridge_controller.py`)**
   - Parses CLI/environment for all options.
   - Calls `start_bridge_controller(...)`:
     - Initializes BLE gateway.
     - Instantiates `BLEBridge`.
     - Starts MQTT dispatcher.

4. **BLEBridge/Controller Logic**
   - **MAC Address Handling:**
     - If `bb8_mac` is provided, it is used directly.
     - If `bb8_mac` is empty, should call `auto_detect.resolve_bb8_mac()` to scan/cache/resolve MAC.
     - (Current implementation may not trigger scan if MAC is empty—needs validation/fix.)
   - **Auto-Detect/Scan Logic (in `auto_detect.py`):**
     - If override is empty, checks cache.
     - If cache is invalid/missing, scans for BB-8 devices.
     - Logs all actions: scan start, scan winner, cache hit, etc.

5. **MQTT Dispatcher (`bb8_core/mqtt_dispatcher.py`)**
   - **Connects to MQTT broker** (with fallback to core-mosquitto/localhost, robust retry).
   - **Publishes Home Assistant MQTT Discovery topics** for all BB-8 entities (presence, RSSI, power, etc.).
   - **Subscribes to command topics** (e.g., `bb8/command`, `bb8/command/power`).
   - **Handles incoming MQTT messages:**
     - On `bb8/command/power`:
       - If payload is `ON`, calls `bb8_power_on_sequence()` (turns on BB-8, triggers BLE connect/scan).
       - If payload is `OFF`, calls `bb8_power_off_sequence()` (puts BB-8 to sleep).
       - Logs all command handling, including errors and unknown payloads.

---

## Type Checking (mypy)

To avoid duplicate module errors, always run mypy from the parent directory:

```zsh
cd /Volumes/addons/local
PYTHONPATH=/Volumes/addons/local mypy beep_boop_bb8
```

Or use the provided `.env` file:

```zsh
cd /Volumes/addons/local
export $(cat beep_boop_bb8/.env)
mypy beep_boop_bb8
```

This ensures only the correct import path (`beep_boop_bb8.bb8_core`) is used.
     - On other command topics:
       - Parses JSON payload for a `command` field.
       - Dispatches to the appropriate method on the BLE bridge/controller (`roll`, `stop`, `set_led`).
       - Logs command dispatch, results, and errors.

- **Publishes status** to the status topic (e.g., `bb8/status`), including diagnostics from the BLE bridge.
- **Handles disconnects** with automatic reconnect and logging.
- **All actions, errors, and state changes are logged** at INFO or DEBUG level for full traceability.

6. **BLE/MQTT Runtime**
   - BLE bridge and controller handle all BLE operations (connect, scan, cache, command execution).
   - MQTT dispatcher continues to process messages and publish status.
   - All events, errors, and diagnostics are logged to both file and console.

---

**Note:**

- The dispatcher is the main event loop for MQTT and BLE integration.
- All MQTT commands, BLE actions, and status updates are logged for audit and debugging.
- If BB-8 MAC is not set, the BLE bridge/controller should trigger auto-detect/scan logic (ensure this is wired up and logged).

---

**Note:**

- If `bb8_mac` is empty, the controller/bridge must call the auto-detect logic and log the scan process.
- Current logs do not show scan/auto-detect events, indicating this may not be wired up or logged as expected.

---

## Next Steps

- [ ] Ensure `auto_detect.resolve_bb8_mac()` is called if `bb8_mac` is empty.
- [ ] Add granular logging at each step: when scanning starts, when a MAC is resolved, when cache is used, etc.
- [ ] Validate that logs show the full MAC resolution process on startup.
