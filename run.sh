#!/bin/sh
set -e

VERSION="0.3.1"  # Update this manually per release/rebuild

# Load config from Home Assistant options.json (mounted at /data/options.json)
CONFIG_FILE="/data/options.json"
if [ ! -f "$CONFIG_FILE" ]; then
  echo "Config file not found: $CONFIG_FILE" >&2
  exit 1
fi

BB8_MAC=$(jq -r .bb8_mac "$CONFIG_FILE")
MQTT_BROKER=$(jq -r .mqtt_broker "$CONFIG_FILE")
MQTT_USERNAME=$(jq -r .mqtt_username "$CONFIG_FILE")
MQTT_PASSWORD=$(jq -r .mqtt_password "$CONFIG_FILE")
MQTT_TOPIC_PREFIX=$(jq -r .mqtt_topic_prefix "$CONFIG_FILE")
BLE_ADAPTER=$(jq -r .ble_adapter "$CONFIG_FILE")

export BB8_MAC
export MQTT_BROKER
export MQTT_USERNAME
export MQTT_PASSWORD
export MQTT_TOPIC_PREFIX
export BLE_ADAPTER

export PYTHONPATH=/app

# Parse MQTT_BROKER (URL or host:port) to set MQTT_HOST and MQTT_PORT
parse_mqtt_url() {
  url="$1"
  # Remove mqtt:// if present
  url_no_proto="${url#mqtt://}"
  # If contains colon, split host:port
  if echo "$url_no_proto" | grep -q ':'; then
    host="${url_no_proto%%:*}"
    port="${url_no_proto##*:}"
  else
    host="$url_no_proto"
    port="1883"
  fi
  export MQTT_HOST="$host"
  export MQTT_PORT="$port"
}

parse_mqtt_url "$MQTT_BROKER"

export MQTT_USER="$MQTT_USERNAME"
export MQTT_PASSWORD="$MQTT_PASSWORD"
export MQTT_TOPIC="${MQTT_TOPIC_PREFIX}/command"
export STATUS_TOPIC="${MQTT_TOPIC_PREFIX}/status"

echo "==== BB-8 Add-on Startup ===="
echo "Version: $VERSION"
echo "Build Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Container Started: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "============================="
echo "BB8_MAC: $BB8_MAC"
echo "MQTT_BROKER: $MQTT_BROKER"
echo "MQTT_USERNAME: $MQTT_USERNAME"
echo "MQTT_TOPIC_PREFIX: $MQTT_TOPIC_PREFIX"
echo "BLE_ADAPTER: $BLE_ADAPTER"
echo "Python version: $(python3 --version 2>&1)"
echo "Python path: $(which python3)"
echo "Current working directory: $(pwd)"
echo "Running as user: $(id -u -n) (UID: $(id -u))"
echo "Contents of /app:"
ls -l /app
echo "Contents of /app/bb8_core:"
ls -l /app/bb8_core
echo "============================="

echo "[BB-8] Running BLE adapter check..."
python3 /app/test_ble_adapter.py

# Start the Python service
exec python3 -m bb8_core.bridge_controller
