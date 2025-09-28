---
title: "MQTT Integration"
authors: "Home Assistant"
source: "Home Assistant Docs"
slug: "mqtt-integration-guide"
tags: ["home-assistant","mqtt","integration","mosquitto","discovery","ops"]
original_date: "2022-04-05"
last_updated: "2025-09-28"
url: "https://www.home-assistant.io/integrations/mqtt/"
---

# MQTT Integration

MQTT (aka MQ Telemetry Transport) is a machine-to-machine or "Internet of Things" connectivity protocol on top of TCP/IP. It allows extremely lightweight publish/subscribe messaging transport.

## Configuration
To add the MQTT integration to your Home Assistant instance, use this My button:

### Manual configuration steps

MQTT Devices and entities can be set up through MQTT discovery or added manually via YAML or subentries.

- Configuration of MQTT components via MQTT discovery
- Configuration of MQTT components via YAML

Your first step to get MQTT and Home Assistant working is to choose a broker.

The easiest option is to install the official Mosquitto Broker add-on. You can choose to set up and configure this add-on automatically when you set up the MQTT integration. Home Assistant will automatically generate and assign a safe username and password, and no further attention is required. This also works if you have already set up this add-on yourself in advance. You can set up additional logins for your MQTT devices and services using the Mosquitto add-on configuration.

> **Important**

When MQTT is set up with the official Mosquitto MQTT broker add-on, the broker’s credentials are generated and kept secret. If the official Mosquitto MQTT broker needs to be re-installed, make sure you save a copy of the add-on user options, like the additional logins. After re-installing the add-on, the MQTT integration will automatically update the new password for the re-installed broker. It will then reconnect automatically.

Alternatively, you can use a different MQTT broker that you configure yourself, ensuring it is compatible with Home Assistant.

### Setting up a broker

While public MQTT brokers are available, the easiest and most private option is running your own.

The recommended setup method is to use the Mosquitto MQTT broker add-on.

> **Warning**

> Neither ActiveMQ MQTT broker nor the RabbitMQ MQTT Plugin are supported, use a known working broker like Mosquitto instead. There are at least two issues with the ActiveMQ MQTT broker which break MQTT message retention.

### Broker configuration

MQTT broker settings are configured when the MQTT integration is first set up and can be changed later if needed.

Add the MQTT integration, then provide your broker's hostname (or IP address) and port and (if required) the username and password that Home Assistant should use. To change the settings later, follow these steps:

1. Go to **Settings > Devices & services**
2. Select the **MQTT integration**
3. Reconfigure the MQTT broker settings via **Settings > Devices & services**, click and select **Reconfigure**

MQTT subentries can also be reconfigured. Additional entities can be added, or an entity can be removed from the sub entry. Each MQTT subentry holds one MQTT device. The MQTT device must have at least one entity.

> **Important**

> If you experience an error message like `Failed to connect due to exception: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed`, then turn on **Advanced options** and set **Broker certificate validation** to **Auto**.

### Advanced broker configuration

Advanced broker configuration options include setting a custom client ID, setting a client certificate and key for authentication, and enabling TLS validation of the broker's certificate for secure connection. To access the advanced settings, open the MQTT broker settings, switch on **Advanced options** and click **Next**. The advanced options will be shown by default if there are advanced settings active already.

> **Tip**

> Advanced broker options are accessible only when advanced mode is enabled (see user settings), or when advanced broker settings are configured already.

#### Alternative client ID

You can set a custom MQTT client ID, this can help when debugging. Mind that the client ID must be unique. Leave this settings default if you want Home Assistant to generate a unique ID.

#### Keep alive

The time in seconds between sending keep alive messages for this client. The default is 60 seconds. The keep alive setting should be minimal 15 seconds.

#### Broker certificate validation

To enable a secure connection to the broker, the broker certificate should be validated. If your broker uses a trusted certificate, then choose **Auto**. This will allow validation against certificate CAs bundled certificates. If a self-signed certificate is used, select **Custom**. A custom PEM- or DER-encoded CA certificate can be uploaded. Click **NEXT** to show the control to upload the CA certificate. If the server certificate does not match the hostname then validation will fail. To allow a connection without the verification of the hostname, turn the **Ignore broker certificate validation** switch on.

#### MQTT Protocol

The MQTT protocol setting defaults to version 3.1.1. If your MQTT broker supports MQTT version 5 you can set the protocol setting to 5.

#### Securing the connection

With a secure broker connection, it is possible to use a client certificate for authentication. To set the client certificate and private key turn on the option **Use a client certificate** and click **Next** to reveal file upload controls. A client certificate and the corresponding private key must be uploaded together. Both client certificate and private key must be either PEM- or DER-encoded. If the private key is encrypted with a password, ensure you supply the correct password when uploading the client certificate and key files.

#### Using WebSockets as transport

You can select websockets as transport method if your MQTT broker supports it. When you select websockets and click **NEXT**, you will be able to add a WebSockets path (default = /) and WebSockets headers (optional). The target WebSockets URI: `ws://{broker}:{port}{WebSockets path}` is built with broker, port and ws_path (WebSocket path) settings. To configure the WebSocket's headers supply a valid JSON dictionary string. E.g. `{ "Authorization": "token" , "x-header": "some header"}`. The default transport method is tcp. The WebSockets transport can be secured using TLS and optionally using user credentials or a client certificate.

> **Note**

> A configured client certificate will only be active if broker certificate validation is enabled.

### Configure MQTT options

To change the options, follow these steps:

1. Go to **Settings > Devices & services**
2. Select the **MQTT integration**
3. Select **Configure**, then **Re-configure MQTT**
4. To open the MQTT options page, select **Next**

#### Change MQTT discovery options

The MQTT discovery options can be changed by following these steps:

1. Go to **Settings > Devices & services**
2. Find the **MQTT integration** and select it
3. To open the MQTT discovery options page, select the **Configure MQTT Options** button
#### Discovery options

MQTT discovery is enabled by default. Discovery can be turned off. The prefix for the discovery topic (default `homeassistant`) can be changed here as well. See also MQTT Discovery section.

#### Birth and last will messages

Home Assistant's MQTT integration supports so-called Birth and Last Will and Testament (LWT) messages. The former is used to send a message after the service has started, and the latter is used to notify other clients about a disconnected client. Please note that the LWT message will be sent both in case of a clean (e.g. Home Assistant shutting down) and in case of an unclean (e.g. Home Assistant crashing or losing its network connection) disconnect.

If a disabled entity is enabled and added after 30 seconds, the MQTT integration will be reloaded and will cause all discovered MQTT entities to be unloaded. When MQTT starts up, all existing MQTT devices, entities, tags, and device triggers, will be unavailable until a discovery message is received and processed. A device or service that exposes the MQTT discovery should subscribe to the Birth message and use this as a trigger to send the discovery payload. To avoid high IO loads on the MQTT broker, adding some random delay in sending the discovery payload is recommended.

Alternative approaches:

Retaining the discovery payload: This will store the discovery payload at the MQTT broker, and offer it to the MQTT integration as soon as it subscribes for MQTT discovery. When there are a lot of entities, this can cause high IO loads.
Periodically resending the discovery payload: This can cause some delay, or a lot of IO if there are a lot of MQTT discovery messages.
By default, Home Assistant sends `online` and `offline` to `homeassistant/status`.

MQTT Birth and Last Will messages can be customized or disabled from the UI. To do this, click on **Configure** in the integration page in the UI, then **Re-configure MQTT** and then **Next**.

## Testing your setup

The mosquitto broker package ships command line tools (often as `*-clients` package) to send and receive MQTT messages. For sending test messages to a broker running on localhost, you can use `mosquitto_pub`, check the example below:

mosquitto_pub -h 127.0.0.1 -t homeassistant/switch/1/on -m "Switch is ON"
Bash

Another way to send MQTT messages manually is to use the MQTT integration in the frontend. Choose “Settings” on the left menu, click “Devices & services”, and choose “Configure” in the “Mosquitto broker” tile. Enter something similar to the example below into the “topic” field under “Publish a packet” and press “PUBLISH” .

Go to Settings > Devices & services.
Select the Mosquitto broker integration, then select Configure.
Enter something similar to the example below into the topic field under Publish a packet. Select Publish.

```bash
homeassistant/switch/1/power
```

and in the Payload field

```bash
ON
```

In the “Listen to a topic” field, type # to see everything, or “homeassistant/switch/#” to just follow a published topic, then press “START LISTENING”. The messages should appear similar to the text below:

```bash
Message 23 received on homeassistant/switch/1/power/stat/POWER at 12:16 PM:
ON
QoS: 0 - Retain: false
Message 22 received on homeassistant/switch/1/power/stat/RESULT at 12:16 PM:
ON
```

In the “Listen to a topic” field, type # to see everything, or “homeassistant/switch/#” to just follow a published topic, then press “START LISTENING”. The messages should appear similar to the text below:

```bash
Message 23 received on homeassistant/switch/1/power/stat/POWER at 12:16 PM:
ON
QoS: 0 - Retain: false
Message 22 received on homeassistant/switch/1/power/stat/RESULT at 12:16 PM:
{
    "POWER": "ON"
}
QoS: 0 - Retain: false
```

For reading all messages sent on the topic `homeassistant` to a broker running on localhost:

```bash
mosquitto_sub -h 127.0.0.1 -v -t "homeassistant/#"
```

## Sharing of device configuration

MQTT entities can share device configuration, meaning one entity can include the full device configuration and other entities can link to that device by only setting mandatory fields. The mandatory fields were previously limited to at least one of connection and identifiers, but have now been extended to at least one of connection and identifiers as well as the name.

## Naming of MQTT Entities

For every configured MQTT entity Home Assistant automatically assigns a unique `entity_id`. If the `unique_id` option is configured, you can change the `entity_id` after creation, and the changes are stored in the Entity Registry. The `entity_id` is generated when an item is loaded the first time.

If the `object_id` option is set, then this will be used to generate the `entity_id`. If, for example, we have configured a sensor, and we have set object_id to test, then Home Assistant will try to assign sensor.test as `entity_id`, but if this `entity_id` already exits it will append it with a suffix to make it unique, for example, sensor.test_2.

This means any MQTT entity which is part of a device will automatically have its `friendly_name` attribute prefixed with the device name

Unnamed binary_sensor, button, number and sensor entities will now be named by their device class instead of being named “MQTT binary sensor” etc. It’s allowed to set an MQTT entity’s name to None (use null in YAML) to mark it as the main feature of a device.

Note that on each MQTT entity, the `has_entity_name` attribute will be set to `True`. More details can be found [here](https://developers.home-assistant.io/docs/core/entity#has-entity-name).

## MQTT Discovery

The discovery of MQTT devices will enable one to use MQTT devices with only minimal configuration effort on the side of Home Assistant. The configuration is done on the device itself and the topic used by the device. Similar to the HTTP binary sensor and the HTTP sensor. To prevent multiple identical entries if a device reconnects, a unique identifier is necessary. Two parts are required on the device side: The configuration topic which contains the necessary device type and unique identifier, and the remaining device configuration without the device type.

MQTT discovery is enabled by default, but can be disabled. The prefix for the discovery topic (default `homeassistant`) can be changed. See the MQTT Options sections.

> **Note**

> Documentation on the MQTT components that support MQTT discovery can be found [here](https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery).

### Discovery messages

#### Discovery topic

The discovery topic needs to follow a specific format:

```bash
<discovery_prefix>/<component>/[<node_id>/]<object_id>/config
```

- `<discovery_prefix>`: The Discovery Prefix defaults to `homeassistant` and this prefix can be changed.
- `<component>`: One of the supported MQTT integrations, e.g., `binary_sensor`, or `device` in case of a device discovery.
- `<node_id>`: (Optional): ID of the node providing the topic, this is not used by Home Assistant but may be used to structure the MQTT topic. The ID of the node must only consist of characters from the character class `[a-zA-Z0-9_-]` (alphanumerics, underscore and hyphen).
- `<object_id>`: The ID of the device. This is only to allow for separate topics for each device and is not used for the `entity_id`. The ID of the device must only consist of characters from the character class `[a-zA-Z0-9_-]` (alphanumerics, underscore and hyphen).

The `<node_id>` level can be used by clients to only subscribe to their own (command) topics by using one wildcard topic like `<discovery_prefix>/+/<node_id>/+/set`.

Best practice for entities with a `unique_id` is to set `<object_id>` to `unique_id` and omit the `<node_id>`.

#### Device discovery payload

A device can send a discovery payload to expose all components for a device. The `<component>` part in the discovery topic must be set to `device`.

As an alternative, it is also possible a device can send a discovery payload for each component it wants to set up.

The shared options at the root level of the JSON message must include:

- `device` mapping (abbreviated as `dev`)
- `origin` mapping (abbreviated as `o`)

These mappings are mandatory and cannot be overridden at the entity/component level.

Supported shared options are:

- The availability options
- The origin (required) options
- `command_topic`
- `state_topic`
- `qos`
- `encoding`

The component specific options are placed as mappings under the `components` key (abbreviated as `cmps`) like:

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
    "name":"bla2mqtt",
    "sw": "2.1",
    "url": "<https://bla2mqtt.example.com/support>"
  },
  "cmps": {
    "some_unique_component_id1": {
      "p": "sensor",
      "device_class":"temperature",
      "unit_of_measurement":"°C",
      "value_template":"{{ value_json.temperature}}",
      "unique_id":"temp01ae_t"
    },
    "some_unique_id2": {
      "p": "sensor",
      "device_class":"humidity",
      "unit_of_measurement":"%",
      "value_template":"{{ value_json.humidity}}",
      "unique_id":"temp01ae_h"
    }
  },
  "state_topic":"sensorBedroom/state",
  "qos": 2
}
```

The components id's under the `components` (`cmps`) key, are used as part of the discovery identification. A `platform` (`p`) config option is required for each component config that is added to identify the component platform. Also required is a `unique_id` for entity-based components.

To remove the components, publish an empty (retained) string payload to the discovery topic. This will remove the component and clear the published discovery payload. It will also remove the device entry if there are no further references to it.

An empty config can be published as an update to remove a single component from the device discovery. Note that adding the `platform` (`p`) option is still required.

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
    "name":"bla2mqtt",
    "sw": "2.1",
    "url": "<https://bla2mqtt.example.com/support>"
  },
  "cmps": {
    "some_unique_component_id1": {
      "p": "sensor",
      "device_class":"temperature",
      "unit_of_measurement":"°C",
      "value_template":"{{ value_json.temperature}}",
      "unique_id":"temp01ae_t"
    },
    "some_unique_id2": {
      "p": "sensor"
    }
  },
  "state_topic":"sensorBedroom/state",
  "qos": 2
}
```

This will explicitly remove the humidity sensor and its entry.

After removing a component, you should send another update with the removed component omitted from the configuration. This ensures that Home Assistant has the most up-to-date device configuration. For example:

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
    "name":"bla2mqtt",
    "sw": "2.1",
    "url": "<https://bla2mqtt.example.com/support>"
  },
  "cmps": {
    "some_unique_component_id1": {
      "p": "sensor",
      "device_class":"temperature",
      "unit_of_measurement":"°C",
      "value_template":"{{ value_json.temperature}}",
      "unique_id":"temp01ae_t"
    }
  },
  "state_topic":"sensorBedroom/state",
  "qos": 2
}
```

A component config part in a device discovery payload must have the `platform` (`p`) option set with the name of the component and also must have at least one component specific config option. Entity components must have set the `unique_id` option and have a device context.

#### Migration from single component to device-based discovery

To allow a smooth migration from single component discovery to device-based discovery:

1. Ensure all entities have a `unique_id` and a device context
2. Move the `object_id` inside the discovery payload, if that is available, or use a unique ID or the component
3. Consider using the previous `node_id` as the new `object_id` of the device discovery topic
4. Ensure the `unique_id` matches and the device context has the correct identifiers
5. Send the following payload to all existing single component discovery topics: `{"migrate_discovery": true }`. This will unload the discovered item, but its settings will be retained
6. Switch the discovery topic to the device-based discovery topic and include all the component configurations
7. Clean up the single component discovery messages with an empty payload

During the migration steps, INFO messages will be logged to inform you about the progress of the migration.

> **Important**: Consider testing the migration process in a non-production environment before applying it to a live system.

#### Discovery migration example with a device automation and a sensor

##### Step 1: Original single component discovery configurations

**Discovery topic single**: `homeassistant/device_automation/0AFFD2/bla1/config`

**Discovery id**: `0AFFD2 bla1` (both 0AFFD2 and bla1 from the discovery topic)

**Discovery payload single**:

```json
```json
{
  "device": {
    "identifiers": ["0AFFD2"],
    "name": "Test device"
  },
  "o": {
    "name": "foobar"
  },
  "automation_type": "trigger",
  "payload": "short_press",
  "topic": "foobar/triggers/button1",
  "type": "button_short_press",
  "subtype": "button_1"
}
```

**Discovery topic single**: `homeassistant/sensor/0AFFD2/bla2/config`

**Discovery id**: `0AFFD2 bla2` (both 0AFFD2 and bla2 from the discovery topic)

**Discovery payload single**:

```json
{
  "device": {
    "identifiers": ["0AFFD2"],
    "name": "Test device"
  },
  "o": {
    "name": "foobar"
  },
  "state_topic": "foobar/sensor/sensor1",
  "unique_id": "bla_sensor001"
}
```
```

##### Step 2: Initiate migration by publishing to both discovery topics

When these single component discovery payloads are processed, and we want to initiate migration to a device-based discovery, we need to publish:

```json
{"migrate_discovery": true }
```

To both discovery topics:

- `homeassistant/device_automation/0AFFD2/bla1/config`
- `homeassistant/sensor/0AFFD2/bla2/config`

> **Important**: Check the logs to ensure this step is executed correctly.

##### Step 3: Publish the new device-based discovery configuration

**Discovery topic device**: `homeassistant/device/0AFFD2/config`

**Discovery id**: `0AFFD2 bla` (0AFFD2 from discovery topic, bla: The key under cmps in the discovery payload)

**Discovery payload device**:

```json
{
  "device": {
    "identifiers": [
      "0AFFD2"
    ]
  },
  "o": {
    "name": "foobar"
  },
  "cmps": {
    "bla1": {
      "p": "device_automation",
      "automation_type": "trigger",
      "payload": "short_press",
      "topic": "foobar/triggers/button1",
      "type": "button_short_press",
      "subtype": "button_1"
    },
    "bla2": {
      "p": "sensor",
      "state_topic": "foobar/sensor/sensor1",
      "unique_id": "bla_sensor001"
    }
  }
}
```

> **Important**: Check the logs to ensure the migration was successful.

##### Step 4: Clean up after successful migration

After the logs show a successful migration, the single component discovery topics can be cleaned up safely by publishing an empty payload to them. The logs should indicate if the discovery migration was successful.

##### Optional: Rolling back the migration

To rollback, publish:

```json
{"migrate_discovery": true }
```

To the device-based discovery topic(s). After that, re-publish the single component discovery payloads. At last, clean up the device-based discovery payloads by publishing an empty payload.

Check the logs for every step.

#### Single component discovery payload

The `<component>` part in the discovery topic must be one of the supported MQTT-platforms. The options in the payload are only used to set up one specific component. If there are more components, more discovery payloads need to be sent for the other components, and it is then recommended to use device-based discovery instead.

**Example discovery payload**:

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
    "name":"bla2mqtt",
    "sw": "2.1",
    "url": "<https://bla2mqtt.example.com/support>"
  },
  "device_class":"temperature",
  "unit_of_measurement":"°C",
  "value_template":"{{ value_json.temperature}}",
  "unique_id":"temp01ae_t",
  "state_topic":"sensorBedroom/state",
  "qos": 2
}
```

To remove the component, publish an empty string to the discovery topic. This will remove the component and clear the published discovery payload. It will also remove the device entry if there are no further references to it.

#### Discovery payload

The payload must be a serialized JSON dictionary and will be checked like an entry in your `configuration.yaml` file if a new device is added, with the exception that unknown configuration keys are allowed but ignored. This means that missing variables will be filled with the integration’s default values. All configuration variables which are required must be present in the payload. The reason for allowing unknown documentation keys is allow some backwards compatibility, software generating MQTT discovery messages can then be used with older Home Assistant versions which will simply ignore new features.

A discovery payload can be sent with a retain flag set. In that case, the discovery message will be stored at the MQTT broker and processed automatically when the MQTT integrations start. This method removes the need for it to be resent. A better approach, though, is for the software generating MQTT discovery messages to send discovery payload(s) when the MQTT integration sends the Birth message.

Subsequent messages on a topic where a valid payload has been received will be handled as a configuration update, and a configuration update with an empty payload will cause a previously discovered device to be deleted.

A base topic ~ may be defined in the payload to conserve memory when the same topic base is used multiple times. In the value of configuration variables ending with _topic, ~ will be replaced with the base topic, if the ~ occurs at the beginning or end of the value.

Configuration variable names in the discovery payload may be abbreviated to conserve memory when sending a discovery message from memory constrained devices.

It is recommended to add information about the origin of MQTT entities by including the `origin` option (abbreviated as `o`) in the discovery payload. For device-based discovery, this information is required. The origin details will be logged in the core event log when an item is discovered or updated. Adding origin information helps with troubleshooting and provides valuable context about the source of MQTT messages in your Home Assistant setup.

> **Note**: These options also support abbreviations, as shown in the table below.

**Origin options:**

- **`name`** (required): The name of the application that is the origin of the discovered MQTT item
- **`sw_version`** (optional): Software version of the application that supplies the discovered MQTT item
- **`support_url`** (optional): Support URL of the application that supplies the discovered MQTT item

#### Supported abbreviations in MQTT discovery messages

- Supported abbreviations for MQTT components
- Supported abbreviations for device registry configuration  
- Supported abbreviations for origin info

### Discovery messages and availability

When MQTT discovery is set up, and a device or service sends a discovery message, an MQTT entity, tag, or device automation will be set up directly after receiving the message. When Home Assistant is restarting, discovered MQTT items with a unique ID will be unavailable until a new discovery message is received. MQTT items without a unique ID will not be added at startup. So a device or service using MQTT discovery must make sure a configuration message is offered after the MQTT integration has been (re)started. There are 2 common approaches to make sure the discovered items are set up at startup:

#### Using Birth and Will messages to trigger discovery

When the MQTT integration starts, a birth message is published at `homeassistant/status` by default. A device or service connected to the shared mqtt broker can subscribe to this topic and use an online message to trigger discovery messages. See also the birth and last will messages section. After the configs have been published, the state topics will need an update, so they need to be republished.

#### Using retained config messages

An alternative method for a device or service is to publish discovery messages with a retain flag. This will make sure discovery messages are replayed when the MQTT integration connects to the broker. After the configs have been published, the state topics will need an update.

#### Using retained state messages

State updates also need to be re-published after a config as been processed. This can also be done by publishing retained messages. As soon as a config is received (or replayed from a retained message), the setup will subscribe any state topics. If a retained message is available at a state topic, this message will be replayed so that the state can be restored for this topic.

> **Warning**: A disadvantage of using retained messages is that these messages retain at the broker, even when the device or service stops working. They are retained even after the system or broker has been restarted. Retained messages can create ghost entities that keep coming back.
> 
> Especially when you have many entities, (unneeded) discovery messages can cause excessive system load. For this reason, use discovery messages with caution.

#### Using Availability topics

A device or service can announce its availability by publishing a Birth message and set a Will message at the broker. When the device or service loses connection to the broker, the broker will publish the Will message. This allows the MQTT integration to make an entity unavailable.

Platform specific availability settings are available for mqtt entity platforms only.

### Discovery examples with component discovery

#### Motion detection (binary sensor)

A motion detection device which can be represented by a binary sensor for your garden would send its configuration as JSON payload to the Configuration topic. After the first message to config, then the MQTT messages sent to the state topic will update the state in Home Assistant.

**Configuration topic**: `homeassistant/binary_sensor/garden/config`

**State topic**: `homeassistant/binary_sensor/garden/state`

**Configuration payload with derived device name**:

```json
{
   "name":null,
   "device_class":"motion",
   "state_topic":"homeassistant/binary_sensor/garden/state",
   "unique_id":"motion01ad",
   "device":{
      "identifiers":[
         "01ad"
      ],
      "name":"Garden"
   }
}
```

> **Retain**: The `-r` switch is added to retain the configuration topic in the broker. Without this, the sensor will not be available after Home Assistant restarts.

It is also a good idea to add a unique_id to allow changes to the entity and a device mapping so we can group all sensors of a device together. We can set “name” to null if we want to inherit the device name for the entity. If we set an entity name, the friendly_name will be a combination of the device and entity name. If name is left away and a device_class is set, the entity name part will be derived from the device_class.

Example configuration payload with no name set and derived device_class name:

```json
{
   "name":null,
   "device_class":"motion",
   "state_topic":"homeassistant/binary_sensor/garden/state",
   "unique_id":"motion01ad",
   "device":{
      "identifiers":[
         "01ad"
      ],
      "name":"Garden"
   }
}
```

If no name is set, a default name will be set by MQTT (see the MQTT platform documentation).

To create a new sensor manually and with the name set to null to derive the device name “Garden”:

```json
{
   "name":null,
   "device_class":"motion",
   "state_topic":"homeassistant/binary_sensor/garden/state",
   "unique_id":"motion01ad",
   "device":{
      "identifiers":[
         "01ad"
      ],
      "name":"Garden"
   }
}
```

```bash
mosquitto_pub -r -h 127.0.0.1 -p 1883 -t "homeassistant/binary_sensor/garden/config" \
  -m '{"name": null, "device_class": "motion", "state_topic": "homeassistant/binary_sensor/garden/state", "unique_id": "motion01ad", "device": {"identifiers": ["01ad"], "name": "Garden" }}'
```

**Update the state**:

```bash
mosquitto_pub -h 127.0.0.1 -p 1883 -t "homeassistant/binary_sensor/garden/state" -m ON
```

**Delete the sensor** by sending an empty message:

```bash
mosquitto_pub -h 127.0.0.1 -p 1883 -t "homeassistant/binary_sensor/garden/config" -m ''
```

For more details please refer to the MQTT testing section.

#### Sensors

Setting up a sensor with multiple measurement values requires multiple consecutive configuration topic submissions.

**Configuration topic no1**: `homeassistant/sensor/sensorBedroomT/config`

**Configuration payload no1**:
```json
{
   "device_class":"temperature",
   "state_topic":"homeassistant/sensor/sensorBedroom/state",
   "unit_of_measurement":"°C",
   "value_template":"{{ value_json.temperature}}",
   "unique_id":"temp01ae",
   "device":{
      "identifiers":[
          "bedroom01ae"
      ],
      "name":"Bedroom",
      "manufacturer": "Example sensors Ltd.",
      "model": "Example Sensor",
      "model_id": "K9",
      "serial_number": "12AE3010545",
      "hw_version": "1.01a",
      "sw_version": "2024.1.0",
      "configuration_url": "<https://example.com/sensor_portal/config>"
   }
}
```

**Configuration topic no2**: `homeassistant/sensor/sensorBedroomH/config`

**Configuration payload no2**:

```json
{
   "device_class":"humidity",
   "state_topic":"homeassistant/sensor/sensorBedroom/state",
   "unit_of_measurement":"%",
   "value_template":"{{ value_json.humidity}}",
   "unique_id":"hum01ae",
   "device":{
      "identifiers":[
         "bedroom01ae"
      ]
   }
}
```

The sensor identifiers or connections option allows to set up multiple entities that share the same device.

> Note: If a device configuration is shared, then it is not needed to add all device details to the other entity configs. It is enough to add shared identifiers or connections to the device mapping for the other entity config payloads.

A common state payload that can be parsed with the value_template in the sensor configs:

```json
{
   "temperature":23.20,
   "humidity":43.70
}
```

#### Entities with command topics

Setting up a light, switch etc. is similar but requires a command_topic as mentioned in the MQTT switch documentation.

**Configuration topic**: `homeassistant/switch/irrigation/config`
**State topic**: `homeassistant/switch/irrigation/state`
**Command topic**: `homeassistant/switch/irrigation/set`
**Payload**:

```json
{
   "name":"Irrigation",
   "command_topic":"homeassistant/switch/irrigation/set",
   "state_topic":"homeassistant/switch/irrigation/state",
   "unique_id":"irr01ad",
   "device":{
      "identifiers":[
         "garden01ad"
      ],
      "name":"Garden"
   }
}
```

**Retain**: The -r switch is added to retain the configuration topic in the broker. Without this, the sensor will not be available after Home Assistant restarts.

```bash
mosquitto_pub -r -h 127.0.0.1 -p 1883 -t "homeassistant/switch/irrigation/config" \
  -m '{"name": "Irrigation", "command_topic": "homeassistant/switch/irrigation/set", "state_topic": "homeassistant/switch/irrigation/state", "unique_id": "irr01ad", "device": {"identifiers": ["garden01ad"], "name": "Garden" }}'
```

Set the state:

```bash
mosquitto_pub -h 127.0.0.1 -p 1883 -t "homeassistant/switch/irrigation/set" -m ON
```

Using abbreviations and base topic
Setting up a switch using topic prefix and abbreviated configuration variable names to reduce payload length.

Configuration topic: homeassistant/switch/irrigation/config
Command topic: homeassistant/switch/irrigation/set
State topic: homeassistant/switch/irrigation/state
Configuration payload:
{
   "~":"homeassistant/switch/irrigation",
   "name":"garden",
   "cmd_t":"~/set",
   "stat_t":"~/state"
}
JSON

Another example using abbreviations topic name and base topic
Setting up a light that takes JSON payloads, with abbreviated configuration variable names:

Configuration topic: homeassistant/light/kitchen/config

Command topic: homeassistant/light/kitchen/set

State topic: homeassistant/light/kitchen/state

Example state payload: {"state": "ON", "brightness": 255}

Configuration payload:

{
  "~": "homeassistant/light/kitchen",
  "name": "Kitchen",
  "uniq_id": "kitchen_light",
  "cmd_t": "~/set",
  "stat_t": "~/state",
  "schema": "json",
  "brightness": true
}
JSON

Example with using abbreviated Device and Origin info in discovery messages
{
  "~": "homeassistant/light/kitchen",
  "name": null,
  "uniq_id": "kitchen_light",
  "cmd_t": "~/set",
  "stat_t": "~/state",
  "schema": "json",
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
    "name":"bla2mqtt",
    "sw": "2.1",
    "url": "<https://bla2mqtt.example.com/support>"
  }
}
JSON

Use object_id to influence the entity id
The entity id is automatically generated from the entity’s name. All MQTT integrations optionally support providing an object_id which will be used instead if provided.

Configuration topic: homeassistant/sensor/device1/config
Example configuration payload:
{
  "name":"My Super Device",
  "object_id":"my_super_device",
  "state_topic": "homeassistant/sensor/device1/state"
 }
JSON

In the example above, the entity_id will be sensor.my_super_device instead of sensor.device1.

Support by third-party tools
The following software has built-in support for MQTT discovery:

ArduinoHA
Arilux AL-LC0X LED controllers
ble2mqtt
diematic_server
digitalstrom-mqtt
ebusd
ecowitt2mqtt
EMS-ESP32 (and EMS-ESP)
ESPHome
ESPurna
go-iotdevice
HASS.Agent
IOTLink (starting with 2.0.0)
MiFlora MQTT Daemon
MyElectricalData
MqDockerUp
Nuki Hub
Nuki Smart Lock 3.0 Pro, more info
OpenMQTTGateway
OTGateway
room-assistant (starting with 1.1.0)
SmartHome
SpeedTest-CLI MQTT
SwitchBot-MQTT-BLE-ESP32
Tasmota (starting with 5.11.1e, development halted)
TeddyCloud
Teleinfo MQTT (starting with 3.0.0)
Tydom2MQTT
What’s up Docker? (starting with 3.5.0)
WyzeSense2MQTT
Xiaomi DaFang Hacks
Zehnder Comfoair RS232 MQTT
Zigbee2MQTT
The following software also supports consuming MQTT discovery information that is intended for Home Assistant. Compatibility and features will vary, and not all devices may work.

Domoticz
openHAB
Manual configured MQTT items
Support to allow adding manual items as a subentry via a config flow, is work in progress. Not all entity platforms are supported yet.

For most integrations, it is also possible to manually set up MQTT items in configuration.yamlThe configuration.yaml file is the main configuration file for Home Assistant. It lists the integrations to be loaded and their specific configurations. In some cases, the configuration needs to be edited manually directly in the configuration.yaml file. Most integrations can be configured in the UI. [Learn more]. Read more about configuration in YAML.

MQTT supports two styles for configuring items in YAML. All configuration items are placed directly under the mqtt integration key. Note that you cannot mix these styles. Use the YAML configuration listed per item style when in doubt.

#### YAML configuration listed per item

This method expects all items to be in a YAML list. Each item has a `{domain}` key and the item config is placed directly under the domain key. This method is considered as best practice. In all the examples we use this format.

```yaml
mqtt:
  - {domain}:
      name: ""
      # ...
  - {domain}:
      name: ""
      # ...
```

#### YAML configuration keyed and bundled by {domain}

All items are grouped per `{domain}` and where all configs are listed.

```yaml
mqtt:
  {domain}:
    - name: ""
      # ...
    - name: ""
      # ...
```

If you have a large number of manually configured items, you might want to consider splitting up the configuration.

Entity state updates
Entities receive state updates via MQTT subscriptions. The payloads received on the state topics are processed to determine whether there is a significant change. If a change is detected, the entity will be updated.

Note that MQTT device payloads often contain information for updating multiple entities that subscribe to the same topics. For example, a light status update might include information about link quality. This data can update a link quality sensor but is not used to update the light itself. MQTT filters out entity state updates when there are no changes.

The last reported state attribute
Because MQTT state updates are often repeated frequently, even when no actual changes exist, it is up to the MQTT subscriber to determine whether a status update was received. If the latest update is missed, it might take some time before the next one arrives. If a retained payload exists at the broker, that value will be replayed first, but it will be an update of a previous last state.

MQTT devices often continuously generate numerous state updates. MQTT does not update last_reported to avoid impacting system stability unless force_update is set. Alternatively, an MQTT sensor can be created to measure the last update.

Using Templates
The MQTT integration supports templating. Read more about using templates with the MQTT integration.

Examples
### REST API

Using the REST API to send a message to a given topic.

### Automations

Use as script in automations.

```yaml
automation:
  alias: "Send me a message when I get home"
  triggers:
    - trigger: state
      entity_id: device_tracker.me
      to: "home"
  actions:
    - action: script.notify_mqtt
      data:
        target: "me"
        message: "I'm home"

script:
  notify_mqtt:
    sequence:
      - action: mqtt.publish
        data:
          payload: "{{ message }}"
          topic: home/"{{ target }}"
          retain: true
```

### Publish & Dump actions

The MQTT integration will register the `mqtt.publish` action, which allows publishing messages to MQTT topics.

#### Action mqtt.publish

| Data attribute | Optional | Description |
|---|---|---|
| `topic` | no | Topic to publish payload to |
| `payload` | yes | Payload to publish. Will publish an empty payload when payload is omitted |
| `evaluate_payload` | yes | If a bytes literal in payload should be evaluated to publish raw data. (default: false) |
| `qos` | yes | Quality of Service to use. (default: 0) |
| `retain` | yes | If message should have the retain flag set. (default: false) |

> **Note**: When payload is rendered from template in a YAML script or automation, and the template renders to a bytes literal, the outgoing MQTT payload will only be sent as raw data, if the `evaluate_payload` option flag is set to `true`.

```yaml
topic: homeassistant/light/1/command
payload: on
```

```yaml
topic: homeassistant/light/1/state
payload: "{{ states('device_tracker.paulus') }}"
```

```yaml
topic: "homeassistant/light/{{ states('sensor.light_active') }}/state"
payload: "{{ states('device_tracker.paulus') }}"
```

Be aware that payload must be a string. If you want to send JSON using the YAML editor then you need to format/escape it properly. Like:

topic: homeassistant/light/1/state
payload: "{\"Status\":\"off\", \"Data\":\"something\"}"`
YAML

The example below shows how to publish a temperature sensor ‘Bathroom Temperature’. The device_class is set, so it is not needed to set the “name” option. The entity will inherit the name from the device_class set and also support translations. If you set “name” in the payload the entity name will start with the device name.

action: mqtt.publish
data:
  topic: homeassistant/sensor/Acurite-986-1R-51778/config
  payload: >-
    {"device_class": "temperature",
    "unit_of_measurement": "\u00b0C",
    "value_template": "{{ value|float }}",
    "state_topic": "rtl_433/rtl433/devices/Acurite-986/1R/51778/temperature_C",
    "unique_id": "Acurite-986-1R-51778-T",
    "device": {
    "identifiers": "Acurite-986-1R-51778",
    "name": "Bathroom",
    "model": "Acurite",
    "model_id": "986",
    "manufacturer": "rtl_433" }
    }
YAML

Example of how to use qos and retain:

```yaml
topic: homeassistant/light/1/command
payload: on
qos: 2
retain: true
```

#### Action mqtt.dump

Listen to the specified topic matcher and dumps all received messages within a specific duration into the file `mqtt_dump.txt` in your configuration folder. This is useful when debugging a problem.

| Data attribute | Optional | Description |
|---|---|---|
| `topic` | no | Topic to dump. Can contain a wildcard (`#` or `+`) |
| `duration` | yes | Duration in seconds that we will listen for messages. Default is 5 seconds |

```yaml
topic: zigbee2mqtt/#
```

## Logging

The logger integration allows the logging of received MQTT messages.

```yaml
# Example configuration.yaml entry
logger:
  default: warning
  logs:
    homeassistant.components.mqtt: debug
```

Event event_mqtt_reloaded
Event event_mqtt_reloaded is fired when Manually configured MQTT entities have been reloaded and entities thus might have changed.

This event has no additional data.

## Removing the integration

1. Go to **Settings > Devices & services** and select the integration card
2. From the list of devices, select the integration instance you want to remove
3. Next to the entry, select the three dots menu. Then, select **Delete**

> **Note**: This action does not remove the MQTT broker or its data. If you want to completely remove MQTT:
> 
> - Check your `configuration.yaml` and other YAML files for MQTT-related configurations and remove them
> - Review your automations and scripts for any MQTT dependencies
> - Consider backing up your configuration before making these changes
