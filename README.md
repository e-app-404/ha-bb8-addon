## Warning Suppression Strategy

We suppress the paho MQTT Callback API v1 DeprecationWarning using:
* PYTHONWARNINGS environment variable
* pytest.ini filterwarnings
* Code-level warning filters
* Refactored instantiation patterns

This ensures robust, maintainable suppression in all environments. See CALLBACK_API_v1.md for details.
<<<<<<< HEAD
# HA-BB8 Add-on: Local Build & Supervisor Integration

## Local Add-on Folder Structure
- Place your add-on in `/addons/local/beep_boop_bb8` on the Home Assistant host.
- Required files:
   - `config.yaml` (with `slug: "beep_boop_bb8"`)
   - `Dockerfile` (Debian base, see TROUBLESHOOTING_RECIPES.md for skeleton)
   - `run.sh` (entrypoint wrapper)

### Patch bump + publish + deploy

   - `SUBTREE_PUBLISH_OK:main@<sha>` — subtree publish succeeded
   - `AUTH_OK`, `CLEAN_RUNTIME_OK`, `DEPLOY_OK`, `VERIFY_OK`, `RUNTIME_TOPOLOGY_OK` — Home Assistant deploy and verification steps

* All release scripts are located in `ops/release/` and `ops/workspace/`.
* The workflow is idempotent: publishing is skipped if no changes are present in `addon/`.
* Makefile targets are tab-indented and ready for one-command releases.
---
Home Assistant add-on for controlling Sphero BB-8 via BLE and MQTT.

## Features

- BLE (Bluetooth Low Energy) control of Sphero BB-8
- MQTT command and status integration
- Home Assistant add-on compliant (configurable via UI)
- Supports BLE adapter selection and diagnostics
  - Presence sensor (`bb8/presence`)
  - RSSI sensor (`bb8/rssi`)
  - Power switch (`bb8/command/power`, `bb8/state/power`)
## Where do options come from?

- **Purpose:** Single source of truth for runtime config (MQTT host/port/creds, topic prefix, BLE adapter, timeouts, TLS).
- **Do not edit manually** in the container; change options in the UI and restart the add-on.

 Add-on runtime path: `/addons/local/beep_boop_bb8` (Home Assistant OS)
 Required files:
    - `config.yaml` (with `slug: "beep_boop_bb8"`)
    - `Dockerfile` (Debian base, see TROUBLESHOOTING_RECIPES.md for skeleton)
    - `run.sh` (entrypoint wrapper)
## Directory Structure
```text
 All deployment is performed via SSH and rsync (no git required on runtime).
 Machine-readable governance tokens are emitted in operational receipts:
    - `SUBTREE_PUBLISH_OK`, `CLEAN_RUNTIME_OK`, `DEPLOY_OK`, `VERIFY_OK`, `RUNTIME_TOPOLOGY_OK` (see `reports/deploy_receipt.txt`)
 Release scripts: `ops/release/deploy_ha_over_ssh.sh` (rsync + Supervisor API restart)
 Idempotent workflow: publishing is skipped if no changes in `addon/`.
 Makefile targets: tab-indented, one-command release and deploy.
 CI/CD coverage threshold enforced in `.github/workflows/repo-guards.yml`.
local/
│   ├── app/
 All operational steps emit tokens for CI and governance validation.
 See `docs/OPERATIONS_OVERVIEW.md` for full token contract and operational flow.
│   │   ├── bb8_bletest_diag.sh
│   │   ├── ble_test_diag.sh
│   │   └── test_ble_adapter.py
│   │   ├── bridge_controller.py
│   │   ├── controller.py
│   │   ├── core.py
│   │   ├── discovery.py
│   │   ├── discovery_publish.py
│   │   ├── evidence_capture.py
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
   - action: mqtt.publish
      data:
         topic: bb8/command/power

## BB-8 Add-on End-to-End Startup Flow

   - `run.sh` is executed as the entrypoint.

2. **Shell Entrypoint (`run.sh`)**
   - Loads config from `/data/options.json`.
   - Exports environment variables for all options (including `BB8_MAC_OVERRIDE`).
   - Prints startup diagnostics and environment.
4. Deploy updated code using `make release-patch` or `ops/release/deploy_ha_over_ssh.sh` (rsync-based, no git required on runtime).
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

## MQTT Library Version Policy
* Runtime dependency: **paho-mqtt >= 2.0, < 3.0** (pinned in `requirements.txt`).
* All `mqtt.Client` instantiations use `callback_api_version=CallbackAPIVersion.VERSION1` for v1 callback signatures (see CALLBACK_API_v1.md).
* If migrating to v2 callbacks later, switch to `CallbackAPIVersion.VERSION2` and update callback signatures accordingly.

### Local development quickstart
```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -U pip setuptools wheel
python -m pip install -r addon/requirements.txt -r addon/requirements-dev.txt
pytest --disable-warnings --cov=addon/bb8_core --cov-report=term-missing
```
