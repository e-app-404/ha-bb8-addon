# beep_boop_bb8

Home Assistant add-on for controlling Sphero BB-8 via BLE and MQTT.

## Features

- BLE (Bluetooth Low Energy) control of Sphero BB-8
- MQTT command and status integration
- Home Assistant add-on compliant (configurable via UI)
- Supports BLE adapter selection and diagnostics

## Directory Structure

```text
beep_boop_bb8/
├── app/
│   └── test_ble_adapter.py
├── bb8_core/
│   └── ... (core Python modules)
├── .devcontainer/
│   ├── devcontainer.json
│   └── Dockerfile
├── run.sh
├── config.yaml
├── Dockerfile
├── README.md
```

## Development

- Devcontainer support: Open in VS Code for full Python, BLE, and HA add-on development.
- To validate BLE: `docker exec -it <container> python3 /app/test_ble_adapter.py`

## Usage

1. Build and install the add-on in Home Assistant.
2. Configure BLE adapter and MQTT options via the add-on UI.
3. Start the add-on and control BB-8 from Home Assistant automations or MQTT.
