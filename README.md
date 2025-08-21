# bb8_core

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
├─bb8_core/
│   ├── app/
│   │   ├── bb8_bletest_diag.sh
│   │   ├── ble_test_diag.sh
│   │   └── test_ble_adapter.py
│   ├── bb8_core/
│   │   ├── __init__.py
│   │   ├── addon_config.py
│   │   ├── auto_detect.py
│   │   ├── bb8_presence_scanner.py
│   │   ├── ble_bridge.py
│   │   ├── ble_gateway.py
│   │   ├── ble_link.py
│   │   ├── ble_utils.py
│   │   ├── bridge_controller.py
│   │   ├── controller.py
│   │   ├── core.py
│   │   ├── discovery.py
│   │   ├── discovery_publish.py
│   │   ├── evidence_capture.py
│   │   ├── facade.py
│   │   ├── logging_setup.py
│   │   ├── mqtt_dispatcher.py
│   │   ├── telemetry.py
│   │   ├── test_mqtt_dispatcher.py
│   │   ├── util.py
│   │   └── version_probe.py
│   ├── .devcontainer/
│   │   ├── Dockerfile
│   │   └── devcontainer.json
│   ├── ops/
│   │   ├── blebridge_handler_surface_check.py
│   │   ├── delta_contract.yaml
│   │   ├── entity_set.json
│   │   ├── entity_set_extended.json
│   │   ├── evidence/
│   │   │   ├── collect_stp4.py
│   │   │   └── evidence_capture.py
│   │   ├── facade_mapping_table.json
│   │   ├── intervention_plan.json
│   │   ├── strategic_assessment.json
│   │   └── test_facade_attach_mqtt.py
│   ├── reports/
│   │   └── (various .json and stp4_* evidence bundles)
│   ├── services.d/
│   │   └── ble_bridge/
│   │       └── run
│   ├── tests/
│   │   ├── test_facade.py
│   │   └── test_mqtt_smoke.py
│   ├── CHANGELOG.md
│   ├── Dockerfile
│   ├── Makefile
│   ├── README.md
│   ├── apparor.txt
│   ├── config.yaml
│   ├── copilot_patch_overview.log
│   ├── pyproject.toml
│   ├── requirements-dev.txt
│   ├── requirements.in
│   ├── requirements.txt
│   ├── run.sh
│   ├── scan_bb8_gatt.py
│   ├── tox.ini
```

## Configuration System

- All runtime config is unified via `bb8_core/addon_config.py`, which loads from `/data/options.json`, environment, and YAML, with provenance logging.
- MQTT topics, client IDs, device names, and toggles (e.g., telemetry) are dynamically constructed from config. No hardcoded prefixes remain.
- Telemetry publishing is controlled by `ENABLE_BRIDGE_TELEMETRY` and `ENABLE_SCANNER_TELEMETRY`, both loaded via the config loader.

## Evidence Collection

- Evidence scripts live in `ops/evidence/`, and can be run via Makefile (`make evidence-stp4`). Output is stored in `reports/`.
- See `CHANGELOG.md` for recent config and evidence system changes.

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
