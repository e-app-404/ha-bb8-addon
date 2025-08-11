# beep_boop_bb8

Home Assistant add-on for controlling Sphero BB-8 via BLE and MQTT.

## Features

- BLE (Bluetooth Low Energy) control of Sphero BB-8
- MQTT command and status integration
- Home Assistant add-on compliant (configurable via UI)
- Supports BLE adapter selection and diagnostics
- MQTT Discovery for the following Home Assistant entities:
  - Presence sensor (`bb8/presence`)
  - RSSI sensor (`bb8/rssi`)
  - Power switch (`bb8/command/power`, `bb8/state/power`)

## Where do options come from?

- **Origin:** Home Assistant Supervisor generates `/data/options.json` from the add-on’s `config.yaml` schema and the values you set in the Add-on Options UI.
- **Author:** You (the HA admin) via the UI; Supervisor materializes the file inside the container.
- **Purpose:** Single source of truth for runtime config (MQTT host/port/creds, topic prefix, BLE adapter, timeouts, TLS).
- **Do not edit manually** in the container; change options in the UI and restart the add-on.

## Directory Structure

```text
local/
├─beep_boop_bb8/
├─── app/
│   └── test_ble_adapter.py
├─── bb8_core/
│   └── ... (core Python modules)
├─── .devcontainer/
│   ├── devcontainer.json
│   └── Dockerfile
├─── run.sh
├─── config.yaml
├─── Dockerfile
├─── README.md
```

## Development

- Devcontainer support: Open in VS Code for full Python, BLE, and HA add-on development.
- To validate BLE: `docker exec -it <container> python3 /app/test_ble_adapter.py`

## Usage

1. Build and install the add-on in Home Assistant.
2. Configure BLE adapter and MQTT options via the add-on UI.
3. Start the add-on and control BB-8 from Home Assistant automations or MQTT.

### Example Home Assistant Automation (2024.8+ syntax)

```yaml
action:
   - action: mqtt.publish
      data:
         topic: bb8/command/power
         payload: "ON"
```

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
     - `python -m bb8_core.bridge_controller --bb8-mac "$BB8_MAC_OVERRIDE" --scan-seconds "$BB8_SCAN_SECONDS" --rescan-on-fail "$BB8_RESCAN_ON_FAIL" --cache-ttl-hours "$BB8_CACHE_TTL_HOURS"`

3. **Python Entrypoint (`bb8_core/bridge_controller.py`)**
   - Parses CLI/environment for all options.
   - Calls `start_bridge_controller(...)`:
     - Initializes BLE gateway.
     - Instantiates `BLEBridge`.
     - Starts MQTT dispatcher.

4. **MAC Address Handling & Auto-Detect**
   - If a MAC is provided (`--bb8-mac`), it is used directly.
   - If empty/missing, the controller **calls `auto_detect.resolve_bb8_mac()`** to scan/cache/resolve the MAC.
   - Auto-detect logs: scan start, cache hits, discovery result, cache writes.

5. **MQTT Dispatcher**
   - Connects to broker, subscribes to command topics.
   - Publishes availability (`bb8/status`), presence and RSSI (if available).

6. **Runtime**
   - BLE and MQTT events handled by dispatcher and bridge.
   - All actions and errors are logged with structured JSON lines.
