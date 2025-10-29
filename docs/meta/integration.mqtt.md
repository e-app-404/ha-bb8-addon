---
id: "HA-INTEGRATION-MQTT-01"
title: "Home Assistant MQTT Integration and Configuration Guide"
authors: "Home Assistant Community"
source: "https://www.home-assistant.io/integrations/mqtt/"
slug: "ha-mqtt-configuration-info"
type: "reference"
tags: ["mqtt", "home-assistant", "integration", "configuration"]
date: "2024-06-01"
last_updated: "2024-06-09"
url: "https://www.home-assistant.io/integrations/mqtt/"
related: ""
adr: ""
---

# Home Assistant MQTT Integration and Configuration Guide

MQTT (Message Queuing Telemetry Transport) is a lightweight, publish/subscribe messaging protocol designed for machine-to-machine (M2M) and Internet of Things (IoT) connectivity over TCP/IP.

## Table of Contents

- [Overview](#overview)
- [Configuration](#configuration)
  - [Adding the MQTT Integration](#adding-the-mqtt-integration)
  - [Manual Configuration Steps](#manual-configuration-steps)
  - [MQTT Discovery vs YAML Configuration](#mqtt-discovery-vs-yaml-configuration)
- [Setting Up a Broker](#setting-up-a-broker)
  - [Recommended: Mosquitto Broker Add-on](#recommended-mosquitto-broker-add-on)
  - [Broker Configuration](#broker-configuration)
  - [Advanced Broker Configuration](#advanced-broker-configuration)
- [MQTT Protocol and Security](#mqtt-protocol-and-security)
  - [MQTT Protocol Version](#mqtt-protocol-version)
  - [Securing the Connection](#securing-the-connection)
  - [WebSockets as Transport](#websockets-as-transport)
- [Configuring MQTT Options](#configuring-mqtt-options)
  - [Changing MQTT Discovery Options](#changing-mqtt-discovery-options)
  - [Birth and Last Will Messages](#birth-and-last-will-messages)
- [Testing Your Setup](#testing-your-setup)
- [MQTT Discovery](#mqtt-discovery)
  - [Discovery Topic Format](#discovery-topic-format)
  - [Device Discovery Payload](#device-discovery-payload)
  - [Migration to Device-Based Discovery](#migration-to-device-based-discovery)
  - [Single Component Discovery Payload](#single-component-discovery-payload)
- [Discovery Examples](#discovery-examples)
  - [Binary Sensor Example](#binary-sensor-example)
  - [Sensor Example](#sensor-example)
  - [Switch Example](#switch-example)
  - [Abbreviations and Base Topic](#abbreviations-and-base-topic)
  - [Object ID Usage](#object-id-usage)
- [Support by Third-Party Tools](#support-by-third-party-tools)
- [Manual Configuration in YAML](#manual-configuration-in-yaml)
- [Entity State Updates](#entity-state-updates)
- [Using Templates](#using-templates)
- [Publish & Dump Actions](#publish--dump-actions)
- [Logging](#logging)
- [Removing the Integration](#removing-the-integration)
- [Feedback](#feedback)

---

## Overview

MQTT is a lightweight protocol for publish/subscribe messaging, ideal for IoT and automation scenarios. Home Assistant supports MQTT integration for device and entity control, automation, and telemetry.

## Configuration

### Adding the MQTT Integration

To add the MQTT integration to your Home Assistant instance, use the "My" button or follow the manual steps below.

### Manual Configuration Steps

MQTT devices and entities can be set up via MQTT Discovery or added manually using YAML or subentries.

#### MQTT Discovery vs YAML Configuration

- **MQTT Discovery:** Devices and entities are automatically discovered and configured via MQTT messages.
- **YAML Configuration:** Devices and entities are manually defined in YAML files.

## Setting Up a Broker

### Recommended: Mosquitto Broker Add-on

The easiest and most private option is to run your own broker using the official Mosquitto Broker add-on. Home Assistant can automatically generate and assign credentials. Additional logins can be configured via the Mosquitto add-on.

> **Important**: If you reinstall the Mosquitto add-on, save a copy of user options (including additional logins). Home Assistant will update credentials automatically after reinstall.

Alternatively, you may use a different MQTT broker, ensuring compatibility with Home Assistant.

> **Warning**: Neither ActiveMQ MQTT broker nor RabbitMQ MQTT Plugin are supported. Use a known working broker like Mosquitto.

### Broker Configuration

Broker settings are configured during MQTT integration setup and can be changed later:

1. Go to **Settings > Devices & Services**.
2. Select the MQTT integration.
3. Click **Reconfigure** to update broker settings.

MQTT subentries can also be reconfigured. Each subentry holds one MQTT device with at least one entity.

> **Important**: For SSL errors (e.g., `[SSL: CERTIFICATE_VERIFY_FAILED]`), enable Advanced options and set Broker certificate validation to Auto.

### Advanced Broker Configuration

Advanced options include setting a custom client ID, client certificate/key, and enabling TLS validation.

- Enable advanced mode in user settings to access these options.
- Custom client IDs must be unique.
- Default keep alive is 60 seconds (minimum 15 seconds).
- Broker certificate validation can be set to Auto (trusted CA) or Custom (self-signed).
- WebSockets transport is supported if your broker allows it.

> **Tip**: Client certificates are only active if broker certificate validation is enabled.

## MQTT Protocol and Security

### MQTT Protocol Version

- Default protocol is MQTT 3.1.1.
- If your broker supports MQTT 5, you can select version 5.

### Securing the Connection

- Enable secure connections with client certificates and private keys (PEM or DER-encoded).
- If the private key is encrypted, provide the password during upload.

### WebSockets as Transport

- WebSockets can be used as a transport method if supported by your broker.
- Configure WebSockets path and headers as needed.
- WebSockets transport can be secured with TLS and credentials.

## Configuring MQTT Options

To change MQTT options:

1. Go to **Settings > Devices & Services**.
2. Select the MQTT integration.
3. Click **Configure**, then **Re-configure MQTT**.
4. Click **Next** to access options.

### Changing MQTT Discovery Options

1. Go to **Settings > Devices & Services**.
2. Select the MQTT integration.
3. Click **Configure MQTT Options**.
4. Change discovery options as needed.

- MQTT discovery is enabled by default.
- The discovery topic prefix (default: `homeassistant`) can be changed.

### Birth and Last Will Messages

Home Assistant supports Birth and Last Will and Testament (LWT) messages to signal service startup and disconnects.

- LWT is sent on both clean and unclean disconnects.
- Devices should subscribe to the Birth message and use it to trigger discovery payloads.
- Retaining the discovery payload or periodically resending it are alternative approaches.

> **Important**: Excessive retained messages can cause high IO loads or ghost entities.

## Testing Your Setup

Use the `mosquitto_pub` and `mosquitto_sub` command-line tools to send and receive MQTT messages.

```bash
# Publish a test message
mosquitto_pub -h 127.0.0.1 -t homeassistant/switch/1/on -m "Switch is ON"

# Subscribe to all messages
mosquitto_sub -h 127.0.0.1 -v -t "homeassistant/#"
```

You can also use the Home Assistant frontend to publish and listen to MQTT topics.

## MQTT Discovery

### Discovery Topic Format

The discovery topic must follow this format:

```
<discovery_prefix>/<component>/[<node_id>/]<object_id>/config
```

- `<discovery_prefix>`: Defaults to `homeassistant`.
- `<component>`: Supported MQTT integration (e.g., `binary_sensor`).
- `<node_id>`: Optional node identifier.
- `<object_id>`: Device identifier.

Best practice: Set `<object_id>` to `unique_id` and omit `<node_id>` for entities with a unique ID.

### Device Discovery Payload

A device can send a discovery payload to expose all components. Example:

```json
{
  "dev": {
    "ids": "ea334450945afc",
    "name": "Kitchen",
    "mf": "Bla electronics",
    "mdl": "xya",
    "sw": "1.0",
    "sn": "ea334450945afc",
    "hw": "1.0rev2"
  },
  "o": {
    "name": "bla2mqtt",
    "sw": "2.1",
    "url": "https://bla2mqtt.example.com/support"
  },
  "cmps": {
    "temp_sensor": {
      "p": "sensor",
      "device_class": "temperature",
      "unit_of_measurement": "°C",
      "value_template": "{{ value_json.temperature }}",
      "unique_id": "temp01ae_t"
    },
    "humidity_sensor": {
      "p": "sensor",
      "device_class": "humidity",
      "unit_of_measurement": "%",
      "value_template": "{{ value_json.humidity }}",
      "unique_id": "temp01ae_h"
    }
  },
  "state_topic": "sensorBedroom/state",
  "qos": 2
}
```

- To remove a component, publish an empty (retained) string payload to the discovery topic.
- After removing, send an updated config omitting the removed component.

### Migration to Device-Based Discovery

To migrate from single component to device-based discovery:

1. Ensure all entities have a `unique_id` and device context.
2. Publish `{"migrate_discovery": true}` to existing single component discovery topics.
3. Switch to device-based discovery topic and include all component configs.
4. Clean up single component discovery messages with an empty payload.

> **Important**: Test migration in a non-production environment.

### Single Component Discovery Payload

Example:

```json
{
  "dev": {
    "ids": "ea334450945afc",
    "name": "Kitchen",
    "mf": "Bla electronics",
    "mdl": "xya",
    "sw": "1.0",
    "sn": "ea334450945afc",
    "hw": "1.0rev2"
  },
  "o": {
    "name": "bla2mqtt",
    "sw": "2.1",
    "url": "https://bla2mqtt.example.com/support"
  },
  "device_class": "temperature",
  "unit_of_measurement": "°C",
  "value_template": "{{ value_json.temperature }}",
  "unique_id": "temp01ae_t",
  "state_topic": "sensorBedroom/state",
  "qos": 2
}
```

## Discovery Examples

### Binary Sensor Example

```json
{
  "name": null,
  "device_class": "motion",
  "state_topic": "homeassistant/binary_sensor/garden/state",
  "unique_id": "motion01ad",
  "device": {
    "identifiers": ["01ad"],
    "name": "Garden"
  }
}
```

Publish with retain:

```bash
mosquitto_pub -r -h 127.0.0.1 -p 1883 -t "homeassistant/binary_sensor/garden/config" -m '{...}'
```

Update state:

```bash
mosquitto_pub -h 127.0.0.1 -p 1883 -t "homeassistant/binary_sensor/garden/state" -m ON
```

Delete sensor:

```bash
mosquitto_pub -h 127.0.0.1 -p 1883 -t "homeassistant/binary_sensor/garden/config" -m ''
```

### Sensor Example

```json
{
  "device_class": "temperature",
  "state_topic": "homeassistant/sensor/sensorBedroom/state",
  "unit_of_measurement": "°C",
  "value_template": "{{ value_json.temperature }}",
  "unique_id": "temp01ae",
  "device": {
    "identifiers": ["bedroom01ae"],
    "name": "Bedroom",
    "manufacturer": "Example sensors Ltd.",
    "model": "Example Sensor",
    "model_id": "K9",
    "serial_number": "12AE3010545",
    "hw_version": "1.01a",
    "sw_version": "2024.1.0",
    "configuration_url": "https://example.com/sensor_portal/config"
  }
}
```

### Switch Example

```json
{
  "name": "Irrigation",
  "command_topic": "homeassistant/switch/irrigation/set",
  "state_topic": "homeassistant/switch/irrigation/state",
  "unique_id": "irr01ad",
  "device": {
    "identifiers": ["garden01ad"],
    "name": "Garden"
  }
}
```

Publish with retain:

```bash
mosquitto_pub -r -h 127.0.0.1 -p 1883 -t "homeassistant/switch/irrigation/config" -m '{...}'
```

Set state:

```bash
mosquitto_pub -h 127.0.0.1 -p 1883 -t "homeassistant/switch/irrigation/set" -m ON
```

### Abbreviations and Base Topic

Example using abbreviations and base topic:

```json
{
  "~": "homeassistant/light/kitchen",
  "name": "Kitchen",
  "uniq_id": "kitchen_light",
  "cmd_t": "~/set",
  "stat_t": "~/state",
  "schema": "json",
  "brightness": true,
  "dev": {
    "ids": "ea334450945afc",
    "name": "Kitchen",
    "mf": "Bla electronics",
    "mdl": "xya",
    "mdl_id": "ABC123",
    "sw": "1.0",
    "sn": "ea334450945afc",
    "hw": "1.0rev2"
  },
  "o": {
    "name": "bla2mqtt",
    "sw": "2.1",
    "url": "https://bla2mqtt.example.com/support"
  }
}
```

### Object ID Usage

Set `object_id` to influence the entity ID:

```json
{
  "name": "My Super Device",
  "object_id": "my_super_device",
  "state_topic": "homeassistant/sensor/device1/state"
}
```

Entity ID will be `sensor.my_super_device`.

## Support by Third-Party Tools

The following software supports MQTT discovery:

- ArduinoHA
- Arilux AL-LC0X LED controllers
- ble2mqtt
- diematic_server
- digitalstrom-mqtt
- ebusd
- ecowitt2mqtt
- EMS-ESP32 (and EMS-ESP)
- ESPHome
- ESPurna
- go-iotdevice
- HASS.Agent
- IOTLink (2.0.0+)
- MiFlora MQTT Daemon
- MyElectricalData
- MqDockerUp
- Nuki Hub
- Nuki Smart Lock 3.0 Pro
- OpenMQTTGateway
- OTGateway
- room-assistant (1.1.0+)
- SmartHome
- SpeedTest-CLI MQTT
- SwitchBot-MQTT-BLE-ESP32
- Tasmota (5.11.1e+)
- TeddyCloud
- Teleinfo MQTT (3.0.0+)
- Tydom2MQTT
- What’s up Docker? (3.5.0+)
- WyzeSense2MQTT
- Xiaomi DaFang Hacks
- Zehnder Comfoair RS232 MQTT
- Zigbee2MQTT

Other software (e.g., Domoticz, openHAB) can consume MQTT discovery information intended for Home Assistant.

## Manual Configuration in YAML

MQTT supports two YAML configuration styles:

**List Style (recommended):**

```yaml
mqtt:
  - switch:
      name: "..."
  - sensor:
      name: "..."
```

**Domain-Bundled Style:**

```yaml
mqtt:
  switch:
    - name: "..."
    - name: "..."
```

Do not mix styles. For large configs, consider splitting configuration.

## Entity State Updates

Entities receive state updates via MQTT subscriptions. Payloads are processed to determine significant changes. Retained messages are replayed on restart.

- MQTT does not update `last_reported` unless `force_update` is set.
- Use a sensor to measure last update if needed.

## Using Templates

The MQTT integration supports templating for payloads. See the [Home Assistant documentation](https://www.home-assistant.io/docs/configuration/templating/) for details.

## Publish & Dump Actions

The `mqtt.publish` action allows publishing messages to MQTT topics.

```yaml
action: mqtt.publish
data:
  topic: homeassistant/sensor/Acurite-986-1R-51778/config
  payload: >-
    {"device_class": "temperature",
     "unit_of_measurement": "°C",
     "value_template": "{{ value|float }}",
     "state_topic": "rtl_433/rtl433/devices/Acurite-986/1R/51778/temperature_C",
     "unique_id": "Acurite-986-1R-51778-T",
     "device": {
       "identifiers": "Acurite-986-1R-51778",
       "name": "Bathroom",
       "model": "Acurite",
       "model_id": "986",
       "manufacturer": "rtl_433"
     }
    }
```

**Attributes:**

- `topic` (required): Topic to publish to.
- `payload` (optional): Payload to publish.
- `evaluate_payload` (optional): Evaluate bytes literal as raw data.
- `qos` (optional): Quality of Service (default: 0).
- `retain` (optional): Retain flag (default: false).

The `mqtt.dump` action listens to a topic matcher and dumps messages to `mqtt_dump.txt` for debugging.

## Logging

Enable debug logging for MQTT:

```yaml
logger:
  default: warning
  logs:
    homeassistant.components.mqtt: debug
```

## Removing the Integration

1. Go to **Settings > Devices & Services**.
2. Select the MQTT integration.
3. Click the three dots menu and select **Delete**.

> **Note**: This does not remove the MQTT broker or its data. Remove MQTT-related configs from `configuration.yaml` and review automations/scripts as needed.

## Feedback

Help improve this documentation by suggesting edits or providing feedback.

---
