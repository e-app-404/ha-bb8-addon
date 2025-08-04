#!/usr/bin/with-contenv bashio
set -e

# Load config from Home Assistant options.json (mounted at /data/options.json)
CONFIG_FILE="/data/options.json"
if [ ! -f "$CONFIG_FILE" ]; then
  echo "Config file not found: $CONFIG_FILE" >&2
  exit 1
fi

BB8_MAC=$(jq -r .bb8_mac $CONFIG_FILE)
MQTT_BROKER=$(jq -r .mqtt_broker $CONFIG_FILE)
MQTT_USERNAME=$(jq -r .mqtt_username $CONFIG_FILE)
MQTT_PASSWORD=$(jq -r .mqtt_password $CONFIG_FILE)
MQTT_TOPIC_PREFIX=$(jq -r .mqtt_topic_prefix $CONFIG_FILE)
BLE_ADAPTER=$(jq -r .ble_adapter $CONFIG_FILE)

export BB8_MAC
export MQTT_BROKER
export MQTT_USERNAME
export MQTT_PASSWORD
export MQTT_TOPIC_PREFIX
export BLE_ADAPTER

# Start the Python service
exec python3 -m src.ha_sphero_bb8
